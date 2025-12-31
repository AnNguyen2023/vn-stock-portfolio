from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional

class DepositRequest(BaseModel):
    # gt=0: Greater than 0 (Phải lớn hơn 0)
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = "Nạp tiền vào tài khoản"

class BuyStockRequest(BaseModel):
    ticker: str = Field(..., min_length=3, max_length=10)
    volume: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee_rate: Optional[Decimal] = Field(Decimal("0.0015"), ge=0) # ge=0: Lớn hơn hoặc bằng 0
    # Sử dụng default_factory để lấy thời gian tại thời điểm tạo request (quan trọng)
    transaction_date: datetime = Field(default_factory=datetime.now)

    @field_validator('ticker')
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper()

class SellStockRequest(BaseModel):
    ticker: str = Field(..., min_length=3, max_length=10)
    volume: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee_rate: Optional[Decimal] = Field(Decimal("0.0015"), ge=0)
    tax_rate: Optional[Decimal] = Field(Decimal("0.001"), ge=0)
    transaction_date: datetime = Field(default_factory=datetime.now)

    @field_validator('ticker')
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper()