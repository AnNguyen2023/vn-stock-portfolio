import os
import time
import redis
import json
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from decimal import Decimal

# Kết nối Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

def _safe_float(x: Any, default: float = 0.0) -> float:
    try: return float(x) if x is not None else default
    except: return default

def get_current_prices(tickers: List[str]) -> Dict[str, Any]:
    """Lấy giá Real-time từ VPS (Vẫn giữ vì nguồn này cực nhanh)"""
    if not tickers: return {}
    output = {}
    missing = []
    for t in tickers:
        t_up = t.upper().strip()
        try:
            cached = r.get(f"price:{t_up}")
            if cached: output[t_up] = json.loads(cached)
            else: missing.append(t_up)
        except: missing.append(t_up)

    if missing:
        try:
            url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{','.join(missing)}"
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                for item in res.json():
                    sym = item.get('sym')
                    last_p = float(item.get('lastPrice', 0)) * 1000
                    ref_p = float(item.get('re', 0)) * 1000
                    price_package = {"price": last_p if last_p > 0 else ref_p, "ref": ref_p}
                    r.set(f"price:{sym}", json.dumps(price_package), ex=30)
                    output[sym] = price_package
        except: pass
    return {t.upper(): output.get(t.upper(), {"price": 0, "ref": 0}) for t in tickers}

def get_historical_prices(ticker: str, period: str = "1m"):
    """
    Lấy giá lịch sử CHUẨN từ VPS Chart API.
    Bản này không dùng thư viện ngoài, không bị treo chờ xác nhận license.
    """
    symbol = ticker.upper().strip()
    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = days_map.get(period, 30)
    
    # 1. Tính toán timestamp cho VPS (Epoch time)
    end_t = int(time.time())
    start_t = int((datetime.now() - timedelta(days=days)).timestamp())

    try:
        # VPS phân biệt link lấy Index (VNINDEX) và Stock (mã CP)
        type_path = "index" if symbol == "VNINDEX" else "stock"
        url = f"https://bgapidatafeed.vps.com.vn/getchartdata/{type_path}/{symbol}"
        
        # Gọi API với timeout 5s
        res = requests.get(url, params={"resolution": "1D", "from": start_t, "to": end_t}, timeout=5)
        
        if res.status_code == 200:
            d = res.json()
            # VPS trả về: t (time), c (close), o (open), h (high), l (low)
            if 't' in d and 'c' in d:
                result = []
                for i in range(len(d['t'])):
                    date_str = datetime.fromtimestamp(d['t'][i]).strftime('%Y-%m-%d')
                    result.append({
                        "date": date_str, 
                        "close": float(d['c'][i])
                    })
                print(f"--- [CRAWLER] Da lay {len(result)} ngay cho {symbol} tu VPS ---")
                return result
        
        print(f"--- [CRAWLER] VPS khong nhan ma {symbol} ---")
    except Exception as e:
        print(f"--- [CRAWLER LOI] {symbol}: {e} ---")
    
    return []