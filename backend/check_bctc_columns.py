from vnstock import Vnstock
import pandas as pd

TICKER = 'MBS'
stock = Vnstock().stock(symbol=TICKER)

print("Fetching BS & IS...")
df_bs = stock.finance.balance_sheet(period='quarterly', lang='vi')
df_is = stock.finance.income_statement(period='quarterly', lang='vi')

print("\n[Balance Sheet Columns]:")
print(df_bs.columns.tolist())

print("\n[Income Statement Columns]:")
print(df_is.columns.tolist())

# Try to find Equity
equity_cols = [c for c in df_bs.columns if 'vốn chủ' in c.lower() or 'equity' in c.lower()]
print(f"\nEquity Candidates: {equity_cols}")
if equity_cols:
    print(f"Latest Equity value: {df_bs.iloc[0][equity_cols[0]]}")

# Try to find Net Income
profit_cols = [c for c in df_is.columns if 'lợi nhuận sau thuế' in c.lower()]
print(f"\nProfit Candidates: {profit_cols}")
if profit_cols:
     print(f"Latest Profit value: {df_is.iloc[0][profit_cols[0]]}")
