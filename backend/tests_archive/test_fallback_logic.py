from vnstock import Vnstock
import pandas as pd

TICKER = 'MBS'
stock_obj = Vnstock().stock(symbol=TICKER, source='VCI')

print(f"=== Testing Fallback Logic for {TICKER} ===\n")

try:
    # 1. Fetch Quarterly Data (4 quarters)
    print("Fetching Quarterly BCTC...")
    df_is = stock_obj.finance.income_statement(period='quarterly', lang='vi')
    df_bs = stock_obj.finance.balance_sheet(period='quarterly', lang='vi')
    
    if df_is.empty: print("❌ Income Statement empty")
    if df_bs.empty: print("❌ Balance Sheet empty")
    
    if not df_is.empty and not df_bs.empty:
        # Get latest 4 quarters
        df_is = df_is.head(4)
        df_bs_latest = df_bs.iloc[0]
        
        print(f"Latest BS Date: {df_bs_latest.get('Năm', '')} Q{df_bs_latest.get('Kỳ', '')}")
        
        # Identify Columns
        cols_equity = [c for c in df_bs.columns if 'VỐN CHỦ SỞ HỮU' in c.upper() or 'EQUITY' in c.upper()]
        cols_assets = [c for c in df_bs.columns if 'TỔNG CỘNG TÀI SẢN' in c.upper() or 'ASSETS' in c.upper()]
        
        # Note: MBS (Securities company) might have slightly different Income Statement column names
        # Let's print IS columns to be sure
        print("\nIS Columns:", df_is.columns.tolist())
        
        cols_profit = [c for c in df_is.columns if 'SAU THUẾ CỦA CỔ ĐÔNG' in c.upper() or 'NET INCOME' in c.upper()]
        
        print(f"\nCol Equity: {cols_equity}")
        print(f"Col Assets: {cols_assets}")
        print(f"Col Profit: {cols_profit}")
        
        equity = df_bs_latest[cols_equity[0]] if cols_equity else 0
        total_assets = df_bs_latest[cols_assets[0]] if cols_assets else 0
        
        # Sum 4 quarters profit
        total_profit = 0
        if cols_profit:
             print("Profits (4Q):", df_is[cols_profit[0]].tolist())
             total_profit = df_is[cols_profit[0]].sum()
        
        print(f"\nCalculated Values:")
        print(f"  Equity: {equity:,.0f}")
        print(f"  Assets: {total_assets:,.0f}")
        print(f"  Total Profit (4Q): {total_profit:,.0f}")
             
        # Get Market Data
        profile = stock_obj.company.overview()
        issues_share = 0
        if not profile.empty:
            share_col = [c for c in profile.columns if 'issue_share' in c.lower()]
            if share_col:
                issues_share = float(profile.iloc[0][share_col[0]])
        
        print(f"  Issued Shares: {issues_share:,.0f}")
        
        # Fetch current price
        try:
             price_df = stock_obj.quote.price()
             price = float(price_df.iloc[0]['giá']) if not price_df.empty else 0
        except:
             price = 0 # Dummy price if fetch fails
        
        print(f"  Price: {price}")
             
        market_cap = price * issues_share
        
        # Calculate Ratios
        roe = (total_profit / equity * 100) if equity > 0 else 0
        roa = (total_profit / total_assets * 100) if total_assets > 0 else 0
        pb = (market_cap / equity) if equity > 0 else 0
        pe = (price / (total_profit / issues_share)) if (issues_share > 0 and total_profit > 0) else 0
        
        print(f"\nFinal Results:")
        print(f"  ROE: {roe:.2f}%")
        print(f"  ROA: {roa:.2f}%")
        print(f"  P/B: {pb:.2f}")
        print(f"  P/E: {pe:.2f}")

except Exception as e:
    print(f"❌ Exception in logic: {e}")
