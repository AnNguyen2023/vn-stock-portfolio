import requests
import json

def test_vps(symbols):
    # Remove spaces and join with comma
    query_str = ",".join([s.strip() for s in symbols.split(",")])
    url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{query_str}"
    
    print(f"\n--- Testing VPS API for: {query_str} ---")
    print(f"URL: {url}")
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                print("SUCCESS: Retrieved JSON data")
                # Print first 2 items to avoid clutter
                print(json.dumps(data[:2], indent=2, ensure_ascii=False))
                print(f"... and {len(data)-2} more items.")
            except:
                print("WARNING: Response is not JSON")
                print(resp.text[:500])
        else:
            print(f"FAILED: Status Code {resp.status_code}")
    except Exception as e:
        print(f"ERROR: {e}")

# Test 1: User's provided list
user_list = "FPT, HAG, VCI, MBB, STB, FUEVFVND, MBS, BAF, DXG, SHB"
test_vps(user_list)

# Test 2: Indices (Indices often have special symbols like INDX:VNINDEX or just VNINDEX)
# Trying common variations
indices_list = "VNINDEX, HNX, UPCOM, HNX30, VN30, HNXIndex, UpcomIndex"
test_vps(indices_list)
