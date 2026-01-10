import requests
import json

def probe_vndirect(symbol):
    print(f"--- Probing VNDirect for {symbol} ---")
    url = "https://finfo-api.vndirect.com.vn/v4/stock_prices"
    params = {
        "sort": "date",
        "q": f"code:{symbol}",
        "size": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        data = res.json()
        if 'data' in data and len(data['data']) > 0:
            item = data['data'][0]
            print("SUCCESS")
            print("Date:", item.get('date'))
            print("Close:", item.get('close'))
            print("Volume:", item.get('nmVolume'))
            print("Value:", item.get('nmValue'))
            print("Raw Item:", json.dumps(item, indent=2))
        else:
            print("No data found")
    except Exception as e:
        print(f"Error: {e}")

probe_vndirect("VNINDEX")
probe_vndirect("VN30")
