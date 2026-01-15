# routers/trading.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

import schemas
from core.db import get_db
from services import trading_service

router = APIRouter(
    tags=["Trading"],
)

@router.post("/buy")
def buy_stock(req: schemas.BuyStockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Executes a buy order via the trading service.
    """
    data = trading_service.process_buy_order(db, req, background_tasks)
    return {
        "success": True, 
        "message": f"Bought {int(data['volume']):,} {data['ticker']} ({data['full_name']})",
        "data": {
            "ticker": data["ticker"],
            "volume": data["volume"],
            "price": data["price"]
        }
    }

@router.post("/sell")
def sell_stock(req: schemas.SellStockRequest, db: Session = Depends(get_db)):
    """
    Executes a sell order via the trading service.
    """
    data = trading_service.process_sell_order(db, req)
    return {
        "success": True, 
        "message": f"Sold {int(data['volume'])} {data['ticker']}",
        "data": {
            "profit": data["profit"], 
            "net_proceeds": data["net_proceeds"]
        }
    }

@router.post("/undo-last-buy")
def undo_last_buy(db: Session = Depends(get_db)):
    """
    Reverts the most recent buy transaction via the trading service.
    """
    data = trading_service.undo_last_buy_order(db)
    return {
        "success": True, 
        "message": f"Reverted buy order for {data['ticker']}.",
        "data": data
    }
@router.post("/register-dividend")
def register_dividend(req: schemas.RegisterDividendRequest, db: Session = Depends(get_db)):
    """
    Registers a dividend event and handles cash logic (PENDING flow).
    """
    data = trading_service.register_dividend(db, req)
    return {
        "success": True,
        "message": f"Đã đăng ký cổ tức {req.type.value} cho {req.ticker}",
        "data": data
    }

@router.get("/dividends/pending")
def get_pending_dividends(db: Session = Depends(get_db)):
    """Fetches all pending dividend records."""
    return trading_service.get_pending_dividends(db)

@router.delete("/dividends/{dividend_id}")
def delete_dividend(dividend_id: int, db: Session = Depends(get_db)):
    """Deletes a pending dividend record."""
    success = trading_service.delete_dividend(db, dividend_id)
    if not success:
        return {"success": False, "message": "Dividend not found or already processed"}
    return {"success": True, "message": "Dividend deleted successfully"}

@router.put("/dividends/{dividend_id}")
def update_dividend(dividend_id: int, req: schemas.UpdateDividendRequest, db: Session = Depends(get_db)):
    """Updates a pending dividend record."""
    data = trading_service.update_dividend(db, dividend_id, req)
    if not data:
        return {"success": False, "message": "Dividend not found or already processed"}
    return {
        "success": True,
        "message": f"Updated dividend for {req.ticker}",
        "data": {
            "expected_value": data["expected_value"],
            "expected_growth": data.get("type", "")
        }
    }
