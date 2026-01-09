from core.db import SessionLocal
import models
import crawler
from decimal import Decimal
from datetime import date
import json

def update_daily_snapshot_task():
    """
    Nhiệm vụ ngầm: Tính toán NAV và chốt sổ Daily Snapshot.
    Đã cập nhật để xử lý gói dữ liệu giá mới nhất {price, ref}.
    """
    db = SessionLocal()
    try:
        asset = db.query(models.AssetSummary).first()
        if not asset: return
        
        holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
        tickers = [h.ticker for h in holdings]
        
        # Lấy gói giá từ Crawler (Gồm price và ref)
        prices = crawler.get_current_prices(tickers)
        
        current_stock_val = Decimal("0")
        for h in holdings:
            p_info = prices.get(h.ticker, 0)
            
            # KIỂM TRA: Nếu p_info là dict thì lấy 'price', nếu là số thì lấy trực tiếp
            if isinstance(p_info, dict):
                price_val = Decimal(str(p_info.get("price", 0)))
            else:
                price_val = Decimal(str(p_info or 0))
            
            # Nếu giá thị trường bằng 0, dùng tạm giá vốn để tránh sập NAV
            actual_price = price_val if price_val > 0 else h.average_price
            current_stock_val += actual_price * h.total_volume
        
        current_nav = asset.cash_balance + current_stock_val
        
        # Chốt sổ vào Database
        today_s = db.query(models.DailySnapshot).filter_by(date=date.today()).first()
        if not today_s:
            db.add(models.DailySnapshot(date=date.today(), total_nav=current_nav))
        else:
            today_s.total_nav = current_nav
            
        db.commit()
        print(f"--- [WORKER] ĐÃ CHỐT NAV NGÀY {date.today()}: {float(current_nav):,.0f} VND ---")
        
    except Exception as e:
        print(f"--- [WORKER LỖI] Không thể chốt sổ: {str(e)} ---")
        db.rollback()
    finally:
        db.close()

def cleanup_expired_data_task():
    """
    Nhiệm vụ ngầm: Tự động xóa dữ liệu giao dịch của các mã đã bán hết quá 3 năm.
    Quy luật: Khoản đầu tư hiện hữu giữ vĩnh viễn, đã bán sạch thì xóa sau 3 năm.
    """
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        # 1. Xác định mốc thời gian 3 năm trước
        three_years_ago = datetime.now() - timedelta(days=3*365)
        
        # 2. Tìm các mã cổ phiếu đã bán hết (total_volume == 0) và thời điểm bán cuối cùng > 3 năm
        expired_holdings = db.query(models.TickerHolding).filter(
            models.TickerHolding.total_volume <= 0,
            models.TickerHolding.liquidated_at != None,
            models.TickerHolding.liquidated_at < three_years_ago
        ).all()
        
        if not expired_holdings:
            print("--- [CLEANUP] Không có dữ liệu nào hết hạn (3 năm). ---")
            return

        expired_tickers = [h.ticker for h in expired_holdings]
        
        # 3. Xóa các giao dịch liên quan đến các mã này
        deleted_count = db.query(models.StockTransaction).filter(
            models.StockTransaction.ticker.in_(expired_tickers)
        ).delete(synchronize_session=False)
        
        # 4. Xóa luôn trong realized_profit
        db.query(models.RealizedProfit).filter(
            models.RealizedProfit.ticker.in_(expired_tickers)
        ).delete(synchronize_session=False)

        db.commit()
        print(f"--- [CLEANUP] Đã dọn dẹp {deleted_count} giao dịch của các mã: {', '.join(expired_tickers)} ---")
        
    except Exception as e:
        print(f"--- [CLEANUP ERROR] Lỗi khi dọn dẹp dữ liệu: {str(e)} ---")
        db.rollback()
    finally:
        db.close()