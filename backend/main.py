import crawler
import models
import schemas
import redis  # <--- PHẢI CÓ DÒNG NÀY (viết thường)
import json
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta, date
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from fastapi.exceptions import RequestValidationError
from sqlalchemy import cast, Date, desc
from rq import Queue # Import Queue để dùng cho Worker

app = FastAPI()

# Khởi tạo bảng ngay khi chạy server
models.Base.metadata.create_all(bind=models.engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- CẤU HÌNH REDIS & QUEUE ---
# Trong Docker, link là 'redis', ngoài Docker (local) là 'localhost'
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
# Sử dụng module redis đã import ở trên
redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
q = Queue(connection=redis_conn)


# --- 1. XỬ LÝ LỖI TẬP TRUNG ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Dữ liệu không hợp lệ", "detail": exc.errors()[0]['msg']}
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Lỗi cơ sở dữ liệu", "detail": str(exc)}
    )

def raise_error(message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=message)

# --- 2. CẤU TRÚC DATABASE SESSION ---

def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. API HIỂN THỊ (GET) ---

@app.get("/")
def home():
    return {"message": "Invest Journal API is running"}

@app.get("/dashboard-init")
def dashboard_init(db: Session = Depends(get_db)):
    return {
        "portfolio": get_portfolio(db),
        "logs": get_audit_log(db),
        "performance": get_performance(db)
    }

@app.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {"cash_balance": 0, "total_stock_value": 0, "total_nav": 0, "holdings": []}

    # Logic lãi qua đêm
    today = date.today()
    if asset.last_interest_calc_date < today:
        days = (today - asset.last_interest_calc_date).days
        interest = asset.cash_balance * (Decimal("0.005") / Decimal("360")) * days
        if interest > Decimal("0.01"):
            asset.cash_balance += interest
            db.add(models.CashFlow(type=models.CashFlowType.INTEREST, amount=interest, description=f"Lãi qua đêm {days} ngày"))
        asset.last_interest_calc_date = today
        db.commit()

    holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
    realtime_prices = crawler.get_current_prices([h.ticker for h in holdings])
    
    portfolio_data = []
    total_stock_value = Decimal("0")

    for h in holdings:
        mkt_price = Decimal(str(realtime_prices.get(h.ticker, 0)))
        curr_price = mkt_price if mkt_price > 0 else h.average_price
        curr_val = curr_price * h.total_volume
        profit_loss = curr_val - (h.average_price * h.total_volume)
        profit_pct = ((curr_price / h.average_price) - 1) * 100 if h.average_price > 0 else 0
        total_stock_value += curr_val

        portfolio_data.append({
            "ticker": h.ticker,
            "volume": int(h.total_volume),
            "available": int(h.available_volume),
            "avg_price": float(h.average_price / 1000),
            "current_price": float(curr_price / 1000),
            "profit_loss": float(profit_loss),
            "profit_percent": float(profit_pct),
            "current_value": float(curr_val)
        })

    return {
        "cash_balance": float(asset.cash_balance),
        "total_stock_value": float(total_stock_value),
        "total_nav": float(asset.cash_balance + total_stock_value),
        "holdings": portfolio_data
    }

# --- 4. API GIAO DỊCH (POST) ---

@app.post("/deposit")
def deposit_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    asset = db.query(models.AssetSummary).first()
    if not asset:
        asset = models.AssetSummary(cash_balance=0, total_deposited=0, last_interest_calc_date=date.today())
        db.add(asset)
    asset.cash_balance += req.amount
    asset.total_deposited += req.amount
    db.add(models.CashFlow(type=models.CashFlowType.DEPOSIT, amount=req.amount, description=req.description))
    db.commit()
    return {"message": "Thành công"}

@app.post("/withdraw")
def withdraw_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < req.amount:
        raise_error("Không đủ số dư để rút")
    asset.cash_balance -= req.amount
    db.add(models.CashFlow(type=models.CashFlowType.WITHDRAW, amount=req.amount, description=req.description))
    db.commit()
    return {"message": "Thành công"}

@app.post("/buy")
def buy_stock(req: schemas.BuyStockRequest, db: Session = Depends(get_db)):
    ticker = req.ticker.upper()
    total_cost = (Decimal(str(req.volume)) * Decimal(str(req.price))) * (1 + Decimal(str(req.fee_rate)))
    
    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < total_cost:
        raise_error(f"Thiếu {float(total_cost - asset.cash_balance):,.0f} VND")

    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    if holding:
        new_vol = holding.total_volume + req.volume
        holding.average_price = ((holding.total_volume * holding.average_price) + total_cost) / new_vol
        holding.total_volume = new_vol
        holding.available_volume = new_vol
    else:
        db.add(models.TickerHolding(ticker=ticker, total_volume=req.volume, available_volume=req.volume, average_price=total_cost/req.volume))

    asset.cash_balance -= total_cost
    db.add(models.CashFlow(type=models.CashFlowType.WITHDRAW, amount=total_cost, description=f"Mua {req.volume} {ticker}"))
    db.add(models.StockTransaction(ticker=ticker, type=models.TransactionType.BUY, volume=req.volume, price=req.price, total_value=total_cost))
    db.commit()
    return {"message": "Đã khớp lệnh mua"}

