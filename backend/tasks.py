import models
import crawler
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session

def update_daily_snapshot_task():
    """
    Nhiệm vụ ngầm: Tính toán NAV hiện tại và chốt sổ Daily Snapshot.
    Worker sẽ chạy cái này mà không làm phiền người dùng.
    """
    db = models.SessionLocal()
    try:
        asset = db.query(models.AssetSummary).first()
        if not asset: return
        
        holdings = db.query(models.TickerHolding).all()
        tickers = [h.ticker for h in holdings]
        prices = crawler.get_current_prices(tickers)
        
        current_stock_val = sum(
            (Decimal(str(prices.get(h.ticker, 0))) or h.average_price) * h.total_volume 
            for h in holdings
        )
        current_nav = asset.cash_balance + current_stock_val
        
        # Chốt sổ vào DB
        today_s = db.query(models.DailySnapshot).filter_by(date=date.today()).first()
        if not today_s:
            db.add(models.DailySnapshot(date=date.today(), total_nav=current_nav))
        else:
            today_s.total_nav = current_nav
        db.commit()
        print(f"Worker: Da chot NAV ngay {date.today()}: {current_nav:,.0f}")
    finally:
        db.close()