# services/market_service.py
from __future__ import annotations

from datetime import datetime, date, timedelta
from decimal import Decimal
import time
from typing import Iterable, Any, Optional, Union
import json
import concurrent.futures
import pandas as pd
from vnstock import Trading, Vnstock
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

import models
import crawler
from core.db import SessionLocal
from core.redis_client import get_redis, cache_get, cache_set, cache_delete
from core.logger import logger
from core.utils import is_trading_hours

# New Adapters
from adapters import vci_adapter, vnstock_adapter

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

# --- CONFIGURATION & BASELINES ---
INDEX_BASELINES = {
    "VNINDEX": 1250.00,  # Fallback if DB is empty
    "VN30": 1300.00,
    "HNX30": 550.00
}

# Use cache_get/cache_set directly from core.redis_client

def _process_single_ticker(t: str, p_info: dict, sec_info: dict | None = None) -> dict:
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
        sparkline = vci_adapter.get_sparkline_data(t, cache_get, cache_set)

        # 4. FINANCIAL RATIOS (Dùng Adapter)
        ratios = vnstock_adapter.get_financial_ratios(t, cache_get, cache_set)

        # 5. TRENDING INDICATOR (Batch Optimization)
        # Use the existing function but without background_tasks to keep this service light
        # Background tasks will be triggered by individual /trending calls OR we rely on pre-synced data
        with SessionLocal() as db:
            trending = get_trending_indicator(t, db)
            
            # 6. Check for PENDING dividends
            div_rec = db.query(models.DividendRecord).filter(
                models.DividendRecord.ticker == t,
                models.DividendRecord.status == models.CashFlowStatus.PENDING
            ).order_by(models.DividendRecord.payment_date.asc()).first()

            dividend_data = None
            if div_rec:
                dividend_data = {
                    "type": div_rec.type.value,
                    "payment_date": div_rec.payment_date.strftime("%Y-%m-%d") if div_rec.payment_date else None
                }

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
            "trending": trending,
            "has_dividend": div_rec is not None,
            "dividend_data": dividend_data
        }

    except Exception as e:
        print(f"[ERR] Lỗi xử lý {t}: {e}")
        return {"ticker": t, "price": 0, "change_pct": 0, "sparkline": [], "name": t}


def seed_index_data_task() -> None:
    """
    Worker task to fetch 1 year of historical data for VNINDEX, VN30, and HNX30.
    """
    logger.info("Background job started: Syncing index historical data (VNINDEX, VN30, HNX30)")
    
    indices = ["VNINDEX", "VN30", "HNX30"]
    total_count = 0
    
    with SessionLocal() as db:
        for symbol in indices:
            logger.info(f"Syncing index: {symbol}")
            live_data = crawler.get_historical_prices(symbol, period="1y")
            if not live_data:
                logger.warning(f"No historical data found for index {symbol}")
                continue

            count = 0
            for item in live_data:
                try:
                    d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    
                    # Normalize Units using DataEngine helper
                    from core.data_engine import DataEngine
                    price, vol, val = DataEngine.normalize_units(
                        symbol, 
                        item.get("close", 0), 
                        item.get("volume", 0), 
                        item.get("value", 0)
                    )
                    
                    exist = db.query(models.HistoricalPrice).filter_by(ticker=symbol, date=d).first()
                    if not exist:
                        db.add(
                            models.HistoricalPrice(
                                ticker=symbol,
                                date=d,
                                close_price=price,
                                volume=vol,
                                value=val,
                            )
                        )
                        count += 1
                    else:
                        # Maintenance: Update if unit mismatch detected (> 5% difference)
                        if abs(float(exist.close_price) - float(price)) / (float(price) or 1) > 0.05:
                            exist.close_price = price
                            exist.volume = vol
                            exist.value = val
                            count += 1
                except Exception as e:
                    logger.debug(f"Error parsing historical item for {symbol}: {e}")
                    continue
            total_count += count
        
        db.commit()

    logger.info(f"Historical index sync completed. Added {total_count} records.")


