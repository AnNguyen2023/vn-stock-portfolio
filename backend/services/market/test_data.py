
from __future__ import annotations
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
import models
from core.db import SessionLocal
from core.logger import logger

def seed_test_data_task(ticker: str, days: int = 7) -> dict:
    """
    Seeds the TestHistoricalPrice table with data from HistoricalPrice 
    for the last 'days' trading sessions.
    """
    ticker = ticker.upper().strip()
    with SessionLocal() as db:
        # Get last N days of real historical data
        real_data = (
            db.query(models.HistoricalPrice)
            .filter(models.HistoricalPrice.ticker == ticker)
            .order_by(models.HistoricalPrice.date.desc())
            .limit(days)
            .all()
        )
        
        if not real_data:
            logger.warning(f"No historical data found for {ticker} to seed test table.")
            return {"success": False, "message": f"No data found for {ticker}"}

        count = 0
        for item in real_data:
            try:
                # Upsert into TestHistoricalPrice
                exist = db.query(models.TestHistoricalPrice).filter_by(ticker=ticker, date=item.date).first()
                if exist:
                    exist.close_price = item.close_price
                    exist.volume = item.volume
                    exist.value = item.value
                else:
                    db.add(
                        models.TestHistoricalPrice(
                            ticker=ticker,
                            date=item.date,
                            close_price=item.close_price,
                            volume=item.volume,
                            value=item.value
                        )
                    )
                count += 1
            except Exception as e:
                logger.error(f"Error seeding test item for {ticker}: {e}")
                continue
        
        db.commit()
        logger.info(f"Seeded {count} test records for {ticker}.")
        return {"success": True, "count": count}

def update_test_price(ticker: str, price: float, volume: float = 0, target_date: date = None) -> dict:
    """
    Manually update or insert a price entry in the test table for a specific date (default today).
    """
    ticker = ticker.upper().strip()
    if target_date is None:
        target_date = date.today()
        
    with SessionLocal() as db:
        exist = db.query(models.TestHistoricalPrice).filter_by(ticker=ticker, date=target_date).first()
        if exist:
            exist.close_price = Decimal(str(price))
            exist.volume = Decimal(str(volume))
        else:
            db.add(
                models.TestHistoricalPrice(
                    ticker=ticker,
                    date=target_date,
                    close_price=Decimal(str(price)),
                    volume=Decimal(str(volume)),
                    value=0
                )
            )
        db.commit()
        return {"success": True, "ticker": ticker, "date": str(target_date), "price": price}

def get_test_market_summary_service(db: Session) -> list[dict]:
    """
    Retrieves market summary specifically from the test data table.
    """
    indices = ["VNINDEX", "VN30", "HNX30"]
    results = []
    
    for index_name in indices:
        # Get latest 2 days from test table to calc change
        latest_two = (
            db.query(models.TestHistoricalPrice)
            .filter(models.TestHistoricalPrice.ticker == index_name)
            .order_by(models.TestHistoricalPrice.date.desc())
            .limit(2)
            .all()
        )
        
        if not latest_two:
            continue
            
        latest = latest_two[0]
        prev = latest_two[1] if len(latest_two) > 1 else latest
        
        price = float(latest.close_price)
        ref = float(prev.close_price)
        
        # Point conversion for indices if needed (consistency with _process_market_row)
        if price > 10000:
            price /= 1000
            ref /= 1000
            
        change = price - ref
        change_pct = (change / ref * 100) if ref > 0 else 0
        
        results.append({
            "index": index_name,
            "date": latest.date.strftime("%Y-%m-%d"),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(latest.volume or 0),
            "value": float(latest.value or 0) / 1e9,
            "source": "test_table"
        })
    
    return results