@app.post("/sell")
def sell_stock(req: schemas.SellStockRequest, db: Session = Depends(get_db)):
    ticker = req.ticker.upper()
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    if not holding or holding.total_volume < req.volume:
        raise_error("Không đủ cổ phiếu")

    revenue = (Decimal(str(req.volume)) * Decimal(str(req.price))) * (1 - Decimal(str(req.fee_rate)) - Decimal(str(req.tax_rate)))
    profit = revenue - (Decimal(str(req.volume)) * holding.average_price)

    holding.total_volume -= req.volume
    holding.available_volume = holding.total_volume
    if holding.total_volume <= 0: db.delete(holding)

    asset = db.query(models.AssetSummary).first()
    asset.cash_balance += revenue
    db.add(models.CashFlow(type=models.CashFlowType.DEPOSIT, amount=revenue, description=f"Bán {req.volume} {ticker}"))
    db.add(models.StockTransaction(ticker=ticker, type=models.TransactionType.SELL, volume=req.volume, price=req.price, total_value=revenue))
    db.add(models.RealizedProfit(ticker=ticker, volume=req.volume, buy_avg_price=holding.average_price if holding else 0, sell_price=req.price, net_profit=profit))
    db.commit()
    return {"message": "Đã khớp lệnh bán"}

@app.post("/undo-last-buy")
def undo_last_buy(db: Session = Depends(get_db)):
    print("--- [DEBUG] BẮT ĐẦU QUY TRÌNH UNDO ---")
    
    # 1. Lấy giao dịch cuối cùng - Chỉ lọc duy nhất lệnh MUA
    # Chúng ta tìm lệnh mua gần nhất dựa trên ID lớn nhất
    last_tx = db.query(models.StockTransaction).filter(
        models.StockTransaction.type == models.TransactionType.BUY
    ).order_by(models.StockTransaction.id.desc()).first()
    
    if not last_tx:
        print("--- [DEBUG] KHÔNG TÌM THẤY LỆNH MUA NÀO ---")
        raise HTTPException(status_code=400, detail="Không tìm thấy lệnh mua nào để hoàn tác.")

    print(f"--- [DEBUG] ĐANG XỬ LÝ MÃ: {last_tx.ticker}, GIÁ TRỊ: {last_tx.total_value} ---")

    try:
        # 2. Lấy dữ liệu Asset và Holding
        asset = db.query(models.AssetSummary).first()
        holding = db.query(models.TickerHolding).filter(models.TickerHolding.ticker == last_tx.ticker).first()

        # 3. HOÀN TIỀN MẶT (Dùng float trung gian để tuyệt đối không lỗi Decimal)
        if asset:
            current_cash = float(asset.cash_balance)
            refund_amount = float(last_tx.total_value)
            asset.cash_balance = Decimal(str(current_cash + refund_amount))
            print(f"--- [DEBUG] ĐÃ HOÀN TIỀN: {refund_amount} ---")

        # 4. HOÀN CỔ PHIẾU
        if holding:
            curr_vol = float(holding.total_volume)
            tx_vol = float(last_tx.volume)
            
            if curr_vol <= tx_vol:
                # Nếu hoàn tác xong là hết sạch mã này -> Xóa luôn
                db.delete(holding)
                print(f"--- [DEBUG] ĐÃ XÓA MÃ {last_tx.ticker} KHỎI DANH MỤC ---")
            else:
                # Tính lại giá vốn bình quân cũ
                # Tổng vốn cũ = (Vốn hiện tại * SL hiện tại) - Vốn lệnh vừa mua
                curr_price = float(holding.average_price)
                new_vol = curr_vol - tx_vol
                old_total_cost = (curr_vol * curr_price) - float(last_tx.total_value)
                
                holding.total_volume = Decimal(str(new_vol))
                holding.available_volume = Decimal(str(new_vol))
                holding.average_price = Decimal(str(old_total_cost / new_vol))
                print(f"--- [DEBUG] ĐÃ GIẢM SL {last_tx.ticker} VỀ {new_vol} ---")

        # 5. XÓA NHẬT KÝ DÒNG TIỀN (Log Withdraw của mã này)
        cash_log = db.query(models.CashFlow).filter(
            models.CashFlow.type == models.CashFlowType.WITHDRAW,
            models.CashFlow.description.contains(last_tx.ticker)
        ).order_by(models.CashFlow.id.desc()).first()
        
        if cash_log:
            db.delete(cash_log)
            print("--- [DEBUG] ĐÃ XÓA LOG DÒNG TIỀN ---")

        # 6. XÓA CHÍNH LỆNH GIAO DỊCH ĐÓ
        db.delete(last_tx)
        
        db.commit()
        print("--- [DEBUG] HOÀN TÁC THÀNH CÔNG RỰC RỠ ---")
        return {"message": f"Đã hoàn tác thành công lệnh mua {last_tx.ticker}."}

    except Exception as e:
        db.rollback()
        import traceback
        error_info = traceback.format_exc()
        print(f"--- [CRITICAL ERROR] ---\n{error_info}")
        raise HTTPException(status_code=500, detail=f"Lỗi logic Backend: {str(e)}")


