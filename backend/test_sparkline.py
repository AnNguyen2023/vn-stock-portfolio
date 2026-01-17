"""
Debug script to test sparkline data retrieval
"""
import sys
sys.path.append('e:/vn-stock-portfolio/backend')

from adapters.vci_adapter import get_intraday_sparkline
from utils.cache import mem_get, mem_set

# Test VNINDEX sparkline
print("Testing VNINDEX sparkline...")
result = get_intraday_sparkline("VNINDEX", mem_get, mem_set)
print(f"Result type: {type(result)}")
print(f"Result length: {len(result) if result else 0}")
if result:
    print(f"First item: {result[0]}")
    print(f"Last item: {result[-1]}")
else:
    print("EMPTY RESULT!")

print("\n" + "="*50 + "\n")

# Test VN30 sparkline  
print("Testing VN30 sparkline...")
result2 = get_intraday_sparkline("VN30", mem_get, mem_set)
print(f"Result type: {type(result2)}")
print(f"Result length: {len(result2) if result2 else 0}")
if result2:
    print(f"First item: {result2[0]}")
    print(f"Last item: {result2[-1]}")
else:
    print("EMPTY RESULT!")
