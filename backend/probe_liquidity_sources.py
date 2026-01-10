from vnstock import Vnstock
import json

symbols = ["VNINDEX", "VN30", "HNX30"]

print("--- PROBING TCBS & SSI FOR TURNOVER/VALUE ---")

for source in ['TCBS', 'SSI']:
    print(f"\n[{source}] Testing...")
    try:
        # Try snapshot
        # Note: vnstock API details might vary, we try standard stock()
        stock = Vnstock().stock(symbol='VNINDEX', source=source)
        # Try history first as user mentioned "previous session"
        df = stock.quote.history(start='2026-01-09', end='2026-01-10', interval='1D')
        if df is not None and not df.empty:
            print(f"[{source}] History Columns: {df.columns.tolist()}")
            print(df.tail(1))
            
            # Check for value column
            if 'value' in df.columns or 'turnover' in df.columns:
                print(f"[{source}] FOUND VALUE COLUMN!")
        else:
            print(f"[{source}] History Empty")

    except Exception as e:
        print(f"[{source}] Error: {e}")
