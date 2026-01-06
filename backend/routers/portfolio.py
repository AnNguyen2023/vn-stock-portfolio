"""
routers/portfolio.py - API endpoints cho quản lý danh mục đầu tư
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta, date
import models, schemas, crawler, redis, json, os
from sqlalchemy import desc, cast, Date
from rq import Queue

router = APIRouter(
    tags=["Portfolio & Performance"],
)

# =========================================================================================
# --- CẤU HÌNH KẾT NỐI REDIS & WORKER ---
# =========================================================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    q = Queue(connection=r)
    REDIS_AVAILABLE = True
    print("[REDIS] ✅ Kết nối thành công")
except Exception as e:
    print(f"[REDIS] ⚠️ Không kết nối được, chạy không cache: {e}")
    r = None
    q = None
    REDIS_AVAILABLE = False

def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def raise_error(message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=message)

# =========================================================================================
# 1. NHÓM API QUẢN LÝ TIỀN MẶT (CASH)
# =========================================================================================

@router.post("/deposit")
def deposit_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    """Nạp tiền vào tài khoản"""
    asset = db.query(models.AssetSummary).first()
    if not asset:
        asset = models.AssetSummary(
            cash_balance=0, 
            total_deposited=0, 
            last_interest_calc_date=date.today()
        )
        db.add(asset)
        db.flush()
    
    asset.cash_balance += req.amount
    asset.total_deposited += req.amount
    db.add(models.CashFlow(
        type=models.CashFlowType.DEPOSIT, 
        amount=req.amount, 
        description=req.description
    ))
    db.commit()
    
    # Xóa cache (safe)
    if REDIS_AVAILABLE and r:
        try:
            r.delete("dashboard_performance")
            print("[REDIS] ✅ Đã xóa cache")
        except Exception as e:
            print(f"[REDIS] ⚠️ Không xóa được cache: {e}")
    
    return {"status": "success", "message": "Nạp tiền thành công"}

@router.post("/withdraw")
def withdraw_money(req: schemas.DepositRequest, db: Session = Depends(get_db)):
    """Rút tiền khỏi tài khoản"""
    asset = db.query(models.AssetSummary).first()
    if not asset or asset.cash_balance < req.amount:
        raise_error("Không đủ số dư để rút")
    
    asset.cash_balance -= req.amount
    db.add(models.CashFlow(
        type=models.CashFlowType.WITHDRAW, 
        amount=req.amount, 
        description=req.description
    ))
    db.commit()
    
    # Xóa cache (safe)
    if REDIS_AVAILABLE and r:
        try:
            r.delete("dashboard_performance")
        except:
            pass
    
    return {"message": "Rút tiền thành công"}

# =========================================================================================
# 2. NHÓM API HIỂN THỊ DANH MỤC (PORTFOLIO)
# =========================================================================================

@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    """Lấy thông tin danh mục đầu tư hiện tại"""
    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {
            "cash_balance": 0, 
            "total_stock_value": 0, 
            "total_nav": 0, 
            "holdings": []
        }
    
    # A. Logic Lãi qua đêm (Lazy Update)
    today = date.today()
    if asset.last_interest_calc_date < today:
        days = (today - asset.last_interest_calc_date).days
        interest = asset.cash_balance * (Decimal("0.005") / Decimal("360")) * days
        if interest > Decimal("0.01"):
            asset.cash_balance += interest
            db.add(models.CashFlow(
                type=models.CashFlowType.INTEREST, 
                amount=interest, 
                description=f"Lãi qua đêm {days} ngày"
            ))
            asset.last_interest_calc_date = today
            db.commit()
    
    # B. Lấy giá và tính toán danh mục
    holdings = db.query(models.TickerHolding)\
        .filter(models.TickerHolding.total_volume > 0)\
        .all()
    
    realtime_prices = crawler.get_current_prices([h.ticker for h in holdings])
    portfolio_data = []
    total_stock_value = Decimal("0")
    
    for h in holdings:
        price_info = realtime_prices.get(h.ticker, {})
        
        # Ép kiểu an toàn từ Redis
        if isinstance(price_info, dict):
            mkt_p = Decimal(str(price_info.get("price", 0)))
            ref_p = Decimal(str(price_info.get("ref", 0)))
        else:
            mkt_p = Decimal(str(price_info or 0))
            ref_p = Decimal("0")
        
        curr_p = mkt_p if mkt_p > 0 else (ref_p if ref_p > 0 else h.average_price)
        actual_ref = ref_p if ref_p > 0 else curr_p
        curr_val = curr_p * h.total_volume
        profit_loss = curr_val - (h.average_price * h.total_volume)
        profit_pct = ((curr_p / h.average_price) - 1) * 100 if h.average_price > 0 else 0
        total_stock_value += curr_val
        today_pct = ((curr_p / actual_ref) - 1) * 100 if actual_ref > 0 else 0
        
        portfolio_data.append({
            "ticker": h.ticker,
            "volume": float(h.total_volume),
            "available": float(h.available_volume),
            "avg_price": float(h.average_price / 1000),
            "current_price": float(curr_p / 1000),
            "today_change_percent": float(today_pct),
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

# =========================================================================================
# 3. NHÓM API HIỆU SUẤT & BIỂU ĐỒ (PERFORMANCE & CHARTS)
# =========================================================================================

@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    """Lấy summary metrics: lãi/lỗ theo 1d, 1m, 1y, ytd"""
    # Thử lấy từ Cache Redis trước
    cache_key = "dashboard_performance"
    if REDIS_AVAILABLE and r:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass
    
    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {}
    
    # Tính NAV hiện tại
    holdings = db.query(models.TickerHolding).all()
    prices = crawler.get_current_prices([h.ticker for h in holdings])
    
    curr_stock_val = sum(
        (Decimal(str(prices.get(h.ticker, {}).get("price", 0) if isinstance(prices.get(h.ticker), dict) else prices.get(h.ticker, 0))) or h.average_price) * h.total_volume 
        for h in holdings
    )
    curr_nav = asset.cash_balance + curr_stock_val
    
    # Hàm tính % tăng trưởng chuẩn (TWRR)
    def calc_pct(days_ago=None, ytd=False):
        target = date(date.today().year, 1, 1) if ytd else (date.today() - timedelta(days=days_ago))
        snap = db.query(models.DailySnapshot)\
            .filter(models.DailySnapshot.date <= target)\
            .order_by(desc(models.DailySnapshot.date))\
            .first()
        
        old_nav = snap.total_nav if snap else Decimal("0")
        
        flows = db.query(models.CashFlow)\
            .filter(cast(models.CashFlow.created_at, Date) >= target)\
            .all()
        
        net_flow = sum(
            (f.amount if f.type == models.CashFlowType.DEPOSIT else -f.amount)
            for f in flows 
            if f.type in [models.CashFlowType.DEPOSIT, models.CashFlowType.WITHDRAW]
        )
        
        profit = curr_nav - (old_nav + net_flow)
        denom = old_nav + net_flow
        return float(profit), float((profit / denom * 100) if denom > 0 else 0)
    
    result = {
        "1d": {"val": calc_pct(days_ago=1)[0], "pct": calc_pct(days_ago=1)[1]},
        "1m": {"val": calc_pct(days_ago=30)[0], "pct": calc_pct(days_ago=30)[1]},
        "1y": {"val": calc_pct(days_ago=365)[0], "pct": calc_pct(days_ago=365)[1]},
        "ytd": {"val": calc_pct(ytd=True)[0], "pct": calc_pct(ytd=True)[1]}
    }
    
    # Lưu cache và đẩy task cho Worker (safe)
    if REDIS_AVAILABLE and r:
        try:
            r.setex(cache_key, 300, json.dumps(result))
            from tasks import update_daily_snapshot_task
            q.enqueue(update_daily_snapshot_task)
        except:
            pass
    
    return result

@router.get("/chart-growth")
def get_chart_growth(period: str = "1m", db: Session = Depends(get_db)):
    """
    Trả về % tăng trưởng tích lũy của danh mục để vẽ chart
    So sánh với điểm xuất phát (ngày đầu của khoảng thời gian)
    """
    # Cache key theo period
    cache_key = f"chart_growth_{period}"
    if REDIS_AVAILABLE and r:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass
    
    # 1. Xác định khoảng thời gian
    end_date = date.today()
    period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = period_map.get(period, 30)
    start_date = end_date - timedelta(days=days)
    
    # 2. Lấy tất cả snapshot trong khoảng thời gian
    snapshots = db.query(models.DailySnapshot)\
        .filter(models.DailySnapshot.date >= start_date)\
        .order_by(models.DailySnapshot.date)\
        .all()
    
    if not snapshots or len(snapshots) < 2:
        return {
            "portfolio": [],
            "message": "Chưa đủ dữ liệu lịch sử (cần ít nhất 2 ngày)"
        }
    
    # 3. Lấy NAV điểm xuất phát (ngày đầu tiên)
    base_nav = snapshots[0].total_nav
    
    if base_nav == 0:
        return {
            "portfolio": [],
            "message": "NAV điểm xuất phát bằng 0"
        }
    
    # 4. Tính % tăng trưởng tích lũy cho từng ngày
    portfolio_series = []
    
    for snap in snapshots:
        # Tính net cash flow từ ngày bắt đầu đến ngày hiện tại
        flows = db.query(models.CashFlow)\
            .filter(
                cast(models.CashFlow.created_at, Date) >= start_date,
                cast(models.CashFlow.created_at, Date) <= snap.date
            ).all()
        
        net_flow = sum(
            (f.amount if f.type == models.CashFlowType.DEPOSIT else -f.amount)
            for f in flows
            if f.type in [models.CashFlowType.DEPOSIT, models.CashFlowType.WITHDRAW]
        )
        
        # NAV adjusted = NAV base + net cash flow
        adjusted_base = base_nav + net_flow
        
        # % tăng trưởng = (NAV hiện tại - adjusted base) / adjusted base * 100
        if adjusted_base > 0:
            growth_pct = ((snap.total_nav - adjusted_base) / adjusted_base) * 100
        else:
            growth_pct = 0
        
        portfolio_series.append({
            "date": snap.date.strftime('%Y-%m-%d'),
            "close": round(float(growth_pct), 2)  # Frontend dùng key "close" giống VNINDEX
        })
    
    result = {
        "portfolio": portfolio_series,
        "base_date": snapshots[0].date.strftime('%Y-%m-%d'),
        "base_nav": float(base_nav),
        "data_points": len(portfolio_series)
    }
    
    # Lưu cache 5 phút
    if REDIS_AVAILABLE and r:
        try:
            r.setex(cache_key, 300, json.dumps(result))
        except:
            pass
    
    return result

@router.get("/nav-history")
def get_nav_history(limit: int = 20, db: Session = Depends(get_db)):
    """Lấy lịch sử biến động NAV để vẽ bảng Nhật ký tài sản"""
    snaps = db.query(models.DailySnapshot)\
        .order_by(desc(models.DailySnapshot.date))\
        .limit(limit)\
        .all()
    
    res = []
    for i in range(len(snaps)-1):
        curr, prev = snaps[i], snaps[i+1]
        change = curr.total_nav - prev.total_nav
        pct = (change / prev.total_nav * 100) if prev.total_nav > 0 else 0
        res.append({
            "date": curr.date.strftime('%Y-%m-%d'), 
            "nav": float(curr.total_nav), 
            "change": float(change), 
            "pct": float(pct)
        })
    
    return res

# =========================================================================================
# 4. HÀM TÍNH TOÁN LÃI TRỌN ĐỜI
# =========================================================================================

@router.get("/ticker-lifetime-profit/{ticker}")
def get_ticker_lifetime_profit(ticker: str, db: Session = Depends(get_db)):
    """Tính tổng lãi lỗ trọn đời của một mã (Lãi đã chốt + Lãi đang chạy)"""
    ticker = ticker.upper()
    
    # 1. Tổng lãi đã chốt (Realized)
    realized = db.query(models.RealizedProfit).filter_by(ticker=ticker).all()
    total_realized = sum(item.net_profit for item in realized)
    
    # 2. Lãi đang chạy (Unrealized) nếu còn đang nắm giữ
    holding = db.query(models.TickerHolding).filter_by(ticker=ticker).first()
    unrealized_profit = Decimal("0")
    
    if holding and holding.total_volume > 0:
        prices = crawler.get_current_prices([ticker])
        p_info = prices.get(ticker, 0)
        curr_p = Decimal(str(p_info.get("price", 0) if isinstance(p_info, dict) else p_info))
        if curr_p > 0:
            unrealized_profit = (curr_p - holding.average_price) * holding.total_volume
    
    return {
        "ticker": ticker,
        "total_profit": float(total_realized + unrealized_profit),
        "realized": float(total_realized),
        "unrealized": float(unrealized_profit)
    }

# =========================================================================================
# 5. HỆ THỐNG GỘP & RESET
# =========================================================================================

@router.get("/dashboard-init")
def dashboard_init(db: Session = Depends(get_db)):
    """Lấy tất cả dữ liệu cần thiết cho dashboard trong 1 request"""
    from routers import logs
    
    return {
        "portfolio": get_portfolio(db),
        "performance": get_performance(db),
        "logs": logs.get_audit_log(db)
    }

@router.post("/reset-data")
def reset_data(db: Session = Depends(get_db)):
    """Xóa toàn bộ dữ liệu (dùng khi dev/test)"""
    db.query(models.StockTransaction).delete()
    db.query(models.TickerHolding).delete()
    db.query(models.AssetSummary).delete()
    db.query(models.CashFlow).delete()
    db.query(models.RealizedProfit).delete()
    db.query(models.DailySnapshot).delete()
    db.query(models.HistoricalPrice).delete()
    db.commit()
    
    # Xóa Redis cache (safe)
    if REDIS_AVAILABLE and r:
        try:
            r.flushall()
        except:
            pass
    
    return {"message": "Hệ thống đã về trạng thái trắng tinh!"}
