"""
core/scheduler.py
Background scheduler for periodic tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.logger import logger
from core.data_engine import DataEngine


scheduler = BackgroundScheduler()


def init_scheduler():
    """
    Initialize and start the background scheduler.
    """
    try:
        # 1. Start EOD process daily at 15:05
        scheduler.add_job(
            func=DataEngine.end_of_day_sync,
            trigger=CronTrigger(hour=15, minute=5),
            id='eod_sync',
            name='Daily Data Sync and NAV Snapshot',
            replace_existing=True
        )
        
        # 2. Startup Self-Healing
        # (This is better called here as part of system readiness)
        DataEngine.startup_sync()
        
        scheduler.start()
        logger.info("✅ Background scheduler and DataEngine started")
        
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
