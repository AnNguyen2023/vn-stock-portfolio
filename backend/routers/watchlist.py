# routers/watchlist.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List

import models
import schemas
from core.db import get_db
from core.exceptions import ValidationError, EntityNotFoundException
from core.logger import logger
from services.market_service import get_watchlist_detail_service, invalidate_watchlist_detail_cache

router = APIRouter(prefix="/watchlists", tags=["Watchlist"])

@router.get("/")
def get_watchlists(db: Session = Depends(get_db)):
    """
    Retrieves all user watchlists with tickers eager-loaded.
    """
    watchlists = db.query(models.Watchlist).options(joinedload(models.Watchlist.tickers)).all()
    # Explicitly use WatchlistSchema for each item to ensure serialization
    return {
        "success": True, 
        "data": [schemas.WatchlistSchema.model_validate(w) for w in watchlists]
    }

@router.post("/")
def create_watchlist(req: schemas.WatchlistCreate, db: Session = Depends(get_db)):
    """
    Creates a new empty watchlist.
    """
    exist = db.query(models.Watchlist).filter(models.Watchlist.name == req.name).first()
    if exist:
        raise ValidationError(f"Watchlist with name '{req.name}' already exists.")
    
    new_wl = models.Watchlist(name=req.name)
    db.add(new_wl)
    db.commit()
    db.refresh(new_wl)
    logger.info(f"Watchlist created: {req.name} (ID: {new_wl.id})")
    
    return {"success": True, "data": new_wl}

@router.put("/{id}")
def rename_watchlist(id: int, req: schemas.WatchlistUpdate, db: Session = Depends(get_db)):
    """
    Renames an existing watchlist.
    """
    wl = db.query(models.Watchlist).filter(models.Watchlist.id == id).first()
    if not wl:
        raise EntityNotFoundException("Watchlist", id)
    
    exist = db.query(models.Watchlist).filter(models.Watchlist.name == req.name, models.Watchlist.id != id).first()
    if exist:
        raise ValidationError(f"Watchlist with name '{req.name}' already exists.")
    
    old_name = wl.name
    wl.name = req.name
    db.commit()
    db.refresh(wl)
    logger.info(f"Watchlist renamed: {old_name} -> {req.name}")
    
    return {"success": True, "data": wl}

@router.delete("/{id}")
def delete_watchlist(id: int, db: Session = Depends(get_db)):
    """
    Deletes a watchlist and all its associated tickers.
    """
    wl = db.query(models.Watchlist).filter(models.Watchlist.id == id).first()
    if not wl:
        raise EntityNotFoundException("Watchlist", id)
    
    db.delete(wl)
    db.commit()
    logger.info(f"Watchlist deleted: {id}")
    
    return {"success": True, "message": "Watchlist deleted successfully."}

@router.post("/{id}/tickers")
def add_ticker_to_watchlist(id: int, req: schemas.WatchlistTickerCreate, db: Session = Depends(get_db)):
    """
    Adds a security ticker to a specific watchlist.
    """
    wl = db.query(models.Watchlist).filter(models.Watchlist.id == id).first()
    if not wl:
        raise EntityNotFoundException("Watchlist", id)
    
    ticker = req.ticker.strip().upper()
    
    # 1. Check if already present
    exist = db.query(models.WatchlistTicker).filter_by(watchlist_id=id, ticker=ticker).first()
    if exist:
        raise ValidationError(f"Ticker '{ticker}' is already in this watchlist.")
    
    # 2. Check security Existence
    security = db.query(models.Security).filter_by(symbol=ticker).first()
    if not security:
        raise EntityNotFoundException("Security", ticker)
    
    new_item = models.WatchlistTicker(watchlist_id=id, ticker=ticker)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    # Invalidate Cache
    invalidate_watchlist_detail_cache(id)
    
    logger.info(f"Added {ticker} to watchlist {id}")
    
    return {"success": True, "data": new_item}

@router.delete("/{id}/tickers/{ticker_id}")
def remove_ticker_from_watchlist(id: int, ticker_id: int, db: Session = Depends(get_db)):
    """
    Removes a ticker entry from a specific watchlist.
    """
    item = db.query(models.WatchlistTicker).filter_by(id=ticker_id, watchlist_id=id).first()
    if not item:
        raise EntityNotFoundException("Watchlist Item", ticker_id)
    
    ticker = item.ticker
    db.delete(item)
    db.commit()
    
    # Invalidate Cache
    invalidate_watchlist_detail_cache(id)
    
    logger.info(f"Removed {ticker} from watchlist {id}")
    
    return {"success": True, "message": f"Removed {ticker} from watchlist."}

@router.get("/{id}/detail")
def get_watchlist_detail(id: int, db: Session = Depends(get_db)):
    """
    Retrieves detailed real-time market data for all symbols in the watchlist.
    Includes the specific WatchlistTicker ID for management purposes.
    """
    wl = db.query(models.Watchlist).filter(models.Watchlist.id == id).first()
    if not wl:
        raise EntityNotFoundException("Watchlist", id)
    
    # Create a mapping for ticker -> WatchlistTicker.id
    ticker_to_id = {t.ticker: t.id for t in wl.tickers}
    tickers = list(ticker_to_id.keys())
    
    # Pass ID for results caching (10s)
    market_data = get_watchlist_detail_service(tickers, watchlist_id=id)
    
    # Inject the mapping ID into the market data objects
    for item in market_data:
        symbol = item.get('ticker')
        if symbol in ticker_to_id:
            item['watchlist_ticker_id'] = ticker_to_id[symbol]
            
    return {"success": True, "data": market_data}
