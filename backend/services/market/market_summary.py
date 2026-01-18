
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
import pandas as pd
from typing import Any, Optional
from vnstock import Trading

import models
from core.db import SessionLocal
from core.logger import logger
from services.market.cache import mem_get, mem_set
from services.market.data_processor import (
    _vn_now, _is_market_open, _get_intraday_from_db, _save_intraday_session
)
from adapters.vci_adapter import get_intraday_sparkline

def _process_market_row(row: Any, index_name: str, db: Session, vps_data: dict = None) -> Optional[dict]:
    """Helper to process a single index row with VPS priority and safe extraction."""
    try:
        # Standardize index names
        if index_name == "HASTC": index_name = "HNXINDEX"

        # Safe extraction from row (VCI board)
        match_price = 0
        ref_price = 0
        match_vol = 0
        total_val = 0
        
        if hasattr(row, 'get'):
            match_price = row.get(('match', 'match_price')) or 0
            ref_price = row.get(('match', 'reference_price')) or 0
            match_vol = row.get(('match', 'match_vol')) or row.get(('match', 'accumulated_volume')) or 0
            total_val = row.get(('match', 'total_value')) or row.get(('match', 'total_val')) or 0
        
        price = float(match_price or ref_price or 0)
        ref = float(ref_price or 0)
        volume = float(match_vol or 0)
        # VCI VND -> Billions (Assume Thousands of VND if it's too small)
        value = float(total_val) / 1e9 
        if 0 < value < 100: # Heuristic: if it's suspiciously small (e.g. 41B), it might be missing Thousands multiplier
            value *= 1000 # 41B -> 41,000B

        # VPS Data Priority
        has_vps = False
        if vps_data and index_name in vps_data:
            has_vps = True
            v_data = vps_data[index_name]
            v_price = v_data.get("price", 0)
            if v_price > 0: price = v_price
            
            v_ref = v_data.get("ref", 0)
            if v_ref > 0: ref = v_ref
            
            v_vol = v_data.get("volume", 0)
            if v_vol > 0: volume = v_vol
            
            v_val = v_data.get("value", 0)
            if v_val > 0: 
                # Smart scaling: VPS can return Millions (e.g. 40,000,000) or Billions (e.g. 40,000)
                # Goal: Billion VND (Tỷ). If > 1M, it's definitely Millions or raw VND.
                if v_val > 500000: # Heuristic for Millions VND (Min liq for VNINDEX is ~5k Tỷ)
                    value = v_val / 1000
                else:
                    value = v_val
        
        # Unify to points if price is raw (e.g. 1,000,000)
        if price > 5000:
            price /= 1000
            ref /= 1000

        if price <= 0 or ref <= 0:
            return None

        # Determine value fallback if still 0
        if value <= 0:
            latest_hist = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == index_name
            ).order_by(models.HistoricalPrice.date.desc()).first()
            if latest_hist:
                if latest_hist.value > 0:
                    # Historical value is usually in VND, convert to Billions
                    value = float(latest_hist.value) / (1e9 if latest_hist.value > 1e6 else 1)
                if volume <= 0:
                    volume = int(latest_hist.volume or 0)
        
        change = price - ref
        change_pct = (change / ref * 100) if ref > 0 else 0
        
        sparkline = []
        try:
            vn_now = _vn_now()
            market_open = _is_market_open(vn_now)

            if (not market_open) and index_name == "VNINDEX":
                sparkline = _get_intraday_from_db(db, index_name)

            if not sparkline:
                fallback_date = None
                fallback_close = None
                if index_name == "VNINDEX":
                    latest_hist = db.query(models.HistoricalPrice).filter(
                        models.HistoricalPrice.ticker == index_name
                    ).order_by(models.HistoricalPrice.date.desc()).first()
                    if latest_hist:
                        fallback_date = latest_hist.date.strftime("%Y-%m-%d")
                        fallback_close = float(latest_hist.close_price)
                sparkline = get_intraday_sparkline(
                    index_name,
                    mem_get,
                    mem_set,
                    fallback_session_date=fallback_date,
                    fallback_close=fallback_close,
                )

            if market_open and index_name == "VNINDEX" and sparkline:
                _save_intraday_session(db, index_name, sparkline)
        except Exception as se:
            logger.debug(f"Intraday sparkline failed for {index_name}: {se}")

        # Persistent Intraday Safety Net: Update database for today
        # CRITICAL: Only VNINDEX is stored for calculations; VN30 is display-only.
        should_persist = (index_name == "VNINDEX")
        
        if should_persist and price > 0:
            try:
                today_d = date.today()
                existing = db.query(models.HistoricalPrice).filter(
                    models.HistoricalPrice.ticker == index_name,
                    models.HistoricalPrice.date == today_d
                ).first()
                if not existing:
                    new_h = models.HistoricalPrice(
                        ticker=index_name,
                        date=today_d,
                        close_price=Decimal(str(price)),
                        volume=Decimal(str(volume)),
                        value=Decimal(str(value))
                    )
                    db.add(new_h)
                else:
                    # Update with freshest live data
                    existing.close_price = Decimal(str(price))
                    existing.volume = Decimal(str(volume))
                    existing.value = Decimal(str(value))
                db.commit()
                logger.info(f"[DB] Saved {index_name} to HistoricalPrice: {price:.2f}")
            except Exception as db_e:
                db.rollback()
                logger.debug(f"Persistence failed for {index_name}: {db_e}")

        logger.info(f"MarketRow [{index_name}]: P={price:.2f} V={volume} Val={value:.3f} VPS={has_vps}")

        return {
            "index": index_name,
            "last_updated": datetime.now().isoformat(),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(volume),
            "value": round(value, 3),
            "sparkline": sparkline
        }
    except Exception as e:
        logger.debug(f"Row processing failed for {index_name}: {e}")
        return None

