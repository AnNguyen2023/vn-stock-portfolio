from vnstock import Vnstock, Trading
import json
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

print("--- DEEP PROBE FOR VNINDEX VALUE ---")

try:
    # 1. Price Board
    print("\n1. Testing Trading().price_board(['VNINDEX'])")
    df = Trading(source='VCI').price_board(['VNINDEX'])
    if df is not None and not df.empty:
        row = df.iloc[0]
        print("Keys available:", row.index.tolist())
        # iterate and print to find any large numbers
        for k, v in row.items():
            print(f"{k}: {v}")
    
    # 2. Quote Snapshot
    print("\n2. Testing Vnstock().stock(symbol='VNINDEX', source='VCI').quote.snapshot()")
    stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
    # try snapshot
    try:
        # snapshot might be method or property depending on version
        # Some versions use quote.snapshot()
        # inspect available methods
        print("Dir of quote:", dir(stock.quote))
    except: pass
    
except Exception as e:
    print(f"Error: {e}")
