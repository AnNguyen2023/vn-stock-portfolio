# services/market_service.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import time
from typing import Iterable, Any, Optional, Union
import json
import concurrent.futures
import pandas as pd
from vnstock import Trading
from sqlalchemy.orm import Session

import models
import crawler
from core.db import SessionLocal
from core.redis_client import get_redis
from core.logger import logger

# New Adapters
from adapters import vci_adapter, vnstock_adapter

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

# --- IN-MEMORY CACHE (FALLBACK KHI REDIS DIE) ---
MEMORY_CACHE: dict[str, tuple[Any, float]] = {}

def mem_get(key: str) -> Optional[Any]:
    """
    Retrieves data from RAM if it exists and has not expired.

    Args:
        key (str): Cache key.

    Returns:
        Optional[Any]: Cached value or None if expired/not found.
    """
    if key in MEMORY_CACHE:
        val, exp = MEMORY_CACHE[key]
        if time.time() < exp:
            return val
        else:
            del MEMORY_CACHE[key]
    return None

def mem_set(key: str, val: Any, ttl: int) -> None:
    """
    Stores data in RAM with a Time To Live (TTL).

    Args:
        key (str): Cache key.
        val (Any): Value to store.
        ttl (int): Time to live in seconds.
    """
    MEMORY_CACHE[key] = (val, time.time() + ttl)

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
        sparkline = vci_adapter.get_sparkline_data(t, mem_get, mem_set)

        # 4. FINANCIAL RATIOS (Dùng Adapter)
        ratios = vnstock_adapter.get_financial_ratios(t, mem_get, mem_set)

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
                    exist = db.query(models.HistoricalPrice).filter_by(ticker=symbol, date=d).first()
                    if not exist:
                        db.add(
                            models.HistoricalPrice(
                                ticker=symbol,
                                date=d,
                                close_price=Decimal(str(item["close"])),
                                volume=Decimal(str(item.get("volume", 0))),
                                value=Decimal(str(item.get("value", 0))),
                            )
                        )
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
                        db.add(
                            models.HistoricalPrice(
                                ticker=ticker,
                                date=d,
                                close_price=Decimal(str(item["close"])),
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
    if REDIS_AVAILABLE:
        try:
            redis_client.delete(cache_key)
        except:
            pass
    if cache_key in MEMORY_CACHE:
        del MEMORY_CACHE[cache_key]
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
        # Thử lấy từ Memory
        cached_res = mem_get(result_cache_key)
        if cached_res:
            return cached_res
        
        # Thử lấy từ Redis
        if REDIS_AVAILABLE:
            try:
                raw_redis = redis_client.get(result_cache_key)
                if raw_redis:
                    res_obj = json.loads(raw_redis)
                    mem_set(result_cache_key, res_obj, 10) # Backfill memory 10s
                    return res_obj
            except:
                pass

    # 1. Batch Metadata Fetch (LONG-TERM CACHE 1H)
    sec_metadata = {}
    missing_meta_tickers = []
    
    for t in tickers_upper:
        meta_key = f"sec_meta_v1:{t}"
        # Ưu tiên lấy từ Memory (vì 1h là rất lâu)
        cached_meta = mem_get(meta_key)
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
                mem_set(f"sec_meta_v1:{sec.symbol}", meta_obj, 28800)
                if REDIS_AVAILABLE:
                    try:
                        redis_client.setex(f"sec_meta_v1:{sec.symbol}", 28800, json.dumps(meta_obj))
                    except:
                        pass

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
        mem_set(result_cache_key, ordered_results, 10)
        if REDIS_AVAILABLE:
            try:
                redis_client.setex(result_cache_key, 10, json.dumps(ordered_results))
            except:
                pass
                
    return ordered_results


def get_trending_indicator(ticker: str) -> dict:
    """
    Calculates the price trend indicator based on the last 5 trading sessions.
    Results are cached in Redis (if available) and Memory for 5 minutes.

    Args:
        ticker (str): Ticker symbol.

    Returns:
        dict: Trending data including 'trend' (string) and 'change_pct' (float).
    """
    ticker = ticker.upper()
    cache_key = f"trending:{ticker}"
    
    # 1. Try Cache layers
    if REDIS_AVAILABLE:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Redis cache read failed for {cache_key}: {e}")
    
    cached_mem = mem_get(cache_key)
    if cached_mem:
        return cached_mem
    
    # 2. Calculate from DB
    with SessionLocal() as db:
        prices = (
            db.query(models.HistoricalPrice)
            .filter(models.HistoricalPrice.ticker == ticker)
            .order_by(models.HistoricalPrice.date.desc())
            .limit(5)
            .all()
        )
        
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
        
        # 3. Save to Cache
        if REDIS_AVAILABLE:
            try:
                redis_client.setex(cache_key, 300, json.dumps(result))
            except Exception as e:
                logger.debug(f"Redis cache write failed for {cache_key}: {e}")
        
        mem_set(cache_key, result, 300)
        return result

def _process_market_row(row: Any, index_name: str, db: Session) -> Optional[dict]:
    """Helper to process a single index row from the VCI price board."""
    try:
        match_price = row[('match', 'match_price')]
        ref_price = row[('match', 'reference_price')]
        match_vol = row[('match', 'match_vol')]
        
        price = float(match_price or ref_price or 0)
        ref = float(ref_price or 0)
        
        # Unify to points
        if price > 10000:
            price /= 1000
            ref /= 1000

        if price <= 0 or ref <= 0:
            return None

        change = price - ref
        change_pct = (change / ref * 100)
        volume = float(match_vol or 0)
        
        # Determine value (billions)
        total_val = row.get(('match', 'total_value')) or row.get(('match', 'total_val')) or 0
        value = float(total_val) / 1e9
        
        if value == 0:
            latest_hist = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == index_name
            ).order_by(models.HistoricalPrice.date.desc()).first()
            if latest_hist and latest_hist.value > 0:
                value = float(latest_hist.value) / (1e9 if latest_hist.value > 1e6 else 1)
        
        from adapters.vci_adapter import get_intraday_sparkline
        sparkline = get_intraday_sparkline(index_name, mem_get, mem_set)

        return {
            "index": index_name,
            "date": datetime.now().strftime('%d/%m/%Y'),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(volume),
            "value": round(value, 2),
            "sparkline": sparkline
        }
    except Exception as e:
        logger.debug(f"Row processing failed for {index_name}: {e}")
        return None

def _get_market_fallback(db: Session, indices: list[str]) -> list[dict]:
    """Helper for database fallback synchronization."""
    fallback_results = []
    from adapters.vci_adapter import get_intraday_sparkline
    
    for index_name in indices:
        latest = db.query(models.HistoricalPrice).filter(
            models.HistoricalPrice.ticker == index_name
        ).order_by(models.HistoricalPrice.date.desc()).first()
        
        if not latest:
            continue

        prev = db.query(models.HistoricalPrice).filter(
            models.HistoricalPrice.ticker == index_name, 
            models.HistoricalPrice.date < latest.date
        ).order_by(models.HistoricalPrice.date.desc()).first()
        
        price = float(latest.close_price)
        ref = float(prev.close_price) if prev else price
        
        if price > 10000:
            price /= 1000
            ref /= 1000
            
        change = price - ref
        change_pct = (change / ref * 100) if ref > 0 else 0
        
        sparkline = get_intraday_sparkline(index_name, mem_get, mem_set)
        
        fallback_results.append({
            "index": index_name,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(latest.volume or 0),
            "value": float(latest.value or 0) / (1e9 if (latest.value or 0) > 1e6 else 1),
            "last_updated": latest.date.strftime("%Y-%m-%d"),
            "sparkline": sparkline,
            "source": "database"
        })
    return fallback_results

def get_market_summary_service(db: Session) -> list[dict]:
    """
    Orchestrates market summary retrieval. 
    Tries VCI API first with throttling, then falls back to database.
    """
    indices = ["VNINDEX", "VN30", "HNX30"]
    cache_key = "market_summary_full_v3"
    
    # 0. Throttling
    cached = mem_get(cache_key)
    if cached:
        return cached

    # 1. API Call with Backoff logic
    backoff = mem_get("vci_backoff")
    if not backoff:
        try:
            df = Trading(source='VCI').price_board(indices)
            if df is not None and not df.empty:
                results = []
                for index_name in indices:
                    # Find matching row in multi-index DF
                    row = None
                    for i in range(len(df)):
                        if df.iloc[i][('listing', 'symbol')] == index_name:
                            row = df.iloc[i]
                            break
                    
                    if row is not None:
                        processed = _process_market_row(row, index_name, db)
                        if processed:
                            results.append(processed)
                
                if len(results) == len(indices):
                    mem_set(cache_key, results, 10)
                    return results
        except Exception as e:
            logger.error(f"VCI API Market Summary failed: {e}")
            mem_set("vci_backoff", True, 60)

    # 2. Database Fallback
    logger.info("Falling back to database for market summary")
    fallback = _get_market_fallback(db, indices)
    if fallback:
        mem_set(cache_key, fallback, 10)
        return fallback
    
    from core.exceptions import ExternalServiceError
    raise ExternalServiceError("Market", "Failed to retrieve market summary from all sources")
