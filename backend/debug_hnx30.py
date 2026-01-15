
from core.db import SessionLocal
from services.market_service import _process_market_row
from adapters.vps_adapter import get_realtime_prices_vps
import pandas as pd

db = SessionLocal()
indices = ["VNINDEX", "VN30", "HNX30"]

# Get VPS data
vps_data = get_realtime_prices_vps(indices)
print(f"VPS Data: {vps_data}")

# Test processing HNX30
row = pd.Series({('listing', 'symbol'): 'HNX30'})
result = _process_market_row(row, 'HNX30', db, vps_data)
print(f"\nHNX30 Process Result: {result}")
