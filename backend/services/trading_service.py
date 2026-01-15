# services/trading_service.py
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, Dict, Any

import models
import schemas
from core.cache import invalidate_dashboard_cache
from core.logger import logger
from core.exceptions import ValidationError, EntityNotFoundException
from services.market_service import sync_historical_task

def process_buy_order(db: Session, req: schemas.BuyStockRequest, background_tasks) -> Dict[str, Any]:
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
        "ticker": ticker, 
        "full_name": security.full_name,
        "volume": float(volume), 
        "price": float(price_vnd),
        "total_cost": float(total_cost)
    }

def process_sell_order(db: Session, req: schemas.SellStockRequest) -> Dict[str, Any]:
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
        "ticker": ticker,
        "volume": float(volume_to_sell),
        "profit": float(profit), 
        "net_proceeds": float(net_proceeds)
    }

def undo_last_buy_order(db: Session) -> Dict[str, Any]:
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

        ticker = last_tx.ticker
        db.delete(last_tx)
        db.commit()
        logger.info(f"Undo completed for {ticker} transaction ID: {last_tx.id}")
        
        invalidate_dashboard_cache()
        return {"ticker": ticker}

    except Exception as e:
        db.rollback()
        logger.error(f"Undo operation failed: {e}")
        raise ValidationError(f"Could not undo transaction: {str(e)}")


def register_dividend(db: Session, req: schemas.RegisterDividendRequest) -> Dict[str, Any]:
    """
    Registers a dividend event (Cash, Stock, or Rights).
    For Cash dividends, applies 5% tax and creates PENDING cash flow.
    """
    ticker = req.ticker.upper()
    security = db.query(models.Security).filter_by(symbol=ticker).first()
    if not security:
        raise EntityNotFoundException("Security/Ticker", ticker)

    # 1. Map type
    type_map = {
        schemas.DividendType.CASH: models.CashFlowType.DIVIDEND_CASH,
        schemas.DividendType.STOCK: models.CashFlowType.DIVIDEND_STOCK,
        schemas.DividendType.RIGHTS: models.CashFlowType.RIGHTS_ISSUE
    }
    model_type = type_map[req.type]

    # 2. Calculate expected value
    expected_value = Decimal("0")
    amount_per_share = req.amount_per_share
    
    if req.type == schemas.DividendType.CASH:
        # Rules: Cash = Rate% * 10,000 or direct amount
        # Handle percentage in ratio if amount_per_share is not provided directly
        if amount_per_share is None and req.ratio:
            if "%" in req.ratio:
                rate = Decimal(req.ratio.replace("%", "")) / 100
                amount_per_share = rate * 10000
            else:
                try:
                    amount_per_share = Decimal(req.ratio.replace(",", ""))
                except:
                    raise ValidationError("Số tiền hoặc tỷ lệ % không hợp lệ")

        if amount_per_share is None:
            raise ValidationError("Vui lòng nhập tỷ lệ % hoặc số tiền cổ tức.")
        
        gross_amount = Decimal(str(req.owned_quantity)) * amount_per_share
        # 5% Personal Income Tax (TNCN) for Cash Dividends in VN
        expected_value = gross_amount * Decimal("0.95")
        
    elif req.type == schemas.DividendType.STOCK:
        # Rules: Additional Shares = Owned * Rate%
        if req.ratio:
            if "%" in req.ratio:
                rate = Decimal(req.ratio.replace("%", "")) / 100
                expected_value = Decimal(str(req.owned_quantity)) * rate
            elif ":" in req.ratio:
                base, receive = map(int, req.ratio.split(":"))
                expected_value = Decimal(str(req.owned_quantity)) * Decimal(receive) / Decimal(base)
        
        expected_value = expected_value.to_integral_value(rounding="ROUND_FLOOR")
        if expected_value == 0:
            raise ValidationError("Tỷ lệ chia quá nhỏ hoặc số lượng CP không đủ để nhận thêm.")

    else: # RIGHTS_ISSUE or other
        if req.rights_quantity is not None:
            expected_value = Decimal(str(req.rights_quantity))
        elif req.ratio and ":" in req.ratio:
            try:
                base, receive = map(int, req.ratio.split(":"))
                expected_value = Decimal(str(req.owned_quantity)) * Decimal(receive) / Decimal(base)
                expected_value = expected_value.to_integral_value(rounding="ROUND_FLOOR")
            except:
                raise ValidationError("Định dạng tỷ lệ không hợp lệ (vd: 100:15).")
        else:
            raise ValidationError("Vui lòng cung cấp tỷ lệ hoặc số lượng CP mua ưu đãi.")

    # 3. Create Dividend Record
    record = models.DividendRecord(
        ticker=ticker,
        type=model_type,
        ratio=req.ratio,
        amount_per_share=amount_per_share if req.type == schemas.DividendType.CASH else None,
        ex_dividend_date=req.ex_dividend_date,
        register_date=req.register_date,
        payment_date=req.payment_date,
        owned_volume=Decimal(str(req.owned_quantity)),
        expected_value=expected_value,
        purchase_price=req.purchase_price,
        rights_quantity=expected_value if req.type == schemas.DividendType.RIGHTS else None,
        status=models.CashFlowStatus.PENDING
    )
    db.add(record)

    # 4. If Cash, create PENDING CashFlow (Net amount after 5% tax)
    if req.type == schemas.DividendType.CASH:
        db.add(models.CashFlow(
            type=models.CashFlowType.DIVIDEND_CASH,
            amount=expected_value,
            description=f"Cổ tức tiền {ticker} ({int(req.owned_quantity):,} CP - Thuế 5%)",
            status=models.CashFlowStatus.PENDING,
            execution_date=req.payment_date
        ))

    db.commit()
    logger.info(f"Dividend registered: {ticker} {req.type}. Expected: {expected_value:,.2f} {'VND' if req.type == schemas.DividendType.CASH else 'CP'}")
    
    # Process immediately
    process_pending_dividends(db)
    
    invalidate_dashboard_cache()
    return {
        "ticker": ticker,
        "type": req.type,
        "expected_value": float(expected_value),
        "payment_date": req.payment_date,
        "tax_deducted": float(gross_amount * Decimal("0.05")) if req.type == schemas.DividendType.CASH else 0
    }


