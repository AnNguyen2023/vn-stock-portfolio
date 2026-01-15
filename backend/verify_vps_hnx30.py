import requests
import json

def check_vps():
    url = "https://bgapidatafeed.vps.com.vn/getlistindexdetail/12"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_vps()
