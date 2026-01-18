
from __future__ import annotations
from datetime import datetime, time, date, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

import models
from core.db import SessionLocal
from services.market.cache import mem_get, mem_set

from core.logger import logger
from adapters import vci_adapter, vnstock_adapter
from services.market.sync_tasks import sync_historical_task

def _vn_now():
    return datetime.utcnow() + timedelta(hours=7)

def _is_market_open(now_dt: datetime) -> bool:
    if now_dt.weekday() >= 5:
        return False
    market_open = now_dt.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now_dt.replace(hour=15, minute=0, second=0, microsecond=0)
    return market_open <= now_dt <= market_close

def _get_intraday_from_db(db: Session, ticker: str) -> list[dict]:
    latest_row = (
        db.query(models.IntradayPrice)
        .filter(models.IntradayPrice.ticker == ticker)
        .order_by(models.IntradayPrice.timestamp.desc())
        .first()
    )
    if not latest_row:
        return []

    session_date = latest_row.timestamp.date()
    start_dt = datetime.combine(session_date, time(0, 0))
    end_dt = datetime.combine(session_date, time(23, 59, 59))
    rows = (
        db.query(models.IntradayPrice)
        .filter(
            models.IntradayPrice.ticker == ticker,
            models.IntradayPrice.timestamp >= start_dt,
            models.IntradayPrice.timestamp <= end_dt,
        )
        .order_by(models.IntradayPrice.timestamp.asc())
        .all()
    )
    if not rows:
        return []

    result = []
    for r in rows:
        ts = int(r.timestamp.timestamp())
        result.append({
            "t": r.timestamp.strftime("%H:%M"),
            "timestamp": ts,
            "p": float(r.price),
            "v": int(r.volume or 0),
        })
    return result

def _save_intraday_session(db: Session, ticker: str, points: list[dict]) -> None:
    if not points:
        return

    first_ts = points[0].get("timestamp")
    if not first_ts:
        return

    session_date = datetime.fromtimestamp(first_ts).date()
    start_dt = datetime.combine(session_date, time(0, 0))
    end_dt = datetime.combine(session_date, time(23, 59, 59))

    db.query(models.IntradayPrice).filter(
        models.IntradayPrice.ticker == ticker,
        models.IntradayPrice.timestamp >= start_dt,
        models.IntradayPrice.timestamp <= end_dt,
    ).delete(synchronize_session=False)

    for p in points:
        ts = p.get("timestamp")
        price = p.get("p")
        if not ts or price is None:
            continue
        ts_dt = datetime.fromtimestamp(ts)
        db.add(models.IntradayPrice(
            ticker=ticker,
            timestamp=ts_dt,
            price=Decimal(str(price)),
            volume=Decimal(str(p.get("v") or 0)),
        ))
    db.commit()

def get_trending_indicator(ticker: str, db: Session, background_tasks: Optional[BackgroundTasks] = None) -> dict:
    """
    Calculates the price trend indicator based on the last 5 trading sessions.
    Results are cached in Redis (if available) and Memory for 5 minutes.
    Proactively triggers background sync if local data is insufficient.
    """
    ticker = ticker.upper()
    cache_key = f"trending:{ticker}"
    
    # 1. Try Cache layers (RAM L1 -> Redis L2)
    cached = mem_get(cache_key)
    if cached:
        return cached
    
    # 2. Calculate from DB
    prices = (
        db.query(models.HistoricalPrice)
        .filter(models.HistoricalPrice.ticker == ticker)
        .order_by(models.HistoricalPrice.date.desc())
        .limit(5)
        .all()
    )
    
    needs_sync = False
    if len(prices) < 5:
        # Insufficient data
        if background_tasks:
            logger.info(f"Insufficient history for {ticker} (found {len(prices)}/5), triggering sync.")
            background_tasks.add_task(sync_historical_task, ticker, '1m')
        else:
            needs_sync = True
        
        if len(prices) < 2:
            return {"trend": "sideways", "change_pct": 0.0, "needs_sync": needs_sync}
    
    prices = list(reversed(prices))
    first_price = float(prices[0].close_price)
    last_price = float(prices[-1].close_price)
    change_pct = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0.0
    
    if change_pct >= 3.0: trend = "strong_up"
    elif change_pct >= 1.0: trend = "up"
    elif change_pct <= -3.0: trend = "strong_down"
    elif change_pct <= -1.0: trend = "down"
    else: trend = "sideways"
    
    result = {"trend": trend, "change_pct": round(change_pct, 2), "needs_sync": needs_sync}
    
    # 3. Save to Cache (RAM + Redis) with 15m TTL (900s)
    mem_set(cache_key, result, 900)
    return result

