import requests

def test_url(url):
    print(f"Testing: {url}")
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            print("  -> SUCCESS: " + resp.text[:100])
        else:
            print(f"  -> Failed: {resp.status_code}")
    except Exception as e:
        print(f"  -> Error: {e}")

base = "https://bgapidatafeed.vps.com.vn"
test_url(f"{base}/getlistindexdetail/VNINDEX")
test_url(f"{base}/getlistindexdetail/VNINDEX,HNX")
test_url(f"{base}/getindex/VNINDEX")
test_url(f"{base}/getmarketindex")
