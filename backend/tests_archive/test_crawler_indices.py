from crawler import get_current_prices
import json

symbols = ["VNINDEX", "VN30", "HNX30"]
print(f"--- Testing crawler.get_current_prices({symbols}) ---")

try:
    data = get_current_prices(symbols)
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")