def get_trending_indicators_batch(tickers: list[str], db: Session, background_tasks: Optional[BackgroundTasks] = None) -> dict[str, dict]:
    """
    Batch optimization for getting trending indicators.
    Returns a dict: {ticker: result}
    """
    results = {}
    missing_tickers = []
    
    # 1. Check Cache First
    for ticker in tickers:
        cached = mem_get(f"trending:{ticker}")
        if cached:
            results[ticker] = cached
        else:
            missing_tickers.append(ticker)
            
    if not missing_tickers:
        return results
        
    # 2. Fetch from DB for missing tickers (Sequential in single session is faster than N sessions)
    # We fetch last 30 days of data for these tickers to avoid N queries if possible, 
    # but for accuracy of "last 5 sessions", sequential limit queries is simplest and safe enough 
    # since session overhead is removed.
    
    for ticker in missing_tickers:
        prices = (
            db.query(models.HistoricalPrice)
            .filter(models.HistoricalPrice.ticker == ticker)
            .order_by(models.HistoricalPrice.date.desc())
            .limit(5)
            .all()
        )
        
        if len(prices) < 5:
            if background_tasks:
                background_tasks.add_task(sync_historical_task, ticker, '1m')
            
            if len(prices) < 2:
                results[ticker] = {"trend": "sideways", "change_pct": 0.0}
                # Don't cache bad data for long, or maybe cache short? 
                # Current logic doesn't cache if < 5 except here. 
                # We'll stick to not caching or returning default without cache.
                continue

        prices = list(reversed(prices))
        first_price = float(prices[0].close_price)
        last_price = float(prices[-1].close_price)
        change_pct = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0.0
        
        if change_pct >= 3.0: trend = "strong_up"
        elif change_pct >= 1.0: trend = "up"
        elif change_pct <= -3.0: trend = "strong_down"
        elif change_pct <= -1.0: trend = "down"
        else: trend = "sideways"
        
        res_obj = {"trend": trend, "change_pct": round(change_pct, 2)}
        results[ticker] = res_obj
        mem_set(f"trending:{ticker}", res_obj, 900)
        
    return results

def _process_single_ticker(t: str, p_info: dict, sec_info: dict | None = None, trending_info: dict | None = None) -> dict:
    """Hàm xử lý logic cho 1 mã (chạy trong thread)"""
    t = t.upper()
    try:
        # 1. Giá Realtime (từ batch request)
        if isinstance(p_info, dict):
            curr_price = float(p_info.get("price", 0))
            ref_price_vnd = float(p_info.get("ref", 0))
            ceiling_p = float(p_info.get("ceiling", 0))
            floor_p = float(p_info.get("floor", 0))
            vol = float(p_info.get("volume", 0))
        else:
            curr_price = float(p_info or 0)
            ref_price_vnd = 0; ceiling_p = 0; floor_p = 0; vol = 0

        # 2. Xử lý Metadata (Sử dụng batch data được truyền vào nếu có)
        if sec_info:
            exchange = sec_info.get("exchange", "")
            name = sec_info.get("name", t)
        else:
            # Fallback nếu không có batch (ít xảy ra)
            with SessionLocal() as db:
                sec = db.query(models.Security).filter_by(symbol=t).first()
                exchange = sec.exchange if sec else ""
                name = sec.short_name if sec else t

        # 3. SPARKLINE (Dùng Adapter)
        sparkline = vci_adapter.get_sparkline_data(t, mem_get, mem_set)

        # 4. FINANCIAL RATIOS (Dùng Adapter)
        ratios = vnstock_adapter.get_financial_ratios(t, mem_get, mem_set)

        # 5. TRENDING INDICATOR (Batch Optimization)
        # Use passed trending_info if available (Optimized), else fallback to creating session (N+1 Risk)
        if trending_info:
            trending = trending_info
        else:
            with SessionLocal() as db:
                trending = get_trending_indicator(t, db)

        return {
            "ticker": t,
            "name": name,
            "price": curr_price,
            "ref_price": ref_price_vnd,
            "ceiling_price": ceiling_p,
            "floor_price": floor_p,
            "change_pct": ((curr_price - ref_price_vnd) / ref_price_vnd * 100) if ref_price_vnd > 0 else 0,
            "volume": vol,
            "market_cap": ratios["market_cap"],
            "roe": ratios["roe"],
            "roa": ratios["roa"],
            "pe": ratios["pe"],
            "pb": ratios.get("pb", 0),
            "sparkline": sparkline,
            "industry": exchange,
            "trending": trending
        }

    except Exception as e:
        print(f"[ERR] Lỗi xử lý {t}: {e}")
        return {"ticker": t, "price": 0, "change_pct": 0, "sparkline": [], "name": t}
