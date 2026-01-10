from vnstock import Vnstock
import pandas as pd

TICKER = 'MBS'
print(f"=== Testing ALL Data for {TICKER} ===")

stock = Vnstock().stock(symbol=TICKER)

try:
    print("\n[Valuation Rating]:")
    print(stock.valuation.rating())
except Exception as e:
    print(f"Error: {e}")

try:
    print("\n[Balance Sheet 1 year]:")
    print(stock.finance.balance_sheet(period='yearly', lang='vi').head())
except Exception as e:
    print(f"Error: {e}")

try:
    print("\n[Income Statement 1 year]:")
    print(stock.finance.income_statement(period='yearly', lang='vi').head())
except Exception as e:
    print(f"Error: {e}")
