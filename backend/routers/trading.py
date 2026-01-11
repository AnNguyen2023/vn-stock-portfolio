# routers/trading.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime
from sqlalchemy import desc

import models
import schemas
from core.db import get_db
from core.cache import invalidate_dashboard_cache
from core.logger import logger
from core.exceptions import ValidationError, EntityNotFoundException
from services.market_service import sync_historical_task

router = APIRouter(
    tags=["Trading"],
)

@router.post("/buy")
def buy_stock(req: schemas.BuyStockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Executes a buy order. Validates ticker, cash balance, and updates holdings.
    """
    ticker = req.ticker.strip().upper()
    volume = Decimal(str(req.volume))
    price_vnd = Decimal(str(req.price))

    # 1. Validate Ticker
    security = db.query(models.Security).filter_by(symbol=ticker).first()
    if not security:
        raise EntityNotFoundException("Security/Ticker", ticker)

    # 2. Check Balance
    total_value = volume * price_vnd
    fee = total_value * Decimal(str(req.fee_rate))
    total_cost = total_value + fee

    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < total_cost:
        deficit = float(total_cost - asset.cash_balance)
        raise ValidationError(f"Insufficient funds. Need {deficit:,.0f} VNĐ more.")

    # 3. Update Holdings (Weighted Average Cost)
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    if holding:
        new_vol = holding.total_volume + volume
        current_total_cost = holding.total_volume * holding.average_price
        holding.average_price = (current_total_cost + total_cost) / new_vol
        holding.total_volume = new_vol
        holding.available_volume = new_vol
        holding.liquidated_at = None
    else:
        holding = models.TickerHolding(
            ticker=ticker,
            total_volume=volume,
            available_volume=volume,
            average_price=(total_cost / volume),
        )
        db.add(holding)

    # 4. Record Transaction and Cashflow
    asset.cash_balance -= total_cost
    db.add(models.CashFlow(
        type=models.CashFlowType.WITHDRAW, 
        amount=total_cost, 
        description=f"Buy {int(volume):,} {ticker}"
    ))
    db.add(models.StockTransaction(
        ticker=ticker, 
        type=models.TransactionType.BUY, 
        volume=volume, 
        price=price_vnd, 
        fee=fee, 
        total_value=total_cost, 
        note=req.note
    ))

    db.commit()
    logger.info(f"Trade Executed [BUY]: {int(volume):,} {ticker} @ {price_vnd:,.0f}. Total: {total_cost:,.0f}")
    
    invalidate_dashboard_cache()
    background_tasks.add_task(sync_historical_task, ticker, "1y")

    return {
        "success": True, 
        "message": f"Bought {int(volume):,} {ticker} ({security.full_name})",
        "data": {"ticker": ticker, "volume": float(volume), "price": float(price_vnd)}
    }

@router.post("/sell")
def sell_stock(req: schemas.SellStockRequest, db: Session = Depends(get_db)):
    """
    Executes a sell order. Validates available volume and calculates realized profit/loss.
    """
    ticker = req.ticker.upper()
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    if not holding or holding.total_volume < req.volume:
        available = float(holding.total_volume) if holding else 0
        raise ValidationError(f"Insufficient volume for {ticker}. Available: {available:,.0f}")

    volume_to_sell = Decimal(str(req.volume))
    price_vnd = Decimal(str(req.price))

    # Revenue minus fees/taxes
    gross_revenue = volume_to_sell * price_vnd
    fee = gross_revenue * Decimal(str(req.fee_rate))
    tax = gross_revenue * Decimal(str(req.tax_rate))
    net_proceeds = gross_revenue - fee - tax

    # Profit Calculation (FIFO/Average Cost based on average_price)
    cost_basis = volume_to_sell * holding.average_price
    profit = net_proceeds - cost_basis

    # Update Holding
    holding.total_volume -= volume_to_sell
    holding.available_volume = holding.total_volume
    if holding.total_volume <= 0:
        holding.liquidated_at = datetime.now()
        holding.average_price = 0

    # Record Transactions
    asset = db.query(models.AssetSummary).first()
    asset.cash_balance += net_proceeds
    
    db.add(models.CashFlow(
        type=models.CashFlowType.DEPOSIT, 
        amount=net_proceeds, 
        description=f"Sell {int(volume_to_sell):,} {ticker}"
    ))
    db.add(models.StockTransaction(
        ticker=ticker, 
        type=models.TransactionType.SELL, 
        volume=volume_to_sell, 
        price=price_vnd, 
        fee=fee, 
        tax=tax, 
        total_value=net_proceeds, 
        note=req.note
    ))
    db.add(models.RealizedProfit(
        ticker=ticker, 
        volume=volume_to_sell, 
        buy_avg_price=holding.average_price if holding.total_volume > 0 else (cost_basis/volume_to_sell), 
        sell_price=price_vnd, 
        net_profit=profit
    ))

    db.commit()
    logger.info(f"Trade Executed [SELL]: {int(volume_to_sell):,} {ticker} @ {price_vnd:,.0f}. Net Profit: {profit:,.0f}")
    
    invalidate_dashboard_cache()

    return {
        "success": True, 
        "message": f"Sold {int(volume_to_sell)} {ticker}",
        "data": {"profit": float(profit), "net_proceeds": float(net_proceeds)}
    }

@router.post("/undo-last-buy")
def undo_last_buy(db: Session = Depends(get_db)):
    """
    Reverts the most recent buy transaction.
    """
    last_tx = (
        db.query(models.StockTransaction)
        .filter(models.StockTransaction.type == models.TransactionType.BUY)
        .order_by(desc(models.StockTransaction.id))
        .first()
    )
    if not last_tx:
        raise ValidationError("No buy transaction to revert.")

    asset = db.query(models.AssetSummary).first()
    holding = db.query(models.TickerHolding).filter_by(ticker=last_tx.ticker).first()

    try:
        if asset:
            asset.cash_balance += Decimal(str(last_tx.total_value))
        if holding:
            if holding.total_volume <= last_tx.volume:
                db.delete(holding)
            else:
                curr_total_cost = holding.total_volume * holding.average_price
                new_vol = holding.total_volume - last_tx.volume
                new_cost = curr_total_cost - Decimal(str(last_tx.total_value))
                holding.total_volume = new_vol
                holding.available_volume = new_vol
                holding.average_price = new_cost / new_vol

        # Find linked cashflow and delete
        cash_log = (
            db.query(models.CashFlow)
            .filter(models.CashFlow.description.contains(last_tx.ticker))
            .order_by(desc(models.CashFlow.id))
            .first()
        )
        if cash_log:
            db.delete(cash_log)

        db.delete(last_tx)
        db.commit()
        logger.info(f"Undo completed for {last_tx.ticker} transaction ID: {last_tx.id}")
        
        invalidate_dashboard_cache()
        return {"success": True, "message": f"Reverted buy order for {last_tx.ticker}."}

    except Exception as e:
        db.rollback()
        logger.error(f"Undo operation failed: {e}")
        raise ValidationError(f"Could not undo transaction: {str(e)}")