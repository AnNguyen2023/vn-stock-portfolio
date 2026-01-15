from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

import models
import crawler
from core.redis_client import cache_get, cache_set
from core.logger import logger

CACHE_KEY = "dashboard:portfolio"


def _d(x: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Safely converts any value to Decimal."""
    try:
        return x if isinstance(x, Decimal) else Decimal(str(x))
    except Exception:
        return default


def _pick_price(price_info: Any, fallback: Decimal) -> Tuple[Decimal, Decimal]:
    """
    Determines current and reference prices from API data with fallbacks.

    Args:
        price_info (Any): Price data (dict or number).
        fallback (Decimal): Fallback price if API data is invalid.

    Returns:
        Tuple[Decimal, Decimal]: (current_price, reference_price).
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
    """
    Lazily calculates and applies overnight interest (0.5% p.a.) to cash balance.
    """
    today = date.today()
    if not asset.last_interest_calc_date:
        asset.last_interest_calc_date = today
        db.commit()
        return

    if asset.last_interest_calc_date >= today:
        return

    days = (today - asset.last_interest_calc_date).days
    # Annual rate 0.5% / 360 days
    interest = _d(asset.cash_balance) * (Decimal("0.005") / Decimal("360")) * Decimal(days)

    if interest > Decimal("0.01"):
        asset.cash_balance = _d(asset.cash_balance) + interest
        db.add(
            models.CashFlow(
                type=models.CashFlowType.INTEREST,
                amount=interest,
                description=f"Overnight interest ({days} days)",
            )
        )
        asset.last_interest_calc_date = today
        logger.info(f"Applied interest: {interest:,.2f} VNĐ for {days} days.")
        db.commit()


from core.cache import cache

@cache(ttl=60, key=CACHE_KEY)
def calculate_portfolio(db: Session) -> Dict[str, Any]:
    """
    Calculates detailed portfolio metrics including real-time valuation, 
    profit/loss, and NAV. Results are cached for 60 seconds.
    """
    asset = db.query(models.AssetSummary).first()
    if not asset:
        return {"cash_balance": 0, "total_stock_value": 0, "total_nav": 0, "holdings": []}

    # 1. Update interest
    _lazy_interest(asset, db)

    # 2. Process pending dividends
    try:
        from services.trading_service import process_pending_dividends
        process_pending_dividends(db)
    except Exception as e:
        logger.error(f"Failed to process pending dividends: {e}")

    # 3. Process active holdings
    holdings = (
        db.query(models.TickerHolding)
        .filter(models.TickerHolding.total_volume > 0)
        .all()
    )

    tickers = [h.ticker for h in holdings]
    try:
        prices = crawler.get_current_prices(tickers) if tickers else {}
    except Exception as e:
        logger.error(f"Failed to fetch real-time prices for portfolio: {e}")
        prices = {}

    total_stock_value = Decimal("0")
    items = []

    for h in holdings:
        price_info = prices.get(h.ticker, {})
        curr_p, ref_p = _pick_price(price_info, _d(h.average_price))
        
        actual_ref = ref_p if ref_p > 0 else curr_p
        ceiling_p = _d(price_info.get("ceiling", 0)) if isinstance(price_info, dict) else Decimal("0")
        floor_p = _d(price_info.get("floor", 0)) if isinstance(price_info, dict) else Decimal("0")

        curr_val = curr_p * _d(h.total_volume)
        profit_loss = curr_val - (_d(h.average_price) * _d(h.total_volume))
        profit_pct = ((curr_p / _d(h.average_price)) - 1) * 100 if _d(h.average_price) > 0 else Decimal("0")
        today_pct = ((curr_p / actual_ref) - 1) * 100 if actual_ref > 0 else Decimal("0")

        total_stock_value += curr_val

        from services.market_service import get_trending_indicator
        trending = get_trending_indicator(h.ticker, db)

        # Check for PENDING dividends
        div_rec = db.query(models.DividendRecord).filter(
            models.DividendRecord.ticker == h.ticker,
            models.DividendRecord.status == models.CashFlowStatus.PENDING
        ).order_by(models.DividendRecord.payment_date.asc()).first()
        
        dividend_data = None
        if div_rec:
            dividend_data = {
                "type": div_rec.type.value,
                "payment_date": div_rec.payment_date.strftime("%Y-%m-%d") if div_rec.payment_date else None
            }

        items.append(
            {
                "ticker": h.ticker,
                "volume": float(_d(h.total_volume)),
                "available": float(_d(h.available_volume)),
                "avg_price": float(_d(h.average_price) / 1000),
                "current_price": float(curr_p / 1000),
                "ref_price": float(actual_ref / 1000),
                "ceiling_price": float(ceiling_p / 1000),
                "floor_price": float(floor_p / 1000),
                "today_change_percent": float(today_pct),
                "profit_loss": float(profit_loss),
                "profit_percent": float(profit_pct),
                "current_value": float(curr_val),
                "trending": trending,
                "has_dividend": div_rec is not None,
                "dividend_data": dividend_data,
            }
        )

    result = {
        "cash_balance": float(_d(asset.cash_balance)),
        "total_stock_value": float(total_stock_value),
        "total_nav": float(_d(asset.cash_balance) + total_stock_value),
        "holdings": items,
        "alerts": []
    }

    # 4. Check for approaching Rights Registration
    try:
        approaching_rights = db.query(models.DividendRecord).filter(
            models.DividendRecord.type == models.CashFlowType.RIGHTS_ISSUE,
            models.DividendRecord.status == models.CashFlowStatus.PENDING,
            models.DividendRecord.register_date <= date.today() + timedelta(days=5)
        ).all()
        
        today = date.today()
        for r in approaching_rights:
            cost = r.expected_value * (r.purchase_price or Decimal("0"))
            if _d(asset.cash_balance) < cost:
                result["alerts"].append({
                    "type": "REGISTRATION_WARNING",
                    "ticker": r.ticker,
                    "message": f"Cần nạp tiền để đảm bảo quyền mua {r.ticker} ({int(r.expected_value):,} CP)",
                    "date": r.register_date.strftime("%Y-%m-%d")
                })
    except Exception as e:
        logger.error(f"Error checking rights alerts: {e}")

    return result


def get_ticker_profit(db: Session, ticker: str) -> Dict[str, Any]:
    """
    Returns lifetime profit summary (realized + unrealized) for a specific ticker.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return {"ticker": "", "realized_profit": 0, "unrealized_profit": 0}

    # Realized Profit
    rows = db.query(models.RealizedProfit).filter(models.RealizedProfit.ticker == ticker).all()
    realized = sum((_d(r.net_profit) for r in rows), Decimal("0"))

    # Unrealized (from current holding)
    holding = db.query(models.TickerHolding).filter(models.TickerHolding.ticker == ticker).first()
    unrealized = Decimal("0")
    curr_p = Decimal("0")
    
    if holding and _d(holding.total_volume) > 0:
        try:
            prices = crawler.get_current_prices([ticker])
        except Exception as e:
            logger.debug(f"Failed to fetch current price for unrealized profit of {ticker}: {e}")
            prices = {}
        
        curr_p, _ = _pick_price(prices.get(ticker, {}), _d(holding.average_price))
        unrealized = (curr_p * _d(holding.total_volume)) - (_d(holding.average_price) * _d(holding.total_volume))

    return {
        "ticker": ticker,
        "realized_profit": float(realized),
        "unrealized_profit": float(unrealized),
        "current_price": float(curr_p / 1000) if curr_p > 0 else 0,
        "trades_count": len(rows),
    }
