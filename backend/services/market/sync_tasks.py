
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
import time
from typing import Iterable
from sqlalchemy.orm import Session

import models
import crawler
from adapters import vnstock_adapter
from core.db import SessionLocal
from core.logger import logger

def seed_index_data_task() -> None:
    """
    Worker task to fetch 1 year of historical data for VNINDEX and HNX30.
    """
    logger.info("Background job started: Syncing index historical data (VNINDEX, HNX30)")
    
    indices = ["VNINDEX", "HNX30"]
    total_count = 0
    
    with SessionLocal() as db:
        for symbol in indices:
            logger.info(f"Syncing index: {symbol}")
            live_data = crawler.get_historical_prices(symbol, period="1y")
            if not live_data:
                logger.warning(f"No historical data found for index {symbol}")
                continue

            # Pre-fetch existing dates to avoid N+1 SELECTs
            existing_dates = {
                r.date for r in 
                db.query(models.HistoricalPrice.date)
                .filter(models.HistoricalPrice.ticker == symbol)
                .all()
            }

            count = 0
            for item in live_data:
                try:
                    d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    if d not in existing_dates:
                        db.add(
                            models.HistoricalPrice(
                                ticker=symbol,
                                date=d,
                                close_price=Decimal(str(item["close"])),
                                volume=Decimal(str(item.get("volume", 0))),
                                value=Decimal(str(item.get("value", 0))),
                            )
                        )
                        existing_dates.add(d) # Local update to prevent dups in same batch
                        count += 1
                except Exception as e:
                    logger.debug(f"Error parsing historical item for {symbol}: {e}")
                    continue
            total_count += count
        
        db.commit()

    logger.info(f"Historical index sync completed. Added {total_count} records.")


def sync_portfolio_history_task(tickers: Iterable[str], sleep_sec: float = 2.0) -> None:
    """
    Worker task: Scans the portfolio and fetches 1 year of historical data for each ticker.
    Includes a configurable sleep period to respect external API rate limits.

    Args:
        tickers (Iterable[str]): List of tickers to sync.
        sleep_sec (float): Seconds to sleep between tickers.
    """
    tickers_list = list(tickers)
    logger.info(f"Background job started: Syncing portfolio history for {len(tickers_list)} tickers")
    for t in tickers_list:
        t = (t or "").upper().strip()
        if not t:
            continue

        logger.info(f"Syncing history for ticker: {t}")
        live_data = crawler.get_historical_prices(t, period="1y")
        if live_data:
            with SessionLocal() as db:
                # Pre-fetch existing dates to avoid N+1 SELECTs
                existing_dates = {
                    r.date for r in 
                    db.query(models.HistoricalPrice.date)
                    .filter(models.HistoricalPrice.ticker == t)
                    .all()
                }

                for item in live_data:
                    try:
                        d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                        if d not in existing_dates:
                            db.add(
                                models.HistoricalPrice(
                                    ticker=t,
                                    date=d,
                                    close_price=Decimal(str(item["close"])),
                                    volume=Decimal(str(item.get("volume", 0))),
                                    value=Decimal(str(item.get("value", 0))),
                                )
                            )
                            existing_dates.add(d) # Local update to prevent dups in same batch
                    except Exception as e:
                        logger.debug(f"Error parsing history for {t}: {e}")
                        continue
                db.commit()

        logger.debug(f"Finished {t}, sleeping for {sleep_sec}s")
        time.sleep(sleep_sec)

    logger.info("Portfolio history sync completed.")


def sync_historical_task(ticker: str, period: str) -> None:
    """
    One-off task to catch up on historical data for a specific ticker and period.

    Args:
        ticker (str): Ticker symbol.
        period (str): Date period (e.g., '1y', 'max').
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return
    if ticker == "VN30":
        logger.info("Skipping VN30 historical sync (display-only index).")
        return

    try:
        logger.info(f"Syncing historical data for {ticker} (Period: {period})")
        live_data = crawler.get_historical_prices(ticker, period)
        if not live_data:
            logger.warning(f"No data found for {ticker}")
            return

        with SessionLocal() as db:
            # Pre-fetch existing dates
            existing_dates = {
                r.date for r in 
                db.query(models.HistoricalPrice.date)
                .filter(models.HistoricalPrice.ticker == ticker)
                .all()
            }

            for item in live_data:
                try:
                    d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    if d not in existing_dates:
                        db.add(
                            models.HistoricalPrice(
                                ticker=ticker,
                                date=d,
                                close_price=Decimal(str(item["close"])),
                                volume=Decimal(str(item.get("volume", 0))),
                                value=Decimal(str(item.get("value", 0))),
                            )
                        )
                        existing_dates.add(d)
                except Exception as e:
                    logger.debug(f"Error parsing historical item for {ticker}: {e}")
                    continue
            db.commit()
        logger.info(f"Finished seeding {ticker}")
    except Exception as e:
        logger.error(f"Failed to sync historical data for {ticker}: {e}")


def _upsert_security(db, row) -> bool:
    """
    Helper to create or update a security record in the database.
    
    Returns:
        bool: True if new record created, False if updated.
    """
    symbol = str(row["symbol"]).upper().strip()
    exchange = "HOSE" if row["exchange"] == "HSX" else row["exchange"]

    exist = db.query(models.Security).filter_by(symbol=symbol).first()
    if exist:
        exist.short_name = row.get("organ_short_name")
        exist.full_name = row.get("organ_name")
        exist.exchange = exchange
        exist.type = row["type"]
        exist.last_synced = datetime.now()
        return False
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
        return True

def sync_securities_task() -> None:
    """
    Worker task to sync the list of all valid securities from VNStock adapter.
    Filters for relevant exchanges and types (STOCK, ETF, FUND).
    """
    logger.info("Background job started: Syncing securities list")
    try:
        df = vnstock_adapter.get_all_symbols()
        if df is None or df.empty:
            logger.warning("No security data received from adapter")
            return

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
                is_new = _upsert_security(db, row)
                if is_new: count_new += 1
                else: count_upd += 1
            db.commit()
            logger.info(f"Securities sync completed. New: {count_new}, Updated: {count_upd}")

    except Exception as e:
        logger.error(f"Failed to sync securities list: {e}")
