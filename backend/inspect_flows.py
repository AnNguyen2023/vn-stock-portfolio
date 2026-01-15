
from core.db import SessionLocal
import models

def inspect_flows():
    db = SessionLocal()
    # Unique descriptions for each type
    types = [models.CashFlowType.DEPOSIT, models.CashFlowType.WITHDRAW]
    for ct in types:
        print(f"\n--- Samples for {ct.value} ---")
        flows = db.query(models.CashFlow).filter_by(type=ct).limit(20).all()
        for f in flows:
            print(f"  [{f.created_at}] | {f.amount:>15,.0f} | {f.description}")

if __name__ == "__main__":
    inspect_flows()
