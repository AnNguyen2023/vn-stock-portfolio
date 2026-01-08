# services/performance_service.py
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Tuple
import math

from sqlalchemy import cast, Date, desc
from sqlalchemy.orm import Session

import models
import crawler
from core.cache import cache
from core.redis_client import get_queue


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _d(x: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        d = x if isinstance(x, Decimal) else Decimal(str(x))
        return default if getattr(d, "is_nan", lambda: False)() else d
    except Exception:
        return default


def _pick_current_price(price_info: Any, avg_price: Decimal) -> Decimal:
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


def _calc_profit_pct(curr_nav: Decimal, old_nav: Decimal, net_flow: Decimal) -> Tuple[float, float]:
    profit = curr_nav - (old_nav + net_flow)
    denom = old_nav + net_flow
    pct = (profit / denom * 100) if denom > 0 else Decimal("0")
    return _safe_float(profit, 0.0), _safe_float(pct, 0.0)


@cache(ttl=300, key="dashboard_performance")
def calculate_twr_metrics(db: Session) -> Dict[str, Any]:
    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {}

    holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
    tickers = [h.ticker for h in holdings]

    try:
        prices = crawler.get_current_prices(tickers) if tickers else {}
    except Exception:
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

    # enqueue snapshot update (nếu có worker chạy)
    try:
        q = get_queue()
        if q:
            from tasks import update_daily_snapshot_task  # optional
            q.enqueue(update_daily_snapshot_task)
    except Exception:
        pass

    return result


def _growth_key_fn(*args, **kwargs) -> str:
    period = kwargs.get("period") or (args[1] if len(args) > 1 else "1m")
    return f"chart_growth_{period}"


@cache(ttl=300, key_fn=_growth_key_fn)
def growth_series(db: Session, period: str = "1m") -> Dict[str, Any]:
    end_date = date.today()
    period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = period_map.get(period, 30)
    start_date = end_date - timedelta(days=days)

    # 1. Lấy dữ liệu Portfolio Snapshots
    snaps = (
        db.query(models.DailySnapshot)
        .filter(models.DailySnapshot.date >= start_date)
        .order_by(models.DailySnapshot.date)
        .all()
    )

    if not snaps or len(snaps) < 2:
        return {"portfolio": [], "message": "Chưa đủ dữ liệu lịch sử (cần ít nhất 2 ngày)"}

    # 2. Lấy dữ liệu benchmark VNINDEX
    indices = (
        db.query(models.HistoricalPrice)
        .filter(models.HistoricalPrice.ticker == "VNINDEX", models.HistoricalPrice.date >= start_date)
        .order_by(models.HistoricalPrice.date)
        .all()
    )
    index_map = {idx.date: _d(idx.close_price) for idx in indices}

    base_nav = _d(snaps[0].total_nav)
    # Tìm giá trị VNINDEX tại ngày bắt đầu của snaps để làm mốc 0%
    base_index = index_map.get(snaps[0].date)
    
    # Nếu ngày đầu của snaps không có VNINDEX, tìm ngày gần nhất trước đó hoặc sau đó
    if base_index is None and indices:
        base_index = _d(indices[0].close_price)

    series: List[Dict[str, Any]] = []
    for s in snaps:
        # Tính % Portfolio Growth (TWR-like simplified)
        s_nav = _d(s.total_nav)
        net_flow = _net_cash_flow(db, start=snaps[0].date, end=s.date)
        adjusted_base = base_nav + net_flow
        p_growth = (s_nav - adjusted_base) / adjusted_base * 100 if adjusted_base > 0 else Decimal("0")

        # Tính % VNINDEX Growth
        curr_idx = index_map.get(s.date)
        v_growth = (curr_idx - base_index) / base_index * 100 if (base_index and curr_idx) else Decimal("0")

        series.append({
            "date": s.date.strftime("%Y-%m-%d"),
            "PORTFOLIO": round(_safe_float(p_growth), 2), # FIX: key 'PORTFOLIO' cho frontend
            "VNINDEX": round(_safe_float(v_growth), 2)    # ADD: benchmark
        })

    return {
        "portfolio": series,
        "base_date": snaps[0].date.strftime("%Y-%m-%d"),
        "base_nav": _safe_float(base_nav),
        "data_points": len(series),
    }


def nav_history(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    snaps = db.query(models.DailySnapshot).order_by(desc(models.DailySnapshot.date)).limit(limit).all()

    res: List[Dict[str, Any]] = []
    for i in range(len(snaps) - 1):
        curr, prev = snaps[i], snaps[i + 1]
        curr_nav = _d(curr.total_nav)
        prev_nav = _d(prev.total_nav)
        change = curr_nav - prev_nav
        pct = (change / prev_nav * 100) if prev_nav > 0 else Decimal("0")

        res.append(
            {
                "date": curr.date.strftime("%Y-%m-%d"),
                "nav": _safe_float(curr_nav),
                "change": _safe_float(change),
                "pct": _safe_float(pct),
            }
        )
    return res
