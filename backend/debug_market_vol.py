from core.db import SessionLocal
from services.market_service import get_market_summary_service

db = SessionLocal()
data = get_market_summary_service(db)

for d in data:
    print(f"{d['index']}: price={d['price']}, ref={d['ref_price']}, change={d['change']}, pct={d['change_pct']}")
    print(f"  Volume={d['volume']}, Value={d['value']} Tỷ")
    print()
