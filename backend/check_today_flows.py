
from core.db import SessionLocal
import models
from datetime import date, datetime
from decimal import Decimal

def check_today():
    db = SessionLocal()
    today = date.today()
    flows = db.query(models.CashFlow).filter(models.CashFlow.created_at >= datetime.combine(today, datetime.min.time())).all()
    total = Decimal("0")
    print(f"--- Cash Flows for {today} ---")
    for f in flows:
        amt = Decimal(str(f.amount))
        if f.type == models.CashFlowType.WITHDRAW:
            amt = -amt
        print(f"  {f.created_at}: {f.type.value:<10} | {f.amount:>15,.0f} | {f.description}")
        total += amt
    print(f"TOTAL NET FLOW TODAY: {total:,.0f}")
    
    asset = db.query(models.AssetSummary).first()
    print(f"\nAssetSummary Cash: {asset.cash_balance:,.0f}")
    
    from services.portfolio_service import calculate_portfolio
    p = calculate_portfolio(db)
    print(f"Calculated NAV: {p['total_nav']:,.0f}")

if __name__ == "__main__":
    check_today()
