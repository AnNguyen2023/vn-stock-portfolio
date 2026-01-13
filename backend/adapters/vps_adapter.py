import requests
import logging

# Configure basic logging
logger = logging.getLogger(__name__)

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
                    
                    price = float(item.get("lastPrice", 0)) * 1000
                    ref = float(item.get("r", 0)) * 1000
                    volume = float(item.get("lot", 0)) * 10 
                    
                    val_raw = item.get("totalVal") or item.get("totalValue") or item.get("val") or 0
                    value = float(str(val_raw).replace(",", "")) / 1e9 if val_raw else 0
                    
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
                    
                    price = float(item.get("cIndex", 0))
                    # ot field: change|change%|value|up|down|ref
                    ot = item.get("ot", "")
                    ot_parts = ot.split("|") if ot else []
                    
                    value = 0
                    if len(ot_parts) >= 3:
                        # Third part is liquidity (Value). 
                        # Based on observation, VPS Index API 'ot' value part is usually in MILLIONS of VND.
                        # We want it in BILLIONS of VND. So divide by 1000.
                        raw_val = float(ot_parts[2].replace(",", ""))
                        value = raw_val / 1000
                    else:
                        # Fallback to 'value' field if present
                        val_raw = item.get("value") or 0
                        value = float(str(val_raw).replace(",", "")) / 1000
                        
                    results[sym] = {
                        "price": price, 
                        "ref": price - (float(ot_parts[0]) if len(ot_parts) > 0 else 0),
                        "ceiling": 0,
                        "floor": 0,
                        "volume": float(item.get("vol", 0)), 
                        "value": value
                    }
        except Exception as e:
            logger.error(f"[VPS] Index fetch error: {e}")
            
    return results
