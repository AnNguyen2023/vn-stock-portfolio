
from core.db import SessionLocal
import models
from datetime import datetime, date
from decimal import Decimal

def drill_jan7():
    db = SessionLocal()
    start = datetime(2026, 1, 7)
    end = datetime(2026, 1, 8)
    flows = db.query(models.CashFlow).filter(models.CashFlow.created_at >= start, models.CashFlow.created_at < end).all()
    print(f"--- Flows on Jan 7 ---")
    for f in flows:
        print(f"  [{f.created_at}] | {f.type.value} | {f.amount:,.0f} | {f.description}")
        
    snap07 = db.query(models.DailySnapshot).filter_by(date=date(2026, 1, 7)).first()
    snap06 = db.query(models.DailySnapshot).filter_by(date=date(2026, 1, 6)).first()
    
    print(f"Snap06: {snap06.total_nav if snap06 else 'N/A'}")
    print(f"Snap07: {snap07.total_nav if snap07 else 'N/A'}")

if __name__ == "__main__":
    drill_jan7()
