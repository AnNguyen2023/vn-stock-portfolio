import crawler
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta, date
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from fastapi.exceptions import RequestValidationError


# Import thêm cast và Date để fix lỗi tìm kiếm ngày
from sqlalchemy import cast, Date 

import models
import schemas  # <--- QUAN TRỌNG: Dòng này đang bị thiếu

app = FastAPI()
models.Base.metadata.create_all(bind=models.engine)

# Cấu hình CORS để Next.js (port 3000) gọi được API (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Bắt lỗi định dạng dữ liệu từ Frontend (ví dụ: gửi chữ vào ô số)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Dữ liệu không hợp lệ",
            "detail": exc.errors()
        },
    )

# 2. Bắt lỗi Database
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Lỗi kết nối cơ sở dữ liệu",
            "detail": str(exc)
        },
    )

# 3. Custom Exception Helper để gọi nhanh trong logic
def raise_error(message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=message)


@app.get("/")
def home():
    return {"message": "Hệ thống Quản lý danh mục chứng khoán đang chạy. Truy cập /docs để xem API."}

# Hàm lấy Database Session
def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/deposit")
def deposit_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    try:
        # 1. Lấy thông tin tổng tài sản (Chỉ có 1 bản ghi duy nhất)
        asset = db.query(models.AssetSummary).first()
        
        # 2. Nếu người dùng mới sử dụng App lần đầu, chưa có bản ghi AssetSummary
        if not asset:
            asset = models.AssetSummary(
                cash_balance=Decimal("0"),
                total_deposited=Decimal("0"),
                # Mặc định ngày tính lãi là hôm nay
                last_interest_calc_date=datetime.now().date() 
            )
            db.add(asset)
            # Flush để database ghi nhận object này trước khi cộng tiền
            db.flush() 

        # 3. Cập nhật số dư tiền mặt và tổng vốn đã nạp
        # Lưu ý: Pydantic đã chặn req.amount <= 0 ở vòng ngoài
        asset.cash_balance += req.amount
        asset.total_deposited += req.amount

        # 4. Ghi Nhật ký dòng tiền (CashFlow) để đối soát sau này
        cash_log = models.CashFlow(
            type=models.CashFlowType.DEPOSIT,
            amount=req.amount,
            description=req.description or "Nạp tiền vào tài khoản"
        )
        db.add(cash_log)

        # 5. Commit tất cả thay đổi vào Database
        db.commit()
        
        # Làm mới object để trả về số liệu mới nhất sau khi tính toán
        db.refresh(asset)

        return {
            "status": "success",
            "message": f"Đã nạp thành công {int(req.amount):,} VND",
            "data": {
                "amount_added": float(req.amount),
                "current_balance": float(asset.cash_balance),
                "total_deposited": float(asset.total_deposited)
            }
        }

    except Exception as e:
        # Nếu có bất kỳ lỗi gì xảy ra (ví dụ mất kết nối DB), thu hồi lại các lệnh trên
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi hệ thống khi xử lý nạp tiền: {str(e)}"
        )

# ĐẶT SAU HÀM get_db() VÀ TRƯỚC CÁC HÀM @app.post

