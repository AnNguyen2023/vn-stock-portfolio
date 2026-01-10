from dotenv import load_dotenv
load_dotenv()

from services.performance_service import growth_series
from core.db import SessionLocal
import json
from decimal import Decimal

# Custom JSON encoder for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

db = SessionLocal()
try:
    print("--- DEBUGGING GROWTH SERIES ---")
    result = growth_series(db, period="1m")
    
    print(f"Base Date: {result.get('base_date')}")
    print(f"Base NAV (Stock Value 0): {result.get('base_nav')}")
    print(f"Data Points: {result.get('data_points')}")
    
    series = result.get('portfolio', [])
    if series:
        print("First 3 points:")
        print(json.dumps(series[:3], indent=2, cls=DecimalEncoder))
        print("Last 3 points:")
        print(json.dumps(series[-3:], indent=2, cls=DecimalEncoder))
    else:
        print("Series is empty!")
        print(result.get('message'))

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
