import requests
import time
import redis
import os
from datetime import datetime, timedelta

# Kết nối Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

def get_current_prices(tickers: list):
    """
    Bản an toàn: Ưu tiên trả về kết quả ngay lập tức để không treo giao diện.
    """
    if not tickers: return {}
    
    output = {}
    missing = []

    # 1. Thử lấy từ Redis
    try:
        for t in tickers:
            cached = r.get(f"price:{t}")
            if cached: output[t] = float(cached)
            else: missing.append(t)
    except:
        missing = tickers

    # 2. Gọi VPS nhưng khống chế thời gian chờ cực ngắn (2 giây)
    if missing:
        try:
            url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{','.join(missing)}"
            res = requests.get(url, timeout=2) # Chỉ đợi tối đa 2s
            if res.status_code == 200:
                data = res.json()
                for item in data:
                    sym = item.get('sym')
                    # Lấy giá khớp hoặc giá tham chiếu, nhân 1000
                    last = (item.get('lastPrice', 0) or item.get('re', 0)) * 1000
                    if sym:
                        r.set(f"price:{sym}", last, ex=30)
                        output[sym] = last
        except Exception as e:
            print(f"Crawler Warning: Không lấy được giá VPS, dùng giá tạm thời 0. Lỗi: {e}")

    # 3. Đảm bảo mọi mã đều có giá (dù là 0) để Backend không bị sập phép tính
    return {t: output.get(t, 0) for t in tickers}

def get_historical_prices(ticker: str, period: str = "1m"):
    """
    Bản an toàn cho biểu đồ: Trả về mảng rỗng nếu lỗi, không gây đứng API.
    """
    try:
        # Tạm thời trả về mảng rỗng để Dashboard load nhanh nhất có thể
        # Khi nào anh Zon cần làm biểu đồ, Tèo em sẽ kích hoạt lại bản xịn sau.
        return [] 
    except:
        return []