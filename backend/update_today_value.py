"""
Quick script to update today's market value in database
"""
from datetime import date
from decimal import Decimal
from core.db import SessionLocal
import models

# Today's actual values from market
today_values = {
    "VNINDEX": 41644.62,  # billions
    "VN30": 0,  # Update if you have this
    "HNX30": 0,  # Update if you have this
}

with SessionLocal() as db:
    today = date.today()
    
    for ticker, value_billions in today_values.items():
        if value_billions == 0:
            continue
            
        # Find or create today's record
        record = db.query(models.HistoricalPrice).filter(
            models.HistoricalPrice.ticker == ticker,
            models.HistoricalPrice.date == today
        ).first()
        
        if record:
            # Update existing
            record.value = Decimal(str(value_billions))
            print(f"✅ Updated {ticker} value: {value_billions} Tỷ")
        else:
            # Create new (you'll need to add price and volume too)
            print(f"⚠️  No record found for {ticker} on {today}")
            print(f"   Please run /seed-index API first to create the record")
    
    db.commit()
    print("\n✅ Database updated!")
