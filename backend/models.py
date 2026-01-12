# models.py
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
import enum

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Enum, UniqueConstraint, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from core.db import Base


class TransactionType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class CashFlowType(enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    CUSTODY_FEE = "CUSTODY_FEE"
    INTEREST = "INTEREST"
    DIVIDEND_CASH = "DIVIDEND_CASH"


class AssetSummary(Base):
    """Tổng quan ví tiền mặt và các cài đặt phí thuế"""
    __tablename__ = "asset_summary"
    id = Column(Integer, primary_key=True, index=True)
    cash_balance = Column(Numeric(20, 4), default=0)
    total_deposited = Column(Numeric(20, 4), default=0)
    transaction_fee_rate = Column(Numeric(5, 4), default=0.0015)
    tax_rate = Column(Numeric(5, 4), default=0.001)
    last_interest_calc_date = Column(Date, default=date.today)  # chuẩn hơn


class TickerHolding(Base):
    """Danh mục đang nắm giữ hiện tại"""
    __tablename__ = "ticker_holdings"
    ticker = Column(String(10), primary_key=True, index=True)
    total_volume = Column(Numeric(20, 4), default=0)
    available_volume = Column(Numeric(20, 4), default=0)
    average_price = Column(Numeric(20, 4), default=0)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    liquidated_at = Column(DateTime, nullable=True)


class StockTransaction(Base):
    """Nhật ký chi tiết từng lệnh Mua/Bán (Lưu vĩnh viễn)"""
    __tablename__ = "stock_transactions"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    type = Column(Enum(TransactionType))
    volume = Column(Numeric(20, 4))
    price = Column(Numeric(20, 4))
    fee = Column(Numeric(20, 4), default=0)
    tax = Column(Numeric(20, 4), default=0)
    total_value = Column(Numeric(20, 4))
    transaction_date = Column(DateTime, default=datetime.now, index=True)
    settlement_date = Column(Date, nullable=True)
    note = Column(String(500), nullable=True)


class RealizedProfit(Base):
    """Bảng lưu các khoản lãi/lỗ đã chốt sổ"""
    __tablename__ = "realized_profit"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    volume = Column(Numeric(20, 4))
    buy_avg_price = Column(Numeric(20, 4))
    sell_price = Column(Numeric(20, 4))
    net_profit = Column(Numeric(20, 4))
    sell_date = Column(DateTime, default=datetime.now, index=True)


class CashFlow(Base):
    """Nhật ký dòng tiền nạp/rút/lãi"""
    __tablename__ = "cash_flow"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(CashFlowType))
    amount = Column(Numeric(20, 4))
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.now, index=True)


class DailySnapshot(Base):
    """Dữ liệu chốt sổ NAV mỗi ngày để vẽ biểu đồ hiệu suất"""
    __tablename__ = "daily_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True)
    total_nav = Column(Numeric(20, 4))


class HistoricalPrice(Base):
    """Kho lưu trữ giá vĩnh viễn của VNINDEX và cổ phiếu (Chống lỗi cuối tuần)"""
    __tablename__ = "historical_prices"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    date = Column(Date, index=True)
    close_price = Column(Numeric(20, 4))
    volume = Column(Numeric(20, 4), default=0)
    value = Column(Numeric(20, 4), default=0) # Giá trị giao dịch (Thanh khoản)

    __table_args__ = (UniqueConstraint("ticker", "date", name="_ticker_date_uc"),)


class Security(Base):
    """Danh mục các mã chứng khoán hợp lệ trên thị trường Việt Nam"""
    __tablename__ = "securities"
    symbol = Column(String(20), primary_key=True, index=True)
    short_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True)
    exchange = Column(String(20), index=True)  # HOSE, HNX, UPCOM
    type = Column(String(20), index=True)      # STOCK, ETF, FUND
    last_synced = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Watchlist(Base):
    """Danh sách theo dõi cổ phiếu tùy chỉnh"""
    __tablename__ = "watchlists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    
    tickers = relationship("WatchlistTicker", backref="watchlist", cascade="all, delete-orphan")

class WatchlistTicker(Base):
    """Các mã chứng khoán trong một watchlist"""
    __tablename__ = "watchlist_tickers"
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id", ondelete="CASCADE"))
    ticker = Column(String(20), index=True)
    added_at = Column(DateTime, default=datetime.now)

class TitanScanResult(Base):
    """Bảng lưu kết quả quét từ TITAN Adaptive Scanner"""
    __tablename__ = "titan_scan_results"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    close_price = Column(Numeric(20, 4))
    alpha = Column(Numeric(20, 4))
    is_valid = Column(Boolean, default=False)
    is_buy_signal = Column(Boolean, default=False)
    trend_strength = Column(String(20))
    optimal_length = Column(Integer)
    scanned_at = Column(DateTime, default=datetime.now, index=True)


class TestHistoricalPrice(Base):
    """Bảng dữ liệu test 1 tuần (tách riêng cho mục đích test app)"""
    __tablename__ = "test_historical_prices"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    date = Column(Date, index=True)
    close_price = Column(Numeric(20, 4))
    volume = Column(Numeric(20, 4), default=0)
    value = Column(Numeric(20, 4), default=0)

    __table_args__ = (UniqueConstraint("ticker", "date", name="_test_ticker_date_uc"),)