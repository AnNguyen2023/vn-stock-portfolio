from vnstock import Vnstock
import pandas as pd

try:
    print("Testing Vnstock().stock('HNX30', source='VCI')...")
    stock = Vnstock().stock(symbol='HNX30', source='VCI')
    if stock:
        print("Stock object created.")
        print("Fetching history(interval='1m')...")
        df = stock.quote.history(interval='1m', start='2026-01-14', end='2026-01-14') # Use today's date
        if df is not None and not df.empty:
            print("History found:")
            print("Columns:", df.columns.tolist())
            print(f"Total Volume Sum: {df['volume'].sum():,}")
            print(df.tail())
        else:
            print("History is EMPTY.")
    else:
        print("Stock object is None.")

except Exception as e:
    print(f"Error: {e}")
