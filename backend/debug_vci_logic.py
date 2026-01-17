from vnstock import Vnstock
import pandas as pd
from datetime import datetime, timedelta

def test_logic(ticker):
    print(f"Testing {ticker}...")
    stock = Vnstock().stock(symbol=ticker, source='VCI')
    
    # 1. Try today
    today_str = datetime.now().strftime('%Y-%m-%d')
    print(f"1. Trying today: {today_str}")
    try:
        df = stock.quote.history(interval='1m', start=today_str, end=today_str)
    except Exception as e:
        print(f"Error fetching today: {e}")
        df = pd.DataFrame()

    has_valid_data = False
    if df is not None and not df.empty:
        df['time'] = pd.to_datetime(df['time'])
        intended_date = datetime.strptime(today_str, '%Y-%m-%d').date()
        df_filtered = df[df['time'].dt.date == intended_date]
        if not df_filtered.empty:
            print("   Has valid data for today!")
            has_valid_data = True
        else:
            print(f"   Data found but date mismatch. Rows: {len(df)}")
    else:
        print("   Today data empty.")

    if not has_valid_data:
        print("2. Entering Fallback Logic...")
        today_obj = datetime.now()
        yest_str = (today_obj - timedelta(days=10)).strftime('%Y-%m-%d')
        
        hist_1d = stock.quote.history(interval='1D', start=yest_str, end=today_obj.strftime('%Y-%m-%d'))
        
        if hist_1d is not None and not hist_1d.empty:
            latest_ts = hist_1d['time'].iloc[-1]
            print(f"   Daily History Last Row Time: {latest_ts} (Type: {type(latest_ts)})")
            
            if isinstance(latest_ts, str):
                session_date_str = latest_ts.split(' ')[0]
            else:
                session_date_str = latest_ts.strftime('%Y-%m-%d')
            
            print(f"   Resolved Session Date: {session_date_str}")
            
            print(f"   Fetching Intraday for {session_date_str}...")
            df = stock.quote.history(interval='1m', start=session_date_str, end=session_date_str)
            
            if df is not None and not df.empty:
                print(f"   Intraday Filter Logic Check:")
                df['time'] = pd.to_datetime(df['time'])
                print(f"   Sample Time in DF: {df['time'].iloc[0]}")
                intended_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
                print(f"   Intended Date: {intended_date}")
                
                df_filtered = df[df['time'].dt.date == intended_date]
                if not df_filtered.empty:
                    print(f"   SUCCESS! Found {len(df_filtered)} rows.")
                else:
                    print(f"   FAILURE! Filter returned empty.")
                    # print(df.head())
            else:
                print("   Intraday fetch returned empty.")
        else:
            print("   Daily history empty.")

test_logic('VNINDEX')
