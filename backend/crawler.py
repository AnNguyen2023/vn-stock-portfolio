# File: backend/crawler.py - Hoàn chỉnh, ổn định (VPS realtime + vnstock historical VCI)
import requests
from datetime import date, timedelta

def get_current_prices(tickers: list):
    """
    Lấy giá hiện tại từ VPS Datafeed (real-time)
    """
    if not tickers:
        return {}
    
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
        for item in data:
            ticker = item.get("sym")
            price = item.get("lastPrice") or item.get("c") or item.get("r")
            if price:
                price_map[ticker] = float(price) * 1000
        return price_map
    except Exception as e:
        print(f"Lỗi khi crawl giá từ VPS: {e}")
        return {}

def get_historical_prices(ticker: str, period: str = "1m") -> list:
    """
    Lấy giá lịch sử dùng Vnstock bản mới (Source: VCI).
    Output: [{'date': '2025-12-01', 'close': 26500.5}, ...]
    """
    try:
        end_date = date.today()
        days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        days = days_map.get(period, 30)
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        ticker = ticker.upper()
        if ticker in ['VNINDEX', '^VNI', 'VNI']:
            ticker = 'VNINDEX'

        # Primary: Vnstock.stock.quote.history (new API)
        import vnstock
        stock = vnstock.Vnstock().stock(symbol=ticker, source='VCI')
        df = stock.quote.history(start=start_str, end=end_str)

        if df is not None and not df.empty:
            if 'time' in df.columns:
                df = df.rename(columns={'time': 'date'})
            if 'close' in df.columns:
                df = df[['date', 'close']]
                df['date'] = df['date'].astype(str)
                return df.to_dict(orient='records')
        
        return []

    except Exception as e:
        print(f"Lỗi crawl historical {ticker} (VCI): {e}")
        # Fallback: vnstock.vci.stock_historical_data
        try:
            from vnstock.vci import stock_historical_data
            df = stock_historical_data(ticker, start_str, end_str)
            if df is not None and not df.empty:
                if 'time' in df.columns:
                    df = df.rename(columns={'time': 'date'})
                df['date'] = df['date'].astype(str)
                return df[['date', 'close']].to_dict(orient='records')
        except:
            pass
        return []

# Test tự động
if __name__ == "__main__":
    print("=== Test Realtime VPS ===")
    prices = get_current_prices(["VPS", "VCB"])
    print(prices)

    print("\n=== Test Historical VPS 1m ===")
    hist_vps = get_historical_prices("VPS", "1m")
    print(f"Rows: {len(hist_vps)}, Sample: {hist_vps[:2] if hist_vps else 'Empty'}")

    print("\n=== Test Historical VNINDEX 3m ===")
    hist_vni = get_historical_prices("VNINDEX", "3m")
    print(f"Rows: {len(hist_vni)}, Sample: {hist_vni[:2] if hist_vni else 'Empty'}")
