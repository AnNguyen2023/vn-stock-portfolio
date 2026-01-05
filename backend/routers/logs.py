from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date, desc
import models
from datetime import datetime

router = APIRouter(tags=["Audit Logs"])

def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/logs")
def get_audit_log(db: Session = Depends(get_db)):
    cash = db.query(models.CashFlow).all()
    stocks = db.query(models.StockTransaction).all()
    logs = []
    for c in cash:
        logs.append({
            "id": c.id, "date": c.created_at, "category": "CASH", "note": "",
            "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "content": f"{c.description}: {int(c.amount):,}"
        })
    for s in stocks:
        logs.append({
            "id": s.id, "date": s.transaction_date, "category": "STOCK", "note": s.note or "",
            "type": s.type.value if hasattr(s.type, 'value') else str(s.type),
            "content": f"{s.type.value} {int(s.volume):,} {s.ticker} giá {int(s.price):,}"
        })
    logs.sort(key=lambda x: x['date'], reverse=True)
    return logs

@router.post("/update-note")
def update_note(tx_id: int, note: str, db: Session = Depends(get_db)):
    transaction = db.query(models.StockTransaction).filter(models.StockTransaction.id == tx_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")
    transaction.note = note
    db.commit()
    return {"message": "Đã cập nhật ghi chú thành công"}

@router.get("/history-summary")
def get_history_summary(start_date: str, end_date: str, db: Session = Depends(get_db)):
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    items = db.query(models.RealizedProfit).filter(cast(models.RealizedProfit.sell_date, Date) >= start, cast(models.RealizedProfit.sell_date, Date) <= end).all()
    return {"total_profit": float(sum(i.net_profit for i in items)), "trade_count": len(items)}