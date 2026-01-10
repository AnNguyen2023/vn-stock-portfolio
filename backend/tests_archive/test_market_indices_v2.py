from vnstock import Trading
import pandas as pd
import time

def check_price(indices):
    print(f"\nChecking: {indices}")
    try:
        df = Trading(source='VCI').price_board(indices)
        if df is not None and not df.empty:
            for idx, row in df.iterrows():
                # Extract potential price keys
                try:
                    price = row[('match', 'match_price')]
                    print(f"  {idx}: Price={price}")
                except:
                    print(f"  {idx}: Could not read price")
        else:
            print("  Empty/None DataFrame")
    except Exception as e:
        print(f"  Error: {e}")

check_price(["VNINDEX", "VN30", "HNX", "HNX30", "UPCOM"])
