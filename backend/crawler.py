import requests
from datetime import datetime, timedelta

# --- CẤU HÌNH CACHE BIẾN GLOBAL ---
PRICE_CACHE = {}
LAST_CRAWL_TIME = None
CACHE_DURATION = 30  # Giây

def get_current_prices(tickers: list):
    """
    Lấy giá hiện tại của danh sách mã cổ phiếu.
    Sử dụng Cache để tăng tốc độ phản hồi.
    """
    global PRICE_CACHE, LAST_CRAWL_TIME
    
    if not tickers:
        return {}

    now = datetime.now()

    # 1. KIỂM TRA CACHE: 
    # Nếu thời gian chưa quá 30 giây và tất cả mã cần lấy đều có trong Cache
    if LAST_CRAWL_TIME and (now - LAST_CRAWL_TIME).seconds < CACHE_DURATION:
        # Kiểm tra xem các mã yêu cầu đã có đủ trong cache chưa
        if all(t in PRICE_CACHE for t in tickers):
            # print(f"DEBUG: Trả về giá từ CACHE cho {tickers}")
            return {t: PRICE_CACHE[t] for t in tickers}

    # 2. GỌI API VPS (Nếu Cache hết hạn hoặc thiếu mã)
    # print(f"DEBUG: Gọi API VPS lấy giá mới cho {tickers}")
    try:
        # Giả sử đây là endpoint của VPS hoặc một Datafeed bạn đang dùng
        # URL ví dụ: bảng giá Lightning VPS
        url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{','.join(tickers)}"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # Cập nhật Cache mới
            new_prices = {}
            for item in data:
                symbol = item.get('sym')
                # Giá khớp lệnh (lastPrice) thường nhân 1000 vì đơn vị sàn VN là x10
                last_price = item.get('lastPrice', 0) * 1000
                
                if last_price == 0:
                    # Nếu không có giá khớp, lấy giá tham chiếu (re)
                    last_price = item.get('re', 0) * 1000
                
                new_prices[symbol] = last_price
            
            # Lưu vào bộ nhớ tạm
            PRICE_CACHE.update(new_prices)
            LAST_CRAWL_TIME = now
            
            return {t: PRICE_CACHE.get(t, 0) for t in tickers}
            
    except Exception as e:
        print(f"Lỗi Crawler: {e}")
        # Nếu lỗi, cố gắng trả về giá cũ trong Cache nếu có
        return {t: PRICE_CACHE.get(t, 0) for t in tickers}

    return {}

def get_historical_prices(ticker: str, period: str = "1m"):
    try:
        from vnstock3 import Vnstock
        import pandas as pd
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        # Tính toán start_date (giữ nguyên logic cũ của bạn)
        days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        start_date = (datetime.now() - timedelta(days=days_map.get(period, 30))).strftime('%Y-%m-%d')

        # Dùng nguồn 'TCBS' để lấy Index ổn định hơn
        stock = Vnstock().stock(symbol=ticker, source='TCBS')
        df = stock.quote.history(start=start_date, end=end_date, interval='1D')

        if df is not None and not df.empty:
            df = df.reset_index()
            # print(f"DEBUG: Da lay duoc {len(df)} dong du lieu cho {ticker}")
            
            result = []
            for _, row in df.iterrows():
                # vnstock3 thuong dung cot 'time' hoac 'date'
                time_val = row.get('time') or row.get('date')
                result.append({
                    "date": time_val.strftime('%Y-%m-%d') if hasattr(time_val, 'strftime') else str(time_val),
                    "close": float(row['close'])
                })
            return result
        else:
            print(f"WARNING: Khong co du lieu cho {ticker}")
            
    except Exception as e:
        print(f"Lỗi lấy lịch sử {ticker}: {e}")
    
    return []
    """
    Lấy dữ liệu lịch sử bằng vnstock3 (Cập nhật 2026)
    """
    try:
        from vnstock3 import Vnstock
        
        # 1. Thiết lập khoảng thời gian
        end_date = datetime.now().strftime('%Y-%m-%d')
        if period == "1m":
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif period == "3m":
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        elif period == "6m":
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        else:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        # 2. Khởi tạo Vnstock
        stock = Vnstock().stock(symbol=ticker, source='VCI') # VCI hoặc TCBS

        # 3. Lấy dữ liệu (Xử lý riêng cho chỉ số VNINDEX và Cổ phiếu)
        if ticker.upper() == "VNINDEX":
            # Đối với chỉ số VNINDEX
            df = stock.quote.history(start=start_date, end=end_date, interval='1D')
        else:
            # Đối với cổ phiếu thường
            df = stock.quote.history(start=start_date, end=end_date, interval='1D')

        if df is not None and not df.empty:
            # Reset index để đưa cột 'time' ra ngoài nếu nó đang là index
            df = df.reset_index()
            
            result = []
            for _, row in df.iterrows():
                # Chuyển đổi format ngày tháng để Recharts (Frontend) đọc được
                result.append({
                    "date": row['time'].strftime('%Y-%m-%d') if hasattr(row['time'], 'strftime') else str(row['time']),
                    "close": float(row['close'])
                })
            return result
            
    except Exception as e:
        print(f"Lỗi lấy lịch sử {ticker}: {e}")
    
    return [] 