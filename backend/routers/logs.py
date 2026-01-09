"""
routers/logs.py - API endpoints cho nhật ký giao dịch
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date
from datetime import datetime
from database import get_db
import models

# QUAN TRỌNG: Dùng APIRouter thay vì app
router = APIRouter()

@router.get("/logs")
def get_audit_log(db: Session = Depends(get_db)):
    """
    Trả về timeline nhật ký tổng hợp: Nạp/Rút/Mua/Bán
    """
    # 1. Lấy lịch sử nạp/rút/lãi
    cash = db.query(models.CashFlow).all()
    
    # 2. Lấy lịch sử mua/bán
    stocks = db.query(models.StockTransaction).all()
    
    # 3. Gộp lại thành một danh sách nhật ký duy nhất
    logs = []
    
    for c in cash:
        logs.append({
            "date": c.created_at.isoformat(),  # Convert datetime → string
            "type": c.type.value,
            "content": f"{c.description}: {int(c.amount):,} VND",
            "category": "CASH"
        })
    
    for s in stocks:
        logs.append({
            "date": s.transaction_date.isoformat(),  # Convert datetime → string
            "type": s.type.value,
            "content": f"{s.type.value} {int(s.volume):,} {s.ticker} @ {int(s.price):,}đ",
            "category": "STOCK"
        })
    
    # 4. Sắp xếp theo thời gian mới nhất lên đầu
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