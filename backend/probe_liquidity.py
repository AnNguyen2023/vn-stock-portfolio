import requests
from vnstock import Vnstock
import json

symbols = ["VNINDEX", "VN30", "HNX30"]

print("--- 1. PROBING VPS REALTIME ---")
try:
    url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{','.join(symbols)}"
    res = requests.get(url, timeout=5)
    data = res.json()
    for item in data:
        print(f"Symbol: {item.get('sym')}")
        # Print ALL keys to find 'value'
        print(json.dumps(item, indent=2))
except Exception as e:
    print(f"VPS Error: {e}")

print("\n--- 2. PROBING VNSTOCK HISTORY ---")
try:
    stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
    df = stock.quote.history(start='2026-01-01', end='2026-01-10', interval='1D')
    if df is not None and not df.empty:
        print("Columns:", df.columns.tolist())
        print(df.tail(1))
    else:
        print("History Empty")
except Exception as e:
    print(f"Vnstock Error: {e}")
