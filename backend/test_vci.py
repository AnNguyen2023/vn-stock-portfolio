from vnstock import Trading
import pandas as pd

indices = ["VNINDEX", "VN30", "HNX30"]
try:
    print(f"Fetching price board for {indices} from VCI...")
    df = Trading(source='VCI').price_board(indices)
    print("DataFrame shape:", df.shape if df is not None else "None")
    if df is not None:
        print("Columns:", df.columns.tolist())
        print("Sample data:")
        print(df.head())
        
        # Check for listing symbol
        for i in range(len(df)):
            symbol = df.iloc[i][('listing', 'symbol')]
            print(f"Row {i} symbol: {symbol}")
except Exception as e:
    print(f"Error: {e}")
