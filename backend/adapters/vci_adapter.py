# adapters/vci_adapter.py
import json
import time
import pandas as pd
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
def get_intraday_sparkline(ticker: str, memory_cache_get_fn, memory_cache_set_fn) -> list[float]:
    """
    Fetch intraday sparkline (1m interval) for the most recent session.
    """
    ticker = ticker.upper()
    cache_key = f"intraday_spark_v3_{ticker}"
    
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
                memory_cache_set_fn(cache_key, sparkline, 300) # 5m cache
                return sparkline
        except Exception:
            pass

    # 3. Fetch from API
    # Check for global backoff
    backoff = memory_cache_get_fn("vci_backoff") or (REDIS_AVAILABLE and redis_client.get("vci_rate_limit_backoff"))
    if backoff:
        print(f"   [{ticker}] VCI Backoff active. Skipping...")
        return []

    try:
        from vnstock import Vnstock
        from datetime import datetime
        from datetime import datetime, timedelta
        
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        
        # 1. First, find the LATEST trading day from daily history (very fast)
        # This tells us exactly which day to fetch minute data for.
        # Robust latest session finder
        # We fetch last 10 days of daily history to know what's the latest data day
        hist_1d = stock.quote.history(interval='1D')
        if hist_1d is None or hist_1d.empty:
            return []
        
        # Use 'time' column instead of index, as index might be RangeIndex
        latest_date_item = hist_1d['time'].iloc[-1]
        if isinstance(latest_date_item, str):
            latest_date_str = latest_date_item.split(' ')[0]
        else:
            latest_date_str = latest_date_item.strftime('%Y-%m-%d')
        
        print(f"   [{ticker}] Latest trading session: {latest_date_str}")
        
        # 2. Fetch Intraday 1-minute data for THAT session
        df = stock.quote.history(interval='1m', start=latest_date_str, end=latest_date_str)

        if df is not None and not df.empty:
            # Ensure time is datetime and sorted
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')
            df.set_index('time', inplace=True)
            
            # UNIFY TO POINTS (Standardize Index Units)
            # Normal index prices are ~500-3000. VND prices are > 1,000,000.
            is_index = any(idx in ticker.upper() for idx in ["INDEX", "VN30", "HNX30", "VNINDEX"])
            if is_index:
                # If values are raw (e.g. 1,867,900), divide by 1000
                if df['close'].max() > 10000:
                    df['close'] = df['close'] / 1000

            # 4. Professional Intraday Grid (9:00 AM - 3:00 PM)
            data_date = df.index[0].date()
            start_session = datetime.combine(data_date, datetime.strptime("09:00", "%H:%M").time())
            end_session = datetime.combine(data_date, datetime.strptime("15:00", "%H:%M").time())
            
            # Create a full minute-by-minute index for the session
            # This automatically creates the "lunch break" gap which we will ffill
            full_range = pd.date_range(start=start_session, end=end_session, freq='1min')
            
            # Use 'last' to keep the latest price of each minute, then forward fill gaps
            df_reindexed = df.reindex(full_range, method='ffill')
            
            # Bfill for the time between 9:00 and first trade
            df_reindexed = df_reindexed.ffill().bfill()
            
            # Extract close prices
            sparkline = [float(c) for c in df_reindexed['close'].tolist()]
            
            # Downsample for UI (60-80 points is plenty for sparkline)
            if len(sparkline) > 80:
                step = len(sparkline) // 60
                sparkline = sparkline[::step]
            
            # Ensure the very last actual price is included for accuracy
            sparkline.append(float(df['close'].iloc[-1]))
            
            # Update Caches
            memory_cache_set_fn(cache_key, sparkline, 300)
            if REDIS_AVAILABLE:
                redis_client.setex(cache_key, 300, json.dumps(sparkline))
            
            return sparkline
            
    except BaseException as e:
        # Rate limit hit (SystemExit) or other BaseException
        memory_cache_set_fn("vci_backoff", True, 60)
        if REDIS_AVAILABLE:
            redis_client.setex("vci_rate_limit_backoff", 60, "true")
        print(f"[ADAPTER] VCI Rate Limit hit or Critical Error for {ticker}: {e}")
    
    return []
