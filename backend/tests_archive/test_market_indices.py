from vnstock import Trading
import pandas as pd
import time

# Function to test a single list of indices
def test_indices(indices):
    print(f"\nTesting indices: {indices}")
    try:
        # source='VCI' is default for some functions, but for price_board we usually expect it works
        df = Trading(source='VCI').price_board(indices)
        if df is not None and not df.empty:
            print("  -> SUCCESS: Got data!")
            print("Columns:", df.columns.tolist())
            print("First Row:", df.iloc[0].to_dict())
            print(df)
        else:
            print("  -> FAILED: No data returned")
    except Exception as e:
        print(f"  -> ERROR: {e}")

# Test 1: Just VNINDEX (Known good?)
test_indices(["VNINDEX"])
time.sleep(2)

# Test 2: VN30, HNX30
test_indices(["VN30", "HNX30"])
time.sleep(2)

# Test 3: HNX, UPCOM
test_indices(["HNX", "UPCOM"])
time.sleep(2)

# Test 4: HNX-INDEX, UPCOM-INDEX
test_indices(["HNX-INDEX", "UPCOM-INDEX"])
