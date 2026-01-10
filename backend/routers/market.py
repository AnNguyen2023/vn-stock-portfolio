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
    return {"message": "Fetching VN-INDEX historical data, please wait a moment!"}


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
    return {"message": f"Syncing history for {len(tickers)} stocks in your portfolio."}

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


@router.get("/trending/{ticker}")
def get_trending(ticker: str):
    """Get 5-session trending indicator for a ticker"""
    from services.market_service import get_trending_indicator
    return get_trending_indicator(ticker)


@router.get("/market-summary")
def get_market_summary(db: Session = Depends(get_db)):
    """
    Lấy thông tin tổng quan thị trường cho 3 chỉ số:
    - VNINDEX, VN30, HNX30
    """
    from vnstock import Trading
    from datetime import datetime
    
    indices = ["VNINDEX", "VN30", "HNX30"]
    results = []
    
    # Try vnstock3 first
    try:
        print(f"[MARKET] Trying vnstock3 Trading.price_board for {indices}")
        df = Trading(source='VCI').price_board(indices)
        
        if df is not None and not df.empty:
            print(f"[MARKET] vnstock3 returned data with shape: {df.shape}")
            
            for idx, index_name in enumerate(indices):
                try:
                    row = df.iloc[idx]
                    
                    # Get price data
                    match_price = row[('match', 'match_price')]
                    ref_price = row[('match', 'reference_price')]
                    match_vol = row[('match', 'match_vol')]
                    
                    price = float(match_price or ref_price or 0)
                    ref = float(ref_price or 0)
                    
                    if price > 0 and ref > 0:
                        change = price - ref
                        change_pct = (change / ref * 100)
                        volume = float(match_vol or 0)
                        
                        # Try to get total value
                        try:
                            total_val = row[('match', 'total_val')]
                            value = float(total_val or 0) / 1e9
                        except:
                            value = 0
                        
                        # Check if market is closed
                        now = datetime.now()
                        is_weekend = now.weekday() >= 5
                        is_closed = is_weekend or now.hour < 9 or now.hour >= 15
                        
                        results.append({
                            "index": index_name,
                            "price": round(price, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "volume": int(volume),
                            "value": round(value, 2),
                            "is_closed": is_closed
                        })
                except Exception as e:
                    print(f"[MARKET] Error processing {index_name}: {e}")
                    continue
            
            if len(results) == 3:
                print(f"[MARKET] vnstock3 success for all 3 indices")
                return {
                    "status": "success",
                    "data": results
                }
        
    except Exception as e:
        print(f"[MARKET] vnstock3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Fallback to database
    try:
        print("[MARKET] Trying database fallback")
        
        for index_name in indices:
            latest = (
                db.query(models.HistoricalPrice)
                .filter(models.HistoricalPrice.ticker == index_name)
                .order_by(models.HistoricalPrice.date.desc())
                .first()
            )
            
            if latest:
                prev = (
                    db.query(models.HistoricalPrice)
                    .filter(
                        models.HistoricalPrice.ticker == index_name,
                        models.HistoricalPrice.date < latest.date
                    )
                    .order_by(models.HistoricalPrice.date.desc())
                    .first()
                )
                
                price = float(latest.close_price)
                ref = float(prev.close_price) if prev else price
                change = price - ref
                change_pct = (change / ref * 100) if ref > 0 else 0
                
                now = datetime.now()
                is_weekend = now.weekday() >= 5
                is_closed = is_weekend or now.hour < 9 or now.hour >= 15
                
                results.append({
                    "index": index_name,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "volume": 0,
                    "value": 0,
                    "is_closed": is_closed,
                    "last_updated": latest.date.strftime("%Y-%m-%d")
                })
            else:
                # Add placeholder for indices without data
                now = datetime.now()
                is_weekend = now.weekday() >= 5
                is_closed = is_weekend or now.hour < 9 or now.hour >= 15
                
                results.append({
                    "index": index_name,
                    "price": 0,
                    "change": 0,
                    "change_pct": 0,
                    "volume": 0,
                    "value": 0,
                    "is_closed": is_closed,
                    "last_updated": None
                })
        
        if len(results) > 0:
            print(f"[MARKET] Database fallback success for {len(results)} indices")
            return {
                "status": "success",
                "data": results
            }
            
    except Exception as e:
        print(f"[MARKET] Database fallback failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("[MARKET] All methods failed, returning error")
    return {
        "status": "error",
        "data": None,
        "message": "Không thể lấy dữ liệu thị trường"
    }
