
from core.db import get_db
import models
from datetime import date, datetime
from decimal import Decimal

def drill_down_jan6():
    db = next(get_db())
    v_date = date(2026, 1, 6)
    v_date_prev = date(2026, 1, 5)
    
    print(f"--- Drilling down into {v_date} ---")
    
    snap_prev = db.query(models.DailySnapshot).filter_by(date=v_date_prev).first()
    snap_curr = db.query(models.DailySnapshot).filter_by(date=v_date).first()
    
    print(f"Snapshot {v_date_prev}: {snap_prev.total_nav if snap_prev else 'N/A'}")
    print(f"Snapshot {v_date}: {snap_curr.total_nav if snap_curr else 'N/A'}")
    
    flows = db.query(models.CashFlow).filter(
        models.CashFlow.created_at >= datetime(2026, 1, 6),
        models.CashFlow.created_at < datetime(2026, 1, 7)
    ).all()
    
    print(f"\nFlows on {v_date}:")
    total_flow = Decimal("0")
    for f in flows:
        amt = Decimal(str(f.amount))
        if f.type == models.CashFlowType.WITHDRAW:
            amt = -amt
        print(f"  {f.created_at}: {f.type} {f.amount:,.0f} | Desc: {f.description}")
        total_flow += amt
        
    print(f"\nTotal Net Flow on {v_date}: {total_flow:,.0f}")
    
    if snap_prev and snap_curr:
        p_nav = Decimal(str(snap_prev.total_nav))
        c_nav = Decimal(str(snap_curr.total_nav))
        profit = c_nav - p_nav - total_flow
        denom = p_nav + max(Decimal("0"), total_flow)
        pct = (profit / denom * 100) if denom > 0 else 0
        print(f"\nCalculation Check:")
        print(f"  PnL = {c_nav:,.0f} - {p_nav:,.0f} - {total_flow:,.0f} = {profit:,.0f}")
        print(f"  Pct = {profit:,.0f} / ({p_nav:,.0f} + {max(0, total_flow):,.0f}) = {pct:.2f}%")

if __name__ == "__main__":
    drill_down_jan6()
