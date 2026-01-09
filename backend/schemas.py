from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional

class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = "Nạp tiền vào tài khoản"

class BuyStockRequest(BaseModel):
    ticker: str = Field(..., min_length=3, max_length=10)
    volume: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee_rate: Optional[Decimal] = Field(Decimal("0.0015"), ge=0)
    transaction_date: datetime = Field(default_factory=datetime.now)
    # THÊM Ô GHI CHÚ: Không bắt buộc, tối đa 500 ký tự (~3 dòng)
    note: Optional[str] = Field(None, max_length=500)

    @field_validator('ticker')
    @classmethod
    def ticker_must_be_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Mã chứng khoán chỉ được chứa chữ cái và số')
        return v.upper()

class WatchlistUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

class NoteUpdate(BaseModel):
    note: str = Field(..., max_length=500)

# --- WATCHLIST SCHEMAS ---

class WatchlistTickerCreate(BaseModel):
    ticker: str

class WatchlistCreate(BaseModel):
    name: str

class WatchlistTickerSchema(BaseModel):
    id: int
    ticker: str
    added_at: datetime
    class Config:
        from_attributes = True

class WatchlistSchema(BaseModel):
    id: int
    name: str
    tickers: list[WatchlistTickerSchema] = []
    created_at: datetime
    class Config:
        from_attributes = True

class SellStockRequest(BaseModel):
    ticker: str = Field(..., min_length=3, max_length=10)
    volume: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee_rate: Optional[Decimal] = Field(Decimal("0.0015"), ge=0)
    tax_rate: Optional[Decimal] = Field(Decimal("0.001"), ge=0)
    transaction_date: datetime = Field(default_factory=datetime.now)
    # THÊM Ô GHI CHÚ CHO LỆNH BÁN
    note: Optional[str] = Field(None, max_length=500)

    @field_validator('ticker')
    @classmethod
    def ticker_must_be_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Mã chứng khoán chỉ được chứa chữ cái và số')
        return v.upper()