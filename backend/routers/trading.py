# routers/trading.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime

from sqlalchemy import desc

import models
import schemas
from core.db import get_db
from core.cache import invalidate_dashboard_cache
from services.market_service import sync_historical_task

router = APIRouter(
    tags=["Trading"],
    responses={404: {"description": "Not found"}},
)

def raise_error(message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=message)


@router.post("/buy")
def buy_stock(req: schemas.BuyStockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ticker = req.ticker.strip().upper()
    volume = Decimal(str(req.volume))
    price_vnd = Decimal(str(req.price))

    # 0. VALIDATE TICKER AGAINST MASTER LIST
    security = db.query(models.Security).filter_by(symbol=ticker).first()
    if not security:
        raise_error(f"Mã chứng khoán '{ticker}' không hợp lệ hoặc không thuộc danh sách niêm yết được phép (HOSE/HNX/UPCOM).")

    # 1. CHECK CASH BALANCE
    total_value = volume * price_vnd
    fee = total_value * Decimal(str(req.fee_rate))
    total_cost = total_value + fee

    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < total_cost:
        raise_error(f"Thiếu {float(total_cost - asset.cash_balance):,.0f} VND")

    # 2. UPDATE HOLDINGS
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

    # 3. RECORD TRANSACTIONS & CASHFLOW
    asset.cash_balance -= total_cost
    db.add(models.CashFlow(type=models.CashFlowType.WITHDRAW, amount=total_cost, description=f"Mua {int(volume):,} {ticker}"))
    db.add(models.StockTransaction(ticker=ticker, type=models.TransactionType.BUY, volume=volume, price=price_vnd, fee=fee, total_value=total_cost, note=req.note))

    db.commit()

    # clear cache dashboard
    invalidate_dashboard_cache()

    # Auto sync historical data for the new ticker (1 year)
    background_tasks.add_task(sync_historical_task, ticker, "1y")

    return {"message": f"Định danh: {security.full_name} - Đã khớp lệnh mua {int(volume)} {ticker}"}


@router.post("/sell")
def sell_stock(req: schemas.SellStockRequest, db: Session = Depends(get_db)):
    ticker = req.ticker.upper()
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    if not holding or holding.total_volume < req.volume:
        raise_error(f"Không đủ {ticker} để bán")

    volume_to_sell = Decimal(str(req.volume))
    price_vnd = Decimal(str(req.price))

    gross_revenue = volume_to_sell * price_vnd
    fee = gross_revenue * Decimal(str(req.fee_rate))
    tax = gross_revenue * Decimal(str(req.tax_rate))
    net_proceeds = gross_revenue - fee - tax

    cost_basis = volume_to_sell * holding.average_price
    profit = net_proceeds - cost_basis

    holding.total_volume -= volume_to_sell
    holding.available_volume = holding.total_volume
    if holding.total_volume <= 0:
        holding.liquidated_at = datetime.now()
        holding.average_price = 0

    asset = db.query(models.AssetSummary).first()
    asset.cash_balance += net_proceeds
    db.add(models.CashFlow(type=models.CashFlowType.DEPOSIT, amount=net_proceeds, description=f"Bán {int(volume_to_sell):,} {ticker}"))
    db.add(models.StockTransaction(ticker=ticker, type=models.TransactionType.SELL, volume=volume_to_sell, price=price_vnd, fee=fee, tax=tax, total_value=net_proceeds, note=req.note))
    db.add(models.RealizedProfit(ticker=ticker, volume=volume_to_sell, buy_avg_price=holding.average_price if holding.total_volume > 0 else (cost_basis/volume_to_sell), sell_price=price_vnd, net_profit=profit))

    db.commit()

    invalidate_dashboard_cache()

    return {"message": f"Đã bán {int(volume_to_sell)} {ticker}"}


@router.post("/undo-last-buy")
def undo_last_buy(db: Session = Depends(get_db)):
    last_tx = (
        db.query(models.StockTransaction)
        .filter(models.StockTransaction.type == models.TransactionType.BUY)
        .order_by(desc(models.StockTransaction.id))
        .first()
    )
    if not last_tx:
        raise_error("Không có gì để hoàn tác")

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

        invalidate_dashboard_cache()

        return {"message": f"Đã hủy lệnh mua {last_tx.ticker}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))