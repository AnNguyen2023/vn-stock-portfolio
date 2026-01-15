from core.db import SessionLocal
import models

db = SessionLocal()
index_name = "HNX30"

# Step 1: Get latest
latest = db.query(models.HistoricalPrice).filter(
    models.HistoricalPrice.ticker == index_name
).order_by(models.HistoricalPrice.date.desc()).first()

print(f"Latest: date={latest.date}, close={latest.close_price}")

# Step 2: Get prev close - exact same logic as _get_market_fallback
prev_close = db.query(models.HistoricalPrice).filter(
    models.HistoricalPrice.ticker == index_name,
    models.HistoricalPrice.date < latest.date
).order_by(models.HistoricalPrice.date.desc()).first()

print(f"Prev: date={prev_close.date if prev_close else None}, close={prev_close.close_price if prev_close else None}")

# Step 3: Check price normalization
price = float(latest.close_price or 0)
if price > 5000:
    price /= 1000
print(f"Normalized price: {price}")

ref = 0
if prev_close:
    ref = float(prev_close.close_price)
    if ref > 5000:
        ref /= 1000
print(f"Normalized ref: {ref}")

# Check INDEX_BASELINES
from services.market_service import INDEX_BASELINES
print(f"INDEX_BASELINES for HNX30: {INDEX_BASELINES.get('HNX30')}")

# Final ref calculation
final_ref = ref if ref > 0 else INDEX_BASELINES.get(index_name, price * 0.99)
print(f"Final ref: {final_ref}")

change = price - final_ref
change_pct = (change / final_ref * 100) if final_ref > 0 else 0
print(f"Change: {change:.2f}, Change%: {change_pct:.2f}")