@app.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    # 1. Lấy thông tin tài sản tổng quát
    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {"cash_balance": 0, "total_stock_value": 0, "total_nav": 0, "holdings": []}
    
    # Nếu chưa có tài sản (chưa nạp tiền bao giờ), trả về khung dữ liệu trống
    if not asset:
        return {
            "cash_balance": 0,
            "total_stock_value": 0,
            "total_nav": 0,
            "holdings": []
        }

    today = datetime.now().date()

    # 2. LOGIC LAZY UPDATE: Tính lãi tiền mặt qua đêm (Nếu bước sang ngày mới)
    if asset.last_interest_calc_date < today:
        days_passed = (today - asset.last_interest_calc_date).days
        # Lãi suất giả định 0.5%/năm
        overnight_rate = Decimal("0.005") / Decimal("360") 
        interest = asset.cash_balance * overnight_rate * days_passed
        
        if interest > Decimal("0.01"):
            asset.cash_balance += interest
            db.add(models.CashFlow(
                type=models.CashFlowType.INTEREST, 
                amount=interest, 
                description=f"Lãi qua đêm {days_passed} ngày"
            ))
        
        asset.last_interest_calc_date = today
        db.commit()
        db.refresh(asset)

    # 3. Lấy danh sách cổ phiếu đang nắm giữ
    holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
    tickers = [h.ticker for h in holdings]
    
    # 4. Lấy giá thị trường Real-time từ Crawler
    realtime_prices = {}
    if tickers:
        try:
            realtime_prices = crawler.get_current_prices(tickers)
        except Exception as e:
            print(f"Lỗi Crawler: {e}")

    portfolio_data = []
    total_stock_value = Decimal("0")

    # 5. Duyệt qua từng mã để tính toán lãi lỗ
    for h in holdings:
        mkt_price = realtime_prices.get(h.ticker, 0)
        current_price_vnd = Decimal(str(mkt_price)) if mkt_price > 0 else h.average_price
        
        current_value_vnd = current_price_vnd * h.total_volume
        profit_loss = current_value_vnd - (h.average_price * h.total_volume)
        profit_percent = ((current_price_vnd / h.average_price) - 1) * 100 if h.average_price > 0 else 0
        
        total_stock_value += current_value_vnd

        portfolio_data.append({
            "ticker": h.ticker,
            "volume": int(h.total_volume),
            "available": int(h.available_volume),
            "avg_price": float(h.average_price), 
            "current_price": float(current_price_vnd),
            "profit_loss": float(profit_loss),
            "profit_percent": float(profit_percent),
            "current_value": float(current_value_vnd)
        })

    # 6. Tổng kết tài sản (NAV)
    total_nav = asset.cash_balance + total_stock_value

    return {
        "cash_balance": float(asset.cash_balance),
        "total_stock_value": float(total_stock_value),
        "total_nav": float(total_nav),
        "holdings": portfolio_data
    }

@app.post("/buy")
def buy_stock(req: schemas.BuyStockRequest, db: Session = Depends(get_db)):
    # Sử dụng helper raise_error
    if req.volume <= 0: raise_error("Khối lượng mua phải lớn hơn 0")
    if req.price <= 0: raise_error("Giá mua phải lớn hơn 0")
    
    ticker = req.ticker.upper()
    volume = Decimal(str(req.volume))
    price_vnd = Decimal(str(req.price)) 
    fee_rate = Decimal(str(req.fee_rate))

    total_value = volume * price_vnd
    fee = total_value * fee_rate
    total_cost = total_value + fee
    
    asset = db.query(models.AssetSummary).first()
    
    if not asset or asset.cash_balance < total_cost:
        needed = f"{total_cost:,.0f}"
        available = f"{asset.cash_balance:,.0f}" if asset else "0"
        raise_error(f"Không đủ tiền mặt. Cần {needed}, có {available}")
    
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    if holding:
        new_total_volume = Decimal(str(holding.total_volume)) + volume
        new_total_cost = (Decimal(str(holding.total_volume)) * Decimal(str(holding.average_price))) + total_cost
        
        holding.average_price = new_total_cost / new_total_volume
        holding.total_volume = new_total_volume
        holding.available_volume = new_total_volume 
    else:
        holding = models.TickerHolding(
            ticker=ticker,
            total_volume=volume,
            available_volume=volume,
            average_price=(total_cost / volume)
        )
        db.add(holding)
    
    asset.cash_balance -= total_cost
    
    db.add(models.CashFlow(
        type=models.CashFlowType.WITHDRAW, 
        amount=total_cost,
        description=f"Mua {int(volume):,} {ticker} giá {int(price_vnd):,}"
    ))
   
    db.add(models.StockTransaction(
        ticker=ticker,
        type=models.TransactionType.BUY,
        volume=volume,
        price=price_vnd,
        fee=fee,
        total_value=total_cost,
        transaction_date=req.transaction_date,
        settlement_date=req.transaction_date.date()
    ))
    
    db.commit()
    return {"message": f"Đã khớp lệnh mua {int(volume)} {ticker}"}

