import requests

def get_current_prices(tickers: list):
    """
    Lấy giá hiện tại từ VPS Datafeed
    """
    if not tickers:
        return {}
    
    # Chuyển list ['HPG', 'FPT'] thành chuỗi 'HPG,FPT'
    symbols = ",".join(tickers).upper()
    url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{symbols}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        price_map = {}
        # VPS trả về một danh sách các Object
        for item in data:
            ticker = item.get("sym") # Symbol
            # VPS trả về giá đã chia 1000 (VD: 26.9), ta lấy lastPrice hoặc c (khớp lệnh)
            # Nếu thị trường chưa mở cửa, lastPrice có thể bằng 0, ta lấy r (tham chiếu)
            price = item.get("lastPrice") or item.get("c") or item.get("r")
            
            if price:
                price_map[ticker] = float(price) * 1000
                
        return price_map
    except Exception as e:
        print(f"Lỗi khi crawl giá từ VPS: {e}")
        return {}