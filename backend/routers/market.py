from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta, date
import models
import crawler
import time
from sqlalchemy import cast, Date

router = APIRouter(tags=["Market Data"])

# Hàm lấy DB tại chỗ cho chuẩn
def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/seed-index")
def seed_index_data(background_tasks: BackgroundTasks):
    """Lệnh cho Tèo em đi nhặt 1 năm dữ liệu VNINDEX về kho"""
    def slow_crawl_task():
        print("--- [KHO] Tèo em đang chuẩn bị đi nhặt VN-INDEX ---")
        # SỬA TÊN HÀM: get_historical_prices
        live_data = crawler.get_historical_prices("VNINDEX", period="1y")
        if live_data:
            with models.SessionLocal() as db:
                count = 0
                for item in live_data:
                    try:
                        d = datetime.strptime(item['date'], '%Y-%m-%d').date()
                        exist = db.query(models.HistoricalPrice).filter_by(ticker="VNINDEX", date=d).first()
                        if not exist:
                            db.add(models.HistoricalPrice(ticker="VNINDEX", date=d, close_price=Decimal(str(item['close']))))
                            count += 1
                    except: continue
                db.commit()
                print(f"--- [XONG] Đã cất thêm {count} ngày VN-INDEX vào kho! ---")
    background_tasks.add_task(slow_crawl_task)
    return {"message": "Tèo em đang đi nhặt VN-INDEX, đại ca chờ xíu nhé!"}

@router.post("/sync-portfolio-history")
def sync_portfolio_history(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Tèo em tự quét danh mục, nhặt history cho các mã (nghỉ 2s mỗi mã)"""
    holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
    tickers = [h.ticker for h in holdings]
    
    def heavy_sync_task():
        for t in tickers:
            print(f"--- [SO ĐỐI] Kiểm tra kho mã {t} ---")
            # SỬA TÊN HÀM: get_historical_prices
            live_data = crawler.get_historical_prices(t, period="1y")
            if live_data:
                with models.SessionLocal() as inner_db:
                    for item in live_data:
                        try:
                            d = datetime.strptime(item['date'], '%Y-%m-%d').date()
                            exist = inner_db.query(models.HistoricalPrice).filter_by(ticker=t, date=d).first()
                            if not exist:
                                inner_db.add(models.HistoricalPrice(ticker=t, date=d, close_price=Decimal(str(item['close']))))
                        except: continue
                    inner_db.commit()
            print(f"--- [NGHỈ] Xong mã {t}, Tèo em nghỉ 2 giây ---")
            time.sleep(2)
        print("--- [XONG] Đã đồng bộ toàn bộ history danh mục! ---")

    background_tasks.add_task(heavy_sync_task)
    return {"message": f"Tèo em đang nhặt history cho {len(tickers)} mã của đại ca."}

# backend/routers/market.py

@router.get("/historical")
def get_historical(ticker: str, background_tasks: BackgroundTasks, period: str = "1m", db: Session = Depends(get_db)):
    ticker = ticker.upper()
    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    start_date = date.today() - timedelta(days=days_map.get(period, 30))
    
    # 1. ƯU TIÊN LẤY TRONG KHO (DATABASE)
    stored_data = db.query(models.HistoricalPrice).filter(
        models.HistoricalPrice.ticker == ticker,
        models.HistoricalPrice.date >= start_date
    ).order_by(models.HistoricalPrice.date.asc()).all()

    # 2. KIỂM TRA NẾU KHO TRỐNG THÌ MỚI CHO ĐI CRAWL NGẦM (TRÁNH GỌI DỒN DẬP)
    # Nếu chưa có đủ dữ liệu, Tèo em sẽ cho Worker đi nhặt từ từ
    if len(stored_data) < 5: 
        background_tasks.add_task(sync_historical_task, ticker, period)

    # 3. TRẢ VỀ DATA HIỆN CÓ ĐỂ FRONTEND THOÁT LOADING
    return {
        "status": "success", 
        "data": [{"date": i.date.strftime('%Y-%m-%d'), "close": float(i.close_price)} for i in stored_data]
    }

def sync_historical_task(ticker: str, period: str):
    """Hàm Worker nhặt data 'kiến tha lâu đầy tổ'"""
    # Nghỉ giải lao 2s để CTCK không nghi ngờ (Lệnh đại ca Zon)
    time.sleep(0)
        
    with models.SessionLocal() as db:
        try:
            live_data = crawler.get_historical_prices(ticker, period)
            if live_data:
                for item in live_data:
                    d = datetime.strptime(item['date'], '%Y-%m-%d').date()
                    exist = db.query(models.HistoricalPrice).filter_by(ticker=ticker, date=d).first()
                    if not exist:
                        db.add(models.HistoricalPrice(
                            ticker=ticker, date=d, close_price=Decimal(str(item['close']))
                        ))
                db.commit()
                print(f"--- [KHO] ĐÃ NẠP XONG DATA CHO {ticker} ---")
        except Exception as e:
            print(f"--- [LỖI KHO] {ticker}: {e} ---")