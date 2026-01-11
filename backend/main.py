# main.py
from __future__ import annotations

import os
from dotenv import load_dotenv
import pandas as pd

# Pandas future configuration
pd.set_option('future.no_silent_downcasting', True)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import models
from core.db import engine
from core.redis_client import init_redis
from core.logger import logger
from core.exceptions import AppBaseException

from routers import trading, portfolio, logs, market, watchlist, titan
from tasks import cleanup_expired_data_task


load_dotenv(".env", override=True)

app = FastAPI(title="Invest Journal")

# --- GLOBAL EXCEPTION HANDLER ---
@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException):
    """
    Catch all custom application exceptions and return a standardized JSON response.
    """
    logger.error(f"App Error: {exc.message} | Status: {exc.status_code}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.message,
                "detail": exc.detail
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unhandled system exceptions.
    """
    logger.exception(f"Unhandled Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "Internal Server Error",
                "detail": str(exc) if os.getenv("DEBUG") == "True" else None
            }
        }
    )
# --------------------------------

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
        logger.warning(f"Database table creation skipped/error: {e}")

    logger.info("🚀 Invest Journal backend is ready!")
    
    # Run cleanup of expired notes (3 year rule)
    try:
        cleanup_expired_data_task()
    except Exception as e:
        logger.error(f"Maintenance cleanup failed: {e}")


# Routers
app.include_router(portfolio.router)
app.include_router(trading.router)
app.include_router(market.router)
app.include_router(logs.router)
app.include_router(watchlist.router)
app.include_router(titan.router)


@app.get("/")
def root():
    return {"status": "ok", "app": "Invest Journal"}
