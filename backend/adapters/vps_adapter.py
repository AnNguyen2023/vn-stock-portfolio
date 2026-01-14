import requests
import logging

# Configure basic logging
logger = logging.getLogger(__name__)

def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely converts value to float, handling strings with commas and empty values."""
    if val is None:
        return default
    try:
        # Convert to string and strip commas (common in VPS API)
        s_val = str(val).replace(",", "").strip()
        if not s_val:
            return default
        return float(s_val)
    except (ValueError, TypeError):
        return default

def get_realtime_prices_vps(symbols: list[str]) -> dict:
    """
    Fetches realtime price data from VPS API.
    Returns a dict: { "SYMBOL": { "price": ..., "ref": ..., "ceiling": ..., "floor": ..., "volume": ... }, ... }
    """
    if not symbols:
        return {}

    # Clean symbols
    clean_symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not clean_symbols:
        return {}

    # Divide symbols into Stocks and Indices
    # Map index names to VPS numeric codes
    indices_map = {
        "VNINDEX": "10",
        "VN30": "11",
        "HNX30": "12"
    }
    
    req_indices_codes = [indices_map[s] for s in clean_symbols if s in indices_map]
    req_stocks = [s for s in clean_symbols if s not in indices_map]
    
    results = {}

    # 1. Fetch Stocks
    if req_stocks:
        query_str = ",".join(req_stocks)
        url_stocks = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{query_str}"
        try:
            resp = requests.get(url_stocks, timeout=5)
            if resp.status_code == 200:
                for item in resp.json():
                    sym = item.get("sym", "").upper()
                    if not sym: continue
                    
                    price = _safe_float(item.get("lastPrice")) * 1000
                    ref = _safe_float(item.get("r")) * 1000
                    volume = _safe_float(item.get("lot")) * 10 
                    
                    val_raw = item.get("totalVal") or item.get("totalValue") or item.get("val") or 0
                    value = _safe_float(val_raw) / 1e9 if val_raw else 0
                    
                    results[sym] = {
                        "price": price, "ref": ref, 
                        "ceiling": float(item.get("c", 0)) * 1000,
                        "floor": float(item.get("f", 0)) * 1000,
                        "volume": volume, "value": value
                    }
        except Exception as e:
            logger.error(f"[VPS] Stock fetch error: {e}")

    # 2. Fetch Indices
    if req_indices_codes:
        codes_str = ",".join(req_indices_codes)
        url_indices = f"https://bgapidatafeed.vps.com.vn/getlistindexdetail/{codes_str}"
        try:
            resp = requests.get(url_indices, timeout=5)
            if resp.status_code == 200:
                index_data = resp.json()
                # Reverse map codes back to symbols
                code_to_sym = {v: k for k, v in indices_map.items()}
                
                for item in index_data:
                    code = str(item.get("mc", ""))
                    sym = code_to_sym.get(code)
                    if not sym: continue
                    
                    price = _safe_float(item.get("cIndex"))
                    volume = _safe_float(item.get("vol"))
                    
                    # ot field: change|change%|value|up|down|ref
                    ot = item.get("ot", "")
                    ot_parts = ot.split("|") if ot else []
                    
                    value = 0
                    if len(ot_parts) >= 3 and ot_parts[2]:
                        # Third part is liquidity (Value). 
                        # VPS Index API 'ot' value part is in MILLIONS of VND.
                        # We want it in BILLIONS of VND. So divide by 1000.
                        val_raw = _safe_float(ot_parts[2])
                        value = val_raw / 1000
                        logger.info(f"[VPS] {sym} value from ot: {val_raw} -> {value} billion")
                    
                    # CRITICAL FIX: If value is still 0, estimate from volume
                    if value == 0 and volume > 0:
                        # Estimate: value ≈ volume * average_price / 1000 (to get billions)
                        # For indices, use current price as proxy for average
                        value = (volume * price) / 1000
                        logger.warning(f"[VPS] {sym} estimated value from volume: {value:.3f} billion")
                    
                    # Safe float conversion for change value (ot_parts[0])
                    change_val = _safe_float(ot_parts[0]) if len(ot_parts) > 0 else 0
                        
                    results[sym] = {
                        "price": price, 
                        "ref": price - change_val,
                        "ceiling": 0,
                        "floor": 0,
                        "volume": volume, 
                        "value": value
                    }
                    logger.info(f"[VPS] {sym}: price={price}, vol={volume}, value={value}")
        except Exception as e:
            logger.error(f"[VPS] Index fetch error: {e}")
            
    return results
