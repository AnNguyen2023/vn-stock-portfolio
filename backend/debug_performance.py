
from core.db import get_db
import models
from services import performance_service
from datetime import date
from decimal import Decimal

def debug_performance():
    db = next(get_db())
    # Try to match the user's view (last 30 days or so)
    start_date = date(2025, 12, 1) # Earlier than user's view to see context
    end_date = date.today()
    
    print(f"--- Debugging NAV History from {start_date} to {end_date} ---")
    
    res = performance_service.nav_history(db, start_date=start_date, end_date=end_date)
    
    summary = res.get("summary", {})
    history = res.get("history", [])
    
    print("\n[SUMMARY]")
    for k, v in summary.items():
        print(f"  {k}: {v}")
        
    print("\n[HISTORY (Table Data)]")
    print(f"{'Date':<12} | {'NAV':>15} | {'Change':>15} | {'Pct':>10}")
    print("-" * 60)
    for item in history:
         print(f"{item['date']:<12} | {item['nav']:>15,.0f} | {item['change']:>15,.0f} | {item['pct']:>10.2f}%")

    # Raw snapshots check
    print("\n[RAW SNAPSHOTS (Descending)]")
    snaps = db.query(models.DailySnapshot).order_by(models.DailySnapshot.date.desc()).limit(10).all()
    for s in snaps:
        print(f"  {s.date}: {s.total_nav:,.0f}")

    # Cash flows check
    print("\n[RAW CASH FLOWS (Last 10)]")
    flows = db.query(models.CashFlow).order_by(models.CashFlow.created_at.desc()).limit(10).all()
    for f in flows:
        print(f"  {f.created_at}: {f.type} {f.amount:,.0f}")

if __name__ == "__main__":
    debug_performance()
