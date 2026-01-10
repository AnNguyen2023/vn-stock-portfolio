from vnstock import Vnstock
import pandas as pd

symbol = "VNINDEX"

print(f"--- Probing TCBS for {symbol} ---")
try:
    stock = Vnstock().stock(symbol=symbol, source='TCBS')
    # Try history
    df = stock.quote.history(start='2026-01-01', end='2026-01-10', interval='1D')
    if df is not None and not df.empty:
        print("Success!")
        print(df.tail(2))
        print("Columns:", df.columns.tolist())
    else:
        print("Empty DataFrame")
except Exception as e:
    print(f"Error: {e}")
