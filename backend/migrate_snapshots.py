
from core.db import engine, SessionLocal
from sqlalchemy import text
import models

def migrate_snapshots():
    print("Adding created_at column to daily_snapshots...")
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE daily_snapshots ADD COLUMN created_at TIMESTAMP"))
            conn.commit()
            print("Column added.")
    except Exception as e:
        print(f"Column might already exist or error: {e}")

    with SessionLocal() as db:
        snaps = db.query(models.DailySnapshot).all()
        for s in snaps:
            # Set default to 15:00 (Market Close) for past snapshots
            from datetime import datetime, time
            s.created_at = datetime.combine(s.date, time(15, 0))
        db.commit()
        print(f"Updated {len(snaps)} snapshots with default 15:00 timestamp.")

if __name__ == "__main__":
    migrate_snapshots()
