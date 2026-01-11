# core/db.py
from __future__ import annotations

import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# load .env ở backend/
load_dotenv(".env", override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Check backend/.env")

# SQLAlchemy base + session
Base = declarative_base()

# CRITICAL FIX: Force dùng driver psycopg (v3) chuẩn tắc
# Điều này giúp SQLAlchemy nhận diện đúng dialect và áp dụng các arg như prepare_threshold
if "://" in DATABASE_URL:
    scheme, rest = DATABASE_URL.split("://", 1)
    if scheme in ["postgres", "postgresql", "postgresql+psycopg"]:
        DATABASE_URL = f"postgresql+psycopg://{rest}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=False, 
    poolclass=NullPool,
    connect_args={
        "prepare_threshold": None 
    },
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()