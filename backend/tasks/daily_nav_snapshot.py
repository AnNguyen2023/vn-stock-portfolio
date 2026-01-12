"""
tasks/daily_nav_snapshot.py
Background task to automatically save NAV snapshot after market close (15h)
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from core.db import SessionLocal
from core.logger import logger
import models
import requests
import os


def save_daily_nav_snapshot():
    """
    Save today's NAV to database for chart display.
    Should be called after market close (after 15h).
    """
    try:
        # Get current NAV from portfolio service
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        response = requests.get(f"{base_url}/portfolio", timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch portfolio data: {response.status_code}")
            return
        
        data = response.json().get("data")
        if not data:
            logger.error("No portfolio data returned")
            return
        
        current_nav = Decimal(str(data["total_nav"]))
        today = date.today()
        
        with SessionLocal() as db:
            # Check if today's snapshot already exists
            existing = db.query(models.DailySnapshot).filter(
                models.DailySnapshot.date == today
            ).first()
            
            if existing:
                # Update existing
                existing.total_nav = current_nav
                logger.info(f"Updated NAV snapshot for {today}: {current_nav:,.2f}")
            else:
                # Create new
                snapshot = models.DailySnapshot(
                    date=today,
                    total_nav=current_nav
                )
                db.add(snapshot)
                logger.info(f"Created NAV snapshot for {today}: {current_nav:,.2f}")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"Failed to save daily NAV snapshot: {e}")


def backfill_missing_nav_snapshots(days_back: int = 7):
    """
    Backfill missing NAV snapshots for the last N days.
    This ensures we have continuous data for chart display.
    """
    try:
        with SessionLocal() as db:
            today = date.today()
            
            for i in range(days_back, 0, -1):
                target_date = today - timedelta(days=i)
                
                # Check if snapshot exists
                existing = db.query(models.DailySnapshot).filter(
                    models.DailySnapshot.date == target_date
                ).first()
                
                if existing:
                    continue  # Already have data for this date
                
                # Try to calculate NAV for this date
                # This is a simplified version - you might need more complex logic
                # to accurately reconstruct historical NAV
                logger.info(f"Missing NAV snapshot for {target_date}, skipping backfill (requires historical transaction data)")
                
    except Exception as e:
        logger.error(f"Failed to backfill NAV snapshots: {e}")


def should_run_daily_snapshot() -> bool:
    """
    Check if we should run the daily snapshot now.
    Returns True if:
    - Current time is after 15:00
    - Today's snapshot doesn't exist yet
    """
    now = datetime.now()
    
    # Only run after market close (15:00)
    if now.hour < 15:
        return False
    
    # Check if today's snapshot already exists
    with SessionLocal() as db:
        existing = db.query(models.DailySnapshot).filter(
            models.DailySnapshot.date == date.today()
        ).first()
        
        return existing is None
