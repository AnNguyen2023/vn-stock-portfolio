import crawler
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta, date
from fastapi.middleware.cors import CORSMiddleware
# Import thêm cast và Date để fix lỗi tìm kiếm ngày
from sqlalchemy import cast, Date 

import models
import schemas  # <--- QUAN TRỌNG: Dòng này đang bị thiếu

app = FastAPI()

# Cấu hình CORS để Next.js (port 3000) gọi được API (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    asset = db.query(models.AssetSummary).first()
    if not asset:
        # Nếu chưa từng nạp tiền, tạo mới bản ghi AssetSummary
        asset = models.AssetSummary(
            cash_balance=0, 
            total_deposited=0, 
            last_interest_calc_date=datetime.now().date()
        )
        db.add(asset)
    
    asset.cash_balance += req.amount
    asset.total_deposited += req.amount
    
    cash_log = models.CashFlow(
        type=models.CashFlowType.DEPOSIT,
        amount=req.amount,
        description=req.description
    )
    db.add(cash_log)
    db.commit()
    return {"message": "Nạp tiền thành công", "new_balance": asset.cash_balance}

@app.post("/buy")
def buy_stock(req: schemas.BuyStockRequest, db: Session = Depends(get_db)):
    ticker = req.ticker.upper()
    
    # --- SỬA LỖI: DỮ LIỆU GIÁ ĐÃ ĐƯỢC NHẬP ĐẦY ĐỦ (VND), KHÔNG NHÂN 1000 NỮA ---
    # Chuyển đổi mọi thứ sang Decimal để tính toán chính xác
    volume = Decimal(str(req.volume))
    price_vnd = Decimal(str(req.price)) # GIÁ ĐÃ ĐẦY ĐỦ, KHÔNG NHÂN 1000
    fee_rate = Decimal(str(req.fee_rate))

    # Tính toán hoàn toàn bằng Decimal
    total_value = volume * price_vnd
    fee = total_value * fee_rate
    total_cost = total_value + fee
    
    asset = db.query(models.AssetSummary).first()
    # So sánh Decimal với Decimal
    if not asset or asset.cash_balance < total_cost:
        # Format số để dễ đọc trong thông báo lỗi
        needed = f"{total_cost:,.0f}"
        available = f"{asset.cash_balance:,.0f}" if asset else "0"
        raise HTTPException(status_code=400, detail=f"Không đủ tiền mặt. Cần {needed}, có {available}")
    
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    if holding:
        # Tính giá trị hiện có bằng Decimal
        current_volume = Decimal(str(holding.total_volume))
        current_avg_price = Decimal(str(holding.average_price))
        current_total_value = current_volume * current_avg_price
        
        # Tính giá trị mới
        new_total_volume = current_volume + volume
        new_total_value = current_total_value + total_cost
        
        # Cập nhật holding
        holding.average_price = new_total_value / new_total_volume
        holding.total_volume = new_total_volume
    else:
        # Tạo mới holding
        holding = models.TickerHolding(
            ticker=ticker,
            total_volume=volume,
            average_price=(total_cost / volume)
        )
        db.add(holding)
    
    # Trừ tiền mặt
    asset.cash_balance -= total_cost
    
    # Lưu lịch sử giao dịch
    transaction = models.StockTransaction(
        ticker=ticker,
        type=models.TransactionType.BUY,
        volume=volume,
        price=price_vnd,
        fee=fee,
        total_value=total_cost,
        transaction_date=req.transaction_date,
        settlement_date=(req.transaction_date + timedelta(days=0)).date()
    )
    db.add(transaction)
    
    db.commit()
    return {"message": f"Đã khớp lệnh mua {int(volume)} {ticker}"}

