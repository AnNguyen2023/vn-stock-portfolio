import sys
import os
from sqlalchemy import text
from datetime import date
from decimal import Decimal

# Add current dir to path
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from backend.core.db import SessionLocal
from backend.models import HistoricalPrice

def fix_history():
    db = SessionLocal()
    try:
        print("Cleaning up HNX30 History (Policy: No DB Persistence)...")
        rows = db.query(HistoricalPrice).filter(HistoricalPrice.ticker == 'HNX30').all()
        count = len(rows)
        if count > 0:
            print(f"Found {count} records. Deleting...")
            for r in rows:
                db.delete(r)
            db.commit()
            print("Deleted all HNX30 records.")
        else:
            print("No HNX30 records found.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_history()
