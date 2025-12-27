from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional

class DepositRequest(BaseModel):
    amount: Decimal
    description: Optional[str] = "Nạp tiền vào tài khoản"

class BuyStockRequest(BaseModel):
    ticker: str
    volume: int
    price: Decimal
    fee_rate: Optional[Decimal] = Decimal("0.0015") # Mặc định 0.15%
    transaction_date: Optional[datetime] = datetime.now()

class SellStockRequest(BaseModel):
    ticker: str
    volume: int
    price: Decimal
    fee_rate: Optional[Decimal] = Decimal("0.0015")
    # Thuế bán tại VN mặc định là 0.1%
    tax_rate: Optional[Decimal] = Decimal("0.001")
    transaction_date: Optional[datetime] = datetime.now()