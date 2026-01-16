from datetime import date
from sqlalchemy.orm import Session
from core.db import SessionLocal
from core.logger import logger
import models
import crawler
from tasks.daily_nav_snapshot import save_daily_nav_snapshot

def force_sync_price_today():
    today = date.today()
    print(f"--- FORCE SYNC FOR {today} ---")
    
    db: Session = SessionLocal()
    try:
        # 1. Get List of Tickers
        holdings = db.query(models.TickerHolding).filter(models.TickerHolding.total_volume > 0).all()
        tickers = [h.ticker for h in holdings]
        # Add Indices
        tickers.extend(["VNINDEX", "VN30"])
        
        print(f"Fetching data for: {tickers}")
        
        # 2. Fetch Prices (Realtime/Close)
        # Using crawler.get_current_prices which usually gets latest available
        prices = crawler.get_current_prices(tickers)
        
        # 3. Save to HistoricalPrice
        count = 0
        for t, info in prices.items():
            if not info:
                continue
            
            # Extract price
            try:
                if isinstance(info, dict):
                    price = float(info.get("price", 0))
                    vol = float(info.get("volume", 0))
                else:
                    price = float(info)
                    vol = 0
            except:
                continue
                
            if price <= 0:
                continue
                
            # Upsert
            existing = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.ticker == t,
                models.HistoricalPrice.date == today
            ).first()
            
            if existing:
                existing.close_price = price
                existing.volume = vol
                print(f"Updated {t}: {price}")
            else:
                new_rec = models.HistoricalPrice(
                    ticker=t,
                    date=today,
                    close_price=price,
                    volume=vol
                )
                db.add(new_rec)
                print(f"Inserted {t}: {price}")
            count += 1
            
        db.commit()
        print(f"✅ Synced {count} tickers.")
        
        # 4. Create Snapshot
        print("Creating Daily Snapshot...")
        save_daily_nav_snapshot()
        print("✅ Snapshot created/updated.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    force_sync_price_today()
