from vnstock import Vnstock
import pandas as pd

try:
    stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
    df = stock.quote.history(interval='1m', start='2026-01-16', end='2026-01-16')
    
    if df is not None and not df.empty:
        print(f"Data for VNINDEX on 2026-01-16 ({len(df)} rows):")
        # Format for readability
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', 1000)
        print(df[['time', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))
    else:
        print("No data found for VNINDEX on 2026-01-16")

except Exception as e:
    print(f"Error: {e}")
