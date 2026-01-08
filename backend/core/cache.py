# core/cache.py
from __future__ import annotations

import functools
import json
from typing import Any, Callable, Optional

from core.redis_client import get_redis, safe_cache_delete


def cache_get(r, key: str):
    if not r:
        return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def cache_setex(r, key: str, ttl_sec: int, obj: Any):
    if not r:
        return
    try:
        r.setex(key, ttl_sec, json.dumps(obj, default=str))
    except Exception:
        pass


def invalidate_dashboard_cache():
    safe_cache_delete(
        "dashboard_performance",
        "chart_growth_1m",
        "chart_growth_3m",
        "chart_growth_6m",
        "chart_growth_1y",
    )


def cache(ttl: int = 300, key: Optional[str] = None, key_fn: Optional[Callable[..., str]] = None):
    def decorator(fn: Callable[..., Any]):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            r = get_redis()
            if not r:
                return fn(*args, **kwargs)

            k = key or (key_fn(*args, **kwargs) if key_fn else fn.__name__)
            cached = cache_get(r, k)
            if cached is not None:
                return cached

            result = fn(*args, **kwargs)
            cache_setex(r, k, ttl, result)
            return result

        return wrapper

    return decorator
