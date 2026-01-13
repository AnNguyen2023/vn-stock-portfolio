# core/redis_client.py
from __future__ import annotations

import os
import time
import json
from typing import Any, Optional
import redis
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis: Optional[redis.Redis] = None
_queue: Optional[Queue] = None

_last_check_ts: float = 0.0
_retry_every_sec: int = 5  # redis down thì 5s thử lại


def init_redis():
    """Backward-compatible: giữ tên cũ cho main.py."""
    return get_redis()


def get_redis() -> Optional[redis.Redis]:
    """
    Trả về redis client nếu kết nối được, None nếu không.
    Có retry theo thời gian để redis bật lại thì app tự reconnect (không cần restart).
    """
    global _redis, _queue, _last_check_ts

    now = time.time()

    # nếu đã có connection OK thì trả luôn
    if _redis is not None:
        return _redis

    # nếu vừa fail gần đây thì chưa thử lại
    if now - _last_check_ts < _retry_every_sec:
        return None

    _last_check_ts = now

    try:
        # rediss:// in the URL already enables SSL for Upstash.
        # Simple is better to avoid version-specific keyword arguments.
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        _redis = r
        _queue = Queue(connection=r)
        print("✅ Redis kết nối thành công")
        return _redis
    except Exception as e:
        _redis = None
        _queue = None
        print(f"[REDIS] ⚠️ Không kết nối được, chạy không cache: {e}")
        return None


def get_queue() -> Optional[Queue]:
    get_redis()
    return _queue


def safe_cache_delete(*keys: str) -> None:
    r = get_redis()
    if not r or not keys:
        return
    try:
        r.delete(*keys)
    except Exception:
        pass


def safe_flushall() -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.flushdb()
    except Exception:
        pass

# --- LEVEL 1 CACHE (RAM) TO SAVE REDIS COMMANDS ---
_MEMORY_CACHE: dict[str, tuple[Any, float]] = {}

def _mem_get(key: str) -> Optional[Any]:
    if key in _MEMORY_CACHE:
        val, exp = _MEMORY_CACHE[key]
        if time.time() < exp:
            return val
        del _MEMORY_CACHE[key]
    return None

def _mem_set(key: str, val: Any, ttl: int) -> None:
    _MEMORY_CACHE[key] = (val, time.time() + ttl)

def cache_get(key: str):
    # 1. Check RAM first (L1)
    cached_mem = _mem_get(key)
    if cached_mem is not None:
        return cached_mem

    # 2. Check Redis (L2)
    r = get_redis()
    if not r:
        return None
    try:
        v = r.get(key)
        if v:
            data = json.loads(v)
            # Store back in RAM for 60s to buffer frequent requests (Upstash command optimization)
            _mem_set(key, data, 60)
            return data
        return None
    except Exception:
        return None

def cache_set(key: str, value: Any, ttl: int = 300, ex: Optional[int] = None) -> None:
    """ttl hoặc ex (giống redis-py). ưu tiên ex nếu có."""
    seconds = int(ex) if ex is not None else int(ttl)
    
    # 1. Update RAM (L1)
    _mem_set(key, value, seconds)

    # 2. Update Redis (L2)
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, seconds, json.dumps(value, default=str))
    except Exception:
        pass

def cache_delete(*keys: str) -> None:
    for k in keys:
        if k in _MEMORY_CACHE:
            del _MEMORY_CACHE[k]
    safe_cache_delete(*keys)
