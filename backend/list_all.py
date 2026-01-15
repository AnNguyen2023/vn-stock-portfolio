
from core.db import SessionLocal
import models

def list_txs():
    db = SessionLocal()
    txs = db.query(models.StockTransaction).all()
    print(f"--- All Transactions ({len(txs)}) ---")
    for t in txs:
        print(f"  [{t.transaction_date}] {t.type.value} {t.ticker}: {t.volume:,.0f} @ {t.price:,.0f}")
        
    holdings = db.query(models.TickerHolding).all()
    print(f"\n--- Holdings ---")
    for h in holdings:
        print(f"  {h.ticker}: Total {h.total_volume:,.0f} | Available {h.available_volume:,.0f}")

if __name__ == "__main__":
    list_txs()