def sync_portfolio_history_task(tickers: Iterable[str], sleep_sec: float = 2.0) -> None:
    """
    Worker task: Scans the portfolio and fetches 1 year of historical data for each ticker.
    Includes a configurable sleep period to respect external API rate limits.

    Args:
        tickers (Iterable[str]): List of tickers to sync.
        sleep_sec (float): Seconds to sleep between tickers.
    """
    tickers_list = list(tickers)
    logger.info(f"Background job started: Syncing portfolio history for {len(tickers_list)} tickers")
    for t in tickers_list:
        t = (t or "").upper().strip()
        if not t:
            continue

        logger.info(f"Syncing history for ticker: {t}")
        live_data = crawler.get_historical_prices(t, period="1y")
        if live_data:
            with SessionLocal() as db:
                for item in live_data:
                    try:
                        d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                        exist = db.query(models.HistoricalPrice).filter_by(ticker=t, date=d).first()
                        if not exist:
                            db.add(
                                models.HistoricalPrice(
                                    ticker=t,
                                    date=d,
                                    close_price=Decimal(str(item["close"])),
                                    volume=Decimal(str(item.get("volume", 0))),
                                    value=Decimal(str(item.get("value", 0))),
                                )
                            )
                    except Exception as e:
                        logger.debug(f"Error parsing history for {t}: {e}")
                        continue
                db.commit()

        logger.debug(f"Finished {t}, sleeping for {sleep_sec}s")
        time.sleep(sleep_sec)

    logger.info("Portfolio history sync completed.")


