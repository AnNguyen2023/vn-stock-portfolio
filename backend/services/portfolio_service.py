# services/portfolio_service.py
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy.orm import Session

import models
import crawler
from core.redis_client import cache_get, cache_set


CACHE_KEY = "dashboard:portfolio"


def _d(x: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return x if isinstance(x, Decimal) else Decimal(str(x))
    except Exception:
        return default


def _pick_price(price_info: Any, fallback: Decimal) -> tuple[Decimal, Decimal]:
    """
    Return (curr_price, ref_price).
    price_info: dict {"price":..,"ref":..} hoặc số.
    curr_price ưu tiên market>0, else ref>0, else fallback.
    """
    if isinstance(price_info, dict):
        mkt = _d(price_info.get("price", 0))
        ref = _d(price_info.get("ref", 0))
    else:
        mkt = _d(price_info or 0)
        ref = Decimal("0")

    curr = mkt if mkt > 0 else (ref if ref > 0 else fallback)
    return curr, ref


def _lazy_interest(asset: models.AssetSummary, db: Session) -> None:
    """Lãi qua đêm 0.5%/năm, lazy update."""
    today = date.today()
    if not asset.last_interest_calc_date:
        asset.last_interest_calc_date = today
        db.commit()
        return

    if asset.last_interest_calc_date >= today:
        return

    days = (today - asset.last_interest_calc_date).days
    interest = _d(asset.cash_balance) * (Decimal("0.005") / Decimal("360")) * Decimal(days)

    if interest > Decimal("0.01"):  # min 10đ
        asset.cash_balance = _d(asset.cash_balance) + interest
        db.add(
            models.CashFlow(
                type=models.CashFlowType.INTEREST,
                amount=interest,
                description=f"Lãi qua đêm {days} ngày",
            )
        )
        asset.last_interest_calc_date = today
        db.commit()


def calculate_portfolio(db: Session) -> Dict[str, Any]:
    """API-compatible với /portfolio (router gọi thẳng)."""
    cached = cache_get(CACHE_KEY)
    if cached:
        return cached

    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {"cash_balance": 0, "total_stock_value": 0, "total_nav": 0, "holdings": []}

    # A) lãi qua đêm
    _lazy_interest(asset, db)

    # B) holdings + giá realtime
    holdings = (
        db.query(models.TickerHolding)
        .filter(models.TickerHolding.total_volume > 0)
        .all()
    )

    tickers = [h.ticker for h in holdings]
    try:
        prices = crawler.get_current_prices(tickers) if tickers else {}
    except Exception:
        prices = {}

    total_stock_value = Decimal("0")
    items = []

    for h in holdings:
        curr_p, ref_p = _pick_price(prices.get(h.ticker, {}), _d(h.average_price))
        actual_ref = ref_p if ref_p > 0 else curr_p

        curr_val = curr_p * _d(h.total_volume)
        profit_loss = curr_val - (_d(h.average_price) * _d(h.total_volume))
        profit_pct = ((curr_p / _d(h.average_price)) - 1) * 100 if _d(h.average_price) > 0 else Decimal("0")
        today_pct = ((curr_p / actual_ref) - 1) * 100 if actual_ref > 0 else Decimal("0")

        total_stock_value += curr_val

        items.append(
            {
                "ticker": h.ticker,
                "volume": float(_d(h.total_volume)),
                "available": float(_d(h.available_volume)),
                # GIỮ ĐÚNG format cũ: chia 1000 để hiển thị theo giá "k"
                "avg_price": float(_d(h.average_price) / 1000),
                "current_price": float(curr_p / 1000),
                "today_change_percent": float(today_pct),
                "profit_loss": float(profit_loss),
                "profit_percent": float(profit_pct),
                "current_value": float(curr_val),
            }
        )

    result = {
        "cash_balance": float(_d(asset.cash_balance)),
        "total_stock_value": float(total_stock_value),
        "total_nav": float(_d(asset.cash_balance) + total_stock_value),
        "holdings": items,
    }

    # cache 60s
    cache_set(CACHE_KEY, result, ex=60)
    return result


def get_ticker_profit(db: Session, ticker: str) -> Dict[str, Any]:
    """API /ticker-lifetime-profit/{ticker}: trả realized + unrealized cơ bản."""
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return {"ticker": "", "realized_profit": 0, "unrealized_profit": 0}

    # realized
    rows = db.query(models.RealizedProfit).filter(models.RealizedProfit.ticker == ticker).all()
    realized = sum((_d(r.net_profit) for r in rows), Decimal("0"))

    # unrealized (nếu còn nắm giữ)
    holding = db.query(models.TickerHolding).filter(models.TickerHolding.ticker == ticker).first()
    unrealized = Decimal("0")
    curr_p = Decimal("0")
    if holding and _d(holding.total_volume) > 0:
        try:
            prices = crawler.get_current_prices([ticker])
        except Exception:
            prices = {}
        curr_p, _ = _pick_price(prices.get(ticker, {}), _d(holding.average_price))
        unrealized = (curr_p * _d(holding.total_volume)) - (_d(holding.average_price) * _d(holding.total_volume))

    return {
        "ticker": ticker,
        "realized_profit": float(realized),
        "unrealized_profit": float(unrealized),
        "current_price": float(curr_p / 1000) if curr_p > 0 else 0,
        "trades": len(rows),
    }
