import requests
import json

def debug_vps_indices():
    ids = ','.join([f'{i:02d}' for i in range(1, 51)])
    url = f'https://bgapidatafeed.vps.com.vn/getlistindexdetail/{ids}'
    try:
        ids = '02,05,10,11,12'
        url = f'https://bgapidatafeed.vps.com.vn/getlistindexdetail/{ids}'
        r = requests.get(url, timeout=5)
        data = r.json()
        
        for i in data:
            if not i: continue
            mc = i.get('mc')
            cPrice = i.get('cIndex')
            vol = i.get('vol')
            val = i.get('value')
            ot = i.get('ot')
            print(f"MC: {mc} | Price: {cPrice} | Vol: {vol} | Val: {val} | OT: {ot}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_vps_indices()