def _get_market_fallback(db: Session, indices: list[str]) -> list[dict]:
    """
    Helper for database fallback synchronization.
    Optimized to use batch queries instead of N+1 loop.
    """
    if not indices:
        return []

    from sqlalchemy import func, tuple_, desc, literal_column
    
    fallback_results = []
    
    # 1. Helper to fetch latest records for multiple tickers from a specific table
    def fetch_latest_from_table(model, tickers):
        if not tickers: return []
        subq = (
            db.query(
                model.ticker,
                func.max(model.date).label('max_date')
            )
            .filter(model.ticker.in_(tickers))
            .group_by(model.ticker)
            .subquery()
        )
        
        return (
            db.query(model)
            .join(subq, (model.ticker == subq.c.ticker) & (model.date == subq.c.max_date))
            .all()
        )

    # 2. Try TestHistoricalPrice first (Priority 1)
    latest_test = fetch_latest_from_table(models.TestHistoricalPrice, indices)
    latest_map = {r.ticker: r for r in latest_test}
    
    # 3. Try HistoricalPrice for missing ones (Priority 2)
    missing_indices = [i for i in indices if i not in latest_map]
    if missing_indices:
        latest_real = fetch_latest_from_table(models.HistoricalPrice, missing_indices)
        for r in latest_real:
            latest_map[r.ticker] = r

    # 4. Fetch Previous Records for Change Calculation (Batch)
    # We need to find the record immediately preceding the latest date for each ticker
    prev_map = {}
    
    # Collect queries for each valid ticker to find its previous record
    # Since specific dates vary per ticker, a single simple batch query is hard without window functions
    # or complex self-joins. Given standard simple SQL usage, we can iterate for PREVIOUS record 
    # (checking 2-3 indices is fast enough if LATEST is already batched, or use UNION ALL)
    
    valid_tickers = [t for t in indices if t in latest_map]
    if valid_tickers:
        # Optimization: Use UNION ALL to fetch previous records in one go
        queries = []
        for t in valid_tickers:
            latest_date = latest_map[t].date
            is_test = isinstance(latest_map[t], models.TestHistoricalPrice)
            table = models.TestHistoricalPrice if is_test else models.HistoricalPrice
            
            # Wrap in subquery to avoid UNION ALL ORDER BY/LIMIT syntax issues
            sub_q = (
                db.query(table.ticker, table.close_price)
                .filter(table.ticker == t, table.date < latest_date)
                .order_by(table.date.desc())
                .limit(1)
                .subquery()
            )
            # Select from the subquery to make it a compatible Selectable
            q = db.query(sub_q.c.ticker, sub_q.c.close_price)
            queries.append(q)
            
        if queries:
            from sqlalchemy import union_all
            # This returns (ticker, close_price) tuples
            try:
                prev_results = db.execute(union_all(*queries)).all()
                for row in prev_results:
                    # row is like ('VNINDEX', Decimal('1234.56'))
                    prev_map[row[0]] = float(row[1])
            except Exception as e:
                logger.debug(f"Batch prev fetch failed: {e}")

    # 5. Build Results
    for index_name in indices:
        latest = latest_map.get(index_name)
        if not latest:
            continue
            
        price = float(latest.close_price)
        prev_price = prev_map.get(index_name, price) # Default to current price if no prev (change=0)
        
        # Determine actual Ref price (Close of prev session)
        ref = prev_price 
        
        if price > 5000:
            price /= 1000
            ref /= 1000
            
        change = price - ref
        change_pct = (change / ref * 100) if ref > 0 else 0
        
        # Sparkline logic (unchanged)
        vn_now = _vn_now()
        market_open = _is_market_open(vn_now)
        sparkline = []
        if (not market_open) and index_name == "VNINDEX":
            sparkline = _get_intraday_from_db(db, index_name)
        if not sparkline:
            fallback_date = None
            fallback_close = None
            if isinstance(latest, models.HistoricalPrice) and latest.ticker == "VNINDEX":
                fallback_date = latest.date.strftime("%Y-%m-%d")
                fallback_close = float(latest.close_price)
            sparkline = get_intraday_sparkline(
                index_name,
                mem_get,
                mem_set,
                fallback_session_date=fallback_date,
                fallback_close=fallback_close,
            )
        
        val_raw = float(latest.value or 0)
        # Auto-detect scale for value: if > 1M => likely VND, convert to Billions
        value_billions = val_raw / (1e9 if val_raw > 1e6 else 1)

        fallback_results.append({
            "index": index_name,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(latest.volume or 0),
            "value": value_billions,
            "last_updated": latest.date.strftime("%Y-%m-%d"),
            "sparkline": sparkline,
            "source": "database"
        })
        
    return fallback_results

