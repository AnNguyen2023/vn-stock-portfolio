
from typing import Any, Optional
from core.redis_client import cache_get, cache_set, cache_delete, get_redis

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

def mem_get(key: str) -> Optional[Any]:
    return cache_get(key)

def mem_set(key: str, val: Any, ttl: int) -> None:
    cache_set(key, val, ttl)

def invalidate_watchlist_detail_cache(watchlist_id: int):
    """Xóa cache chi tiết của một watchlist (dùng khi thêm/xóa mã)"""
    cache_key = f"wl_detail_v1:{watchlist_id}"
    cache_delete(cache_key)
    print(f"[CACHE] Đã xóa cache cho watchlist {watchlist_id}")
