from dotenv import load_dotenv
load_dotenv("backend/.env")

from core.db import engine, Base
from models import HistoricalPrice
import sqlalchemy

def migrate():
    print("--- DROPPING historical_prices table ---")
    try:
        HistoricalPrice.__table__.drop(engine)
        print("Dropped successfully.")
    except Exception as e:
        print(f"Drop failed (maybe not exist): {e}")

    print("--- RE-CREATING tables ---")
    # Base.metadata.create_all checks checkfirst=True by default
    Base.metadata.create_all(bind=engine)
    print("Re-creation complete.")

    # verify
    inspector = sqlalchemy.inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('historical_prices')]
    print(f"Columns in historical_prices: {columns}")
    if 'volume' in columns:
        print("SUCCESS: Volume column exists!")
    else:
        print("FAILURE: Volume column missing!")

if __name__ == "__main__":
    migrate()
