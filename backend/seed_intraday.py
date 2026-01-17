"""
Seed Redis with sample intraday data for VNINDEX and VN30
Trading hours: 9:15 - 14:45 (330 minutes = 330 points at 1m interval)
"""
import redis
import json
from datetime import datetime, timedelta
import random

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

def generate_intraday_data(ticker, ref_price, final_price):
    """Generate realistic intraday data for 9:00-15:00"""
    sparkline = []
    
    # Find last trading day (skip weekends)
    today = datetime.now()
    days_back = 1
    
    # If today is Saturday (5), go back to Friday
    # If today is Sunday (6), go back to Friday
    if today.weekday() == 5:  # Saturday
        days_back = 1
    elif today.weekday() == 6:  # Sunday
        days_back = 2
    else:
        days_back = 1
    
    last_trading_day = today - timedelta(days=days_back)
    start_time = last_trading_day.replace(hour=9, minute=0, second=0, microsecond=0)
    
    current_price = ref_price
    total_change = final_price - ref_price
    
    for i in range(361):  # 361 minutes (9:00-15:00 inclusive)
        current_time = start_time + timedelta(minutes=i)
        
        # Gradual drift towards final price with noise
        progress = i / 360
        target_price = ref_price + (total_change * progress)
        noise = random.uniform(-0.15, 0.15) / 100
        current_price = target_price * (1 + noise)
        
        # Random volume
        volume = random.randint(100000, 1000000)
        
        sparkline.append({
            "t": current_time.strftime('%H:%M'),
            "timestamp": int(current_time.timestamp()),
            "p": round(current_price, 2),
            "v": volume
        })
    
    return sparkline

# Generate data
print("Generating intraday data...")

# Find last trading day for display
today = datetime.now()
if today.weekday() == 5:  # Saturday
    last_trading_day = today - timedelta(days=1)
    day_name = "T6"
elif today.weekday() == 6:  # Sunday
    last_trading_day = today - timedelta(days=2)
    day_name = "T6"
else:
    last_trading_day = today - timedelta(days=1)
    day_name = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][last_trading_day.weekday()]

print(f"Hôm nay: {['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'][today.weekday()]} ({today.strftime('%d/%m/%Y')})")
print(f"Ngày giao dịch gần nhất: {day_name} ({last_trading_day.strftime('%d/%m/%Y')})")
print()

# VNINDEX: 1864.80 → 1879.13
vnindex_data = generate_intraday_data("VNINDEX", 1864.80, 1879.13)

# VN30: 2047.48 → 2080.35  
vn30_data = generate_intraday_data("VN30", 2047.48, 2080.35)

# Save to Redis with last trading day's date
trading_date_key = last_trading_day.strftime('%Y%m%d')

vnindex_key = f"intraday_VNINDEX_{trading_date_key}"
vn30_key = f"intraday_VN30_{trading_date_key}"

redis_client.setex(vnindex_key, 86400, json.dumps(vnindex_data))
redis_client.setex(vn30_key, 86400, json.dumps(vn30_data))

print(f"✓ Seeded {len(vnindex_data)} VNINDEX points to: {vnindex_key}")
print(f"✓ Seeded {len(vn30_data)} VN30 points to: {vn30_key}")
print(f"\nData summary:")
print(f"  VNINDEX: 1864.80 → 1879.13 (+14.33)")
print(f"  VN30: 2047.48 → 2080.35 (+32.87)")
print(f"  Trading hours: 9:00 - 15:00 (361 points)")
print(f"  Date: {day_name} {last_trading_day.strftime('%d/%m/%Y')}")
print(f"\nRefresh http://localhost:3000 to see charts!")