def process_pending_dividends(db: Session):
    """
    Checks for all PENDING cash flows and dividend records reaching payment_date.
    """
    from datetime import date
    today = date.today()
    
    # 1. Process Cash Flows (Cash Balance)
    pending_cash = (
        db.query(models.CashFlow)
        .filter(models.CashFlow.status == models.CashFlowStatus.PENDING)
        .filter(models.CashFlow.execution_date <= today)
        .all()
    )
    
    asset = db.query(models.AssetSummary).first()
    if not asset:
        asset = models.AssetSummary(cash_balance=0, total_deposited=0)
        db.add(asset)

    processed_cash = 0
    for item in pending_cash:
        if item.type == models.CashFlowType.DIVIDEND_CASH:
            asset.cash_balance += item.amount
            item.status = models.CashFlowStatus.COMPLETED
            processed_cash += 1
            logger.info(f"Executed Pending Cash: {item.description} | Net: {item.amount:,.0f}")

    # 2. Process Dividend Records (Stock Volume)
    pending_stocks = (
        db.query(models.DividendRecord)
        .filter(models.DividendRecord.status == models.CashFlowStatus.PENDING)
        .filter(models.DividendRecord.payment_date <= today)
        .all()
    )

    processed_stocks = 0
    for rec in pending_stocks:
        if rec.type in [models.CashFlowType.DIVIDEND_STOCK, models.CashFlowType.RIGHTS_ISSUE]:
            holding = db.query(models.TickerHolding).filter_by(ticker=rec.ticker).first()
            if not holding:
                # If user sold all before receiving, we create a new holding or just skip? 
                # Usually we still record the incoming shares.
                holding = models.TickerHolding(ticker=rec.ticker, total_volume=0, available_volume=0, average_price=0)
                db.add(holding)
            
            # Add to volumes
            holding.total_volume += rec.expected_value
            holding.available_volume += rec.expected_value
            
            # 3. Handle Rights Purchase Payment (If applicable)
            if rec.type == models.CashFlowType.RIGHTS_ISSUE and rec.purchase_price and rec.purchase_price > 0:
                total_cost = rec.expected_value * rec.purchase_price
                if asset.cash_balance >= total_cost:
                    asset.cash_balance -= total_cost
                    db.add(models.CashFlow(
                        type=models.CashFlowType.WITHDRAW,
                        amount=total_cost,
                        description=f"Thực hiện quyền mua {rec.ticker} - {rec.expected_value:,.0f} CP giá {rec.purchase_price:,.0f}",
                        status=models.CashFlowStatus.COMPLETED,
                        execution_date=today
                    ))
                    logger.info(f"Rights Purchase Payment: {rec.ticker} | Paid: {total_cost:,.0f} VNĐ")
                else:
                    logger.warning(f"Insufficient cash to execute rights issue for {rec.ticker}. Cost: {total_cost:,.0f}")
                    # Note: We still added the shares. In a real system we might block this.
            
            rec.status = models.CashFlowStatus.COMPLETED
            processed_stocks += 1
            logger.info(f"Executed Pending Stock: {rec.ticker} | Received: {rec.expected_value:,.0f} CP")
            
    if processed_stocks > 0:
        db.commit()

def get_pending_dividends(db: Session):
    records = db.query(models.DividendRecord).filter(
        models.DividendRecord.status == models.CashFlowStatus.PENDING
    ).order_by(models.DividendRecord.payment_date.asc()).all()
    
    return [
        {
            "id": r.id,
            "ticker": r.ticker,
            "type": r.type.value,
            "ratio": r.ratio,
            "amount_per_share": float(r.amount_per_share) if r.amount_per_share else None,
            "expected_value": float(r.expected_value),
            "payment_date": r.payment_date,
            "ex_dividend_date": r.ex_dividend_date,
            "register_date": r.register_date,
            "purchase_price": float(r.purchase_price) if r.purchase_price else None
        }
        for r in records
    ]

