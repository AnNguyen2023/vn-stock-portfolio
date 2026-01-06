# backend/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Cấu hình Engine tối ưu cho Supabase Pooler
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Tự động kết nối lại nếu bị ngắt
    pool_recycle=300     # Làm mới kết nối sau 5 phút
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class mới theo chuẩn SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()