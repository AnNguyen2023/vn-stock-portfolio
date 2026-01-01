import os
from pathlib import Path # Thêm dòng này
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, Date, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum

# Load biến môi trường từ file .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# Khởi tạo Engine và Session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Định nghĩa các loại giao dịch
class TransactionType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class CashFlowType(enum.Enum):
    DEPOSIT = "DEPOSIT"      # Nạp tiền
    WITHDRAW = "WITHDRAW"    # Rút tiền
    CUSTODY_FEE = "CUSTODY_FEE" # Phí lưu ký
    INTEREST = "INTEREST"    # Lãi qua đêm
    DIVIDEND_CASH = "DIVIDEND_CASH" # Cổ tức tiền mặt

# 1. Bảng Tổng quan tài sản
class AssetSummary(Base):
    __tablename__ = "asset_summary"
    id = Column(Integer, primary_key=True, index=True)
    cash_balance = Column(Numeric(20, 4), default=0)       # Tiền mặt hiện có
    total_deposited = Column(Numeric(20, 4), default=0)    # Tổng vốn đã nạp
    transaction_fee_rate = Column(Numeric(5, 4), default=0.0015) # Phí mặc định 0.15%
    tax_rate = Column(Numeric(5, 4), default=0.001)        # Thuế bán mặc định 0.1%
    last_interest_calc_date = Column(Date, default=datetime.now().date) # Phục vụ Lazy Update

# 2. Bảng Danh mục đang nắm giữ
class TickerHolding(Base):
    __tablename__ = "ticker_holdings"
    ticker = Column(String(10), primary_key=True, index=True)
    total_volume = Column(Integer, default=0)      # Tổng số lượng
    available_volume = Column(Integer, default=0)  # Số lượng có thể bán (đã qua T+2.5)
    # Giá vốn nên để ít nhất 4 số lẻ để tính toán chính xác
    average_price = Column(Numeric(20, 4), default=0) # Giá vốn bình quân
    last_updated = Column(DateTime, default=datetime.now)

# 3. Bảng Lịch sử giao dịch cổ phiếu
class StockTransaction(Base):
    __tablename__ = "stock_transactions"
    id = Column(Integer, primary_key=True, index=True)
    # Thêm index=True vào đây
    transaction_date = Column(DateTime, default=datetime.now, index=True)
    ticker = Column(String(10), index=True)
    type = Column(Enum(TransactionType))
    volume = Column(Integer)
    price = Column(Numeric(20, 4))
    fee = Column(Numeric(20, 4))
    tax = Column(Numeric(20, 4), default=0)
    total_value = Column(Numeric(20, 4)) # Tổng tiền thực chi/nhận
    transaction_date = Column(DateTime, default=datetime.now)
    settlement_date = Column(Date) # Ngày cổ phiếu/tiền về (T+2)

# 4. Bảng Lãi lỗ đã thực hiện (Realized Profit)
class RealizedProfit(Base):
    __tablename__ = "realized_profit"
    id = Column(Integer, primary_key=True, index=True)
    # Thêm index=True vào đây
    sell_date = Column(DateTime, default=datetime.now, index=True)
    ticker = Column(String(10))
    sell_date = Column(DateTime, default=datetime.now)
    volume = Column(Integer)
    buy_avg_price = Column(Numeric(18, 2)) # Giá vốn lúc mua
    sell_price = Column(Numeric(18, 2))    # Giá bán thực tế
    net_profit = Column(Numeric(18, 2))    # Tiền lãi ròng (sau phí thuế)

# 5. Bảng Biến động tiền mặt (Cash Flow)
class CashFlow(Base):
    __tablename__ = "cash_flow"
    id = Column(Integer, primary_key=True, index=True)
    # Thêm index=True vào đây
    created_at = Column(DateTime, default=datetime.now, index=True)
    type = Column(Enum(CashFlowType))
    amount = Column(Numeric(18, 2))
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
    
# Thêm bảng này vào cuối file models.py (trước phần init_db)
class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True)      # Mỗi ngày chỉ lưu 1 bản ghi duy nhất
    total_nav = Column(Numeric(20, 4))   # Tổng tài sản chốt cuối ngày
    
    
# Hàm khởi tạo database (Tạo bảng)
def init_db():
    Base.metadata.create_all(bind=engine)
    print("Đã tạo các bảng thành công trong PostgreSQL!")

if __name__ == "__main__":
    init_db()