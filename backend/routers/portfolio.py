# routers/portfolio.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

import models
import schemas

from core.db import get_db
from core.cache import invalidate_dashboard_cache
from core.redis_client import safe_flushall

from services.portfolio_service import calculate_portfolio, get_ticker_profit
from services.performance_service import calculate_twr_metrics, growth_series, nav_history

router = APIRouter(tags=["Portfolio & Performance"])


def raise_error(message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=message)


@router.post("/deposit")
def deposit_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
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
    return {"status": "success", "message": "Nạp tiền thành công"}


@router.post("/withdraw")
def withdraw_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < req.amount:
        raise_error("Không đủ số dư để rút")

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
    return {"message": "Rút tiền thành công"}


@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    return calculate_portfolio(db)


@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    return calculate_twr_metrics(db)


@router.get("/chart-growth")
def get_chart_growth(period: str = "1m", db: Session = Depends(get_db)):
    return growth_series(db, period=period)


@router.get("/nav-history")
def get_nav_history(start_date: str | None = None, end_date: str | None = None, limit: int = 30, db: Session = Depends(get_db)):
    from datetime import datetime
    d_start = None
    d_end = None
    
    def _parse_date(s):
        if not s: return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try: return datetime.strptime(s, fmt).date()
            except: continue
        return None

    d_start = _parse_date(start_date)
    d_end = _parse_date(end_date)
        
    return nav_history(db, start_date=d_start, end_date=d_end, limit=limit)


@router.get("/ticker-lifetime-profit/{ticker}")
def get_ticker_lifetime_profit(ticker: str, db: Session = Depends(get_db)):
    return get_ticker_profit(db, ticker)


@router.post("/reset-data")
def reset_data(db: Session = Depends(get_db)):
    db.query(models.StockTransaction).delete()
    db.query(models.TickerHolding).delete()
    db.query(models.AssetSummary).delete()
    db.query(models.CashFlow).delete()
    db.query(models.RealizedProfit).delete()
    db.query(models.DailySnapshot).delete()
    db.query(models.HistoricalPrice).delete()
    db.commit()

    # dev: xoá redis cache (nếu có)
    safe_flushall()
    invalidate_dashboard_cache()

    return {"message": "Hệ thống đã về trạng thái trắng tinh!"}