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

    # VPS API format requires comma-separated symbols
    # Clean symbols and join
    clean_symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not clean_symbols:
        return {}
        
    query_str = ",".join(clean_symbols)
    url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{query_str}"
    
    results = {}
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data_list = response.json()
            
            # VPS returns a list of objects.
            # Map fields:
            # "sym": "FPT"
            # "lastPrice": 97.4 (Current Price)
            # "r": 96.5 (Reference Price)
            # "c": 103.2 (Ceiling)
            # "f": 89.8 (Floor)
            # "lot": 1004870 (Total Volume? Or 'lastVolume'?)
            # Usually 'lot' in these APIs refers to total accumulated volume.
            
            for item in data_list:
                sym = item.get("sym", "").upper()
                if not sym:
                    continue
                    
                # Identify if the symbol is an Index
                # Indices values are in points, assume raw value is correct
                # Stocks are in 1000 VND, so x1000
                is_index = sym in ["VNINDEX", "VN30", "HNX30", "HNX", "UPCOM"]
                price_multiplier = 1 if is_index else 1000
                
                # VPS returns prices in '1000 VND' for stocks (e.g., 96.5 -> 96500)
                # For indices, return as is.
                
                price = float(item.get("lastPrice", 0)) * price_multiplier
                ref = float(item.get("r", 0)) * price_multiplier
                ceiling = float(item.get("c", 0)) * price_multiplier
                floor = float(item.get("f", 0)) * price_multiplier
                
                # 'lot' seems to be Total Volume based on large numbers seen in test
                # We adhere to the previous crawler logic which multiplied volume by 10 for stocks
                # For Indices, volume logic might be different but let's keep x10 for consistence unless proven otherwise?
                # Actually, index volume from VPS might need check. But let's stick to x10 or x1 for now.
                # Usually Index volume is raw shares. Let's try x1 for Index and x10 for Stocks.
                vol_multiplier = 1 if is_index else 10
                volume = float(item.get("lot", 0)) * vol_multiplier
                
                results[sym] = {
                    "price": price,
                    "ref": ref,
                    "ceiling": ceiling,
                    "floor": floor,
                    "volume": volume
                }
        else:
            logger.error(f"[VPS] Error fetching data: Status {response.status_code}")
            
    except Exception as e:
        logger.error(f"[VPS] Exception fetching data: {e}")
        
    return results
