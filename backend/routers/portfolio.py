# routers/portfolio.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, datetime

import models
import schemas
from core.db import get_db
from core.cache import invalidate_dashboard_cache
from core.redis_client import safe_flushall
from core.exceptions import ValidationError
from core.logger import logger

from services.portfolio_service import calculate_portfolio, get_ticker_profit
from services.performance_service import calculate_twr_metrics, growth_series, nav_history

router = APIRouter(tags=["Portfolio & Performance"])

@router.post("/deposit")
def deposit_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    """
    Allocates new funds to the user's cash balance.
    """
    asset = db.query(models.AssetSummary).first()
    if not asset:
        asset = models.AssetSummary(
            cash_balance=0,
            total_deposited=0,
            last_interest_calc_date=date.today(),
        )
        db.add(asset)
        db.flush()

    asset.cash_balance += req.amount
    asset.total_deposited += req.amount

    db.add(
        models.CashFlow(
            type=models.CashFlowType.DEPOSIT,
            amount=req.amount,
            description=req.description,
        )
    )
    db.commit()

    invalidate_dashboard_cache()
    logger.info(f"Deposit successful: {req.amount:,.0f} VNĐ. New balance: {asset.cash_balance:,.0f} VNĐ.")
    return {"success": True, "message": "Funds deposited successfully."}

@router.post("/withdraw")
def withdraw_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    """
    Withdraws funds from the user's cash balance. Checks for sufficient funds first.
    """
    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < req.amount:
        raise ValidationError("Insufficient balance for withdrawal.")

    asset.cash_balance -= req.amount
    db.add(
        models.CashFlow(
            type=models.CashFlowType.WITHDRAW,
            amount=req.amount,
            description=req.description,
        )
    )
    db.commit()

    invalidate_dashboard_cache()
    logger.info(f"Withdrawal successful: {req.amount:,.0f} VNĐ. New balance: {asset.cash_balance:,.0f} VNĐ.")
    return {"success": True, "message": "Funds withdrawn successfully."}

@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    """
    Retrieves the complete portfolio valuation and breakdown.
    """
    data = calculate_portfolio(db)
    return {"success": True, "data": data}

@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    """
    Retrieves portfolio performance metrics (TWR).
    """
    data = calculate_twr_metrics(db)
    return {"success": True, "data": data}

@router.get("/chart-growth")
def get_chart_growth(period: str = "1m", db: Session = Depends(get_db)):
    """
    Returns data series for the portfolio growth chart.
    """
    data = growth_series(db, period=period)
    return {"success": True, "data": data}

@router.get("/nav-history")
def get_nav_history(start_date: str | None = None, end_date: str | None = None, limit: int = 30, db: Session = Depends(get_db)):
    """
    Returns historical NAV data with optional date filtering.
    """
    def _parse_date(s):
        if not s: return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try: return datetime.strptime(s, fmt).date()
            except: continue
        return None

    d_start = _parse_date(start_date)
    d_end = _parse_date(end_date)
        
    data = nav_history(db, start_date=d_start, end_date=d_end, limit=limit)
    return {"success": True, "data": data}

@router.get("/ticker-lifetime-profit/{ticker}")
def get_ticker_lifetime_profit(ticker: str, db: Session = Depends(get_db)):
    """
    Calculates lifetime realized and unrealized profit for a specific ticker.
    """
    data = get_ticker_profit(db, ticker)
    return {"success": True, "data": data}

@router.post("/save-nav-snapshot")
def save_nav_snapshot_manual(db: Session = Depends(get_db)):
    """
    Manually trigger NAV snapshot save.
    Useful for testing or manual end-of-day saves.
    """
    try:
        from tasks.daily_nav_snapshot import save_daily_nav_snapshot
        save_daily_nav_snapshot()
        return {"success": True, "message": "NAV snapshot saved successfully"}
    except Exception as e:
        logger.error(f"Manual NAV snapshot failed: {e}")
        return {"success": False, "message": str(e)}

@router.post("/reset-data")
def reset_data(db: Session = Depends(get_db)):
    """
    DANGER: Purges all trading and portfolio data. Used for development reset.
    """
    logger.warning("Triggered DANGEROUS reset-data operation.")
    db.query(models.StockTransaction).delete()
    db.query(models.TickerHolding).delete()
    db.query(models.AssetSummary).delete()
    db.query(models.CashFlow).delete()
    db.query(models.RealizedProfit).delete()
    db.query(models.DailySnapshot).delete()
    db.query(models.HistoricalPrice).delete()
    db.commit()

    safe_flushall()
    invalidate_dashboard_cache()

    return {"success": True, "message": "All system data has been wiped."}