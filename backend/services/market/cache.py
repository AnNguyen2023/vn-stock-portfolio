
from typing import Any, Optional
from core.redis_client import cache_get, cache_set, get_redis

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None
MEMORY_CACHE = {}

def mem_get(key: str) -> Optional[Any]:
    return cache_get(key)

def mem_set(key: str, val: Any, ttl: int) -> None:
    cache_set(key, val, ttl)

def invalidate_watchlist_detail_cache(watchlist_id: int):
    """Xóa cache chi tiết của một watchlist (dùng khi thêm/xóa mã)"""
    cache_key = f"wl_detail_v1:{watchlist_id}"
    if REDIS_AVAILABLE:
        try:
            redis_client.delete(cache_key)
        except:
            pass
    if cache_key in MEMORY_CACHE:
        del MEMORY_CACHE[cache_key]
    print(f"[CACHE] Đã xóa cache cho watchlist {watchlist_id}")
