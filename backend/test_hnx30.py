from vnstock import Trading
import pandas as pd

def test_hnx30_sources():
    index_symbols = ['HNX30', 'HNX30INDEX', 'HNX30-INDEX', 'HNX']
    sources = ['VCI', 'TCBS']
    for src in sources:
        for index_symbol in index_symbols:
            print(f"--- Testing Source: {src} | Symbol: {index_symbol} ---")
            try:
                df = Trading(source=src).price_board([index_symbol])
                if df is not None and not df.empty:
                    # Print relevant columns
                    cols = df.columns
                    print(df[[('listing', 'symbol'), ('match', 'match_price'), ('trading', 'total_volume'), ('trading', 'total_value')]].to_string() if ('match', 'match_price') in df.columns else df.to_string())
                else:
                    print(f"Source {src} returned empty result for {index_symbol}")
            except Exception as e:
                print(f"Source {src} error: {e}")

if __name__ == "__main__":
    test_hnx30_sources()