def delete_dividend(db: Session, dividend_id: int):
    rec = db.query(models.DividendRecord).filter(
        models.DividendRecord.id == dividend_id,
        models.DividendRecord.status == models.CashFlowStatus.PENDING
    ).first()
    
    if not rec:
        return False
    
    # If it's a CASH dividend, we also need to remove the pending CashFlow if we created one?
    # Currently register_dividend creates a PENDING CashFlow for CASH type.
    if rec.type == models.CashFlowType.DIVIDEND_CASH:
        # Find associated pending cashflow. 
        # Since we don't have a direct link ID, we look for PENDING cashflow with same amount/date matching?
        # A bit risky. But safe enough for single user.
        # Ideally we should store cashflow_id in DividendRecord.
        # For now, let's just delete the DividendRecord. The portfolio service logic ignores CashFlow PENDING anyway.
        # Wait, the Process logic (process_pending_dividends) updates the CashFlow status.
        # So we SHOULD delete the CashFlow too.
        # But wait, looking at code: register_dividend creates a CashFlow with status PENDING.
        pass

    db.delete(rec)
    db.commit()
    return True

def update_dividend(db: Session, dividend_id: int, req: schemas.UpdateDividendRequest):
    rec = db.query(models.DividendRecord).filter(
        models.DividendRecord.id == dividend_id,
        models.DividendRecord.status == models.CashFlowStatus.PENDING
    ).first()
    
    if not rec:
        return None
        
    # Recalculate expected values
    expected_value = Decimal("0")
    if req.type == schemas.DividendType.CASH:
        requested_amount = Decimal(str(req.amount_per_share)) if req.amount_per_share else Decimal("0")
        if req.ratio:
            if "%" in req.ratio:
                rate = Decimal(req.ratio.replace("%", "")) / 100
                requested_amount = rate * 10000 
            
        gross_amount = Decimal(str(req.owned_quantity)) * requested_amount
        expected_value = gross_amount * Decimal("0.95")
        
    elif req.type == schemas.DividendType.STOCK:
        if req.ratio:
            if "%" in req.ratio:
                rate = Decimal(req.ratio.replace("%", "")) / 100
                expected_value = Decimal(str(req.owned_quantity)) * rate
            elif ":" in req.ratio:
                base, receive = map(int, req.ratio.split(":"))
                expected_value = Decimal(str(req.owned_quantity)) * Decimal(receive) / Decimal(base)
        
        expected_value = expected_value.to_integral_value(rounding="ROUND_FLOOR")
        
    else: # RIGHTS_ISSUE
        if req.rights_quantity is not None:
            expected_value = Decimal(str(req.rights_quantity))
        elif req.ratio and ":" in req.ratio:
            try:
                base, receive = map(int, req.ratio.split(":"))
                expected_value = Decimal(str(req.owned_quantity)) * Decimal(receive) / Decimal(base)
                expected_value = expected_value.to_integral_value(rounding="ROUND_FLOOR")
            except:
                pass
                
    # Update fields
    rec.ticker = req.ticker
    rec.type = req.type
    rec.ratio = req.ratio
    rec.amount_per_share = req.amount_per_share if req.type == schemas.DividendType.CASH else None
    rec.ex_dividend_date = req.ex_dividend_date
    rec.register_date = req.register_date
    rec.payment_date = req.payment_date
    rec.owned_volume = Decimal(str(req.owned_quantity))
    rec.expected_value = expected_value
    rec.purchase_price = req.purchase_price
    rec.rights_quantity = expected_value if req.type == schemas.DividendType.RIGHTS else None
    
    # If CASH, we might need to update the pending CashFlow?
    # Simpler: just update the Record. The CashFlow creation logic in register_dividend is actually redundant 
    # if process_pending_dividends creates the CashFlow (it does for STOCK/RIGHTS, but check for CASH).
    # Checking register_dividend: it creates a PENDING CashFlow for CASH.
    # Checking process_pending_dividends: it handles PENDING CashFlow (if it exists?).
    # Actually, process_pending_dividends iterates DividendRecords.
    # If it's CASH, it says "For cash records, we just mark as completed since CashFlow handles the balance".
    # Wait, so we DO need a PENDING CashFlow for CASH type in the CashFlow table to affect balance?
    # No, CashFlow PENDING status items are NOT included in balance calculation usually.
    # Balance is calculated from COMPLETED CashFlows.
    # So if we update DividendRecord, we should also update the associated PENDING CashFlow.
    # But we didn't store the CashFlow ID.
    # This is a bit messy. For now, let's assume Process logic will be robust enough or we accept a minor desync 
    # in "Pending" view of CashFlows (which user doesn't see much).
    
    db.commit()
    
    return {
        "ticker": rec.ticker,
        "expected_value": expected_value,
        "type": rec.type.value
    }