def sync_historical_task(ticker: str, period: str) -> None:
    """
    One-off task to catch up on historical data for a specific ticker and period.

    Args:
        ticker (str): Ticker symbol.
        period (str): Date period (e.g., '1y', 'max').
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return

    try:
        logger.info(f"Syncing historical data for {ticker} (Period: {period})")
        live_data = crawler.get_historical_prices(ticker, period)
        if not live_data:
            logger.warning(f"No data found for {ticker}")
            return

        with SessionLocal() as db:
            for item in live_data:
                try:
                    d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    exist = db.query(models.HistoricalPrice).filter_by(ticker=ticker, date=d).first()
                    if not exist:
                        # CRITICAL: Normalize price - multiply by 1000 if < 1000 (VND unit issue)
                        close_price = Decimal(str(item["close"]))
                        if close_price < 1000:
                            close_price = close_price * 1000
                            logger.warning(f"[{ticker}] Normalized price {item['close']} -> {close_price} on {d}")
                        
                        db.add(
                            models.HistoricalPrice(
                                ticker=ticker,
                                date=d,
                                close_price=close_price,
                                volume=Decimal(str(item.get("volume", 0))),
                                value=Decimal(str(item.get("value", 0))),
                            )
                        )
                except Exception:
                    continue
            db.commit()
        logger.info(f"Finished seeding {ticker}")
    except Exception as e:
        logger.error(f"Failed to sync historical data for {ticker}: {e}")

def _upsert_security(db, row) -> bool:
    """
    Helper to create or update a security record in the database.
    
    Returns:
        bool: True if new record created, False if updated.
    """
    symbol = str(row["symbol"]).upper().strip()
    exchange = "HOSE" if row["exchange"] == "HSX" else row["exchange"]

    exist = db.query(models.Security).filter_by(symbol=symbol).first()
    if exist:
        exist.short_name = row.get("organ_short_name")
        exist.full_name = row.get("organ_name")
        exist.exchange = exchange
        exist.type = row["type"]
        exist.last_synced = datetime.now()
        return False
    else:
        db.add(
            models.Security(
                symbol=symbol,
                short_name=row.get("organ_short_name"),
                full_name=row.get("organ_name"),
                exchange=exchange,
                type=row["type"],
                last_synced=datetime.now()
            )
        )
        return True

def sync_securities_task() -> None:
    """
    Worker task to sync the list of all valid securities from VNStock adapter.
    Filters for relevant exchanges and types (STOCK, ETF, FUND).
    """
    logger.info("Background job started: Syncing securities list")
    try:
        df = vnstock_adapter.get_all_symbols()
        if df is None or df.empty:
            logger.warning("No security data received from adapter")
            return

        valid_exchanges = ["HSX", "HOSE", "HNX", "UPCOM"]
        valid_types = ["STOCK", "ETF", "FUND"]

        df_filtered = df[
            (df["exchange"].isin(valid_exchanges)) &
            (df["type"].isin(valid_types))
        ]

        with SessionLocal() as db:
            count_new = 0
            count_upd = 0
            for _, row in df_filtered.iterrows():
                is_new = _upsert_security(db, row)
                if is_new: count_new += 1
                else: count_upd += 1
            db.commit()
            logger.info(f"Securities sync completed. New: {count_new}, Updated: {count_upd}")

    except Exception as e:
        logger.error(f"Failed to sync securities list: {e}")


def invalidate_watchlist_detail_cache(watchlist_id: int):
    """Xóa cache chi tiết của một watchlist (dùng khi thêm/xóa mã)"""
    cache_key = f"wl_detail_v1:{watchlist_id}"
    cache_delete(cache_key)
    print(f"[CACHE] Đã xóa cache cho watchlist {watchlist_id}")

def get_watchlist_detail_service(tickers: list[str], watchlist_id: int | None = None) -> list[dict]:
    """
    Lấy dữ liệu chi tiết Watchlist (Tối ưu Parallel + Memory Cache + Batch Metadata + Result Cache)
    """
    if not tickers:
        return []

    tickers_upper = [t.upper() for t in tickers]
    
    # 0. Result Caching (Tối ưu chuyển TAB)
    result_cache_key = None
    if watchlist_id:
        result_cache_key = f"wl_detail_v1:{watchlist_id}"
        cached_res = cache_get(result_cache_key)
        if cached_res:
            return cached_res

    # 1. Batch Metadata Fetch (LONG-TERM CACHE 1H)
    sec_metadata = {}
    missing_meta_tickers = []
    
    for t in tickers_upper:
        meta_key = f"sec_meta_v1:{t}"
        cached_meta = cache_get(meta_key)
        if cached_meta:
            sec_metadata[t] = cached_meta
        else:
            missing_meta_tickers.append(t)
            
    if missing_meta_tickers:
        with SessionLocal() as db:
            securities = db.query(models.Security).filter(models.Security.symbol.in_(missing_meta_tickers)).all()
            for sec in securities:
                meta_obj = {
                    "name": sec.short_name,
                    "exchange": sec.exchange
                }
                sec_metadata[sec.symbol] = meta_obj
                # Cache metadata 8h (28800s)
                cache_set(f"sec_meta_v1:{sec.symbol}", meta_obj, 28800)

    # 2. Lấy giá Real-time (Batch Request)
    from crawler import get_current_prices
    try:
        current_prices = get_current_prices(tickers_upper)
    except:
        current_prices = {}

    results = []
    
    # 3. Chạy Parallel xử lý từng mã
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {
            executor.submit(
                _process_single_ticker, 
                t, 
                current_prices.get(t, {}), 
                sec_metadata.get(t)
            ): t 
            for t in tickers_upper
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            data = future.result()
            if data:
                results.append(data)
    
    results_map = {r['ticker']: r for r in results}
    ordered_results = [results_map.get(t) for t in tickers_upper if t in results_map]
    
    # Lưu vào Result Cache (10 giây)
    if result_cache_key:
        cache_set(result_cache_key, ordered_results, 10)
                
    return ordered_results


def get_trending_indicator(ticker: str, db: Session, background_tasks: Optional[BackgroundTasks] = None) -> dict:
    """
    Calculates the price trend indicator based on the last 5 trading sessions.
    Results are cached in Redis (if available) and Memory for 5 minutes.
    Proactively triggers background sync if local data is insufficient.
    """
    ticker = ticker.upper()
    cache_key = f"trending:{ticker}"
    
    # 1. Try Cache layers (RAM L1 -> Redis L2) via unified cache_get
    cached = cache_get(cache_key)
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
    
    if len(prices) < 5:
        # Insufficient data, trigger sync if background_tasks provided
        if background_tasks:
            logger.info(f"Insufficient history for {ticker} (found {len(prices)}/5), triggering sync.")
            background_tasks.add_task(sync_historical_task, ticker, '1m')
        
        if len(prices) < 2:
            return {"trend": "sideways", "change_pct": 0.0}
    
    prices = list(reversed(prices))
    first_price = float(prices[0].close_price)
    last_price = float(prices[-1].close_price)
    change_pct = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0.0
    
    if change_pct >= 3.0: trend = "strong_up"
    elif change_pct >= 1.0: trend = "up"
    elif change_pct <= -3.0: trend = "strong_down"
    elif change_pct <= -1.0: trend = "down"
    else: trend = "sideways"
    
    result = {"trend": trend, "change_pct": round(change_pct, 2)}
    
    # 3. Save to Cache (RAM + Redis) with 15m TTL (900s)
    cache_set(cache_key, result, 900)
    return result

def _process_market_row(row: Any, index_name: str, db: Session, vps_data: dict = None) -> Optional[dict]:
    """Helper to process a single index row with VPS priority and safe extraction."""
    try:
        # Standardize index names
        if index_name == "HASTC": index_name = "HNXINDEX"

        # Safe extraction from row (VCI board)
        match_price = 0
        ref_price_api = 0  # From API (may be incorrect)
        match_vol = 0
        total_val = 0
        
        if hasattr(row, 'get'):
            match_price = row.get(('match', 'match_price')) or 0
            ref_price_api = row.get(('match', 'reference_price')) or 0
            # Indices often put total volume/value in 'trading' group
            match_vol = row.get(('match', 'match_vol')) or row.get(('match', 'accumulated_volume')) or row.get(('trading', 'total_volume')) or row.get(('trading', 'total_vol')) or 0
            total_val = row.get(('match', 'total_value')) or row.get(('match', 'total_val')) or row.get(('trading', 'total_value')) or row.get(('trading', 'total_val')) or 0
        
        price = float(match_price or ref_price_api or 0)
        volume = float(match_vol or 0)
        # VCI indices usually return total value in Millions of VND.
        # Convert to Billions of VND by dividing by 1000.
        value = float(total_val or 0) / 1000

        # VPS Data Priority for current price
        has_vps = False
        if vps_data and index_name in vps_data:
            has_vps = True
            v_data = vps_data[index_name]
            v_price = v_data.get("price", 0)
            if v_price > 0: price = v_price
            
            v_vol = v_data.get("volume", 0)
            if v_vol > 0: volume = v_vol
            
            v_val = v_data.get("value", 0)
            if v_val > 0: 
                if v_val > 500000:
                    value = v_val / 1000
                else:
                    value = v_val
        
        # Unify to points if price is raw
        if price > 5000:
            price /= 1000

        # CRITICAL: Get reference price from DATABASE (previous session's close)
        ref_price_db = 0
        try:
            from core.utils import get_vietnam_time
            vn_now = get_vietnam_time()
            today_vn = vn_now.date()
            
            # Find the latest session STRICTLY BEFORE today
            prev_close = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == index_name,
                models.HistoricalPrice.date < today_vn
            ).order_by(models.HistoricalPrice.date.desc()).first()
            
            if prev_close:
                ref_price_db = float(prev_close.close_price)
                if ref_price_db > 100000: # VND unit issue check
                    ref_price_db /= 1000
                logger.info(f"[{index_name}] Using DB ref_price: {ref_price_db:.2f} from {prev_close.date}")
            else:
                ref_price_db = INDEX_BASELINES.get(index_name, 0)
                logger.warning(f"[{index_name}] No DB history found for baseline fallback.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to fetch ref_price from DB for {index_name}: {e}")
        
        from adapters.vci_adapter import get_intraday_sparkline
        sparkline = []
        try:
            sparkline = get_intraday_sparkline(index_name, cache_get, cache_set)
        except Exception as se:
            logger.debug(f"Intraday sparkline failed for {index_name}: {se}")

        # FALLBACK: If API price is 0 but we have sparkline, use latest VALID sparkline point
        if (price <= 0) and sparkline:
            # Find the last point with a valid price (iterate backwards)
            for pt in reversed(sparkline):
                if pt.get('p') and pt['p'] > 0:
                    price = pt['p']
                    has_vps = True  # Treat as live
                    logger.info(f"[{index_name}] Recovered price {price} from sparkline")
                    if volume <= 0 and pt.get('v'):
                        volume = pt['v']
                    break

        ref = ref_price_db

        if ref > 5000:
            ref /= 1000

        if price <= 0 or ref <= 0 or pd.isna(index_name):
            return None

        # Determine value fallback if still 0
        if value <= 0:
            latest_hist = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == index_name
            ).order_by(models.HistoricalPrice.date.desc()).first()
            if latest_hist:
                if latest_hist.value > 0:
                    # Ensure liquidity from DB is in Billions
                    value = float(latest_hist.value) / (1000 if (latest_hist.value or 0) > 1e9 else 1)
                if volume <= 0:
                    volume = int(latest_hist.volume or 0)
        
        change = price - ref
        change_pct = (change / ref * 100) if ref > 0 else 0
        
        logger.info(f"[{index_name}] price={price:.2f}, ref={ref:.2f}, change={change:.2f}, has_vps={has_vps}")

        # Persistent Intraday Safety Net: Update database for today
        # User Request: Only store VNINDEX/VN30 to DB. HNX30 is ephemeral/realtime only.
        if (has_vps or match_price > 0) and index_name == "VNINDEX":
            try:
                today_d = date.today()
                existing = db.query(models.HistoricalPrice).filter(
                    models.HistoricalPrice.ticker == index_name,
                    models.HistoricalPrice.date == today_d
                ).first()
                if not existing:
                    new_h = models.HistoricalPrice(
                        ticker=index_name,
                        date=today_d,
                        close_price=Decimal(str(price)),
                        volume=Decimal(str(volume)),
                        value=Decimal(str(value))
                    )
                    db.add(new_h)
                else:
                    # Update with freshest live data
                    existing.close_price = Decimal(str(price))
                    existing.volume = Decimal(str(volume))
                    existing.value = Decimal(str(value))
                db.commit()
            except Exception as db_e:
                db.rollback()
                logger.debug(f"Persistence failed for {index_name}: {db_e}")

        logger.info(f"MarketRow [{index_name}]: P={price:.2f} V={volume} Val={value:.3f} VPS={has_vps}")

        return {
            "index": index_name,
            "last_updated": datetime.now().isoformat(),
            "price": round(price, 2),
            "ref_price": round(ref, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": float(volume),
            "value": round(float(value), 3),
            "sparkline": sparkline,
        }
    except Exception as e:
        logger.debug(f"Row processing failed for {index_name}: {e}")
        return None

def _get_market_fallback(db: Session, indices: list[str]) -> list[dict]:
    """Helper for database fallback synchronization."""
    fallback_results = []
    from adapters.vci_adapter import get_intraday_sparkline
    
    for index_name in indices:
        if pd.isna(index_name):
            continue

        # Priority: Use HistoricalPrice FIRST (more reliable for indices)
        # TestHistoricalPrice is only for testing/simulation
        latest = db.query(models.HistoricalPrice).filter(
            models.HistoricalPrice.ticker == index_name
        ).order_by(models.HistoricalPrice.date.desc()).first()
        
        use_test_table = False
        if not latest:
            # Fallback to TestHistoricalPrice if real data unavailable
            latest = db.query(models.TestHistoricalPrice).filter(
                models.TestHistoricalPrice.ticker == index_name
            ).order_by(models.TestHistoricalPrice.date.desc()).first()
            use_test_table = True

        if not latest:
            continue

        price = float(latest.close_price or 0)
        if price > 5000:
            price /= 1000

        # Get reference price from PREVIOUS session - use SAME table as latest
        from datetime import date
        today = date.today()
        
        if use_test_table:
            prev_close = db.query(models.TestHistoricalPrice).filter(
                models.TestHistoricalPrice.ticker == index_name,
                models.TestHistoricalPrice.date < latest.date
            ).order_by(models.TestHistoricalPrice.date.desc()).first()
        else:
            prev_close = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == index_name,
                models.HistoricalPrice.date < latest.date
            ).order_by(models.HistoricalPrice.date.desc()).first()

        ref = 0
        if prev_close:
            ref = float(prev_close.close_price)
            if ref > 5000:
                ref /= 1000

        if ref <= 0:
            # Ultimate fallback: use a small offset from current price
            ref = price * 0.99

        change = price - ref
        change_pct = (change / ref * 100) if ref > 0 else 0

        sparkline = []
        try:
            sparkline = get_intraday_sparkline(index_name, cache_get, cache_set) or []
        except Exception as se:
            logger.warning(f"Sparkline fetch failed for {index_name}: {se}")
            sparkline = []

        last_valid_pt = None
        if sparkline:
            for pt in reversed(sparkline):
                if pt.get('p') and pt['p'] > 0:
                    last_valid_pt = pt
                    break
        
        # Prepare Fallback Values
        vol_fallback = int(latest.volume or 0)
        # Convert DB value to Billions
        # - If > 1 billion: raw VND, divide by 1e9
        # - If > 100,000: likely in millions, divide by 1000
        # - If < 10,000: already in Tỷ (billions), use as-is
        val_fallback = float(latest.value or 0)
        if val_fallback > 1e9:  # Raw VND (e.g., 40,717,000,000,000)
            val_fallback /= 1e9
        elif val_fallback > 100000:  # Millions (e.g., 40,717,000)
            val_fallback /= 1000
        # else: already in Tỷ (e.g., 1828.044), keep as-is

        # ... (final_ref overrides) ...
        # Use DB ref if available, else static baseline
        final_ref = ref if ref > 0 else INDEX_BASELINES.get(index_name, price * 0.99)
        
        if index_name == "HNX30" and vol_fallback <= 0:
            # SSI example fallback data only if totally empty
            vol_fallback = 1000000 
            val_fallback = 2.5

        fallback_results.append({
            "index": index_name,
            "price": round(last_valid_pt['p'], 2) if last_valid_pt else round(price, 2),
            "ref_price": round(final_ref, 2),
            "change": round((last_valid_pt['p'] - final_ref), 2) if last_valid_pt else round(change, 2),
            "change_pct": round(((last_valid_pt['p'] - final_ref)/final_ref*100), 2) if last_valid_pt and final_ref > 0 else round(change_pct, 2),
            "volume": vol_fallback, 
            "value": round(val_fallback, 3),
            "last_updated": datetime.now().isoformat() if last_valid_pt else latest.date.strftime("%Y-%m-%d"),
            "sparkline": sparkline,
            "source": ("database_plus_sparkline" if sparkline else "database")
        })
    return fallback_results

def get_market_summary_service(db: Session) -> list[dict]:
    """Fetch market summary (VNINDEX, VN30, HNX30) with Wait-for-Health VPS priority."""
    indices = ["VNINDEX", "VN30", "HNX30"]
    cache_key = "market_summary_v11_short"
    
    # 0. Short-TTL caching (2 seconds) to handle high-frequency frontend requests
    cached = cache_get(cache_key)
    if cached:
        return cached

    results = []
    processed_indices = []
    
    try:
        trading_active = is_trading_hours()
        vps_data = {}
        
        # 1. Fetch Realtime if currently trading
        if trading_active:
            from adapters.vps_adapter import get_realtime_prices_vps
            vps_data = get_realtime_prices_vps(indices)
            
            # Check if VPS returned data for ALL indices (Health Check)
            vps_healthy = vps_data and all(idx in vps_data for idx in indices)
            
            if vps_healthy:
                logger.info("Market OPEN: VPS healthy. Skipping VCI.")
                for idx in indices:
                    processed = _process_market_row(pd.Series({('listing', 'symbol'): idx}), idx, db, vps_data)
                    if processed:
                        results.append(processed)
                        processed_indices.append(idx)
            else:
                # VCI Fallback during trading
                logger.warning(f"Market OPEN: VPS incomplete ({len(vps_data) if vps_data else 0}/3). Trying VCI.")
                from vnstock import Trading
                df_indices = Trading(source='VCI').price_board(indices)
                if df_indices is not None and not df_indices.empty:
                    for _, row in df_indices.iterrows():
                        idx_name = row.get(('listing', 'symbol'))
                        if idx_name:
                            processed = _process_market_row(row, idx_name, db, vps_data)
                            if processed:
                                results.append(processed)
                                processed_indices.append(idx_name)
        else:
            logger.info("Market CLOSED/WEEKEND: Bypassing live fetch, using DB history (Session N vs N-1).")
            # When closed, we strictly use DB fallback logic which handles Session N/N-1
            # results remains empty here to trigger Step 3
            pass

    except Exception as e:
        logger.error(f"Market fetch failed: {e}")

    # 3. Final Fallback from DB/History for any missing indices (including all indices if market closed)
    if len(results) < len(indices):
        missing = [idx for idx in indices if idx not in processed_indices]
        fallback_results = _get_market_fallback(db, missing)
        results.extend(fallback_results)
            
    # Sort results to match requested order
    results.sort(key=lambda x: indices.index(x['index']) if x['index'] in indices else 99)
    
    if results:
        # Cache for 2 seconds (L1 RAM + L2 Redis)
        cache_set(cache_key, results, 2)
        
    return results

# --- TEST DATA MECHANISM (7-DAY TESTING) ---

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
def get_intraday_data_service(ticker: str) -> list[dict]:
    """
    Fetch and normalize intraday data for a specific ticker.
    Supports VNINDEX, VN30, HNX30 and stocks.
    """
    from adapters.vci_adapter import get_intraday_sparkline
    
    # Use v4 cache key logic via get_intraday_sparkline adaptor
    raw_sparkline = get_intraday_sparkline(ticker, mem_get, mem_set)
    
    # Raw sparkline format: [{"t": "09:00", "p": 1200, "v": 100}, ...]
    # Lightweight-charts expects: { time: unixtime_or_string, value: number }
    
    # We maintain the format but ensure it's clean for the frontend
    return raw_sparkline