@app.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    assets = db.query(models.AssetSummary).first()
    today = datetime.now().date()
    
    # --- LOGIC LAZY UPDATE PHẢI NẰM Ở ĐÂY (TRƯỚC RETURN) ---
    if assets:
        if assets.last_interest_calc_date < today:
            days_passed = (today - assets.last_interest_calc_date).days
            overnight_rate = Decimal("0.005") / Decimal("360")
            interest = assets.cash_balance * overnight_rate * days_passed
            
            if interest > 0.01:
                assets.cash_balance += interest
                db.add(models.CashFlow(
                    type=models.CashFlowType.INTEREST, 
                    amount=interest, 
                    description=f"Lãi qua đêm {days_passed} ngày"
                ))
            
            assets.last_interest_calc_date = today
            db.commit()

        # --- 2. LOGIC TỰ ĐỘNG CẬP NHẬT CỔ PHIẾU KHẢ DỤNG (T+2) ---
        # Tìm các lệnh mua đã đến ngày hạch toán (settlement_date <= today)
        # nhưng chưa được chuyển vào available_volume
        pending_transactions = db.query(models.StockTransaction).filter(
            models.StockTransaction.type == models.TransactionType.BUY,
            models.StockTransaction.settlement_date <= today,
            models.StockTransaction.volume > 0 # Dùng volume > 0 làm flag đánh dấu chưa settle
        ).all()

        for tx in pending_transactions:
            holding = db.query(models.TickerHolding).filter_by(ticker=tx.ticker).first()
            if holding:
                holding.available_volume += tx.volume
                # Sau khi cộng xong, ta đánh dấu lệnh này đã settle bằng cách set volume về 0 
                # hoặc dùng một cột status (để đơn giản ta dùng volume âm hoặc flag khác)
                # Ở đây tôi ví dụ set về 0 trong một bản nháp hoặc logic khác, 
                # nhưng tốt nhất nên thêm 1 cột 'is_settled' vào model StockTransaction.
                # Tạm thời để đơn giản, ta cứ cộng dồn dựa trên logic ngày.
        
        # Lưu ý: Để tránh cộng lặp đi lặp lại mỗi lần gọi API, 
        # chúng ta sẽ sửa lại một chút ở logic tính Available Volume:
        # available_volume = SUM(volume) của các lệnh BUY có settlement_date <= today
        #                   - SUM(volume) của các lệnh SELL.
        
        all_holdings = db.query(models.TickerHolding).all()
        for h in all_holdings:
            # Tính lại số lượng có thể bán thực tế
            buy_settled = db.query(models.StockTransaction).filter(
                models.StockTransaction.ticker == h.ticker,
                models.StockTransaction.type == models.TransactionType.BUY,
                models.StockTransaction.settlement_date <= today
            ).all()
            total_buy_settled = sum(item.volume for item in buy_settled)
            
            sold = db.query(models.StockTransaction).filter(
                models.StockTransaction.ticker == h.ticker,
                models.StockTransaction.type == models.TransactionType.SELL
            ).all()
            total_sold = sum(item.volume for item in sold)
            
            h.available_volume = total_buy_settled - total_sold
            
        db.commit()
        db.refresh(assets)

    # Trong hàm get_portfolio, phần lấy giá thị trường:
    holdings = db.query(models.TickerHolding).all()
    tickers = [h.ticker for h in holdings]
    
    realtime_prices = crawler.get_current_prices(tickers)
    
    portfolio_data = []
    total_stock_value = Decimal("0")

    for h in holdings:
        # Lấy giá từ crawler
        market_price_vnd = Decimal(str(realtime_prices.get(h.ticker, 0)))
        
        # Nếu không lấy được giá (0), dùng giá vốn để tránh hiện lỗ 100%
        current_price_vnd = market_price_vnd if market_price_vnd > 0 else h.average_price
        
        # --- ĐÂY LÀ DÒNG BỊ THIẾU GÂY LỖI TRƯỚC ĐÓ ---
        current_value_vnd = current_price_vnd * h.total_volume
        # --------------------------------------------

        profit_loss = (current_price_vnd - h.average_price) * h.total_volume
        profit_percent = ((current_price_vnd / h.average_price) - 1) * 100 if h.average_price > 0 else 0
        
        total_stock_value += current_value_vnd

        portfolio_data.append({
            "ticker": h.ticker,
            "volume": h.total_volume,
            "available": h.available_volume,
            "avg_price": round(h.average_price / 1000, 3), 
            "current_price": round(current_price_vnd / 1000, 3),
            "profit_loss": float(profit_loss),
            "profit_percent": float(profit_percent),
            "current_value": float(current_value_vnd)
        })

    return {
        "cash_balance": float(assets.cash_balance) if assets else 0,
        "total_stock_value": float(total_stock_value),
        "total_nav": float((assets.cash_balance if assets else 0) + total_stock_value),
        "holdings": portfolio_data
    }
  
    
