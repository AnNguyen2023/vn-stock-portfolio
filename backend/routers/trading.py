# routers/trading.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

import schemas
from core.db import get_db
from services import trading_service
from core.response import success, fail

router = APIRouter(
    tags=["Trading"],
)

@router.post("/buy")
def buy_stock(req: schemas.BuyStockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Executes a buy order via the trading service.
    """
    data = trading_service.process_buy_order(db, req, background_tasks)
    return success(data={
        "message": f"Bought {int(data['volume']):,} {data['ticker']} ({data['full_name']})",
        "ticker": data["ticker"],
        "volume": data["volume"],
        "price": data["price"]
    })

@router.post("/sell")
def sell_stock(req: schemas.SellStockRequest, db: Session = Depends(get_db)):
    """
    Executes a sell order via the trading service.
    """
    data = trading_service.process_sell_order(db, req)
    return success(data={
        "message": f"Sold {int(data['volume'])} {data['ticker']}",
        "profit": data["profit"], 
        "net_proceeds": data["net_proceeds"]
    })

@router.post("/undo-last-buy")
def undo_last_buy(db: Session = Depends(get_db)):
    """
    Reverts the most recent buy transaction via the trading service.
    """
    data = trading_service.undo_last_buy_order(db)
    return success(data={
        "message": f"Reverted buy order for {data['ticker']}.",
        "detail": data
    })