@app.post("/sell") 
def sell_stock(req: schemas.SellStockRequest, db: Session = Depends(get_db)):
    if req.volume <= 0: raise_error("Khối lượng bán phải lớn hơn 0")
    
    ticker = req.ticker.upper()
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    
    if not holding or holding.total_volume < req.volume:
        current_vol = int(holding.total_volume) if holding else 0
        raise_error(f"Không đủ cổ phiếu {ticker} để bán (Hiện có: {current_vol})")

    actual_price_vnd = Decimal(str(req.price)) 
    gross_revenue = req.volume * actual_price_vnd
    fee = gross_revenue * Decimal(str(req.fee_rate))
    tax = gross_revenue * Decimal(str(req.tax_rate))
    net_proceeds = gross_revenue - fee - tax 

    cost_basis = req.volume * holding.average_price 
    profit = net_proceeds - cost_basis

    # Cập nhật số lượng
    holding.total_volume -= req.volume
    holding.available_volume = holding.total_volume 
    
    # --- LOGIC MỚI: XÓA MÃ NẾU HẾT CỔ PHIẾU ---
    if holding.total_volume <= 0:
        db.delete(holding) 
    # ------------------------------------------
    
    asset = db.query(models.AssetSummary).first()
    asset.cash_balance += net_proceeds

    db.add(models.CashFlow(
        type=models.CashFlowType.DEPOSIT,
        amount=net_proceeds,
        description=f"Bán {int(req.volume):,} {ticker} giá {int(actual_price_vnd):,}"
    ))

    db.add(models.StockTransaction(
        ticker=ticker,
        type=models.TransactionType.SELL,
        volume=req.volume,
        price=actual_price_vnd,
        fee=fee,
        tax=tax,
        total_value=net_proceeds,
        transaction_date=req.transaction_date,
        settlement_date=datetime.now().date() 
    ))

    db.add(models.RealizedProfit(
        ticker=ticker,
        volume=req.volume,
        buy_avg_price=holding.average_price if holding else cost_basis/req.volume,
        sell_price=actual_price_vnd,
        net_profit=profit,
        sell_date=datetime.now() 
    ))

    db.commit()
    return {
        "message": f"Đã bán {req.volume} {ticker}. Lãi/Lỗ: {profit:,.0f} đ", 
        "profit": float(profit)
    }

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    # 1. Lấy dữ liệu từ bảng realized_profit, sắp xếp theo ngày bán mới nhất
    history_data = db.query(models.RealizedProfit).order_by(models.RealizedProfit.sell_date.desc()).all()
    
    # 2. Trả về kết quả dưới dạng danh sách
    return {
        "status": "success",
        "history": history_data
    }

# 1. API Rút tiền
@app.post("/withdraw")
def withdraw_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < req.amount:
        raise_error("Không đủ số dư để rút")
    
    asset.cash_balance -= req.amount
    db.add(models.CashFlow(
        type=models.CashFlowType.WITHDRAW,
        amount=req.amount,
        description=req.description or "Rút tiền khỏi tài khoản"
    ))
    db.commit()
    return {"message": "Rút tiền thành công"}

# 2. API Nhật ký tổng hợp (Audit Log)
@app.get("/logs")
def get_audit_log(db: Session = Depends(get_db)):
    # Lấy lịch sử nạp/rút/lãi
    cash = db.query(models.CashFlow).all()
    # Lấy lịch sử mua/bán
    stocks = db.query(models.StockTransaction).all()
    
    # Gộp lại thành một danh sách nhật ký duy nhất
    logs = []
    for c in cash:
        logs.append({
            "date": c.created_at,
            "type": c.type.value,
            "content": f"{c.description}: {format(int(c.amount), ',')} VND",
            "category": "CASH"
        })
    for s in stocks:
        logs.append({
            "date": s.transaction_date,
            "type": s.type.value,
            "content": f"{s.type.value} {s.volume} {s.ticker} giá {format(int(s.price/1000), ',')}",
            "category": "STOCK"
        })
    
    # Sắp xếp theo thời gian mới nhất lên đầu
    logs.sort(key=lambda x: x['date'], reverse=True)
    return logs