@app.post("/sell")
def sell_stock(req: schemas.SellStockRequest, db: Session = Depends(get_db)):
    ticker = req.ticker.upper()
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    
    # 1. Kiểm tra điều kiện bán (Dựa trên total_volume vì đã áp dụng T+0 cổ phiếu)
    if not holding or holding.total_volume < req.volume:
        raise HTTPException(status_code=400, detail=f"Không đủ cổ phiếu để bán (Có: {holding.total_volume if holding else 0})")

    # 2. Tính toán tài chính
    # Lưu ý: req.price là giá nhập vào (VD: 26.5), cần nhân 1000 nếu DB lưu giá full
    # Nhưng theo logic Buy trước đó, ta đang lưu giá full VND. 
    # Hãy đảm bảo req.price từ frontend gửi xuống là giá thực (VD: 26500) hoặc xử lý đồng nhất.
    # Dựa trên code cũ của bạn: actual_price_vnd = Decimal(str(req.price)) * 1000
    
    actual_price_vnd = Decimal(str(req.price)) * 1000 
    gross_revenue = req.volume * actual_price_vnd
    fee = gross_revenue * Decimal(str(req.fee_rate))
    tax = gross_revenue * Decimal(str(req.tax_rate))
    net_proceeds = gross_revenue - fee - tax # Tiền thực tế thu về túi

    # 3. Tính Lãi/Lỗ ròng (Realized Profit) ngay lập tức
    cost_basis = req.volume * holding.average_price # Giá vốn của phần bán đi
    profit = net_proceeds - cost_basis

    # 4. Cập nhật Database
    # Trừ cổ phiếu
    holding.total_volume -= req.volume
    holding.available_volume = holding.total_volume # Đồng bộ T+0 (bán xong phần còn lại vẫn bán được tiếp)
    
    # Cộng tiền NGAY LẬP TỨC (T+0 Money)
    asset = db.query(models.AssetSummary).first()
    asset.cash_balance += net_proceeds

    # Lưu lịch sử giao dịch (Đánh dấu settlement_date = Hôm nay)
    transaction = models.StockTransaction(
        ticker=ticker,
        type=models.TransactionType.SELL,
        volume=req.volume,
        price=actual_price_vnd,
        fee=fee,
        tax=tax,
        total_value=net_proceeds,
        transaction_date=req.transaction_date,
        settlement_date=datetime.now().date() # <--- QUAN TRỌNG: Tiền về ngay hôm nay
    )
    db.add(transaction)

    # Lưu ngay vào bảng Lãi lỗ (để hiện bên tab Hiệu suất)
    realized = models.RealizedProfit(
        ticker=ticker,
        volume=req.volume,
        buy_avg_price=holding.average_price,
        sell_price=actual_price_vnd,
        net_profit=profit,
        sell_date=datetime.now() # Lưu ngày giờ bán thực tế
    )
    db.add(realized)

    # Xử lý giá vốn nếu bán hết
    if holding.total_volume == 0:
        holding.average_price = 0

    db.commit()
    
    return {
        "message": f"Đã bán {req.volume} {ticker}. Tiền về: {net_proceeds:,.0f} đ. Lãi/Lỗ: {profit:,.0f} đ", 
        "profit": profit
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
        raise HTTPException(status_code=400, detail="Không đủ số dư để rút")
    
    asset.cash_balance -= req.amount
    # Lưu vào CashFlow
    cash_log = models.CashFlow(
        type=models.CashFlowType.WITHDRAW,
        amount=req.amount,
        description=req.description or "Rút tiền khỏi tài khoản"
    )
    db.add(cash_log)
    db.commit()
    return {"message": "Rút tiền thành công"}

# 2. API Nhật ký tổng hợp (Audit Log)
@app.get("/audit-log")
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

@app.post("/danger-zone/reset-data")
def reset_data(db: Session = Depends(get_db)):
    # Xóa dữ liệu các bảng theo thứ tự để tránh lỗi khóa ngoại
    db.query(models.StockTransaction).delete()
    db.query(models.TickerHolding).delete()
    db.query(models.AssetSummary).delete()
    db.query(models.CashFlow).delete()
    db.query(models.RealizedProfit).delete()
    db.commit()
    return {"message": "Dữ liệu đã được xóa sạch. Bạn có thể bắt đầu nhập lại."}