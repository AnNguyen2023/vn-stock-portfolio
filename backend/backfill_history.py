"""
backfill_history.py - Tải dữ liệu lịch sử cổ phiếu từ 01/12/2025
"""
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
from vnstock import Vnstock
from core.db import SessionLocal
import models
from core.logger import logger

def backfill():
    start_date = "2025-12-01"
    today_str = date.today().strftime('%Y-%m-%d')
    
    with SessionLocal() as db:
        # 1. Lấy danh sách các mã trong danh mục hiện tại
        holdings = db.query(models.TickerHolding.ticker).all()
        tickers = [h[0] for h in holdings]
        
        # Thêm các chỉ số quan trọng
        indices = ["VNINDEX", "VN30", "HNX30"]
        all_symbols = list(set(tickers + indices))
        
        logger.info(f"🚀 Bắt đầu tải dữ liệu cho {len(all_symbols)} mã từ {start_date}...")
        
        vn = Vnstock()
        
        for symbol in all_symbols:
            try:
                logger.info(f"--- Đang xử lý: {symbol} ---")
                stock = vn.stock(symbol=symbol, source='VCI')
                
                # Lấy dữ liệu lịch sử
                df = stock.quote.history(start=start_date, end=today_str, interval='1D')
                
                if df is None or df.empty:
                    logger.warning(f"⚠️ Không có dữ liệu cho {symbol}")
                    continue
                
                new_records = 0
                for _, row in df.iterrows():
                    # Chuyển đổi date
                    d = row['time'].date() if isinstance(row['time'], datetime) else pd.to_datetime(row['time']).date()
                    
                    # Kiểm tra xem đã có trong DB chưa
                    existing = db.query(models.HistoricalPrice).filter(
                        models.HistoricalPrice.ticker == symbol,
                        models.HistoricalPrice.date == d
                    ).first()
                    
                    if not existing:
                        price = Decimal(str(row['close']))
                        vol = Decimal(str(row.get('volume', 0)))
                        
                        # VCI có thể không có cột value cho index, chúng ta tính tạm nếu cần
                        val = Decimal(str(row.get('value', 0)))
                        if symbol in indices and val == 0:
                            # Tạm thời để 0 hoặc tính toán logic khác nếu cần
                            pass

                        new_hist = models.HistoricalPrice(
                            ticker=symbol,
                            date=d,
                            close_price=price,
                            volume=vol,
                            value=val
                        )
                        db.add(new_hist)
                        new_records += 1
                
                db.commit()
                logger.info(f"✅ Hoàn thành {symbol}: Lưu mới {new_records} ngày.")
                
            except Exception as e:
                logger.error(f"❌ Lỗi khi tải mã {symbol}: {e}")
                db.rollback()

    logger.info("✨ Đã hoàn thành tải dữ liệu lịch sử!")

if __name__ == "__main__":
    backfill()
