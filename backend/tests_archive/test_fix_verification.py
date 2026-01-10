import sys
sys.path.insert(0, '/e:/vn-stock-portfolio/backend')

from adapters import vnstock_adapter

# Mock cache functions
def mock_get(key):
    return None

def mock_set(key, val, ttl):
    pass

print("=== Testing vnstock_adapter.get_financial_ratios() ===\n")

# Test MBB
result = vnstock_adapter.get_financial_ratios('MBB', mock_get, mock_set)

print(f"MBB Financial Ratios:")
print(f"  ROE: {result['roe']:.3f}% (Expected: ~19.38%)")
print(f"  ROA: {result['roa']:.3f}% (Expected: ~1.98%)")
print(f"  P/E: {result['pe']:.2f} (Expected: ~9.05)")
print(f"  Market Cap: {result['market_cap']:,.0f}")

print("\n✅ If ROE ≈ 19.38% and ROA ≈ 1.98%, the fix is working!")
print("❌ If ROE ≈ 0.19% and ROA ≈ 0.02%, the fix failed!")
