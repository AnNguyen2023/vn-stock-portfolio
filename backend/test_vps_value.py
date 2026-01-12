import requests

symbols = ["VNINDEX", "VN30", "HNX30"]
url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{','.join(symbols)}"

response = requests.get(url, timeout=5)
data = response.json()

for item in data:
    print(f"\n{item.get('sym')}:")
    print(f"  Price: {item.get('lastPrice')}")
    print(f"  Volume (lot): {item.get('lot')}")
    
    # Check all keys for value-related fields
    print(f"  All keys: {list(item.keys())}")
    
    # Look for value fields
    for key in item.keys():
        if 'val' in key.lower() or 'value' in key.lower():
            print(f"  >>> {key}: {item[key]}")
