
from core.db import SessionLocal
import models
import re
from decimal import Decimal

def check_manual_flows():
    db = SessionLocal()
    flows = db.query(models.CashFlow).all()
    total_manual = Decimal("0")
    print("--- Manual Capital Flows ---")
    for f in flows:
        desc = f.description or ""
        # Check if it looks like a system-generated trade flow
        is_trade = re.match(r"^(Buy|Sell|Mua|Bán) \d", desc)
        
        # We only care about DEPOSIT/WITHDRAW for capital injections
        if f.type in [models.CashFlowType.DEPOSIT, models.CashFlowType.WITHDRAW]:
            if not is_trade:
                amt = Decimal(str(f.amount))
                if f.type == models.CashFlowType.WITHDRAW:
                    amt = -amt
                print(f"  [{f.created_at}] | {f.type.value:<10} | {f.amount:>15,.0f} | {f.description}")
                total_manual += amt
    
    print(f"\nTOTAL MANUAL NET FLOW (Injection): {total_manual:,.0f}")
    
    from services.portfolio_service import calculate_portfolio
    p = calculate_portfolio(db)
    live_nav = Decimal(str(p["total_nav"]))
    print(f"Current NAV: {live_nav:,.0f}")
    
    # Simple PnL = Current NAV - Net Injections - Starting NAV
    # Let's assume starting NAV was 14,149,230,526 (from my previous debug output)
    start_nav = Decimal("14149230526")
    profit = live_nav - total_manual - start_nav
    print(f"Estimated Real Lifetime Profit: {profit:,.0f}")

if __name__ == "__main__":
    check_manual_flows()
