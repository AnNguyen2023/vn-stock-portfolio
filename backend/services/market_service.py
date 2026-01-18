
# services/market_service.py
# This file is now a facade for the modularized structure in services/market/

from services.market import (
    mem_get, 
    mem_set, 
    invalidate_watchlist_detail_cache,
    get_trending_indicator,
    seed_index_data_task, 
    sync_portfolio_history_task, 
    sync_historical_task, 
    sync_securities_task,
    get_watchlist_detail_service,
    seed_test_data_task, 
    update_test_price, 
    get_test_market_summary_service,
    get_market_summary_service, 
    get_intraday_data_service,
    get_index_widget_data
)
