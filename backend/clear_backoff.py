import sys
import os
import redis

# Add current dir to path
sys.path.append(os.getcwd())
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

def clear_backoff():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        keys = r.keys("backoff:VCI*")
        if keys:
            print(f"Deleting {len(keys)} backoff keys: {keys}")
            r.delete(*keys)
        else:
            print("No VCI backoff keys found.")
            
        # Also clear cache for market summary to force rebuild
        r.delete("market_summary_full_v10")
        print("Cleared market_summary cache.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_backoff()
