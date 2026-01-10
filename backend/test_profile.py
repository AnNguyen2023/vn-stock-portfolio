from vnstock import Vnstock
import pandas as pd

TICKER = 'MBS'
print(f"=== Testing Profile Data for {TICKER} ===")

try:
    stock = Vnstock().stock(symbol=TICKER, source='VCI')
    # Try company profile/overview
    profile = stock.company.overview()
    print("\n[Overview]:")
    print(profile)
    
    # Try different source for listing if available
    # VCI might not support all methods
    
except Exception as e:
    print(f"❌ Exception: {e}")
