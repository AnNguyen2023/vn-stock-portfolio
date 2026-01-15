
from core.db import SessionLocal
from adapters.vps_adapter import get_realtime_prices_vps
import pandas as pd
import models
from datetime import datetime, date
from decimal import Decimal
from core.redis_client import cache_get, cache_set
from core.logger import logger

db = SessionLocal()

# Replicate _process_market_row for HNX30 with verbose logging
index_name = "HNX30"
vps_data = get_realtime_prices_vps([index_name])
print(f"VPS Data: {vps_data}")

try:
    match_price = 0
    ref_price_api = 0
    match_vol = 0
    total_val = 0
    price = 0
    volume = 0
    value = 0

    # VPS Data Priority
    has_vps = False
    if vps_data and index_name in vps_data:
        has_vps = True
        v_data = vps_data[index_name]
        price = v_data.get("price", 0)
        volume = v_data.get("volume", 0)
        v_val = v_data.get("value", 0)
        if v_val > 500000:
            value = v_val / 1000
        else:
            value = v_val
    
    print(f"From VPS: price={price}, volume={volume}, value={value}")
    
    # Unify to points if price is raw
    if price > 5000:
        price /= 1000
    
    print(f"After normalization: price={price}")

    # Get reference price from DB
    ref_price_db = 0
    from core.utils import get_vietnam_time
    vn_now = get_vietnam_time()
    today_vn = vn_now.date()
    
    prev_close = db.query(models.HistoricalPrice).filter(
        models.HistoricalPrice.ticker == index_name,
        models.HistoricalPrice.date < today_vn
    ).order_by(models.HistoricalPrice.date.desc()).first()
    
    if prev_close:
        ref_price_db = float(prev_close.close_price)
        if ref_price_db > 100000:
            ref_price_db /= 1000
        print(f"DB ref_price: {ref_price_db:.2f} from {prev_close.date}")
    else:
        print("No prev_close found!")
    
    # Sparkline
    from adapters.vci_adapter import get_intraday_sparkline
    sparkline = get_intraday_sparkline(index_name, cache_get, cache_set)
    print(f"Sparkline len: {len(sparkline) if sparkline else 0}")
    
    # FALLBACK: If API price is 0 but we have sparkline, use latest sparkline point
    if (price <= 0) and sparkline:
        last_pt = sparkline[-1]
        if last_pt.get('p') and last_pt['p'] > 0:
            price = last_pt['p']
            has_vps = True
            print(f"Recovered price {price} from sparkline")
    
    ref = ref_price_db
    if ref > 5000:
        ref /= 1000
    
    print(f"Final check: price={price}, ref={ref}")
    
    if price <= 0 or ref <= 0 or pd.isna(index_name):
        print(f"RETURNING NONE: price={price}, ref={ref}")
    else:
        change = price - ref
        change_pct = (change / ref * 100) if ref > 0 else 0
        print(f"SUCCESS: price={price:.2f}, ref={ref:.2f}, change={change:.2f}, pct={change_pct:.2f}")
        
except Exception as e:
    import traceback
    print(f"EXCEPTION: {e}")
    traceback.print_exc()