@app.get("/logs")
def get_audit_log(db: Session = Depends(get_db)):
    cash = db.query(models.CashFlow).all()
    stocks = db.query(models.StockTransaction).all()
    logs = []
    for c in cash:
        logs.append({"date": c.created_at, "type": c.type.value, "content": f"{c.description}: {int(c.amount):,} đ", "category": "CASH"})
    for s in stocks:
        logs.append({"date": s.transaction_date, "type": s.type.value, "content": f"{s.type.value} {int(s.volume)} {s.ticker} giá {int(s.price):,}", "category": "STOCK"})
    logs.sort(key=lambda x: x['date'], reverse=True)
    return logs

from redis import Redis
from rq import Queue
import json

# Kết nối Redis
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
q = Queue(connection=redis_conn)

@app.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    # 1. THỬ LẤY TỪ CACHE REDIS
    cache_key = "dashboard_performance"
    cached_data = redis_conn.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # 2. NẾU KHÔNG CÓ TRONG CACHE -> TÍNH TOÁN (Logic cũ của bạn)
    asset = db.query(models.AssetSummary).first()
    if not asset: return {}
    
    holdings = db.query(models.TickerHolding).all()
    prices = crawler.get_current_prices([h.ticker for h in holdings])
    curr_stock_val = sum((Decimal(str(prices.get(h.ticker, 0))) or h.average_price) * h.total_volume for h in holdings)
    curr_nav = asset.cash_balance + curr_stock_val

    def calc_pct(days_ago=None, ytd=False):
        target = date(date.today().year, 1, 1) if ytd else (date.today() - timedelta(days=days_ago))
        snap = db.query(models.DailySnapshot).filter(models.DailySnapshot.date <= target).order_by(desc(models.DailySnapshot.date)).first()
        old_nav = snap.total_nav if snap else Decimal("0")
        flows = db.query(models.CashFlow).filter(cast(models.CashFlow.created_at, Date) >= target).all()
        net_flow = sum((f.amount if f.type == models.CashFlowType.DEPOSIT else -f.amount) for f in flows if f.type in [models.CashFlowType.DEPOSIT, models.CashFlowType.WITHDRAW])
        profit = curr_nav - (old_nav + net_flow)
        denom = old_nav + net_flow
        return float(profit), float((profit / denom * 100) if denom > 0 else 0)

    result = {
        "1d": {"val": calc_pct(days_ago=1)[0], "pct": calc_pct(days_ago=1)[1]},
        "1m": {"val": calc_pct(days_ago=30)[0], "pct": calc_pct(days_ago=30)[1]},
        "1y": {"val": calc_pct(days_ago=365)[0], "pct": calc_pct(days_ago=365)[1]},
        "ytd": {"val": calc_pct(ytd=True)[0], "pct": calc_pct(ytd=True)[1]}
    }

    # 3. LƯU VÀO REDIS TRONG 5 PHÚT (300 giây)
    redis_conn.setex(cache_key, 300, json.dumps(result))
    
    # 4. ĐẨY NHIỆM VỤ CHỐT SỔ NGẦM CHO WORKER (Dùng RQ)
    from tasks import update_daily_snapshot_task
    q.enqueue(update_daily_snapshot_task)

    return result

@app.get("/historical")
def get_historical(ticker: str, period: str = "1m"):
    return {"status": "success", "data": crawler.get_historical_prices(ticker, period)}

@app.get("/history-summary")
def get_history_summary(start_date: str, end_date: str, db: Session = Depends(get_db)):
    items = db.query(models.RealizedProfit).filter(cast(models.RealizedProfit.sell_date, Date) >= datetime.strptime(start_date, "%Y-%m-%d").date(), cast(models.RealizedProfit.sell_date, Date) <= datetime.strptime(end_date, "%Y-%m-%d").date()).all()
    return {"total_profit": float(sum(i.net_profit for i in items)), "trade_count": len(items)}

@app.post("/reset-data")
def reset_data(db: Session = Depends(get_db)):
    """Xóa sạch dữ liệu để làm lại từ đầu"""
    db.query(models.StockTransaction).delete()
    db.query(models.TickerHolding).delete()
    db.query(models.AssetSummary).delete()
    db.query(models.CashFlow).delete()
    db.query(models.RealizedProfit).delete()
    db.query(models.DailySnapshot).delete()
    db.commit()
    return {"message": "Hệ thống đã được đưa về trạng thái trắng."}