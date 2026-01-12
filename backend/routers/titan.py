# backend/routers/titan.py
from __future__ import annotations

import asyncio
import random
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.db import get_db
import models
from titan.alpha_scanner import AlphaScanner
from pydantic import BaseModel
from core.exceptions import ValidationError, EntityNotFoundException
from core.logger import logger

router = APIRouter(prefix="/titan", tags=["TITAN Scanner"])
scanner = AlphaScanner()

class ScanSettings(BaseModel):
    fee_bps: Optional[float] = None
    slippage_bps: Optional[float] = None
    wf_train_bars: Optional[int] = None
    wf_test_bars: Optional[int] = None
    wf_step_bars: Optional[int] = None
    wf_min_folds: Optional[int] = None
    stability_lambda: Optional[float] = None
    trade_penalty_bps: Optional[float] = None

# Global state for scan progress
scan_status = {
    "is_running": False,
    "last_run": None,
    "progress": 0,
    "total": 0,
    "current_symbol": ""
}
should_stop = False

@router.get("/status")
def get_titan_status():
    """
    Returns the current status and progress of the TITAN scanner.
    """
    return {"success": True, "data": scan_status}

@router.post("/stop")
def stop_titan_scan():
    """
    Stops a currently running TITAN scan process.
    """
    global should_stop
    if scan_status["is_running"]:
        should_stop = True
        logger.info("TITAN scan stop signal initiated by user.")
        return {"success": True, "message": "Stop signal sent to TITAN scanner."}
    return {"success": True, "message": "No active TITAN scan process to stop."}

@router.get("/results")
def get_titan_results(db: Session = Depends(get_db)):
    """
    Retrieves the most recent TITAN scan results from the database.
    """
    # 1. Identify the timestamp of the latest scan session
    latest_scan = (
        db.query(models.TitanScanResult.scanned_at)
        .order_by(desc(models.TitanScanResult.scanned_at))
        .first()
    )
    if not latest_scan:
        return {"success": True, "data": []}
    
    # 2. Retrieve all outcomes for that session
    results = (
        db.query(models.TitanScanResult)
        .filter(models.TitanScanResult.scanned_at == latest_scan[0])
        .all()
    )
    return {"success": True, "data": results}

async def run_scan_task(db_session_factory, settings: Optional[ScanSettings] = None):
    """
    Background worker for TITAN Alpha Scanner. 
    Implements rate-limited parallel analysis of market symbols.
    """
    global scan_status, should_stop
    try:
        # Load custom scanner settings
        if settings:
            for key, value in settings.model_dump(exclude_none=True).items():
                setattr(scanner, key, value)

        should_stop = False
        scan_status["is_running"] = True
        scan_status["progress"] = 0
        
        tickers = scanner.client.get_vn100_tickers()
        scan_status["total"] = len(tickers)
        
        # Throttling to respect VCI API limits
        semaphore = asyncio.Semaphore(2)
        
        async def analyze_with_limit(symbol):
            async with semaphore:
                if should_stop:
                    return None
                    
                # Intelligent jitter to avoid bot pattern detection
                await asyncio.sleep(random.uniform(1.5, 3.0))
                scan_status["current_symbol"] = symbol
                
                try:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, scanner.analyze_symbol, symbol)
                except (Exception, SystemExit) as e:
                    logger.error(f"TITAN scan error for {symbol}: {e}")
                    await asyncio.sleep(5)
                    return None

        # Execute parallel tasks
        tasks = [analyze_with_limit(s) for s in tickers]
        all_results = []
        processed_count = 0
        
        for task in asyncio.as_completed(tasks):
            if should_stop:
                logger.warning("TITAN scan aborted by user.")
                break
                
            result = await task
            processed_count += 1
            scan_status["progress"] = processed_count
            
            if result:
                all_results.append(result)
        
        # Persist results
        if all_results and not should_stop:
            db = next(db_session_factory())
            try:
                scanned_at = datetime.now()
                for r in all_results:
                    db_result = models.TitanScanResult(
                        symbol=r['symbol'],
                        close_price=r['close_price'] * 1000,
                        alpha=r['alpha'],
                        is_valid=r['is_valid'],
                        is_buy_signal=r['is_buy_signal'],
                        trend_strength=r['trend_strength'],
                        optimal_length=r['optimal_length'],
                        scanned_at=scanned_at
                    )
                    db.add(db_result)
                db.commit()
                scan_status["last_run"] = scanned_at.isoformat()
                logger.info(f"TITAN scan session completed. {len(all_results)} results saved.")
            except Exception as e:
                logger.error(f"Failed to save TITAN scan results: {e}")
                db.rollback()
            finally:
                db.close()
                
    except Exception as e:
        logger.critical(f"Critical failure in TITAN scanner task: {e}")
    finally:
        scan_status["is_running"] = False
        scan_status["current_symbol"] = ""

@router.post("/scan")
def trigger_titan_scan(background_tasks: BackgroundTasks, settings: Optional[ScanSettings] = None):
    """
    Initiates an asynchronous VN100 adaptive scan session.
    """
    if scan_status["is_running"]:
        raise ValidationError("A TITAN scan session is already in progress.")
    
    # Pre-emptive state lock
    scan_status["is_running"] = True
    background_tasks.add_task(run_scan_task, get_db, settings)
    logger.info("TITAN Alpha scan triggered.")
    
    return {"success": True, "message": "TITAN Alpha scanner background task started."}

@router.get("/inspect/{symbol}")
def inspect_ticker(symbol: str):
    """
    Provides a detailed parameter stability heatmap for a specific symbol.
    """
    data = scanner.inspect_ticker_stability(symbol.upper())
    if not data:
        raise EntityNotFoundException("Scanner data", symbol)
    return {"success": True, "data": data}
