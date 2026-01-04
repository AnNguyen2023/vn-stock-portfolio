import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum

# 1. Cấu hình môi trường
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Định nghĩa Enum (Giữ nguyên)
class TransactionType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class CashFlowType(enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    CUSTODY_FEE = "CUSTODY_FEE"
    INTEREST = "INTEREST"
    DIVIDEND_CASH = "DIVIDEND_CASH"

# 3. Các bảng dữ liệu (Đã dọn dẹp lỗi lặp và chuẩn hóa kiểu dữ liệu)

class AssetSummary(Base):
    __tablename__ = "asset_summary"
    id = Column(Integer, primary_key=True, index=True)
    cash_balance = Column(Numeric(20, 4), default=0)
    total_deposited = Column(Numeric(20, 4), default=0)
    transaction_fee_rate = Column(Numeric(5, 4), default=0.0015)
    tax_rate = Column(Numeric(5, 4), default=0.001)
    last_interest_calc_date = Column(Date, default=datetime.now().date)
# =================================================================================== #
class TickerHolding(Base):
    __tablename__ = "ticker_holdings"
    ticker = Column(String(10), primary_key=True, index=True)
    total_volume = Column(Numeric(20, 4), default=0)
    available_volume = Column(Numeric(20, 4), default=0)
    average_price = Column(Numeric(20, 4), default=0)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    # MỚI: Ngày bán hết sạch mã này. Nếu > 0 thì để Null. 
    # Khi volume về 0, ta sẽ ghi ngày vào đây để Worker tính mốc 3 năm xóa log.
    liquidated_at = Column(DateTime, nullable=True)
class StockTransaction(Base):
    __tablename__ = "stock_transactions"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    type = Column(Enum(TransactionType))
    volume = Column(Numeric(20, 4))
    price = Column(Numeric(20, 4))
    fee = Column(Numeric(20, 4))
    tax = Column(Numeric(20, 4), default=0)
    total_value = Column(Numeric(20, 4))
    transaction_date = Column(DateTime, default=datetime.now, index=True)
    settlement_date = Column(Date)
    # MỚI: Lưu ghi chú cho từng lệnh mua/bán của anh Zon
    note = Column(String(500), nullable=True)

# =================================================================================== #
class RealizedProfit(Base):
    __tablename__ = "realized_profit"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10))
    volume = Column(Numeric(20, 4))
    buy_avg_price = Column(Numeric(20, 4))
    sell_price = Column(Numeric(20, 4))
    net_profit = Column(Numeric(20, 4))
    sell_date = Column(DateTime, default=datetime.now, index=True) # Đã bỏ dòng lặp

class CashFlow(Base):
    __tablename__ = "cash_flow"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(CashFlowType))
    amount = Column(Numeric(20, 4))
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.now, index=True) # Đã bỏ dòng lặp

class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True)
    total_nav = Column(Numeric(20, 4))

# 4. Khởi tạo
def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database đã được làm sạch và khởi tạo thành công!")

if __name__ == "__main__":
    init_db()