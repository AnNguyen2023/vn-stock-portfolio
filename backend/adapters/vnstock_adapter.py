# adapters/vnstock_adapter.py
import json
from vnstock import Vnstock
from core.redis_client import get_redis

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

def get_financial_ratios(ticker: str, memory_cache_get_fn, memory_cache_set_fn) -> dict:
    """
    Fetch financial ratios (PE, ROE, ROA, Market Cap) from vnstock.
    Uses Redis and Memory caching (24h).
    """
    ticker = ticker.upper()
    cache_key = f"ratios:{ticker}"
    
    # 1. Try Memory Cache
    cached_mem = memory_cache_get_fn(cache_key)
    if cached_mem and cached_mem.get("market_cap", 0) < 1e17:
        return cached_mem
        
    # 2. Try Redis Cache
    if REDIS_AVAILABLE:
        try:
            cached_redis = redis_client.get(cache_key)
            if cached_redis:
                r_obj = json.loads(cached_redis)
                if r_obj.get("market_cap", 0) < 1e17:
                    # Backfill memory
                    memory_cache_set_fn(cache_key, r_obj, 86400)
                    return r_obj
                else:
                    # Invalidate corrupted cache
                    redis_client.delete(cache_key)
        except Exception:
            pass

    # 3. Fetch from Vnstock
    try:
        stock = Vnstock().stock(symbol=ticker)
        df_ratio = stock.finance.ratio(period='yearly', lang='vi')
        
        if not df_ratio.empty:
            latest = df_ratio.iloc[0]
            pe = latest.get(('Chỉ tiêu định giá', 'P/E')) or latest.get('priceToEarning') or 0
            
            mc_bil = latest.get(('Chỉ tiêu định giá', 'Vốn hóa (Tỷ đồng)'))
            market_cap = 0
            if mc_bil:
                mc_val = float(mc_bil)
                market_cap = mc_val if mc_val > 1e9 else mc_val * 1e9
            
            roe = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROE (%)')) or 0
            roa = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROA (%)')) or 0
            
            r_obj = {
                "pe": float(pe),
                "market_cap": float(market_cap),
                "roe": float(roe),
                "roa": float(roa)
            }
            
            # Save to Caches
            memory_cache_set_fn(cache_key, r_obj, 86400)
            if REDIS_AVAILABLE:
                redis_client.setex(cache_key, 86400, json.dumps(r_obj))
                
            return r_obj
    except Exception as e:
        print(f"[ADAPTER] Vnstock error for {ticker}: {e}")
        
    return {"pe": 0, "market_cap": 0, "roe": 0, "roa": 0}

def get_all_symbols():
    """Fetch all symbols by exchange (HSX, HNX, UPCOM)."""
    try:
        ls = Vnstock().stock(symbol="FPT").listing
        df = ls.symbols_by_exchange()
        return df
    except Exception as e:
        print(f"[ADAPTER] Vnstock listing error: {e}")
        return None
