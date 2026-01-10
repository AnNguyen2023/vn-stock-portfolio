"""
backend/titan/data_feed.py
==========================
VNStock Data Feed Wrapper (VN100 Edition) with Smart Caching
"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd

try:
    from vnstock import Vnstock
    VNSTOCK_AVAILABLE = True
except ImportError:
    VNSTOCK_AVAILABLE = False
    Vnstock = None

# Optimization: Local caching (12 hours)
CACHE_DIR = "cache"
CACHE_EXPIRY_HOURS = 2

class VnStockClient:
    """
    VNStock Data Client with Persistent Caching.
    """
    
    def __init__(self):
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
    def _get_cache_path(self, symbol: str) -> str:
        return os.path.join(CACHE_DIR, f"{symbol}_history.csv")

    def get_stock_history(self, symbol: str, days: int = 730) -> pd.DataFrame:
        if not VNSTOCK_AVAILABLE:
            return pd.DataFrame()
        
        cache_path = self._get_cache_path(symbol)
        
        # Check cache validity
        if os.path.exists(cache_path):
            file_mod_time = os.path.getmtime(cache_path)
            cache_age_hours = (time.time() - file_mod_time) / 3600
            
            if cache_age_hours < CACHE_EXPIRY_HOURS:
                try:
                    # Load from cache
                    df = pd.read_csv(cache_path)
                    # Convert 'Date' back to proper type if necessary
                    return df
                except Exception:
                    pass # Fallback to live fetch

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df = stock.quote.history(
                start=start_str,
                end=end_str,
                interval='1D'
            )
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            column_mapping = {
                'time': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Save to cache
            df.to_csv(cache_path, index=False)
            
            required_cols = ['Open', 'High', 'Low', 'Close']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                return pd.DataFrame()
            
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            
            if 'Date' in df.columns:
                df = df.sort_values(by='Date', ascending=True)
            
            df = df.reset_index(drop=True)
            
            return df
            
        except Exception:
            return pd.DataFrame()
    
    def get_vn100_tickers(self) -> List[str]:
        vn30 = [
            'ACB', 'BCM', 'BID', 'BVH', 'CTG',
            'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
            'MBB', 'MSN', 'MWG', 'PLX', 'POW',
            'SAB', 'SHB', 'SSB', 'SSI', 'STB',
            'TCB', 'TPB', 'VCB', 'VHM', 'VIB',
            'VIC', 'VJC', 'VNM', 'VPB', 'VRE'
        ]
        
        midcap_liquid = [
            'DIG', 'DXG', 'KDH', 'NLG', 'PDR', 'KBC', 'DXS', 'NVL', 'CEO', 'HDG',
            'IJC', 'SCR', 'TDH', 'HAR', 'VRC', 'NHA', 'LDG', 'NBB', 'TIP', 'IDC',
            'VND', 'HCM', 'VCI', 'VIX', 'FTS', 'BSI', 'CTS', 'AGR', 'SHS', 'TVS',
            'APG', 'TCI', 'ART', 'EVF', 'ORS', 'DSC', 'BVS', 'PSI', 'MBS',
            'GEX', 'PC1', 'REE', 'CTD', 'FCN', 'HBC', 'HHV', 'LCG', 'VCG', 'CII',
            'HT1', 'DGC', 'DCM', 'DPM', 'LAS', 'CSV', 'PVD', 'PVT', 'GIL', 'NT2',
            'FRT', 'PNJ', 'DGW', 'VGC', 'PAN', 'HAG', 'HNG', 'ASM', 'AMV',
            'CMG', 'ELC', 'ITD', 'SAM', 'VGI', 'ONE', 'VTP',
            'VHC', 'ANV', 'IDI', 'ABT', 'HSL', 'LSS', 'HAP', 'BBC',
            'GMD', 'VOS', 'DVP', 'PHP', 'TMS', 'HAH', 'VSC'
        ]
        
        all_tickers = list(dict.fromkeys(vn30 + midcap_liquid))
        return all_tickers
