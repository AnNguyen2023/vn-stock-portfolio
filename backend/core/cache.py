# core/cache.py
from __future__ import annotations

import functools
import json
from typing import Any, Callable, Optional

from core.redis_client import get_redis, safe_cache_delete


from core.redis_client import cache_get as redis_cache_get, cache_set as redis_cache_set, safe_cache_delete


def cache_get(r, key: str):
    """Alias for backward compatibility with the decorator, using the new L1/L2 logic."""
    return redis_cache_get(key)


def cache_setex(r, key: str, ttl_sec: int, obj: Any):
    """Alias for backward compatibility, using the new L1/L2 logic."""
    redis_cache_set(key, obj, ttl=ttl_sec)


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
            k = key or (key_fn(*args, **kwargs) if key_fn else fn.__name__)
            # redis_cache_get now handles L1 RAM -> L2 Redis automatically
            cached = redis_cache_get(k)
            if cached is not None:
                return cached

            result = fn(*args, **kwargs)
            # redis_cache_set now handles L1 RAM -> L2 Redis automatically
            redis_cache_set(k, result, ttl=ttl)
            return result

        return wrapper

    return decorator
