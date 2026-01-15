# routers/logs.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date
from datetime import datetime
from core.db import get_db
from core.exceptions import EntityNotFoundException, ValidationError
from core.logger import logger
import models
import schemas

router = APIRouter(tags=["Audit Logs"])

@router.get("/logs")
def get_audit_log(db: Session = Depends(get_db)):
    """
    Returns a unified timeline of all financial events: Deposits, Withdrawals, Buy/Sell trades.
    """
    # 1. Fetch historical record types
    cash = db.query(models.CashFlow).all()
    stocks = db.query(models.StockTransaction).all()
    
    logs = []
    
    # 2. Normalize CashFlow entries
    for c in cash:
        status_suffix = " (Chờ về)" if c.status == models.CashFlowStatus.PENDING else ""
        logs.append({
            "date": c.created_at.isoformat(),
            "type": c.type.value,
            "content": f"{c.description}: {int(c.amount):,} VND{status_suffix}",
            "category": "CASH",
            "status": c.status.value
        })
    
    # 3. Normalize StockTransaction entries
    for s in stocks:
        logs.append({
            "id": s.id,
            "date": s.transaction_date.isoformat(),
            "type": s.type.value,
            "content": f"{s.type.value} {int(s.volume):,} {s.ticker} @ {int(s.price):,} VNĐ",
            "note": s.note,
            "category": "STOCK"
        })
    
    # 4. Sort by chronological descending order
    logs.sort(key=lambda x: x['date'], reverse=True)
    
    return {"success": True, "data": logs}

@router.put("/logs/{tx_id}/note")
def update_note(tx_id: int, req: schemas.NoteUpdate, db: Session = Depends(get_db)):
    """
    Updates the personal note/rationale for a specific stock transaction.
    """
    transaction = db.query(models.StockTransaction).filter(models.StockTransaction.id == tx_id).first()
    if not transaction:
        raise EntityNotFoundException("Transaction", tx_id)
        
    transaction.note = req.note
    db.commit()
    logger.info(f"Updated note for transaction {tx_id}")
    
    return {"success": True, "message": "Transaction note updated successfully."}

@router.get("/history-summary")
def get_history_summary(start_date: str, end_date: str, db: Session = Depends(get_db)):
    """
    Provides a high-level summary of realized profit/loss within a specific date range.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Invalid date format. Expected YYYY-MM-DD.")
        
    items = (
        db.query(models.RealizedProfit)
        .filter(
            cast(models.RealizedProfit.sell_date, Date) >= start, 
            cast(models.RealizedProfit.sell_date, Date) <= end
        ).all()
    )
    
    data = {
        "total_profit": float(sum(i.net_profit for i in items)), 
        "trade_count": len(items)
    }
    
    return {"success": True, "data": data}