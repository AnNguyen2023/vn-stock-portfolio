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

    @field_validator('ticker')
    @classmethod
    def ticker_must_be_alpha(cls, v: str) -> str:
        # CHẶN SỐ: Chỉ cho phép chữ cái (A-Z)
        if not v.isalpha():
            raise ValueError('Mã chứng khoán chỉ được chứa chữ cái (VD: FPT, STB)')
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
    def ticker_must_be_alpha(cls, v: str) -> str:
        # ĐỒNG BỘ: Chặn số cả ở lệnh Bán
        if not v.isalpha():
            raise ValueError('Mã chứng khoán chỉ được chứa chữ cái')
        return v.upper()