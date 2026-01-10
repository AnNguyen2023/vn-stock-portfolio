from vnstock import Vnstock
import pandas as pd

def probe_method(name, func, symbol):
    print(f"\n--- Testing {name} for {symbol} ---")
    try:
        df = func(symbol)
        if df is not None and not df.empty:
            print("SUCCESS!")
            print(df.head(2))
            print("Columns:", df.columns.tolist())
        else:
            print("Empty/None")
    except Exception as e:
        print(f"Error: {e}")

symbol = "VNINDEX" # Also try VN30

# Initialize VCI source
stock = Vnstock().stock(symbol=symbol, source='VCI')

# Methods to probe
# 1. Snapshot
print("--> Probing Quote Snapshot")
try:
    # quote.snapshot usually takes a list
    df = stock.quote.snapshot()
    if df is not None: print(df); print(df.columns)
except Exception as e: print(e)

# 2. Intraday (For Charts)
print("--> Probing Quote Intraday")
try:
    df = stock.quote.intraday(page_size=100)
    if df is not None: 
        print(df.tail(2))
        print("Columns:", df.columns.tolist())
except Exception as e: print(e)

# 3. History (Already known, but check recent for volume)
print("--> Probing Quote History (Recent)")
try:
    df = stock.quote.history(start='2026-01-01', end='2026-01-10', interval='1D')
    if df is not None: print(df.tail(2))
except Exception as e: print(e)
