# services/market_service.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import time
from typing import Iterable

import models
import crawler
from core.db import SessionLocal
from core.redis_client import get_redis
import json

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None


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
    """Worker: Đồng bộ danh sách mã chứng khoán (HOSE, HNX, UPCOM) từ vnstock3."""
    print("--- [SYNC] Tèo đang bắt đầu đồng bộ danh sách mã chứng khoán ---")
    try:
        from vnstock import Vnstock
        # vnstock3 yêu cầu khởi tạo stock object để truy cập listing
        ls = Vnstock().stock(symbol="FPT").listing
        df = ls.symbols_by_exchange()

        if df is None or df.empty:
            print("[SYNC] ⚠️ Không lấy được dữ liệu từ vnstock3")
            return

        # Filter theo yêu cầu: HOSE (HSX), HNX, UPCOM và loại STOCK, ETF, FUND
        # Lưu ý: vnstock3 dùng 'HSX' thay vì 'HOSE'
        valid_exchanges = ["HSX", "HOSE", "HNX", "UPCOM"]
        valid_types = ["STOCK", "ETF", "FUND"]

        df_filtered = df[
            (df["exchange"].isin(valid_exchanges)) &
            (df["type"].isin(valid_types))
        ]

        with SessionLocal() as db:
            count_new = 0
            count_upd = 0
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
    """Lấy dữ liệu chi tiết cho danh sách mã trong Watchlist"""
    if not tickers:
        return []
    
    from crawler import get_current_prices, get_historical_prices
    from vnstock import Vnstock
    
    # 1. Lấy dữ liệu giá real-time từ Crawler (đã bao gồm Trần/Sàn/Tham chiếu)
    current_prices = get_current_prices(tickers)
    
    results = []
    with SessionLocal() as db:
        for t in tickers:
            t = t.upper()
            sec = db.query(models.Security).filter_by(symbol=t).first()
            
            p_info = current_prices.get(t, {})
            # Phân tách dữ liệu từ crawler (đảm bảo tương thích nếu crawler trả về float hoặc dict)
            if isinstance(p_info, dict):
                curr_price = float(p_info.get("price", 0))
                ref_price_vnd = float(p_info.get("ref", 0))
                ceiling_p = float(p_info.get("ceiling", 0))
                floor_p = float(p_info.get("floor", 0))
            else:
                curr_price = float(p_info or 0)
                ref_price_vnd = 0
                ceiling_p = 0
                floor_p = 0

            # 2. Lấy dữ liệu Sparkline (7 ngày) - CẦN CACHE MẠNH
            sparkline = []
            cache_spark_key = f"sparkline:{t}"
            
            # Thử lấy từ Redis trước
            if REDIS_AVAILABLE:
                try:
                    cached_spark = redis_client.get(cache_spark_key)
                    if cached_spark:
                        sparkline = json.loads(cached_spark)
                except: pass

            if not sparkline:
                # Nếu không có trong cache, thử lấy từ DB
                history_db = db.query(models.HistoricalPrice)\
                    .filter(models.HistoricalPrice.ticker == t)\
                    .order_by(models.HistoricalPrice.date.desc())\
                    .limit(7).all()
                sparkline = [float(h.close_price) for h in reversed(history_db)]
                
            if not sparkline:
                try:
                    # Kiểm tra xem VCI có đang trong thời gian "nghỉ" do Rate Limit không
                    vci_backoff = False
                    if REDIS_AVAILABLE:
                        vci_backoff = redis_client.get("vci_rate_limit_backoff")
                    
                    if not vci_backoff:
                        # Nếu DB trống và không bị backoff, lấy live
                        print(f"[MARKET] Đang lấy Sparkline mới cho {t} từ VCI...")
                        live_hist = get_historical_prices(t, period="1m")
                        if live_hist:
                            sparkline = [float(h["close"]) for h in live_hist[-7:]]
                            # Lưu vào Redis 1 tiếng để không phải lấy lại
                            if REDIS_AVAILABLE and sparkline:
                                redis_client.setex(cache_spark_key, 3600, json.dumps(sparkline))
                        
                        # Nghỉ một chút để tránh VCI quá tải
                        time.sleep(0.5) 
                except BaseException as be:
                    print(f"[MARKET] VCI Rate Limit detected cho {t}, tạm dừng lấy lịch sử")
                    # Nếu gặp Rate Limit (SystemExit/BaseException), bắt VCI nghỉ 60s
                    if REDIS_AVAILABLE:
                        redis_client.setex("vci_rate_limit_backoff", 60, "true")
                    sparkline = []

            # 3. Chỉ số tài chính - CẦN CACHE MẠNH (Dùng 24h)
            pe = 0
            market_cap = 0
            cache_ratio_key = f"ratios:{t}"
            
            # Thử lấy từ Redis trước
            if REDIS_AVAILABLE:
                try:
                    cached_ratios = redis_client.get(cache_ratio_key)
                    if cached_ratios:
                        ratio_data = json.loads(cached_ratios)
                        pe = ratio_data.get("pe", 0)
                        market_cap = float(ratio_data.get("market_cap", 0))
                        roe = ratio_data.get("roe", 0)
                        roa = ratio_data.get("roa", 0)
                        
                        # [SỬA LỖI] Nếu market_cap quá lớn (> 10^17), chắc chắn bị nhân lố, xóa cache để lấy lại
                        if market_cap > 1e17:
                            redis_client.delete(cache_ratio_key)
                            market_cap = 0
                            pe = 0
                            roe = 0
                            roa = 0
                except: pass

            # Nếu cache bị thiếu ROE/ROA (do nạp từ bản cũ), cũng coi như pe=0 để nạp lại
            if pe == 0 or market_cap == 0 or roe == 0 or roa == 0:
                try:
                    # Nếu chưa có cache, lấy từ Vnstock
                    print(f"[MARKET] Đang lấy Chỉ số tài chính mới cho {t}...")
                    stock = Vnstock().stock(symbol=t)
                    df_ratio = stock.finance.ratio(period='yearly', lang='vi')
                    if not df_ratio.empty:
                        latest = df_ratio.iloc[0]
                        pe = latest.get(('Chỉ tiêu định giá', 'P/E')) or latest.get('priceToEarning') or 0
                        
                        mc_bil = latest.get(('Chỉ tiêu định giá', 'Vốn hóa (Tỷ đồng)'))
                        if mc_bil:
                            # Nếu giá trị > 10^9, khả năng cao Vnstock đã trả về raw VND
                            mc_val = float(mc_bil)
                            market_cap = mc_val if mc_val > 1e9 else mc_val * 1e9
                        
                        # Lấy ROE, ROA
                        roe = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROE (%)')) or 0
                        roa = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROA (%)')) or 0
                        
                        # Lưu vào Redis 24 tiếng (86400s)
                        if REDIS_AVAILABLE:
                            redis_client.delete(cache_ratio_key) # Xóa cache cũ lỗi
                            redis_client.setex(cache_ratio_key, 86400, json.dumps({
                                "pe": float(pe), 
                                "market_cap": float(market_cap),
                                "roe": float(roe),
                                "roa": float(roa)
                            }))
                except Exception as e:
                    print(f"[MARKET] Lỗi lấy chỉ số cho {t}: {e}")

            results.append({
                "ticker": t,
                "name": sec.short_name if sec else t,
                "price": curr_price,
                "ref_price": ref_price_vnd,
                "ceiling_price": ceiling_p,
                "floor_price": floor_p,
                "change_pct": ((curr_price - ref_price_vnd) / ref_price_vnd * 100) if ref_price_vnd > 0 else 0,
                "volume": p_info.get("volume", 0) if isinstance(p_info, dict) else 0,
                "market_cap": market_cap,
                "roe": roe,
                "roa": roa,
                "pe": pe,
                "sparkline": sparkline,
                "industry": sec.exchange if sec else "",
                "ref_price": ref_price_vnd,
                "ceiling_price": ceiling_p,
                "floor_price": floor_p
            })
            
    return results
