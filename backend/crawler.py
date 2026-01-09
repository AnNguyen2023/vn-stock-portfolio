"""
crawler.py - Module lấy dữ liệu giá cổ phiếu & VNINDEX từ vnstock3
"""
from vnstock import Vnstock, Trading
from datetime import datetime, timedelta
import redis
import json
import requests

# --- CẤU HÌNH ---
CACHE_DURATION = 30  # thời gian cache (giây)

# --- CẤU HÌNH REDIS CACHE ---
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    print("[CRAWLER] Redis không khả dụng, chạy không cache")

def get_prices_from_vps(tickers: list) -> dict:
    """
    Lấy giá real-time từ VPS API (Nhanh và không giới hạn)
    """
    if not tickers:
        return {}
    
    try:
        url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{','.join(tickers)}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            result = {}
            for item in data:
                sym = item.get('sym')
                if sym:
                    # VPS trả về đơn vị 1 (vd: 96.5), cần nhân 1000 cho VND
                    result[sym] = {
                        "price": float(item.get('lastPrice') or item.get('r') or 0) * 1000,
                        "ref": float(item.get('r') or 0) * 1000,
                        "ceiling": float(item.get('c') or 0) * 1000,
                        "floor": float(item.get('f') or 0) * 1000,
                        "volume": float(item.get('lot') or 0) * 10 # lot là khối lượng (thường x10)
                    }
            return result
    except Exception as e:
        print(f"[CRAWLER] Lỗi lấy giá từ VPS: {e}")
    return {}

def get_current_prices(tickers: list) -> dict:
    """
    Lấy giá hiện tại: Ưu tiên VPS -> Fallback VCI (vnstock3)
    """
    if not tickers:
        return {}
    
    # 1. KIỂM TRA CACHE
    cache_key = "stock_prices"
    if REDIS_AVAILABLE:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            all_prices = json.loads(cached_data)
            if all(t in all_prices for t in tickers):
                return {t: all_prices[t] for t in tickers}
    
    # 2. ƯU TIÊN LẤY TỪ VPS
    result = get_prices_from_vps(tickers)
    
    # 3. NẾU THIẾU MÃ HOẶC VPS LỖI -> GỌI VCI (VNSTOCK3) LÀM FALLBACK
    missing_tickers = [t for t in tickers if t not in result or result[t]["price"] == 0]
    
    if missing_tickers:
        try:
            print(f"[CRAWLER] Lấy {len(missing_tickers)} mã từ VCI làm fallback...")
            df = Trading(source='VCI').price_board(missing_tickers)
            
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    try:
                        symbol = row[('listing', 'symbol')]
                        m_price = row[('match', 'match_price')]
                        r_price = row[('match', 'reference_price')]
                        c_price = row[('match', 'ceiling_price')]
                        f_price = row[('match', 'floor_price')]
                        m_vol = row[('match', 'match_vol')]
                        
                        price = float(m_price or r_price or 0)
                        
                        result[symbol] = {
                            "price": price,
                            "ref": float(r_price or 0),
                            "ceiling": float(c_price or 0),
                            "floor": float(f_price or 0),
                            "volume": float(m_vol or 0)
                        }
                    except:
                        # Fallback basic
                        symbol = row.get('ticker') or row.get('symbol') or row.iloc[0]
                        price = row.get('lastPrice') or row.get('referencePrice') or 0
                        result[symbol] = {
                            "price": float(price) * 1000 if float(price) < 10000 else float(price),
                            "ref": 0, "ceiling": 0, "floor": 0, "volume": 0
                        }
        except BaseException as e:
            print(f"[CRAWLER] Lỗi lấy giá từ VCI (fallback): {e}")
            # Nếu VCI lỗi hoặc Rate Limit (SystemExit), ta vẫn tiếp tục với những mã đã lấy được từ VPS
            # Nếu VCI lỗi (vd: rate limit), ta vẫn tiếp tục với những mã đã lấy được từ VPS

    # Lưu vào Redis cache (merge với dữ liệu cũ nếu có)
    if REDIS_AVAILABLE and result:
        try:
            current_cache = {}
            cached_raw = redis_client.get(cache_key)
            if cached_raw:
                current_cache = json.loads(cached_raw)
            current_cache.update(result)
            # Dùng giá trị mặc định 30 nếu CACHE_DURATION bị lỗi vì lý do gì đó
            ttl = globals().get('CACHE_DURATION', 30)
            redis_client.setex(cache_key, ttl, json.dumps(current_cache))
        except Exception as re:
            print(f"[CRAWLER] Lỗi cập nhật Redis: {re}")
    
    return result

def get_historical_prices(ticker: str, period: str = "1m") -> list:
    """
    Lấy dữ liệu lịch sử bằng vnstock3
    """
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Tính start_date
        days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        start_date = (datetime.now() - timedelta(days=days_map.get(period, 30))).strftime('%Y-%m-%d')
        
        # VNSTOCK3 DÙNG .stock() CHO CẢ CHỈ SỐ VÀ CỔ PHIẾU
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        df = stock.quote.history(start=start_date, end=end_date, interval='1D')
        
        if df is not None and not df.empty:
            df = df.reset_index()
            result = []
            
            for _, row in df.iterrows():
                # vnstock3 dùng cột 'time' hoặc 'date'
                time_val = row.get('time') or row.get('date')
                close_val = row.get('close') or row.get('Close') or 0
                
                # vnstock3 history is usually in 1000 VND units (e.g. 96.5)
                # while price_board is in VND (e.g. 96500). We unify to VND.
                final_close = float(close_val)
                if final_close < 10000: # Heuristic to detect 1000 VND units
                    final_close *= 1000

                result.append({
                    "date": time_val.strftime('%Y-%m-%d') if hasattr(time_val, 'strftime') else str(time_val),
                    "close": final_close
                })
            
            return result
        else:
            print(f"[CRAWLER] Không có dữ liệu cho {ticker}")
            return []
            
    except BaseException as e:
        # Bắt BaseException để xử lý cả SystemExit từ vnstock3 (Rate limit)
        print(f"[CRAWLER] Lỗi lấy lịch sử {ticker} từ vnstock3: {e}")
        return []
