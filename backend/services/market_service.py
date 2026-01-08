# services/market_service.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import time
from typing import Iterable

import models
import crawler
from core.db import SessionLocal


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
