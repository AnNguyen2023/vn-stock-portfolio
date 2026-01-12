"""
core/scheduler.py
Background scheduler for periodic tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.logger import logger
from tasks.daily_nav_snapshot import save_daily_nav_snapshot, should_run_daily_snapshot


scheduler = BackgroundScheduler()


def init_scheduler():
    """
    Initialize and start the background scheduler.
    Runs daily NAV snapshot at 15:05 every day (5 minutes after market close).
    """
    try:
        # Schedule daily NAV snapshot at 15:05 every day
        scheduler.add_job(
            func=save_daily_nav_snapshot,
            trigger=CronTrigger(hour=15, minute=5),
            id='daily_nav_snapshot',
            name='Save daily NAV snapshot after market close',
            replace_existing=True
        )
        
        # Also check on startup if we need to save today's snapshot
        # (in case server was down at 15:05)
        if should_run_daily_snapshot():
            logger.info("Running missed daily NAV snapshot on startup")
            save_daily_nav_snapshot()
        
        scheduler.start()
        logger.info("✅ Background scheduler started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")


def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Background scheduler shut down")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")
