from vnstock import Vnstock
import pandas as pd

TICKER = 'MBS'

print(f"=== Testing Financial Ratios for {TICKER} ===")

try:
    stock = Vnstock().stock(symbol=TICKER)
    df = stock.finance.ratio(period='yearly', lang='vi')

    if df.empty:
        print(f"❌ DataFrame is empty for {TICKER}")
    else:
        print(f"✅ Data found with shape: {df.shape}")
        print("\nColumns:", df.columns.tolist())
        
        print("\n=== First 5 rows of Yearly Data ===")
        print(df.head(5)[['Meta', 'Chỉ tiêu định giá', 'Chỉ tiêu khả năng sinh lợi']].iloc[:, :5]) # Print a subset to avoid mess
        
        # Try Quarterly
        print("\n=== Testing Quarterly Data ===")
        df_q = stock.finance.ratio(period='quarterly', lang='vi')
        if not df_q.empty:
             print("Quarterly Data found. Latest:")
             latest_q = df_q.iloc[0]
             print(latest_q[['Meta', 'Chỉ tiêu định giá', 'Chỉ tiêu khả năng sinh lợi']])
        else:
             print("❌ Quarterly Data empty")

except Exception as e:
    print(f"❌ Exception occurred: {e}")
