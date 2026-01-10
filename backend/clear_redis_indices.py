import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    keys = ["price:VNINDEX", "price:VN30", "price:HNX30", "price:HNX", "price:UPCOM"]
    print(f"Deleting keys: {keys}")
    count = r.delete(*keys)
    print(f"Deleted {count} keys.")
except Exception as e:
    print(f"Error: {e}")
