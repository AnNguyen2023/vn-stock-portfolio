from vnstock import Vnstock
from datetime import datetime, timedelta

today = datetime.now().strftime('%Y-%m-%d')
yest = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
df = stock.quote.history(start=yest, end=today, interval='1D')

print("Columns:", df.columns.tolist())
print("\nLatest row:")
latest = df.iloc[-1]
print(f"Time: {latest['time']}")
print(f"Close: {latest['close']}")
print(f"Volume: {latest.get('volume', 'N/A')}")
print(f"Value: {latest.get('value', 'N/A')}")

# Check if value exists and its magnitude
if 'value' in df.columns:
    print(f"\nValue column exists!")
    print(f"Raw value: {latest['value']}")
    print(f"Value in billions: {float(latest['value']) / 1e9:.2f} Tỷ")
else:
    print("\nValue column NOT found in data")
