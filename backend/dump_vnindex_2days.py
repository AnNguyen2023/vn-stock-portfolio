from vnstock import Vnstock
import pandas as pd

try:
    print("Fetching VNINDEX data for 2026-01-15 to 2026-01-16...")
    stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
    df = stock.quote.history(interval='1m', start='2026-01-15', end='2026-01-16')
    
    if df is not None and not df.empty:
        df['time'] = pd.to_datetime(df['time'])
        print(f"Total Rows: {len(df)}")
        
        # Group by date and print summary
        dates = df['time'].dt.date.unique()
        for d in dates:
            day_data = df[df['time'].dt.date == d]
            print(f"\n--- Date: {d} ({len(day_data)} rows) ---")
            print(f"Start: {day_data['time'].min().time()} | End: {day_data['time'].max().time()}")
            print(day_data[['time', 'close', 'volume']].head(3).to_string(index=False, header=False))
            print("...")
            print(day_data[['time', 'close', 'volume']].tail(3).to_string(index=False, header=False))
            
    else:
        print("No data found.")

except Exception as e:
    print(f"Error: {e}")
