# routers/market.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import timedelta, date

from sqlalchemy import cast, Date

import models
from core.db import get_db
from services.market_service import (
    seed_index_data_task,
    sync_portfolio_history_task,
    sync_historical_task,
)

router = APIRouter(tags=["Market Data"])


@router.post("/seed-index")
def seed_index_data(background_tasks: BackgroundTasks):
    """Lệnh cho Tèo em đi nhặt 1 năm dữ liệu VNINDEX về kho"""
    background_tasks.add_task(seed_index_data_task)
    return {"message": "Tèo em đang đi nhặt VN-INDEX, đại ca chờ xíu nhé!"}


@router.post("/sync-portfolio-history")
def sync_portfolio_history(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Tèo em tự quét danh mục, nhặt history cho các mã (nghỉ 2s mỗi mã)"""
    holdings = (
        db.query(models.TickerHolding)
        .filter(models.TickerHolding.total_volume > 0)
        .all()
    )
    tickers = [h.ticker for h in holdings]

    background_tasks.add_task(sync_portfolio_history_task, tickers, 2.0)
    return {"message": f"Đang lấy history cho {len(tickers)} mã chúng khoán của đại ca Zon."}

@router.get("/historical")
def get_historical(
    ticker: str,
    background_tasks: BackgroundTasks,
    period: str = "1m",
    db: Session = Depends(get_db),
):
    ticker = ticker.upper()
    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    start_date = date.today() - timedelta(days=days_map.get(period, 30))

    # 1) ưu tiên lấy trong kho
    stored_data = (
        db.query(models.HistoricalPrice)
        .filter(
            models.HistoricalPrice.ticker == ticker,
            cast(models.HistoricalPrice.date, Date) >= start_date,
        )
        .order_by(models.HistoricalPrice.date.asc())
        .all()
    )

    # 2) nếu kho trống thì crawl ngầm
    if len(stored_data) < 5:
        background_tasks.add_task(sync_historical_task, ticker, period)

    # 3) trả ngay data hiện có
    return {
        "status": "success",
        "data": [{"date": i.date.strftime("%Y-%m-%d"), "close": float(i.close_price)} for i in stored_data],
    }
