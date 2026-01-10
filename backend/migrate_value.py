from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load env variables to get DATABASE_URL
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found")
    exit(1)

engine = create_engine(DATABASE_URL)

def run_migration():
    print("--- MIGRATING DATABASE: ADDING 'value' COLUMN ---")
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            # Check if column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='historical_prices' AND column_name='value'"))
            if result.fetchone():
                print("Column 'value' already exists.")
            else:
                print("Adding column 'value'...")
                conn.execute(text("ALTER TABLE historical_prices ADD COLUMN value NUMERIC DEFAULT 0"))
                print("Success!")
        except Exception as e:
            print(f"Migration Error: {e}")

if __name__ == "__main__":
    run_migration()
