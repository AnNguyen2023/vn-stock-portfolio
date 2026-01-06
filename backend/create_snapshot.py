# backend/create_snapshot.py
from models import SessionLocal, DailySnapshot, AssetSummary, TickerHolding
from datetime import date, timedelta
from decimal import Decimal
import crawler

db = SessionLocal()

# Lấy thông tin hiện tại
asset = db.query(AssetSummary).first()
holdings = db.query(TickerHolding).all()

if asset:
    # Tính NAV hiện tại
    prices = crawler.get_current_prices([h.ticker for h in holdings])
    stock_value = sum(
        (Decimal(str(prices.get(h.ticker, {}).get("price", 0) or 0)) or h.average_price) * h.total_volume 
        for h in holdings
    )
    total_nav = asset.cash_balance + stock_value
    
    # Tạo snapshot cho hôm nay
    today_snap = DailySnapshot(
        date=date.today(),
        cash_balance=asset.cash_balance,
        total_stock_value=stock_value,
        total_nav=total_nav
    )
    db.add(today_snap)
    
    # Tạo snapshot cho hôm qua (giả lập)
    yesterday_snap = DailySnapshot(
        date=date.today() - timedelta(days=1),
        cash_balance=asset.cash_balance * Decimal("0.98"),  # Giả lập NAV thấp hơn 2%
        total_stock_value=stock_value * Decimal("0.98"),
        total_nav=total_nav * Decimal("0.98")
    )
    db.add(yesterday_snap)
    
    db.commit()
    print("✅ Đã tạo 2 snapshot (hôm qua & hôm nay)")
else:
    print("❌ Chưa có AssetSummary, vui lòng nạp tiền trước")

db.close()
