# routers/market.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import timedelta, date

from sqlalchemy import cast, Date, text

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


@router.get("/migrate-value")
def migrate_value_column(db: Session = Depends(get_db)):
    try:
        # Check if column exists
        check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='historical_prices' AND column_name='value'")
        result = db.execute(check_sql).fetchone()
        
        if result:
            return {"status": "skipped", "message": "Column 'value' already exists"}
        
        # Add column
        db.execute(text("ALTER TABLE historical_prices ADD COLUMN value NUMERIC DEFAULT 0"))
        db.commit()
        return {"status": "success", "message": "Added column 'value'"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
    
    from services.market_service import mem_get, mem_set
    
    # 0. Throttling: Cache kết quả toàn bộ cho 10 giây để tránh spam API
    cached_summary = mem_get("market_summary_full_v3")
    if cached_summary:
        return {"status": "success", "data": cached_summary, "cached": True}

    # 1. Kiểm tra Circuit Breaker (Backoff)
    from core.redis_client import get_redis
    r_client = get_redis()
    backoff = False
    try:
        backoff = mem_get("vci_backoff") or (r_client.get("vci_rate_limit_backoff") if r_client else None)
    except:
        pass
    
    if backoff:
        print("[MARKET] VCI Backoff active. Skipping API call.")
    else:
        # 2. Try vnstock3
        try:
            print(f"[MARKET] Trying vnstock3 Trading.price_board for {indices}")
            df = Trading(source='VCI').price_board(indices)
            
            if df is not None and not df.empty:
                print(f"[MARKET] vnstock3 returned data with shape: {df.shape}")
                
                for idx, index_name in enumerate(indices):
                    try:
                        # VCI might return symbols in different order or missing some?
                        # Usually it matches as we passed the list, but let's be safe.
                        # search for row where symbol matches
                        symbol_found = False
                        row = None
                        for r_idx in range(len(df)):
                            if df.iloc[r_idx][('listing', 'symbol')] == index_name:
                                row = df.iloc[r_idx]
                                symbol_found = True
                                break
                        
                        if not symbol_found: continue

                        # Get price data
                        match_price = row[('match', 'match_price')]
                        ref_price = row[('match', 'reference_price')]
                        match_vol = row[('match', 'match_vol')]
                        
                        price = float(match_price or ref_price or 0)
                        ref = float(ref_price or 0)
                        
                        # --- UNIFY TO POINTS (Standardize Index Units) ---
                        if price > 10000:
                            price /= 1000
                            ref /= 1000

                        if price > 0 and ref > 0:
                            change = price - ref
                            change_pct = (change / ref * 100)
                            volume = float(match_vol or 0)
                            
                            # Try to get total value
                            try:
                                total_val = row.get(('match', 'total_value')) or row.get(('match', 'total_val')) or 0
                                value = float(total_val) / 1e9
                            except:
                                value = 0
                                
                            # FALLBACK: If value is still 0, try the DB
                            if value == 0:
                                try:
                                    latest_hist = db.query(models.HistoricalPrice).filter(
                                        models.HistoricalPrice.ticker == index_name
                                    ).order_by(models.HistoricalPrice.date.desc()).first()
                                    if latest_hist and latest_hist.value > 0:
                                        value = float(latest_hist.value) / (1e9 if latest_hist.value > 1e6 else 1)
                                except:
                                    pass
                            
                            # Check if market is closed
                            now = datetime.now()
                            is_weekend = now.weekday() >= 5
                            is_closed = is_weekend or now.hour < 9 or now.hour >= 15
                            
                            # FETCH INTRADAY SPARKLINE
                            from adapters.vci_adapter import get_intraday_sparkline
                            sparkline = get_intraday_sparkline(index_name, mem_get, mem_set)

                            results.append({
                                "index": index_name,
                                "date": datetime.now().strftime('%d/%m/%Y'),
                                "price": round(price, 2),
                                "change": round(change, 2),
                                "change_pct": round(change_pct, 2),
                                "volume": int(volume),
                                "value": round(value, 2),
                                "sparkline": sparkline
                            })
                    except Exception as e:
                        print(f"[MARKET] Error processing {index_name}: {e}")
                        continue
                
                if len(results) == len(indices):
                    print(f"[MARKET] vnstock3 success for all indices")
                    mem_set("market_summary_full_v3", results, 10)
                    return {"status": "success", "data": results}
            
        except BaseException as e:
            mem_set("vci_backoff", True, 60)
            if r_client:
                try: r_client.setex("vci_rate_limit_backoff", 60, "true")
                except: pass
            print(f"[MARKET] vnstock3 CRITICAL failure (Rate Limit?): {e}")
    
    # 3. Fallback to database if results incomplete
    processed_count = 0
    fallback_results = []
    try:
        print("[MARKET] Trying database fallback")
        for index_name in indices:
            # Check if we already have this in results (if some API calls succeeded)
            existing = next((r for r in results if r["index"] == index_name), None)
            if existing:
                fallback_results.append(existing)
                continue

            latest = db.query(models.HistoricalPrice).filter(models.HistoricalPrice.ticker == index_name).order_by(models.HistoricalPrice.date.desc()).first()
            if latest:
                prev = db.query(models.HistoricalPrice).filter(models.HistoricalPrice.ticker == index_name, models.HistoricalPrice.date < latest.date).order_by(models.HistoricalPrice.date.desc()).first()
                
                price = float(latest.close_price)
                ref = float(prev.close_price) if prev else price
                
                if price > 10000:
                    price /= 1000
                    ref /= 1000
                    
                change = price - ref
                change_pct = (change / ref * 100) if ref > 0 else 0
                
                now = datetime.now()
                is_weekend = now.weekday() >= 5
                is_closed = is_weekend or now.hour < 9 or now.hour >= 15
                
                from adapters.vci_adapter import get_intraday_sparkline
                sparkline = get_intraday_sparkline(index_name, mem_get, mem_set)
                
                fallback_results.append({
                    "index": index_name,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "volume": int(latest.volume or 0),
                    "value": float(latest.value or 0) / (1e9 if (latest.value or 0) > 1e6 else 1),
                    "is_closed": is_closed,
                    "last_updated": latest.date.strftime("%Y-%m-%d"),
                    "sparkline": sparkline
                })

        if len(fallback_results) > 0:
            mem_set("market_summary_full_v3", fallback_results, 10)
            return {"status": "success", "data": fallback_results, "source": "database"}
            
    except Exception as e:
        print(f"[MARKET] Database fallback failed: {e}")
    
    return {
        "status": "error",
        "message": "Không thể lấy dữ liệu thị trường"
    }


