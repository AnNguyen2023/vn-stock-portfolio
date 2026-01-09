# services/market_service.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import time
from typing import Iterable
import json
import concurrent.futures

import models
import crawler
from core.db import SessionLocal
from core.redis_client import get_redis

# New Adapters
from adapters import vci_adapter, vnstock_adapter

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

# --- IN-MEMORY CACHE (FALLBACK KHI REDIS DIE) ---
MEMORY_CACHE = {}

def mem_get(key):
    """Lấy dữ liệu từ RAM nếu chưa hết hạn"""
    if key in MEMORY_CACHE:
        val, exp = MEMORY_CACHE[key]
        if time.time() < exp:
            return val
        else:
            del MEMORY_CACHE[key]
    return None

def mem_set(key, val, ttl):
    """Lưu dữ liệu vào RAM với TTL (giây)"""
    MEMORY_CACHE[key] = (val, time.time() + ttl)

def _process_single_ticker(t: str, p_info: dict) -> dict:
    """Hàm xử lý logic cho 1 mã (chạy trong thread)"""
    t = t.upper()
    try:
        # 1. Giá Realtime (từ batch request)
        if isinstance(p_info, dict):
            curr_price = float(p_info.get("price", 0))
            ref_price_vnd = float(p_info.get("ref", 0))
            ceiling_p = float(p_info.get("ceiling", 0))
            floor_p = float(p_info.get("floor", 0))
            vol = float(p_info.get("volume", 0))
        else:
            curr_price = float(p_info or 0)
            ref_price_vnd = 0; ceiling_p = 0; floor_p = 0; vol = 0

        # 2. Xử lý DB & Metadata (Ngắn gọn)
        with SessionLocal() as db:
            sec = db.query(models.Security).filter_by(symbol=t).first()
            exchange = sec.exchange if sec else ""
            name = sec.short_name if sec else t

            # 3. SPARKLINE (Dùng Adapter)
            sparkline = vci_adapter.get_sparkline_data(t, mem_get, mem_set)

            # 4. FINANCIAL RATIOS (Dùng Adapter)
            ratios = vnstock_adapter.get_financial_ratios(t, mem_get, mem_set)

            return {
                "ticker": t,
                "name": name,
                "price": curr_price,
                "ref_price": ref_price_vnd,
                "ceiling_price": ceiling_p,
                "floor_price": floor_p,
                "change_pct": ((curr_price - ref_price_vnd) / ref_price_vnd * 100) if ref_price_vnd > 0 else 0,
                "volume": vol,
                "market_cap": ratios["market_cap"],
                "roe": ratios["roe"],
                "roa": ratios["roa"],
                "pe": ratios["pe"],
                "sparkline": sparkline,
                "industry": exchange,
            }

    except Exception as e:
        print(f"[ERR] Lỗi xử lý {t}: {e}")
        return {"ticker": t, "price": 0, "change_pct": 0, "sparkline": [], "name": t}


def seed_index_data_task() -> None:
    """Worker: nhặt 1 năm dữ liệu VNINDEX về kho."""
    print("--- [KHO] Tèo em đang chuẩn bị đi nhặt VN-INDEX ---")
    live_data = crawler.get_historical_prices("VNINDEX", period="1y")
    if not live_data:
        return

    with SessionLocal() as db:
        count = 0
        for item in live_data:
            try:
                d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                exist = db.query(models.HistoricalPrice).filter_by(ticker="VNINDEX", date=d).first()
                if not exist:
                    db.add(
                        models.HistoricalPrice(
                            ticker="VNINDEX",
                            date=d,
                            close_price=Decimal(str(item["close"])),
                        )
                    )
                    count += 1
            except Exception:
                continue
        db.commit()

    print(f"--- [XONG] Đã cất thêm {count} ngày VN-INDEX vào kho! ---")


def sync_portfolio_history_task(tickers: Iterable[str], sleep_sec: float = 2.0) -> None:
    """Worker: quét danh mục, nhặt history cho các mã (nghỉ 2s mỗi mã)."""
    for t in tickers:
        t = (t or "").upper().strip()
        if not t:
            continue

        print(f"--- [SO ĐỐI] Kiểm tra kho mã {t} ---")
        live_data = crawler.get_historical_prices(t, period="1y")
        if live_data:
            with SessionLocal() as db:
                for item in live_data:
                    try:
                        d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                        exist = db.query(models.HistoricalPrice).filter_by(ticker=t, date=d).first()
                        if not exist:
                            db.add(
                                models.HistoricalPrice(
                                    ticker=t,
                                    date=d,
                                    close_price=Decimal(str(item["close"])),
                                )
                            )
                    except Exception:
                        continue
                db.commit()

        print(f"--- [NGHỈ] Xong mã {t}, Tèo em nghỉ {sleep_sec} giây ---")
        time.sleep(sleep_sec)

    print("--- [XONG] Đã đồng bộ toàn bộ history danh mục! ---")


