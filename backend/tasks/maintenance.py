"""
tasks/maintenance.py
Maintenance tasks like data cleanup
"""
from datetime import datetime, timedelta
from core.db import SessionLocal
from core.logger import logger
import models

def cleanup_expired_data_task():
    """
    Nhiệm vụ ngầm: Tự động xóa dữ liệu giao dịch của các mã đã bán hết quá 3 năm.
    Quy luật: Khoản đầu tư hiện hữu giữ vĩnh viễn, đã bán sạch thì xóa sau 3 năm.
    """
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
            logger.info("--- [CLEANUP] Không có dữ liệu nào hết hạn (3 năm). ---")
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
        logger.info(f"--- [CLEANUP] Đã dọn dẹp {deleted_count} giao dịch của các mã: {', '.join(expired_tickers)} ---")
        
    except Exception as e:
        logger.error(f"--- [CLEANUP ERROR] Lỗi khi dọn dẹp dữ liệu: {str(e)} ---")
        db.rollback()
    finally:
        db.close()
