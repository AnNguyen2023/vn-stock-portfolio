# services/performance_service.py
from __future__ import annotations

import math
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple, Optional

from sqlalchemy import cast, Date, desc
from sqlalchemy.orm import Session

import models
import crawler
from core.cache import cache
from core.redis_client import get_queue
from core.logger import logger


def _safe_float(x: Any, default: float = 0.0) -> float:
    """Safely converts any value to a finite float."""
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _d(x: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Safely converts any value to a non-NaN Decimal."""
    try:
        d = x if isinstance(x, Decimal) else Decimal(str(x))
        return default if getattr(d, "is_nan", lambda: False)() else d
    except Exception:
        return default


def _pick_current_price(price_info: Any, avg_price: Decimal) -> Decimal:
    """
    Returns the most relevant current price from info or fallback.
    """
    try:
        if isinstance(price_info, dict):
            mkt = _d(price_info.get("price", 0))
            ref = _d(price_info.get("ref", 0))
        else:
            mkt = _d(price_info or 0)
            ref = Decimal("0")

        if mkt > 0:
            return mkt
        if ref > 0:
            return ref
        return avg_price
    except Exception:
        return avg_price


def _net_cash_flow(db: Session, start: date, end: date | None = None) -> Decimal:
    """Calculates net cash flow (Deposits - Withdrawals) for a period."""
    q = db.query(models.CashFlow).filter(cast(models.CashFlow.created_at, Date) >= start)
    if end is not None:
        q = q.filter(cast(models.CashFlow.created_at, Date) <= end)

    net = Decimal("0")
    for f in q.all():
        if f.type == models.CashFlowType.DEPOSIT:
            net += _d(f.amount)
        elif f.type == models.CashFlowType.WITHDRAW:
            net -= _d(f.amount)
    return net


def _get_flows_map(db: Session, start: date, end: date) -> Dict[date, Decimal]:
    """Returns a map of {date: daily_net_flow} within a period."""
    flows = db.query(models.CashFlow).filter(
        cast(models.CashFlow.created_at, Date) >= start,
        cast(models.CashFlow.created_at, Date) <= end
    ).all()
    
    res = {}
    for f in flows:
        d_key = f.created_at.date()
        amt = _d(f.amount)
        if f.type == models.CashFlowType.WITHDRAW:
            amt = -amt
        res[d_key] = res.get(d_key, Decimal("0")) + amt
    return res


def _calc_profit_pct(curr_nav: Decimal, old_nav: Decimal, net_flow: Decimal) -> Tuple[float, float]:
    """
    Calculates Profit and ROR (Rate of Return) using the SSI formula.
    PnL = NAV_t - NAV_t-1 - NetFlow
    ROR = PnL / (NAV_t-1 + Max(0, NetFlow))
    """
    profit = curr_nav - old_nav - net_flow
    denom = old_nav + max(Decimal("0"), net_flow)
    pct = (profit / denom * 100) if denom > 0 else Decimal("0")
    return _safe_float(profit, 0.0), _safe_float(pct, 0.0)


@cache(ttl=300, key="dashboard_performance")
def calculate_twr_metrics(db: Session) -> Dict[str, Any]:
    """
    Calculates portfolio performance metrics for various time horizons (1D, 1M, 1Y, YTD).
    Uses DailySnapshot for historical comparison.
    """
    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {}

    holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
    tickers = [h.ticker for h in holdings]

    try:
        prices = crawler.get_current_prices(tickers) if tickers else {}
    except Exception as e:
        logger.error(f"Performance calculation pricing failed: {e}")
        prices = {}

    curr_stock_val = Decimal("0")
    for h in holdings:
        p_info = prices.get(h.ticker, {})
        curr_p = _pick_current_price(p_info, _d(h.average_price))
        curr_stock_val += curr_p * _d(h.total_volume)

    curr_nav = _d(asset.cash_balance) + _d(curr_stock_val)

    def calc_for_target(target_day: date) -> Tuple[float, float]:
        snap = (
            db.query(models.DailySnapshot)
            .filter(models.DailySnapshot.date <= target_day)
            .order_by(desc(models.DailySnapshot.date))
            .first()
        )
        old_nav = _d(snap.total_nav) if snap else Decimal("0")
        net_flow = _net_cash_flow(db, start=target_day)
        return _calc_profit_pct(curr_nav, old_nav, net_flow)

    today = date.today()
    ytd_day = date(today.year, 1, 1)

    p1d = calc_for_target(today - timedelta(days=1))
    p1m = calc_for_target(today - timedelta(days=30))
    p1y = calc_for_target(today - timedelta(days=365))
    pytd = calc_for_target(ytd_day)

    result = {
        "1d": {"val": _safe_float(p1d[0]), "pct": _safe_float(p1d[1])},
        "1m": {"val": _safe_float(p1m[0]), "pct": _safe_float(p1m[1])},
        "1y": {"val": _safe_float(p1y[0]), "pct": _safe_float(p1y[1])},
        "ytd": {"val": _safe_float(pytd[0]), "pct": _safe_float(pytd[1])},
    }

    # Asynchronously dispatch snapshot update
    try:
        q = get_queue()
        if q:
            from tasks import update_daily_snapshot_task
            q.enqueue(update_daily_snapshot_task)
    except Exception:
        pass

    return result


def _growth_key_fn(*args, **kwargs) -> str:
    period = kwargs.get("period") or (args[1] if len(args) > 1 else "1m")
    return f"chart_growth_v3_{period}"


@cache(ttl=300, key_fn=_growth_key_fn)
def growth_series(db: Session, period: str = "1m") -> Dict[str, Any]:
    """
    Generates time-series data for portfolio growth vs. individual assets and benchmarks.
    """
    end_date = date.today()
    period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = period_map.get(period, 30)
    start_date = end_date - timedelta(days=days)

    holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
    tickers = [h.ticker for h in holdings]
    fetch_tickers = tickers + ["VNINDEX"]

    raw_prices = (
        db.query(models.HistoricalPrice)
        .filter(
            models.HistoricalPrice.ticker.in_(fetch_tickers),
            models.HistoricalPrice.date >= start_date
        )
        .order_by(models.HistoricalPrice.date)
        .all()
    )

    price_map: Dict[date, Dict[str, Decimal]] = {}
    all_dates = set()
    for p in raw_prices:
        if p.date not in price_map:
            price_map[p.date] = {}
        price_map[p.date][p.ticker] = _d(p.close_price)
        all_dates.add(p.date)

    sorted_dates = sorted(list(all_dates))
    if not sorted_dates:
         return {"portfolio": [], "message": "No historical price data found for selected period."}

    ticker_base_prices: Dict[str, Decimal] = {}
    portfolio_daily_values = []
    first_valid_port_idx = -1
    
    # Forward-fill price map to handle missing data (prevents nosedive)
    last_known_prices: Dict[str, Decimal] = {}

    for i, day in enumerate(sorted_dates):
        day_prices = price_map[day]
        
        # 1. Update last known prices with today's available data
        for t in fetch_tickers:
            p = day_prices.get(t, Decimal("0"))
            if p > 0:
                last_known_prices[t] = p
            elif t in last_known_prices:
                # Fallback to previous day's price if missing
                day_prices[t] = last_known_prices[t]

        # 2. Capture Base Prices (First non-zero occurrence)
        for t in fetch_tickers:
            price = last_known_prices.get(t, Decimal("0"))
            if t not in ticker_base_prices and price > 0:
                ticker_base_prices[t] = price

        # 3. Calculate Portfolio Value
        val_t = Decimal("0")
        for h in holdings:
            # Use forward-filled price
            p = day_prices.get(h.ticker, Decimal("0"))
            if p == 0:
                 p = last_known_prices.get(h.ticker, Decimal("0"))
            val_t += _d(h.total_volume) * p
        portfolio_daily_values.append(val_t)
        
        if first_valid_port_idx == -1 and val_t > 0:
            first_valid_port_idx = i

    base_nav = portfolio_daily_values[first_valid_port_idx] if first_valid_port_idx != -1 else Decimal("0")

    series: List[Dict[str, Any]] = []
    for i, day in enumerate(sorted_dates):
        day_prices = price_map[day]
        item = {"date": day.strftime("%Y-%m-%d")}
        
        # 1. PORTFOLIO GROWTH
        val_t = portfolio_daily_values[i]
        p_growth = Decimal("0")
        if base_nav > 0 and i >= first_valid_port_idx:
            p_growth = (val_t - base_nav) / base_nav * 100
        item["PORTFOLIO"] = round(_safe_float(p_growth), 2)
        
        # 2. TICKER GROWTH (Indices & Stocks)
        for t in fetch_tickers:
            t_growth = Decimal("0")
            # Use forward-filled price for consistency
            curr_p = day_prices.get(t, Decimal("0"))
            base_p = ticker_base_prices.get(t, Decimal("0"))
            
            if base_p > 0 and curr_p > 0:
                t_growth = (curr_p - base_p) / base_p * 100
            item[t] = round(_safe_float(t_growth), 2)

        series.append(item)

    return {
        "portfolio": series,
        "base_date": sorted_dates[0].strftime("%Y-%m-%d"),
        "base_nav": _safe_float(base_nav),
        "data_points": len(series),
    }


def nav_history(db: Session, start_date: date | None = None, end_date: date | None = None, limit: int = 30) -> Dict[str, Any]:
    """
    Returns historical NAV records with performance summary metrics.
    """
    query = db.query(models.DailySnapshot)
    if start_date:
        search_start = start_date - timedelta(days=7)
        query = query.filter(models.DailySnapshot.date >= search_start)
    if end_date:
        query = query.filter(models.DailySnapshot.date <= end_date)
    
    snaps = query.order_by(desc(models.DailySnapshot.date)).all()
    if not start_date:
        snaps = snaps[:limit]

    if snaps:
        flows_map = _get_flows_map(db, snaps[-1].date, snaps[0].date)
    else:
        flows_map = {}

    res: List[Dict[str, Any]] = []
    total_r_plus_1 = 1.0
    total_net_flow = Decimal("0")
    
    for i in range(len(snaps)):
        curr = snaps[i]
        if start_date and curr.date < start_date:
            continue
        curr_nav = _d(curr.total_nav)
        
        if i + 1 < len(snaps):
            prev = snaps[i + 1]
            prev_nav = _d(prev.total_nav)
            net_flow = flows_map.get(curr.date, Decimal("0"))
            profit, pct = _calc_profit_pct(curr_nav, prev_nav, net_flow)
            if math.isfinite(pct):
                total_r_plus_1 *= (1 + pct / 100)
            total_net_flow += net_flow
            change = curr_nav - prev_nav - net_flow
        else:
            change = Decimal("0")
            pct = 0.0

        res.append({
            "date": curr.date.strftime("%Y-%m-%d"),
            "nav": _safe_float(curr_nav),
            "change": _safe_float(change),
            "pct": pct,
        })
    
    perf_pct = (total_r_plus_1 - 1) * 100
    # Calculate visible summary metrics to match the table exactly
    visible_start_nav = res[-1]["nav"] if res else 0
    visible_end_nav = res[0]["nav"] if res else 0
    visible_profit = sum(item["change"] for item in res)
    
    # Derive flow to ensure accounting identity: End = Start + Flow + Profit => Flow = End - Start - Profit
    visible_net_flow = _d(visible_end_nav) - _d(visible_start_nav) - _d(visible_profit)

    summary = {
        "start_nav": visible_start_nav,
        "end_nav": visible_end_nav,
        "net_flow": _safe_float(visible_net_flow),
        "total_profit": _safe_float(visible_profit),
        "total_performance_pct": _safe_float(perf_pct)
    }

    return {"history": res, "summary": summary}
