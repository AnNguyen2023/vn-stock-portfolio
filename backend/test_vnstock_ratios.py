from vnstock import Vnstock

stock = Vnstock().stock(symbol='MBB')
df = stock.finance.ratio(period='yearly', lang='vi')

if not df.empty:
    latest = df.iloc[0]
    
    print("=== MBB Financial Ratios (Latest Year) ===")
    print(f"\nFull columns: {df.columns.tolist()}")
    
    # Try to get ROE
    roe_key1 = ('Chỉ tiêu khả năng sinh lợi', 'ROE (%)')
    roe = latest.get(roe_key1)
    print(f"\nROE (from {roe_key1}): {roe}")
    print(f"ROE type: {type(roe)}")
    
    # Try to get ROA
    roa_key1 = ('Chỉ tiêu khả năng sinh lợi', 'ROA (%)')
    roa = latest.get(roa_key1)
    print(f"\nROA (from {roa_key1}): {roa}")
    print(f"ROA type: {type(roa)}")
    
    # Try to get P/E
    pe_key1 = ('Chỉ tiêu định giá', 'P/E')
    pe = latest.get(pe_key1)
    print(f"\nP/E (from {pe_key1}): {pe}")
    print(f"P/E type: {type(pe)}")
    
    # Print all profitability metrics
    print("\n=== All Profitability Metrics ===")
    for col in df.columns:
        if 'sinh lợi' in str(col).lower() or 'roe' in str(col).lower() or 'roa' in str(col).lower():
            print(f"{col}: {latest.get(col)}")
    
    # Print all valuation metrics
    print("\n=== All Valuation Metrics ===")
    for col in df.columns:
        if 'định giá' in str(col).lower() or 'p/e' in str(col).lower():
            print(f"{col}: {latest.get(col)}")
