import sys
import os
from sqlalchemy.orm import Session

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from backend.services.market_service import get_market_summary_service, mem_set
from backend.core.redis_client import get_redis
from backend.core.db import SessionLocal

def test_service():
    print("Clearing VCI backoff & caches...")
    r = get_redis()
    if r:
        r.delete("vci_rate_limit_backoff")
        r.delete("intraday_spark_v4_HNX30")
        r.delete("market_summary_full_v10")
    mem_set("vci_backoff", None, 1) 
    mem_set("intraday_spark_v4_HNX30", None, 1)
    mem_set("market_summary_full_v10", None, 1)

    print("Testing get_market_summary_service...")
    try:
        db = SessionLocal()
        results = get_market_summary_service(db)
        print("Success!")
        for r in results:
            print(f"{r['index']}: P={r['price']} V={r['volume']} Val={r['value']}")
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_service()
