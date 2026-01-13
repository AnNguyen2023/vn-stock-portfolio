"""
core/data_engine.py - The "Heart" of data synchronization
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd
from vnstock import Vnstock, Trading
from sqlalchemy.orm import Session
from core.db import SessionLocal
from core.logger import logger
import models
import os
import requests
from adapters.vps_adapter import get_realtime_prices_vps

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
                # Default to 100 days ago to ensure the requested 90-day history is always available
                last_sync = today - timedelta(days=100)
                
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
            # 1. Get all tickers in portfolio with ACTIVE holdings (total_volume > 0)
            holdings = db.query(models.TickerHolding.ticker).filter(models.TickerHolding.total_volume > 0).all()
            tickers = [h[0] for h in holdings]
            
            # 2. Add indices (Limit to 3 core indices)
            indices = ["VNINDEX", "VN30", "HNX30"]
            all_symbols = list(set(tickers + indices))
            
            vn = Vnstock()
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Fetch Batch data from multiple sources if end_date is today
            vps_data = {}
            index_extras = {} # Data from VCI price board for indices
            
            if end_date >= date.today():
                logger.info(f"--- [DataEngine] Fetching batch realtime data for {len(all_symbols)} symbols")
                try:
                    vps_data = get_realtime_prices_vps(all_symbols)
                    logger.info(f"--- [DataEngine] VPS data fetched for {len(vps_data)} symbols")
                except Exception as e:
                    logger.warning(f"--- [DataEngine] VPS fetch failed: {e}")

                try:
                    # Supplement indices with VCI price board (more reliable for Index Value)
                    df_indices = Trading(source='VCI').price_board(indices)
                    if df_indices is not None and not df_indices.empty:
                        logger.info(f"--- [DataEngine] VCI price_board fetched {len(df_indices)} indices")
                        # Print columns to debug if needed
                        # logger.info(f"--- [DataEngine] VCI columns: {df_indices.columns}")
                        
                        for _, row_idx in df_indices.iterrows():
                            # Safely get symbol
                            sym_idx = ""
                            for col in df_indices.columns:
                                if isinstance(col, tuple) and col[1] == 'symbol':
                                    sym_idx = str(row_idx[col]).upper()
                                    break
                            
                            if not sym_idx: continue
                            
                            # Safely get price, volume, value
                            p = 0; v = 0; val = 0
                            for col in df_indices.columns:
                                if not isinstance(col, tuple): continue
                                if col[1] in ['match_price', 'reference_price'] and p == 0:
                                    p = float(row_idx[col] or 0)
                                if col[1] in ['accumulated_volume', 'match_volume']:
                                    v = float(row_idx[col] or 0)
                                if col[1] in ['total_value', 'total_val']:
                                    val = float(row_idx[col] or 0)
                            
                            index_extras[sym_idx] = {
                                "price": p,
                                "volume": v,
                                "value": round(val / 1e9, 3) if val else 0
                            }
                            logger.info(f"--- [DataEngine] Index {sym_idx}: Value={index_extras[sym_idx]['value']} Bil")
                except Exception as e:
                    logger.warning(f"--- [DataEngine] VCI Index price_board failed: {e}")
            
            for symbol in all_symbols:
                try:
                    # Combine vps_data and index_extras
                    extra = vps_data.get(symbol, {}).copy() # Use copy to avoid mutating cache
                    if symbol in index_extras:
                        idx_data = index_extras[symbol]
                        if idx_data['value'] > 0: extra['value'] = idx_data['value']
                        if idx_data['volume'] > 0: extra['volume'] = idx_data['volume']
                        if idx_data['price'] > 0: extra['price'] = idx_data['price']

                    cls.sync_single_ticker(db, vn, symbol, start_str, end_str, extra)
                except Exception as e:
                    logger.error(f"[DataEngine] Error syncing {symbol}: {e}")

    @staticmethod
    def sync_single_ticker(db: Session, vn: Vnstock, symbol: str, start_str: str, end_str: str, extra: dict = None):
        """
        Syncs a single ticker using available sources.
        'extra' can contain realtime price/vol/val to supplement or fallback.
        """
        logger.info(f"--- [DataEngine] Syncing {symbol} ({start_str} to {end_str})")
        
        # 1. Try to get history from Vnstock (VCI)
        df = None
        try:
            stock = vn.stock(symbol=symbol, source='VCI')
            df = stock.quote.history(start=start_str, end=end_str, interval='1D')
        except Exception as e:
            logger.warning(f"[DataEngine] Vnstock history failed for {symbol}: {e}")

        # 2. If it's today and history is empty/None, use extra data as a pseudo-row
        is_today = (end_str == date.today().strftime("%Y-%m-%d"))
        if (df is None or df.empty) and is_today and extra:
            df = pd.DataFrame([{
                'time': datetime.now(),
                'close': extra.get('price', 0),
                'volume': extra.get('volume', 0),
                'value': extra.get('value', 0)
            }])
            logger.info(f"--- [DataEngine] Created row from extra data for {symbol}")

        if df is None or df.empty:
            return

        for _, row in df.iterrows():
            # Get date reliably
            try:
                if isinstance(row['time'], datetime):
                    d = row['time'].date()
                else:
                    d = pd.to_datetime(row['time']).date()
            except:
                continue
            
            existing = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == symbol,
                models.HistoricalPrice.date == d
            ).first()
            
            # Extract values from row
            close_p = Decimal(str(row.get('close') or row.get('close_p') or 0))
            vol = Decimal(str(row.get('volume') or row.get('vol') or 0))
            val = Decimal(str(row.get('value') or row.get('val') or 0))
            
            # Use extra data to refine today's record
            if is_today and d == date.today() and extra:
                if extra.get('price', 0) > 0: close_p = Decimal(str(extra['price']))
                if extra.get('volume', 0) > 0: vol = Decimal(str(extra['volume']))
                if extra.get('value', 0) > 0: val = Decimal(str(extra['value']))

            if not existing:
                h = models.HistoricalPrice(
                    ticker=symbol,
                    date=d,
                    close_price=close_p,
                    volume=vol,
                    value=val
                )
                db.add(h)
            else:
                # Update today's record (it might be changing)
                if d == date.today():
                    existing.close_price = close_p
                    existing.volume = vol
                    existing.value = val
        
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
