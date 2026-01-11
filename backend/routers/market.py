# routers/market.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import timedelta, date
from sqlalchemy import cast, Date, text

import models
from core.db import get_db
from core.logger import logger
from services import market_service

router = APIRouter(tags=["Market Data"])

@router.post("/seed-index")
def seed_index_data(background_tasks: BackgroundTasks):
    """
    Trigger background job to sync VNINDEX, VN30, HNX30 historical data.
    """
    background_tasks.add_task(market_service.seed_index_data_task)
    return {"success": True, "message": "Fetching VN-INDEX historical data in background."}

@router.post("/sync-portfolio-history")
def sync_portfolio_history(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger background job to sync history for all stocks in the active portfolio.
    """
    holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
    tickers = [h.ticker for h in holdings]
    
    if not tickers:
        return {"success": True, "message": "No active holdings found to sync."}

    background_tasks.add_task(market_service.sync_portfolio_history_task, tickers, 2.0)
    return {"success": True, "message": f"Syncing history for {len(tickers)} stocks in background."}

@router.get("/historical")
def get_historical(
    ticker: str,
    background_tasks: BackgroundTasks,
    period: str = "1m",
    db: Session = Depends(get_db),
):
    """
    Retrieve historical price data from local store.
    Triggers background sync if local data is insufficient.
    """
    ticker = ticker.upper()
    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    start_date = date.today() - timedelta(days=days_map.get(period, 30))

    stored_data = (
        db.query(models.HistoricalPrice)
        .filter(
            models.HistoricalPrice.ticker == ticker,
            cast(models.HistoricalPrice.date, Date) >= start_date,
        )
        .order_by(models.HistoricalPrice.date.asc())
        .all()
    )

    if len(stored_data) < 5:
        logger.info(f"Low history cache for {ticker}, triggering background sync.")
        background_tasks.add_task(market_service.sync_historical_task, ticker, period)

    return {
        "success": True,
        "ticker": ticker,
        "data": [{"date": i.date.strftime("%Y-%m-%d"), "close": float(i.close_price)} for i in stored_data],
    }

@router.get("/trending/{ticker}")
def get_trending(ticker: str):
    """
    Get 5-session price trending indicator for a ticker.
    """
    return market_service.get_trending_indicator(ticker)

@router.get("/market-summary")
def get_market_summary(db: Session = Depends(get_db)):
    """
    Get real-time market overview for major indices (VNINDEX, VN30, HNX30).
    Orchestrated by the service layer with dual-layer caching (Redis/Memory).
    """
    data = market_service.get_market_summary_service(db)
    return {
        "success": True,
        "data": data
    }

@router.get("/migrate-value")
def migrate_value_column(db: Session = Depends(get_db)):
    """
    Administrative utility to ensure the schema includes the 'value' column.
    """
    try:
        check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='historical_prices' AND column_name='value'")
        result = db.execute(check_sql).fetchone()
        
        if result:
            return {"success": True, "message": "Column 'value' already exists."}
        
        db.execute(text("ALTER TABLE historical_prices ADD COLUMN value NUMERIC DEFAULT 0"))
        db.commit()
        return {"success": True, "message": "Added column 'value' to historical_prices."}
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return {"success": False, "message": str(e)}
