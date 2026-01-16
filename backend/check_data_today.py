from sqlalchemy import text
from datetime import date
from core.db import engine # Use the actual engine from the app

today = '2026-01-16' # Hardcoded
print(f"--- CHECKING DATA FOR: {today} ---")

try:
    with engine.connect() as conn:
        # Get Holdings
        holdings_q = text("SELECT ticker FROM ticker_holdings WHERE total_volume > 0")
        holdings = [r.ticker for r in conn.execute(holdings_q).fetchall()]
        expected_tickers = holdings + ["VNINDEX"] # Add indices if needed, e.g. VN30

        print(f"Expected Tickers ({len(expected_tickers)}): {expected_tickers}")

        # Check Historical Prices
        hp_query = text(f"SELECT ticker, close_price FROM historical_prices WHERE date = '{today}'")
        hp_rows = conn.execute(hp_query).fetchall()
        present_tickers = [r.ticker for r in hp_rows]
        
        print(f"\n[Historical Prices] Found {len(present_tickers)} records.")
        missing_tickers = set(expected_tickers) - set(present_tickers)
        if missing_tickers:
            print(f"❌ MISSING Data for: {missing_tickers}")
        else:
            print("✅ All expected tickers present.")
            
        # Check Daily Snapshots
        ds_query = text(f"SELECT total_nav FROM daily_snapshots WHERE date = '{today}'")
        ds_rows = conn.execute(ds_query).fetchall()
        print(f"\n[Daily Snapshots] Total Records: {len(ds_rows)}")
        if ds_rows:
            print(f"Snapshot found! NAV: {ds_rows[0].total_nav}")
        else:
            print("❌ MISSING Daily Snapshot for today.")

except Exception as e:
    print(f"Error: {e}")

except Exception as e:
    print(f"Error: {e}")
