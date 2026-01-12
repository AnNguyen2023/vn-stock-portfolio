"""
core/data_engine.py - The "Heart" of data synchronization
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd
from vnstock import Vnstock
from sqlalchemy.orm import Session
from core.db import SessionLocal
from core.logger import logger
import models
import os
import requests

class DataEngine:
    @staticmethod
    def get_setting(db: Session, key: str, default: str = None) -> str:
        setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(db: Session, key: str, value: str):
        setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = models.SystemSetting(key=key, value=value)
            db.add(setting)
        db.commit()

    @classmethod
    def startup_sync(cls):
        """
        Check for missing days since last sync and perform "Self-Healing".
        """
        with SessionLocal() as db:
            last_sync_str = cls.get_setting(db, "last_sync_date")
            today = date.today()
            
            # Start date for sync: could be from settings or a default
            if last_sync_str:
                last_sync = datetime.strptime(last_sync_str, "%Y-%m-%d").date()
            else:
                # Default to 7 days ago if first time
                last_sync = today - timedelta(days=7)
                
            if last_sync < today:
                logger.info(f"--- [DataEngine] Missing sync since {last_sync}. Starting self-healing...")
                cls.sync_historical_data(last_sync, today)
                cls.set_setting(db, "last_sync_date", today.strftime("%Y-%m-%d"))
                logger.info(f"--- [DataEngine] Startup sync completed up to {today}")

    @classmethod
    def sync_historical_data(cls, start_date: date, end_date: date):
        """
        Generic function to fetch historical data for all relevant tickers.
        """
        with SessionLocal() as db:
            # 1. Get all tickers in portfolio
            holdings = db.query(models.TickerHolding.ticker).all()
            tickers = [h[0] for h in holdings]
            
            # 2. Add indices
            indices = ["VNINDEX", "VN30", "HNX30", "HNX", "UPCOM"]
            all_symbols = list(set(tickers + indices))
            
            vn = Vnstock()
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            for symbol in all_symbols:
                try:
                    cls.sync_single_ticker(db, vn, symbol, start_str, end_str)
                except Exception as e:
                    logger.error(f"❌ [DataEngine] Error syncing {symbol}: {e}")

    @staticmethod
    def sync_single_ticker(db: Session, vn: Vnstock, symbol: str, start_str: str, end_str: str):
        logger.info(f"--- [DataEngine] Syncing {symbol} from {start_str} to {end_str}")
        stock = vn.stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start=start_str, end=end_str, interval='1D')
        
        if df is None or df.empty:
            return

        for _, row in df.iterrows():
            d = row['time'].date() if isinstance(row['time'], datetime) else pd.to_datetime(row['time']).date()
            
            existing = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == symbol,
                models.HistoricalPrice.date == d
            ).first()
            
            if not existing:
                h = models.HistoricalPrice(
                    ticker=symbol,
                    date=d,
                    close_price=Decimal(str(row['close'])),
                    volume=Decimal(str(row.get('volume', 0))),
                    value=Decimal(str(row.get('value', 0)))
                )
                db.add(h)
        db.commit()

    @classmethod
    def end_of_day_sync(cls):
        """
        Scheduled chốt sổ at 15:05 daily.
        1. Sync history for today (to get final close prices).
        2. Calculate and save NAV snapshot.
        """
        today = date.today()
        logger.info(f"--- [DataEngine] Running End-of-Day chot so for {today}")
        
        # 1. Sync prices
        cls.sync_historical_data(today, today)
        
        # 2. Save NAV snapshot
        from tasks.daily_nav_snapshot import save_daily_nav_snapshot
        save_daily_nav_snapshot()
        
        # 3. Update last sync date
        with SessionLocal() as db:
            cls.set_setting(db, "last_sync_date", today.strftime("%Y-%m-%d"))
        
        logger.info(f"--- [DataEngine] End-of-Day process completed for {today}")
