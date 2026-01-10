from vnstock import Vnstock
import pandas as pd

TICKER = 'MBS'

print(f"=== Testing Financial Ratios for {TICKER} with source='VCI' ===")

try:
    # Initialize with source='VCI'
    stock = Vnstock().stock(symbol=TICKER, source='VCI')
    print("Initialized stock with source='VCI'")
    
    # Try fetching ratios
    print("Fetching yearly ratios...")
    df = stock.finance.ratio(period='yearly', lang='vi')

    if df.empty:
        print(f"❌ DataFrame is empty for {TICKER}")
    else:
        print(f"✅ Data found with shape: {df.shape}")
        if not df.empty:
            print(df.iloc[0])
            
    # Also verify if 'source' arg actually changes the behavior of finance.ratio
    # (Sometimes finance functions are bound to a specific source regardless of init)

except Exception as e:
    print(f"❌ Exception occurred: {e}")
