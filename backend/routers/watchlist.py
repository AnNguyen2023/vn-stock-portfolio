# routers/watchlist.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from core.db import get_db

router = APIRouter(prefix="/watchlists", tags=["Watchlist"])

@router.get("/", response_model=List[schemas.WatchlistSchema])
def get_watchlists(db: Session = Depends(get_db)):
    """Lấy danh sách các Watchlist của người dùng"""
    return db.query(models.Watchlist).all()

@router.post("/", response_model=schemas.WatchlistSchema)
def create_watchlist(req: schemas.WatchlistCreate, db: Session = Depends(get_db)):
    """Tạo một Watchlist mới"""
    exist = db.query(models.Watchlist).filter(models.Watchlist.name == req.name).first()
    if exist:
        raise HTTPException(status_code=400, detail="Tên danh sách đã tồn tại")
    
    new_wl = models.Watchlist(name=req.name)
    db.add(new_wl)
    db.commit()
    db.refresh(new_wl)
    return new_wl

@router.delete("/{id}")
def delete_watchlist(id: int, db: Session = Depends(get_db)):
    """Xóa một Watchlist"""
    wl = db.query(models.Watchlist).filter(models.Watchlist.id == id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh sách")
    
    db.delete(wl)
    db.commit()
    return {"message": "Đã xóa danh sách"}

@router.post("/{id}/tickers", response_model=schemas.WatchlistTickerSchema)
def add_ticker_to_watchlist(id: int, req: schemas.WatchlistTickerCreate, db: Session = Depends(get_db)):
    """Thêm mã chứng khoán vào danh sách"""
    wl = db.query(models.Watchlist).filter(models.Watchlist.id == id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh sách")
    
    ticker = req.ticker.strip().upper()
    
    # 1. Kiểm tra xem mã đã có trong danh sách chưa
    exist = db.query(models.WatchlistTicker).filter_by(watchlist_id=id, ticker=ticker).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"Mã {ticker} đã có trong danh sách")
    
    # 2. Kiểm tra xem mã có thực sự tồn tại trên thị trường không
    security = db.query(models.Security).filter_by(symbol=ticker).first()
    if not security:
        raise HTTPException(status_code=400, detail=f"Mã '{ticker}' không hợp lệ")
    
    new_ticker = models.WatchlistTicker(watchlist_id=id, ticker=ticker)
    db.add(new_ticker)
    db.commit()
    db.refresh(new_ticker)
    return new_ticker

@router.delete("/{id}/tickers/{ticker_id}")
def remove_ticker_from_watchlist(id: int, ticker_id: int, db: Session = Depends(get_db)):
    """Xóa mã chứng khoán khỏi danh sách"""
    item = db.query(models.WatchlistTicker).filter_by(id=ticker_id, watchlist_id=id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã trong danh sách")
    
    db.delete(item)
    db.commit()
    return {"message": "Đã xóa mã khỏi danh sách"}

@router.get("/{id}/detail")
def get_watchlist_detail(id: int, db: Session = Depends(get_db)):
    """Lấy dữ liệu Pro cho toàn bộ mã trong Watchlist"""
    wl = db.query(models.Watchlist).filter(models.Watchlist.id == id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh sách")
    
    tickers = [t.ticker for t in wl.tickers]
    from services.market_service import get_watchlist_detail_service
    return get_watchlist_detail_service(tickers)
