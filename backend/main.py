# main.py
from __future__ import annotations

import os
from dotenv import load_dotenv
import pandas as pd

# Pandas future configuration
pd.set_option('future.no_silent_downcasting', True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from core.db import engine
from core.redis_client import init_redis

from routers import trading, portfolio, logs, market, watchlist


load_dotenv(".env", override=True)

app = FastAPI(title="Invest Journal")


# CORS
cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
cors_origins = [x.strip() for x in cors_raw.split(",") if x.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_redis()
    # create tables once at startup (dev)
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[DB] ⚠️ create_all skipped/error: {e}")

    print("🚀 Invest Journal ready!")


# Routers
app.include_router(portfolio.router)
app.include_router(trading.router)
app.include_router(market.router)
app.include_router(logs.router)
app.include_router(watchlist.router)


@app.get("/")
def root():
    return {"status": "ok", "app": "Invest Journal"}
