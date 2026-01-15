# adapters/vci_adapter.py
import json
import time
import pandas as pd
from core.redis_client import get_redis
from core.logger import logger
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
    cache_key = f"intraday_spark_v4_{ticker}"
    
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
                memory_cache_set_fn(cache_key, sparkline, 60) # 1m cache
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
        if not stock:
            return []
            
        # 1. Try today's 1m data first
        today_str = datetime.now().strftime('%Y-%m-%d')
        session_date_str = today_str
        print(f"   [{ticker}] Checking today's session: {session_date_str}")
        try:
            df = stock.quote.history(interval='1m', start=session_date_str, end=session_date_str)
        except Exception as ex:
            print(f"   [{ticker}] Today fetch failed: {ex}")
            df = None

        if df is None or df.empty:
            # 2. Fallback: find the LATEST trading day from daily history
            today_obj = datetime.now()
            yest_str = (today_obj - timedelta(days=10)).strftime('%Y-%m-%d')
            hist_1d = stock.quote.history(interval='1D', start=yest_str, end=today_str)
            
            if hist_1d is not None and not hist_1d.empty:
                latest_date_item = hist_1d['time'].iloc[-1]
                if isinstance(latest_date_item, str):
                    session_date_str = latest_date_item.split(' ')[0]
                else:
                    session_date_str = latest_date_item.strftime('%Y-%m-%d')
                
                print(f"   [{ticker}] Falling back to latest history session: {session_date_str}")
                df = stock.quote.history(interval='1m', start=session_date_str, end=session_date_str)
            else:
                return []

        if df is not None and not df.empty:
            print(f"   [{ticker}] Successfully found {len(df)} rows.")
            # Ensure time is datetime and sorted
            df['time'] = pd.to_datetime(df['time'])
            
            # CRITICAL: Filter for the intended session date only
            intended_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
            df = df[df['time'].dt.date == intended_date]
            
            if df.empty:
                print(f"   [{ticker}] NO ROWS found for SPECIFIC date: {intended_date}")
                return []
                
            df = df.sort_values('time')
            print(f"   [{ticker}] Session Data range: {df['time'].min()} to {df['time'].max()}")
            df.set_index('time', inplace=True)
            
            # UNIFY TO POINTS (Standardize Index Units)
            # Normal index prices are ~500-3000. VND prices are > 1,000,000.
            is_index = any(idx in ticker.upper() for idx in ["INDEX", "VN30", "HNX30", "HNX", "UPCOM"])
            if is_index:
                # If values are raw (e.g. 1,867,900), divide by 1000
                # Use mean to be robust against outliers/single correct points
                if df['close'].mean() > 5000:
                    df['close'] = df['close'] / 1000

            # 4. Professional Intraday Grid (9:00 AM - 3:00 PM)
            data_date = df.index[0].date()
            start_session = datetime.combine(data_date, datetime.strptime("09:00", "%H:%M").time())
            end_session = datetime.combine(data_date, datetime.strptime("15:00", "%H:%M").time())
            
            # Create a full minute-by-minute index for the session
            full_range = pd.date_range(start=start_session, end=end_session, freq='1min')
            
            # Find the actual last time in the data
            last_actual_time = df.index.max()
            
            # Reindex without filling first
            df_reindexed = df.reindex(full_range)
            
            # Only fill gaps UP TO the last actual trade time
            mask_up_to_last = df_reindexed.index <= last_actual_time
            df_reindexed.loc[mask_up_to_last] = df_reindexed.loc[mask_up_to_last].ffill()
            
            # Bfill for the time between 9:00 and first trade
            df_reindexed = df_reindexed.bfill()
            
            # Use dictionary format: { "t": time_str, "p": price, "v": volume }
            # Reset index to get 'time' as a column
            df_reindexed = df_reindexed.reset_index().rename(columns={'index': 'time'})
            
            # Downsample: 1 point every 5 minutes for 6 hour session (360 mins)
            # This gives ~72 points + end points, perfect for UI
            df_downsampled = df_reindexed.iloc[::5] if len(df_reindexed) > 100 else df_reindexed
            
            sparkline = []
            for _, row in df_downsampled.iterrows():
                p_val = row['close']
                v_val = row.get('volume', 0)
                
                sparkline.append({
                    "t": row['time'].strftime('%H:%M'),
                    "timestamp": int(row['time'].timestamp()),
                    "p": round(float(p_val), 2) if pd.notnull(p_val) else None,
                    "v": int(v_val) if pd.notnull(v_val) else 0
                })
            
            # Always ensure last point is accurate (if not null) and avoid duplicates
            last_row = df_reindexed.iloc[-1]
            last_ts = int(last_row['time'].timestamp())
            
            if not sparkline or sparkline[-1]['timestamp'] != last_ts:
                last_p = last_row['close']
                sparkline.append({
                    "t": last_row['time'].strftime('%H:%M'),
                    "timestamp": last_ts,
                    "p": round(float(last_p), 2) if pd.notnull(last_p) else None,
                    "v": int(last_row.get('volume', 0)) if pd.notnull(last_p) else 0
                })
            
            # Update Caches
            memory_cache_set_fn(cache_key, sparkline, 60)
            if REDIS_AVAILABLE:
                redis_client.setex(cache_key, 60, json.dumps(sparkline))
            
            return sparkline
            
    except BaseException as e:
        # Rate limit hit (SystemExit) or other BaseException (e.g. RetryError raised TypeError)
        logger.error(f"[ADAPTER] VCI Intraday Failed for {ticker}: {e}")
        
        # Rate limit recovery: only backoff if it's a SystemExit or explicitly mentioned
        if "Retry" in str(e) or "SystemExit" in str(e):
             memory_cache_set_fn("vci_backoff", True, 60)
             if REDIS_AVAILABLE:
                 redis_client.setex("vci_rate_limit_backoff", 60, "true")
        
        # CRITICAL FALLBACK: Use 7-day daily history if intraday fails
        print(f"   [{ticker}] Falling back to Daily history sparkline...")
        return get_sparkline_data(ticker, memory_cache_get_fn, memory_cache_set_fn)
    
    return []