def get_market_summary_service(db: Session) -> list[dict]:
    """Fetch market summary (VNINDEX, VN30)."""
    indices = ["VNINDEX", "VN30"]
    cache_key = "market_summary_full_v10"
    
    # 0. Check cache
    cached = mem_get(cache_key)
    if cached:
        return cached

    results = []
    try:
        # 1. Fetch real-time Index from VPS (Priority Source)
        from adapters.vps_adapter import get_realtime_prices_vps
        vps_data = get_realtime_prices_vps(indices)
        
        # 2. Fetch Index from Vnstock (VCI price board) - Supplementary
        df_indices = Trading(source='VCI').price_board(indices)
        
        processed_indices = []
        if df_indices is not None and not df_indices.empty:
            for _, row in df_indices.iterrows():
                idx_name = row.get(('listing', 'symbol'))
                if idx_name:
                    processed = _process_market_row(row, idx_name, db, vps_data)
                    if processed:
                        results.append(processed)
                        processed_indices.append(idx_name)
        
        # 3. If any index is missing from VCI but exists in VPS, process it
        for idx in indices:
            if idx not in processed_indices and vps_data and idx in vps_data:
                # Create a pseudo-row for indices not in VCI board but in VPS
                # _process_market_row handles pd.Series() by using vps_data primarily
                processed = _process_market_row(pd.Series({('listing', 'symbol'): idx}), idx, db, vps_data)
                if processed:
                    results.append(processed)
                    processed_indices.append(idx)

    except Exception as e:
        logger.error(f"Market fetch failed: {e}")

    # 4. Final Fallback from DB if result is empty or missing indices
    if not results or len(results) < len(indices):
        logger.info("Falling back to database/history for missing indices")
        fallback_results = _get_market_fallback(db, indices)
        # Merge results, prioritizing live ones
        processed_names = [r['index'] for r in results]
        for f in fallback_results:
            if f['index'] not in processed_names:
                results.append(f)
            
    # Sort results to match requested order
    results.sort(key=lambda x: indices.index(x['index']) if x['index'] in indices else 99)
    
    if results:
        # Cache for 10 seconds
        mem_set(cache_key, results, 10)
        
    return results

def get_intraday_data_service(ticker: str, db: Session | None = None) -> list[dict]:
    """
    Fetch and normalize intraday data for a specific ticker.
    Supports VNINDEX, VN30, HNX30 and stocks.
    """
    
    # Use v4 cache key logic via get_intraday_sparkline adaptor
    db_sess = db or SessionLocal()
    try:
        vn_now = _vn_now()
        market_open = _is_market_open(vn_now)

        raw_sparkline = []
        if (not market_open) and ticker.upper() == "VNINDEX":
            raw_sparkline = _get_intraday_from_db(db_sess, ticker.upper())

        if not raw_sparkline:
            raw_sparkline = get_intraday_sparkline(ticker, mem_get, mem_set)
            if market_open and ticker.upper() == "VNINDEX" and raw_sparkline:
                _save_intraday_session(db_sess, ticker.upper(), raw_sparkline)
    finally:
        if db is None:
            db_sess.close()
    
    return raw_sparkline

# PLACEHOLDER for get_index_widget_data to ensure functionality
# Re-using logic consistent with get_market_summary_service but for single ticker
def get_index_widget_data(db: Session, ticker: str = "VNINDEX") -> dict:
    """
    Returns data in the nested format expected by VnindexWidget.js.
    Format: { series_points: [], session_info: {}, ref_level: float }
    """
    res = get_market_summary_service(db)
    for r in res:
        if r['index'] == ticker:
            price = r.get('price', 0)
            change = r.get('change', 0)
            ref_level = price - change
            
            return {
                "series_points": r.get("sparkline", []),
                "session_info": {
                    "index_name": r.get("index"),
                    "last_value": price,
                    "change_abs": change,
                    "change_pct": r.get("change_pct", 0),
                    "total_volume": r.get("volume", 0),
                    "total_value": r.get("value", 0) * 1_000_000_000  # Convert Billions to raw VND
                },
                "ref_level": ref_level
            }
    return {}
