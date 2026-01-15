
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env", override=True)
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit(1)

# Ensure psycopg driver is used
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url)

def run_sql(conn, sql):
    try:
        conn.execute(text(sql))
        conn.commit()
    except Exception as e:
        conn.rollback()
        # print(f"Command failed: {sql[:50]}... | Error: {e}")

with engine.connect() as conn:
    print("Checking and updating schema...")
    
    run_sql(conn, "ALTER TABLE cash_flow ADD COLUMN status VARCHAR(50) DEFAULT 'COMPLETED'")
    run_sql(conn, "ALTER TABLE cash_flow ADD COLUMN execution_date DATE DEFAULT CURRENT_DATE")
    
    run_sql(conn, """
        CREATE TABLE IF NOT EXISTS dividend_records (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10),
            type VARCHAR(50),
            ratio VARCHAR(20),
            amount_per_share NUMERIC(20, 4),
            ex_dividend_date DATE,
            register_date DATE,
            payment_date DATE,
            owned_volume NUMERIC(20, 4),
            expected_value NUMERIC(20, 4),
            purchase_price NUMERIC(20, 4),
            rights_quantity NUMERIC(20, 4),
            status VARCHAR(50) DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    run_sql(conn, "ALTER TABLE dividend_records ADD COLUMN purchase_price NUMERIC(20, 4)")
    run_sql(conn, "ALTER TABLE dividend_records ADD COLUMN rights_quantity NUMERIC(20, 4)")
    run_sql(conn, "ALTER TABLE dividend_records ADD COLUMN register_date DATE")

    print("Migration complete!")
