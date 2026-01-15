import sys
import os
from sqlalchemy import text

# Add current dir to path
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from backend.core.db import SessionLocal
from backend.models import HistoricalPrice

def check_history():
    db = SessionLocal()
    try:
        print("Checking HNX30 History...")
        # Get last 5 entries
        rows = db.query(HistoricalPrice).filter(HistoricalPrice.ticker == 'HNX30').order_by(HistoricalPrice.date.desc()).limit(5).all()
        for r in rows:
            print(f"Date: {r.date} | Close: {r.close_price} | Vol: {r.volume} | Val: {r.value}")
    finally:
        db.close()

if __name__ == "__main__":
    check_history()
