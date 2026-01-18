# adapters/vci_adapter.py
import json
import time
import pandas as pd
from core.redis_client import get_redis
from core.logger import logger
from crawler import get_historical_prices

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

def _vn_now():
    from datetime import datetime, timedelta
    return datetime.utcnow() + timedelta(hours=7)

def _is_market_open(now_dt) -> bool:
    if now_dt.weekday() >= 5:
        return False
    market_open = now_dt.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now_dt.replace(hour=15, minute=0, second=0, microsecond=0)
    return market_open <= now_dt <= market_close

def get_sparkline_data(ticker: str, memory_cache_get_fn, memory_cache_set_fn) -> list[dict]:
    """
    """
    ticker = ticker.upper()
    cache_key = f"sparkline_v2:{ticker}"
    
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
            from datetime import datetime
            sparkline = []
            for h in live_hist[-30:]: # Return more history for better context (30 days)
                dt = datetime.strptime(h["date"], "%Y-%m-%d")
                ts = int(dt.timestamp())
                sparkline.append({
                    "timestamp": ts,
                    "t": h["date"],
                    "p": float(h["close"]),
                    "v": float(h.get("volume", 0))
                })
            
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
def _normalize_intraday_df(df: pd.DataFrame, session_date_str: str) -> pd.DataFrame:
    df = df.copy()

    # Identify time column
    time_col = None
    for col in ["time", "timestamp", "datetime", "date", "t"]:
        if col in df.columns:
            time_col = col
            break

    if time_col is None:
        return pd.DataFrame()

    df["time"] = df[time_col]
    time_sample = df["time"].dropna()
    if time_sample.empty:
        return pd.DataFrame()

    # Normalize time to datetime
    sample_val = time_sample.iloc[0]
    if isinstance(sample_val, (int, float)) and not isinstance(sample_val, bool):
        # Heuristic: ms vs sec
        unit = "ms" if sample_val > 1e12 else "s"
        df["time"] = pd.to_datetime(df["time"], unit=unit, errors="coerce")
    else:
        # If time is only HH:MM, attach session date
        if isinstance(sample_val, str) and len(sample_val) <= 8 and ":" in sample_val:
            df["time"] = pd.to_datetime(
                session_date_str + " " + df["time"].astype(str),
                errors="coerce"
            )
        else:
            df["time"] = pd.to_datetime(df["time"], errors="coerce")

    # Normalize price/volume columns
    price_col = None
    for col in ["close", "price", "last", "p", "match_price"]:
        if col in df.columns:
            price_col = col
            break
    if not price_col:
        return pd.DataFrame()
    df["close"] = pd.to_numeric(df[price_col], errors="coerce")

    vol_col = None
    for col in ["volume", "vol", "v", "match_vol", "accumulated_volume"]:
        if col in df.columns:
            vol_col = col
            break
    df["volume"] = pd.to_numeric(df[vol_col], errors="coerce") if vol_col else 0

    df = df.dropna(subset=["time", "close"])
    return df

def get_intraday_sparkline(
    ticker: str,
    memory_cache_get_fn,
    memory_cache_set_fn,
    fallback_session_date: str | None = None,
    fallback_close: float | None = None,
) -> list[dict]:
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
        print(f"   [{ticker}] VCI Backoff active. Skipping Intraday, using Daily Sparkline...")
        return get_sparkline_data(ticker, memory_cache_get_fn, memory_cache_set_fn)

    try:
        from vnstock import Vnstock
        from datetime import datetime, timedelta
        
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        if not stock:
            return []
            
        # 1. Try today's 1m data first
        vn_now = _vn_now()
        market_open = _is_market_open(vn_now)
        today_str = vn_now.strftime('%Y-%m-%d')
        session_date_str = fallback_session_date if (fallback_session_date and not market_open) else today_str
        print(f"   [{ticker}] Checking today's session: {session_date_str}")
        try:
            df = stock.quote.history(interval='1m', start=session_date_str, end=session_date_str)
        except Exception as ex:
            print(f"   [{ticker}] Today fetch failed: {ex}")
            df = None

        if df is None or df.empty:
            # 2. Try intraday endpoint (if history 1m is unavailable)
            try:
                intraday_df = stock.quote.intraday(page_size=1000)
            except Exception as ex:
                intraday_df = None

            if intraday_df is not None and not intraday_df.empty:
                df = _normalize_intraday_df(intraday_df, session_date_str)
                if df is not None and not df.empty:
                    df = df.sort_values("time")
                    session_date_str = df["time"].iloc[-1].strftime("%Y-%m-%d")

        if market_open and (df is None or df.empty):
            print(f"   [{ticker}] Market open but intraday is empty. Returning no data.")
            return []

        if df is None or df.empty:
            # 3. Fallback: find the LATEST trading day from daily history
            today_obj = vn_now
            yest_str = (today_obj - timedelta(days=10)).strftime('%Y-%m-%d')
            hist_1d = stock.quote.history(interval='1D', start=yest_str, end=today_str)
            
            if hist_1d is not None and not hist_1d.empty:
                hist_1d = hist_1d.copy()
                hist_1d['time'] = pd.to_datetime(hist_1d['time'], errors='coerce')
                hist_1d = hist_1d.dropna(subset=['time'])
                hist_1d = hist_1d.sort_values('time')
                latest_date_item = hist_1d['time'].iloc[-1]
                hist_latest_date = latest_date_item.strftime('%Y-%m-%d')
                session_date_str = fallback_session_date or hist_latest_date
                
                print(f"   [{ticker}] Falling back to latest history session: {session_date_str}")
                df = stock.quote.history(interval='1m', start=session_date_str, end=session_date_str)
                
                if (df is None or df.empty) and not market_open:
                    # If intraday is unavailable, synthesize a flat session using latest close
                    last_close = fallback_close
                    if last_close is None and 'close' in hist_1d.columns:
                        last_close = hist_1d['close'].iloc[-1]
                    if last_close is not None:
                        start_session = datetime.combine(latest_date_item.date(), datetime.strptime("09:00", "%H:%M").time())
                        end_session = datetime.combine(latest_date_item.date(), datetime.strptime("15:00", "%H:%M").time())
                        full_range = pd.date_range(start=start_session, end=end_session, freq='1min')
                        df = pd.DataFrame({
                            "time": full_range,
                            "close": [float(last_close)] * len(full_range),
                            "volume": [0] * len(full_range),
                        })
            else:
                # If cannot find last session or history failed
                print(f"   [{ticker}] No fallback session found. Using Daily Sparkline.")
                return get_sparkline_data(ticker, memory_cache_get_fn, memory_cache_set_fn)

        if df is not None and not df.empty:
            print(f"   [{ticker}] Successfully found {len(df)} rows.")
            # Ensure time is datetime and sorted
            df['time'] = pd.to_datetime(df['time'])
            
            # CRITICAL: Filter for the intended session date only
            intended_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
            df = df[df['time'].dt.date == intended_date]
            
            if df.empty:
                print(f"   [{ticker}] NO ROWS found for SPECIFIC date: {intended_date}. Using Daily Sparkline.")
                return get_sparkline_data(ticker, memory_cache_get_fn, memory_cache_set_fn)
                
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
