
# services/market_service.py
# This file is now a facade for the modularized structure in services/market/

from services.market.data_processor import (
    get_trending_indicator,
    _process_single_ticker,
    get_trending_indicators_batch
)
from services.market.sync_tasks import (
    seed_index_data_task,
    sync_portfolio_history_task,
    sync_historical_task,
    sync_securities_task
)
from services.market.watchlist_service import (
    get_watchlist_detail_service,
    invalidate_watchlist_detail_cache
)
from services.market.market_summary import (
    get_market_summary_service,
    get_index_widget_data,
    get_intraday_data_service
)
from services.market.test_data import (
    seed_test_data_task,
    update_test_price,
    get_test_market_summary_service
)
