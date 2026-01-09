import sys
import os
from datetime import date, timedelta
from decimal import Decimal
import random

# Add current dir to path to import models
sys.path.append(os.getcwd())

from core.db import SessionLocal
import models

def seed_nav(days=30):
    db = SessionLocal()
    try:
        # Lấy NAV hiện tại làm mốc
        asset = db.query(models.AssetSummary).first()
        base_nav = Decimal("15000000000") # 15 tỷ mặc định nếu chưa có
        if asset:
            # Tính NAV hiện tại
            holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
            stock_val = sum(h.total_volume * h.average_price for h in holdings)
            base_nav = asset.cash_balance + stock_val
        
        print(f"--- Bắt đầu bơm {days} ngày dữ liệu NAV ảo (Mốc: {float(base_nav):,.0f} VND) ---")
        
        today = date.today()
        for i in range(days, 0, -1):
            target_date = today - timedelta(days=i)
            # Biến động ngẫu nhiên +/- 2% mỗi ngày
            variation = Decimal(str(random.uniform(0.95, 1.05)))
            fake_nav = base_nav * variation
            
            # Kiểm tra xem đã có bản ghi chưa
            existing = db.query(models.DailySnapshot).filter_by(date=target_date).first()
            if not existing:
                db.add(models.DailySnapshot(date=target_date, total_nav=fake_nav))
                print(f" + Đã tạo NAV ngày {target_date}: {float(fake_nav):,.0f}")
            else:
                existing.total_nav = fake_nav
                print(f" ~ Đã cập nhật NAV ngày {target_date}: {float(fake_nav):,.0f}")
        
        db.commit()
        print("--- Hoàn tất! Sếp hãy vào UI nhấn 'Kiểm tra' để xem kết quả nhé. ---")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    days_to_seed = 30
    if len(sys.argv) > 1:
        try: days_to_seed = int(sys.argv[1])
        except: pass
    seed_nav(days_to_seed)
