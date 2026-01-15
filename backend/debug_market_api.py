import requests
import json

def debug_api():
    try:
        resp = requests.get("http://localhost:8000/market-summary", timeout=5)
        data = resp.json()
        
        if isinstance(data, list):
            items = data
        else:
            items = data.get('data', [])
        
        print(f"Data type: {type(data)}")
        print(f"Items count: {len(items)}")
        print(f"Raw data head: {str(data)[:500]}...")

        if not items:
            print("WARNING: Items list is EMPTY.")
        
        for item in items:
            print(f"- {item.get('index')}: Price={item.get('price')}, Vol={item.get('volume')}")

        hnx30 = next((x for x in items if x.get('index') == 'HNX30'), None)
        
        if hnx30:
            print(f"HNX30 Found.")
            print(f"Price: {hnx30.get('price')}")
            print(f"Ref: {hnx30.get('ref_price')}")
            sl = hnx30.get('sparkline', [])
            if sl:
                print(f"Sparkline Len: {len(sl)}")
                # Print first 3 and last 3 non-None items
                valid_sl = [x for x in sl if x.get('p') is not None]
                print(f"Valid Sparkline Len: {len(valid_sl)}")
                if valid_sl:
                    print("First 3:", valid_sl[:3])
                    print("Last 3:", valid_sl[-3:])
            else:
                print("Sparkline is EMPTY or Missing")
        else:
            print("HNX30 NOT FOUND in response")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_api()
