import requests
import time
import redis
import json
import os
from datetime import datetime, timedelta

# --- CẤU HÌNH REDIS (Thay thế cho PRICE_CACHE cũ) ---
# Lấy URL từ biến môi trường trong Docker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

def get_current_prices(tickers: list):
    """
    Lấy giá Real-time từ VPS. 
    Sử dụng Redis Cache 30s - Tốc độ bàn thờ.
    """
    if not tickers:
        return {}

    output = {}
    missing_tickers = []

    # 1. Thử lấy giá từ Redis trước
    for t in tickers:
        cached_price = r.get(f"price:{t}")
        if cached_price:
            output[t] = float(cached_price)
        else:
            missing_tickers.append(t)

    # 2. Nếu thiếu mã nào trong Cache hoặc hết hạn, mới đi hỏi VPS
    if missing_tickers:
        try:
            url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{','.join(missing_tickers)}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    symbol = item.get('sym')
                    last_price = item.get('lastPrice', 0) * 1000
                    if last_price == 0:
                        last_price = item.get('re', 0) * 1000
                    
                    # LƯU VÀO REDIS: Hết hạn sau 30 giây (ex=30)
                    r.set(f"price:{symbol}", last_price, ex=30)
                    output[symbol] = last_price
        except Exception as e:
            print(f"Lỗi Crawler Redis: {e}")

    return {t: output.get(t, 0) for t in tickers}


def get_historical_prices(ticker: str, period: str = "1m"):
    """
    Lấy dữ liệu lịch sử. Ưu tiên API VPS, dự phòng bằng vnstock3.
    """
    symbol = ticker.upper()
    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = days_map.get(period, 30)
    
    # 1. THỬ LẤY TỪ VPS TRƯỚC (Nhanh, đồng bộ)
    try:
        import requests
        import time
        end_time = int(time.time())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())
        
        url = f"https://bgapidatafeed.vps.com.vn/getchartdata/stock/{symbol}"
        if symbol == "VNINDEX":
            url = f"https://bgapidatafeed.vps.com.vn/getchartdata/index/{symbol}"

        res = requests.get(url, params={"resolution": "1D", "from": start_time, "to": end_time}, timeout=5)
        if res.status_code == 200 and 'c' in res.json() and len(res.json()['c']) > 0:
            data = res.json()
            result = []
            for i in range(len(data['t'])):
                result.append({
                    "date": datetime.fromtimestamp(data['t'][i]).strftime('%Y-%m-%d'),
                    "close": float(data['c'][i])
                })
            return result
    except:
        pass # Nếu VPS lỗi, nhảy xuống cách 2

    # 2. DỰ PHÒNG BẰNG VNSTOCK3 (Cực kỳ ổn định cho Index)
    try:
        from vnstock3 import Vnstock
        # Nếu là VNINDEX, vnstock3 lấy rất chuẩn từ nguồn 'TCBS'
        stock = Vnstock().stock(symbol=symbol, source='TCBS')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        df = stock.quote.history(start=start_date, end=end_date, interval='1D')
        if df is not None and not df.empty:
            df = df.reset_index()
            result = []
            for _, row in df.iterrows():
                # Xử lý lấy cột thời gian (tùy nguồn mà tên cột là 'time' hoặc 'date')
                t = row.get('time') or row.get('date')
                result.append({
                    "date": t.strftime('%Y-%m-%d') if hasattr(t, 'strftime') else str(t),
                    "close": float(row['close'])
                })
            return result
    except Exception as e:
        print(f"Lỗi tồi tệ nhất tại {symbol}: {e}")
    
    return []
    """
    Lấy dữ liệu lịch sử chuẩn từ API Chart của VPS (Dùng cho biểu đồ Tăng trưởng)
    Ưu điểm: Cực nhanh, đồng bộ hoàn toàn với bảng giá VPS.
    """
    try:
        # 1. Thiết lập khoảng thời gian
        days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        days = days_map.get(period, 30)
        
        end_time = int(time.time())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())

        symbol = ticker.upper()
        
        # 2. Xác định Endpoint (Index hoặc Stock)
        # VPS tách biệt link lấy dữ liệu cho Chỉ số và cho từng Cổ phiếu
        if symbol == "VNINDEX":
            url = f"https://bgapidatafeed.vps.com.vn/getchartdata/index/{symbol}"
        else:
            url = f"https://bgapidatafeed.vps.com.vn/getchartdata/stock/{symbol}"

        params = {
            "resolution": "1D", # Lấy theo ngày
            "from": start_time,
            "to": end_time
        }

        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Cấu trúc VPS trả về: t (timestamp), c (close - giá đóng cửa)
            if 't' in data and 'c' in data:
                result = []
                for i in range(len(data['t'])):
                    # Chuyển đổi Epoch timestamp sang chuỗi YYYY-MM-DD
                    date_str = datetime.fromtimestamp(data['t'][i]).strftime('%Y-%m-%d')
                    result.append({
                        "date": date_str,
                        "close": float(data['c'][i])
                    })
                
                # Sắp xếp theo thời gian tăng dần
                result.sort(key=lambda x: x['date'])
                return result
                
        print(f"WARNING: VPS không có dữ liệu lịch sử cho {symbol}")
            
    except Exception as e:
        print(f"Lỗi Crawler Lịch sử ({ticker}): {e}")
    
    return []