@app.get("/history-summary")
def get_history_summary(start_date: str, end_date: str, db: Session = Depends(get_db)):
    # Chuyển đổi string sang date object
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # --- SỬA LỖI TIMEZONE/GIỜ PHÚT ---
    # Dùng hàm cast để ép cột sell_date (DateTime) về dạng Date trước khi so sánh
    items = db.query(models.RealizedProfit).filter(
        cast(models.RealizedProfit.sell_date, Date) >= start,
        cast(models.RealizedProfit.sell_date, Date) <= end
    ).all()
    
    total_profit = sum(item.net_profit for item in items)
    
    return {
        "total_profit": float(total_profit),
        "trade_count": len(items),
        "details": items
    }

@app.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    assets = db.query(models.AssetSummary).first()
    if not assets: return {}

    # 1. Tính NAV hiện tại (Real-time)
    holdings = db.query(models.TickerHolding).all()
    tickers = [h.ticker for h in holdings]
    realtime_prices = crawler.get_current_prices(tickers)
    
    current_stock_value = sum(
        (Decimal(str(realtime_prices.get(h.ticker, 0))) or h.average_price) * h.total_volume 
        for h in holdings
    )
    current_nav = assets.cash_balance + current_stock_value

    # 2. Hàm hỗ trợ tính Lãi/Lỗ theo mốc thời gian
    def calc_period_profit(days_ago=None, start_of_year=False):
        today_val = date.today()
        if start_of_year:
            target_date = date(today_val.year, 1, 1)
        else:
            target_date = today_val - timedelta(days=days_ago)

        # Lấy NAV tại mốc thời gian đó từ Snapshot
        snapshot = db.query(models.DailySnapshot).filter(models.DailySnapshot.date <= target_date).order_by(models.DailySnapshot.date.desc()).first()
        
        old_nav = snapshot.total_nav if snapshot else Decimal("0")

        # Tính Net nộp rút từ target_date đến nay
        target_datetime = datetime.combine(target_date, datetime.min.time())
        cash_flows = db.query(models.CashFlow).filter(models.CashFlow.created_at >= target_datetime).all()
        
        net_flow = sum((c.amount if c.type == models.CashFlowType.DEPOSIT else -c.amount) 
                       for c in cash_flows 
                       if c.type in [models.CashFlowType.DEPOSIT, models.CashFlowType.WITHDRAW])
        
        # Công thức: Lãi ròng = NAV hiện tại - (NAV cũ + Nộp rút ròng)
        profit = current_nav - (old_nav + net_flow)
        
        # Tính % tăng trưởng
        denominator = old_nav + net_flow
        percent = (profit / denominator * 100) if denominator > 0 else 0
        
        return float(profit), float(percent)

    # 3. Tính toán cho các mốc
    p1d, pc1d = calc_period_profit(days_ago=1)
    p1m, pc1m = calc_period_profit(days_ago=30)
    p1y, pc1y = calc_period_profit(days_ago=365)
    pytd, pcytd = calc_period_profit(start_of_year=True)

    # Tự động chốt số dư cuối ngày hôm nay vào DailySnapshot
    today_s = db.query(models.DailySnapshot).filter_by(date=date.today()).first()
    if not today_s:
        db.add(models.DailySnapshot(date=date.today(), total_nav=current_nav))
    else:
        today_s.total_nav = current_nav
    db.commit()

    return {
        "1d": {"val": p1d, "pct": pc1d},
        "1m": {"val": p1m, "pct": pc1m},
        "1y": {"val": p1y, "pct": pc1y},
        "ytd": {"val": pytd, "pct": pcytd}
    }

@app.get("/historical")
def get_historical(ticker: str, period: str = "1m"):
    """
    API lấy dữ liệu lịch sử vẽ biểu đồ.
    VD: /historical?ticker=HPG&period=3m
    """
    data = crawler.get_historical_prices(ticker, period)
    
    return {
        "status": "success",
        "ticker": ticker.upper(),
        "period": period,
        "data": data
    }

@app.post("/reset-data")
def reset_data(db: Session = Depends(get_db)):
    db.query(models.StockTransaction).delete()
    db.query(models.TickerHolding).delete()
    db.query(models.AssetSummary).delete()
    db.query(models.CashFlow).delete()
    db.query(models.RealizedProfit).delete()
    db.commit()
    return {"message": "Dữ liệu đã được xóa sạch."}