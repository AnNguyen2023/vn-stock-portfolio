from __future__ import annotations
import concurrent.futures
import json
from typing import Optional
from services.market.cache import mem_get, mem_set, REDIS_AVAILABLE, redis_client
from services.market.data_processor import _process_single_ticker
import models
from core.db import SessionLocal
from crawler import get_current_prices

from fastapi import BackgroundTasks

def get_watchlist_detail_service(tickers: list[str], background_tasks: Optional[BackgroundTasks] = None, watchlist_id: int | None = None) -> list[dict]:
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
            except Exception as e:
                from core.logger import logger
                logger.debug(f"Redis cache fetch error: {e}")

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
                    except Exception as e:
                        from core.logger import logger
                        logger.debug(f"Redis setex error: {e}")

    # 2. Lấy giá Real-time (Batch Request)
    try:
        current_prices = get_current_prices(tickers_upper)
    except Exception as e:
        from core.logger import logger
        logger.warning(f"Failed to fetch real-time prices: {e}")
        current_prices = {}

    # 3. Batch Trending Data (One DB Session for all)
    trending_data_map = {}
    try:
        from services.market.data_processor import get_trending_indicators_batch
        # Use existing SessionLocal context if possible, or create new short-lived one
        # To avoid blocking, we use a dedicated session for this batch read
        with SessionLocal() as db:
            trending_data_map = get_trending_indicators_batch(tickers_upper, db)
    except Exception as e:
        print(f"[ERR] Batch Trending Fetch Failed: {e}")

    results = []
    
    # 4. Chạy Parallel xử lý từng mã
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {
            executor.submit(
                _process_single_ticker, 
                t, 
                current_prices.get(t, {}), 
                sec_metadata.get(t),
                trending_data_map.get(t) # Pass pre-fetched trending data
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
            except Exception as e:
                from core.logger import logger
                logger.debug(f"Redis setex error: {e}")
    
    # Check if any ticker needs historical sync
    if background_tasks:
        from services.market.sync_tasks import sync_historical_task
        from core.logger import logger
        
        tickers_to_sync = []
        for r in ordered_results:
            trending = r.get("trending")
            if trending and isinstance(trending, dict) and trending.get("needs_sync"):
                tickers_to_sync.append(r["ticker"])
        
        if tickers_to_sync:
            logger.info(f"Triggering background sync for {len(tickers_to_sync)} tickers in watchlist.")
            for t in set(tickers_to_sync): # Deduplicate
                background_tasks.add_task(sync_historical_task, t, '1m')

    return ordered_results