def sync_historical_task(ticker: str, period: str) -> None:
    """Worker: nhặt data 'kiến tha lâu đầy tổ'."""
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return

    try:
        live_data = crawler.get_historical_prices(ticker, period)
        if not live_data:
            return

        with SessionLocal() as db:
            for item in live_data:
                try:
                    d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    exist = db.query(models.HistoricalPrice).filter_by(ticker=ticker, date=d).first()
                    if not exist:
                        db.add(
                            models.HistoricalPrice(
                                ticker=ticker,
                                date=d,
                                close_price=Decimal(str(item["close"])),
                            )
                        )
                except Exception:
                    continue
            db.commit()

        print(f"--- [KHO] ĐÃ NẠP XONG DATA CHO {ticker} ---")
    except Exception as e:
        print(f"--- [LỖI KHO] {ticker}: {e} ---")

def sync_securities_task() -> None:
    """Worker: Đồng bộ danh sách mã chứng khoán từ vnstock3 (qua Adapter)."""
    print("--- [SYNC] Tèo đang bắt đầu đồng bộ danh sách mã chứng khoán ---")
    try:
        df = vnstock_adapter.get_all_symbols()
        if df is None or df.empty:
            print("[SYNC] ⚠️ Không lấy được dữ liệu từ vnstock adapter")
            return

        valid_exchanges = ["HSX", "HOSE", "HNX", "UPCOM"]
        valid_types = ["STOCK", "ETF", "FUND"]

        df_filtered = df[
            (df["exchange"].isin(valid_exchanges)) &
            (df["type"].isin(valid_types))
        ]

        with SessionLocal() as db:
            count_new = 0; count_upd = 0
            for _, row in df_filtered.iterrows():
                symbol = str(row["symbol"]).upper().strip()
                exchange = "HOSE" if row["exchange"] == "HSX" else row["exchange"]

                exist = db.query(models.Security).filter_by(symbol=symbol).first()
                if exist:
                    exist.short_name = row.get("organ_short_name")
                    exist.full_name = row.get("organ_name")
                    exist.exchange = exchange
                    exist.type = row["type"]
                    exist.last_synced = datetime.now()
                    count_upd += 1
                else:
                    db.add(
                        models.Security(
                            symbol=symbol,
                            short_name=row.get("organ_short_name"),
                            full_name=row.get("organ_name"),
                            exchange=exchange,
                            type=row["type"],
                            last_synced=datetime.now()
                        )
                    )
                    count_new += 1
            db.commit()
            print(f"--- [XONG] Thêm mới {count_new}, cập nhật {count_upd} mã chứng khoán! ---")

    except Exception as e:
        print(f"--- [LỖI SYNC] Không thể đồng bộ mã chứng khoán: {e} ---")


def get_watchlist_detail_service(tickers: list[str]) -> list[dict]:
    """
    Lấy dữ liệu chi tiết Watchlist (Tối ưu Parallel + Memory Cache)
    """
    if not tickers:
        return []

    # 1. Lấy giá Real-time (Batch Request)
    from crawler import get_current_prices
    try:
        current_prices = get_current_prices(tickers)
    except:
        current_prices = {}

    results = []
    
    # 2. Chạy Parallel xử lý từng mã
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {
            executor.submit(_process_single_ticker, t, current_prices.get(t.upper(), {})): t 
            for t in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            data = future.result()
            if data:
                results.append(data)
    
    results_map = {r['ticker']: r for r in results}
    ordered_results = [results_map.get(t.upper()) for t in tickers if t.upper() in results_map]
    
    return ordered_results


def get_trending_indicator(ticker: str) -> dict:
    """
    Tính xu hướng giá dựa trên 5 phiên gần nhất.
    """
    ticker = ticker.upper()
    cache_key = f"trending:{ticker}"
    
    if REDIS_AVAILABLE:
        try:
            cached = redis_client.get(cache_key)
            if cached: return json.loads(cached)
        except: pass
    
    cached_mem = mem_get(cache_key)
    if cached_mem: return cached_mem
    
    with SessionLocal() as db:
        prices = (
            db.query(models.HistoricalPrice)
            .filter(models.HistoricalPrice.ticker == ticker)
            .order_by(models.HistoricalPrice.date.desc())
            .limit(5)
            .all()
        )
        
        if len(prices) < 2:
            return {"trend": "sideways", "change_pct": 0.0}
        
        prices = list(reversed(prices))
        first_price = float(prices[0].close_price)
        last_price = float(prices[-1].close_price)
        change_pct = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0.0
        
        if change_pct >= 3.0: trend = "strong_up"
        elif change_pct >= 1.0: trend = "up"
        elif change_pct <= -3.0: trend = "strong_down"
        elif change_pct <= -1.0: trend = "down"
        else: trend = "sideways"
        
        result = {"trend": trend, "change_pct": round(change_pct, 2)}
        
        if REDIS_AVAILABLE:
            try: redis_client.setex(cache_key, 300, json.dumps(result))
            except: pass
        mem_set(cache_key, result, 300)
        
        return result
