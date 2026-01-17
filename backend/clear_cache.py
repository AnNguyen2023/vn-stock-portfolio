"""Clear Redis cache for intraday data"""
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

# Clear all intraday cache keys
patterns = [
    "intraday_spark_v5_*",
    "intraday_VNINDEX_*",
    "intraday_VN30_*"
]

for pattern in patterns:
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
        print(f"✓ Deleted {len(keys)} keys matching: {pattern}")
    else:
        print(f"  No keys found for: {pattern}")

print("\n✓ Cache cleared! Restart backend to load fresh data.")
