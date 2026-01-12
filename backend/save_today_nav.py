"""
Quick script to save today's NAV to database
Run this after market close (after 15h) each day
"""
from datetime import date
from decimal import Decimal
from core.db import SessionLocal
import models
import requests

# Get current NAV from API
response = requests.get("http://localhost:8000/portfolio")
data = response.json()["data"]
current_nav = Decimal(str(data["total_nav"]))

today = date.today()

with SessionLocal() as db:
    # Check if today's snapshot already exists
    existing = db.query(models.DailySnapshot).filter(
        models.DailySnapshot.date == today
    ).first()
    
    if existing:
        # Update
        existing.total_nav = current_nav
        print(f"✅ Updated NAV for {today}: {current_nav:,.2f}")
    else:
        # Create new
        snapshot = models.DailySnapshot(
            date=today,
            total_nav=current_nav
        )
        db.add(snapshot)
        print(f"✅ Created NAV snapshot for {today}: {current_nav:,.2f}")
    
    db.commit()
    print("\n✅ Done! Refresh your browser to see the updated chart.")
