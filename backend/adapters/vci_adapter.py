# adapters/vci_adapter.py
import json
import time
from core.redis_client import get_redis
from crawler import get_historical_prices

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

def get_sparkline_data(ticker: str, memory_cache_get_fn, memory_cache_set_fn) -> list[float]:
    """
    Fetch sparkline (last 7 sessions) with multi-level caching.
    Priority: Memory -> Redis -> API.
    """
    ticker = ticker.upper()
    cache_key = f"sparkline:{ticker}"
    
    # 1. Try Memory Cache
    sparkline = memory_cache_get_fn(cache_key)
    if sparkline:
        return sparkline
        
    # 2. Try Redis Cache
    if REDIS_AVAILABLE:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                sparkline = json.loads(cached)
                # Backfill memory cache
                memory_cache_set_fn(cache_key, sparkline, 3600)
                return sparkline
        except Exception:
            pass

    # 3. Fetch from External API (VCI)
    # Check for global backoff
    backoff = memory_cache_get_fn("vci_backoff") or (REDIS_AVAILABLE and redis_client.get("vci_rate_limit_backoff"))
    if backoff:
        return []

    try:
        # Fetch 1 month data to ensure we have at least 7 sessions
        live_hist = get_historical_prices(ticker, period="1m")
        if live_hist:
            sparkline = [float(h["close"]) for h in live_hist[-7:]]
            
            # Update Caches
            memory_cache_set_fn(cache_key, sparkline, 3600)
            if REDIS_AVAILABLE:
                redis_client.setex(cache_key, 3600, json.dumps(sparkline))
            
            return sparkline
    except BaseException:
        # Rate limit hit -> Enable global backoff for 60s
        memory_cache_set_fn("vci_backoff", True, 60)
        if REDIS_AVAILABLE:
            redis_client.setex("vci_rate_limit_backoff", 60, "true")
        print(f"[ADAPTER] VCI Rate Limit hit for {ticker}")
    
    return []
