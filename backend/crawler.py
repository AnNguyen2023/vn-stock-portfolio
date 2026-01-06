"""
crawler.py - Module lấy dữ liệu giá cổ phiếu & VNINDEX từ vnstock3
"""
from vnstock import Vnstock, Trading
from datetime import datetime, timedelta
import redis
import json

# --- CẤU HÌNH REDIS CACHE ---
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    print("[CRAWLER] Redis không khả dụng, chạy không cache")

CACHE_DURATION = 30  # giây

def get_current_prices(tickers: list) -> dict:
    """
    Lấy giá hiện tại của danh sách mã cổ phiếu qua vnstock3
    Sử dụng Redis Cache để tăng tốc độ phản hồi.
    """
    if not tickers:
        return {}
    
    result = {}
    
    # 1. KIỂM TRA CACHE
    if REDIS_AVAILABLE:
        cache_key = "stock_prices"
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            all_prices = json.loads(cached_data)
            # Trả về giá các mã trong cache nếu đủ
            if all(t in all_prices for t in tickers):
                return {t: all_prices[t] for t in tickers}
    
    # 2. GỌI VNSTOCK3 NẾU CACHE KHÔNG CÓ
    try:
        # Sử dụng price_board để lấy giá real-time nhiều mã cùng lúc
        df = Trading(source='VCI').price_board(tickers)
        
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                symbol = row.get('ticker') or row.get('symbol')
                # Lấy giá khớp lệnh hoặc giá tham chiếu
                price = row.get('lastPrice') or row.get('referencePrice') or 0
                result[symbol] = float(price) * 1000  # Chuyển sang VND
            
            # Lưu vào Redis cache
            if REDIS_AVAILABLE:
                redis_client.setex(cache_key, CACHE_DURATION, json.dumps(result))
                
    except Exception as e:
        print(f"[CRAWLER] Lỗi lấy giá từ vnstock3: {e}")
        # Fallback: Trả về giá 0 cho các mã lỗi
        result = {t: 0 for t in tickers}
    
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
                close_val = row.get('close') or row.get('Close')
                
                result.append({
                    "date": time_val.strftime('%Y-%m-%d') if hasattr(time_val, 'strftime') else str(time_val),
                    "close": float(close_val)
                })
            
            return result
        else:
            print(f"[CRAWLER] Không có dữ liệu cho {ticker}")
            return []
            
    except Exception as e:
        print(f"[CRAWLER] Lỗi lấy lịch sử {ticker}: {e}")
        return []
