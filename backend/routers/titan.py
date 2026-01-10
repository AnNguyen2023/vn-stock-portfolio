# backend/routers/titan.py
from __future__ import annotations

import asyncio
import random
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.db import get_db
import models
from titan.alpha_scanner import AlphaScanner

from pydantic import BaseModel

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
    """Lấy trạng thái quá trình quét hiện tại"""
    return scan_status

@router.post("/stop")
def stop_titan_scan():
    """Dừng quá trình quét đang chạy"""
    global should_stop
    if scan_status["is_running"]:
        should_stop = True
        return {"message": "Stop signal sent"}
    return {"message": "No scan running"}

@router.get("/results")
def get_titan_results(db: Session = Depends(get_db)):
    """Lấy kết quả quét mới nhất từ database"""
    # Lấy thời điểm quét gần nhất
    latest_scan = db.query(models.TitanScanResult.scanned_at).order_by(desc(models.TitanScanResult.scanned_at)).first()
    if not latest_scan:
        return []
    
    # Lấy tất cả kết quả của lần quét đó
    results = db.query(models.TitanScanResult).filter(models.TitanScanResult.scanned_at == latest_scan[0]).all()
    return results

async def run_scan_task(db_session_factory, settings: Optional[ScanSettings] = None):
    """Hàm chạy quét ngầm với cơ chế song song (Parallel Processing)"""
    global scan_status, should_stop
    try:
        # Áp dụng cấu hình nếu có
        if settings:
            if settings.fee_bps is not None: scanner.fee_bps = settings.fee_bps
            if settings.slippage_bps is not None: scanner.slippage_bps = settings.slippage_bps
            if settings.wf_train_bars is not None: scanner.wf_train_bars = settings.wf_train_bars
            if settings.wf_test_bars is not None: scanner.wf_test_bars = settings.wf_test_bars
            if settings.wf_step_bars is not None: scanner.wf_step_bars = settings.wf_step_bars
            if settings.wf_min_folds is not None: scanner.wf_min_folds = settings.wf_min_folds
            if settings.stability_lambda is not None: scanner.stability_lambda = settings.stability_lambda
            if settings.trade_penalty_bps is not None: scanner.trade_penalty_bps = settings.trade_penalty_bps

        should_stop = False
        scan_status["is_running"] = True
        scan_status["progress"] = 0
        
        tickers = scanner.client.get_vn100_tickers()
        scan_status["total"] = len(tickers)
        
        # Cấu hình mức độ song song "Cực kỳ an toàn" cho VCI
        # Giảm xuống 2 luồng vì VCI quét rất gắt và có thể kill process bằng SystemExit
        semaphore = asyncio.Semaphore(2)
        
        async def analyze_with_limit(symbol):
            async with semaphore:
                if should_stop:
                    return None
                    
                # Delay lớn hơn (1.5s - 3.0s) để tránh bị coi là bot spam
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
                scan_status["current_symbol"] = symbol
                
                try:
                    # Chạy CPU-bound task trong executor
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, scanner.analyze_symbol, symbol)
                except (Exception, SystemExit) as e:
                    print(f"[TITAN] Error analyzing {symbol}: {e}")
                    # Nếu gặp lỗi Rate Limit cực gắt (SystemExit), ta nên tạm dừng scan một lúc
                    await asyncio.sleep(5)
                    return None

        # Tạo danh sách các coroutine
        tasks = [analyze_with_limit(s) for s in tickers]
        
        all_results = []
        processed_count = 0
        
        # Chạy vả xử lý kết quả khi chúng hoàn thành
        for task in asyncio.as_completed(tasks):
            if should_stop:
                print("[TITAN] Scan stopped by user")
                break
                
            result = await task
            processed_count += 1
            scan_status["progress"] = processed_count
            
            if result:
                all_results.append(result)
        
        # Lưu vào database
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
            except Exception as e:
                print(f"[TITAN] Error saving results: {e}")
                db.rollback()
            finally:
                db.close()
                
    except Exception as e:
        print(f"[TITAN] Scan task failed: {e}")
    finally:
        scan_status["is_running"] = False
        scan_status["current_symbol"] = ""

@router.post("/scan")
def trigger_titan_scan(background_tasks: BackgroundTasks, settings: Optional[ScanSettings] = None):
    """Bắt đầu quá trình quét VN100 Adaptive với cấu hình tùy chỉnh"""
    if scan_status["is_running"]:
        raise HTTPException(status_code=400, detail="Scan is already in progress")
    
    # Set running state immediately to block concurrent requests
    scan_status["is_running"] = True
    background_tasks.add_task(run_scan_task, get_db, settings)
    return {"message": "TITAN Scan started", "is_running": True}

@router.get("/inspect/{symbol}")
def inspect_ticker(symbol: str):
    """Kiểm tra chi tiết heatmap tham số cho một mã"""
    data = scanner.inspect_ticker_stability(symbol.upper())
    if not data:
        raise HTTPException(status_code=404, detail="Ticker data not found")
    return data
