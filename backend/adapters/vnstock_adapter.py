# adapters/vnstock_adapter.py
import json
from vnstock import Vnstock
from core.redis_client import get_redis

redis_client = get_redis()
REDIS_AVAILABLE = redis_client is not None

def get_financial_ratios(ticker: str, memory_cache_get_fn, memory_cache_set_fn) -> dict:
    """
    Fetch financial ratios (PE, ROE, ROA, Market Cap) from vnstock.
    Uses Redis and Memory caching (7 days).
    """
    ticker = ticker.upper()
    cache_key = f"ratios:{ticker}"
    
    # 1. Try Memory Cache
    cached_mem = memory_cache_get_fn(cache_key)
    if cached_mem and cached_mem.get("market_cap", 0) < 1e17:
        return cached_mem
        
    # 2. Try Redis Cache
    if REDIS_AVAILABLE:
        try:
            cached_redis = redis_client.get(cache_key)
            if cached_redis:
                r_obj = json.loads(cached_redis)
                if r_obj.get("market_cap", 0) < 1e17:
                    # Backfill memory (7 days)
                    memory_cache_set_fn(cache_key, r_obj, 604800)
                    return r_obj
                else:
                    # Invalidate corrupted cache
                    redis_client.delete(cache_key)
        except Exception:
            pass

    # 3. Fetch from Vnstock
    try:
        stock = Vnstock().stock(symbol=ticker)
        try:
            df_ratio = stock.finance.ratio(period='yearly', lang='vi')
        except BaseException as e:
            print(f"[ADAPTER] vnstock ratio error/limit: {e}")
            df_ratio = pd.DataFrame()

        if df_ratio is None or df_ratio.empty:
            return _calculate_fallback_ratios(ticker, stock)

        latest = df_ratio.iloc[0]
        pe = latest.get(('Chỉ tiêu định giá', 'P/E')) or latest.get('priceToEarning') or 0
        pb = latest.get(('Chỉ tiêu định giá', 'P/B')) or 0
        mc_bil = latest.get(('Chỉ tiêu định giá', 'Vốn hóa (Tỷ đồng)'))
        market_cap = 0
        if mc_bil:
            mc_val = float(mc_bil)
            market_cap = mc_val if mc_val > 1e9 else mc_val * 1e9
        
        # Validate Units (Percentage vs Decimal)
        # Some sources return 15.5 (%), others return 0.155 (decimal)
        roe = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROE (%)')) or 0
        roa = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROA (%)')) or 0
        
        roe = float(roe)
        roa = float(roa)
        
        # Heuristic: If ROE < 1 (e.g. 0.15), it's likely decimal -> convert to %
        # Unless it's a very low performance company, but <1% ROE is rare for top companies
        if 0 < abs(roe) < 1: roe *= 100
        if 0 < abs(roa) < 1: roa *= 100

        # Check if data is essentially empty/zero
        if all(float(v) == 0 for v in [pe, roe, roa, pb]):
            # Try VCI Source before calculating fallback
            print(f"[ADAPTER] Main source empty for {ticker}, trying VCI...")
            vci_ratios = _fetch_ratios_vci(ticker)
            if vci_ratios: return vci_ratios
            
            return _calculate_fallback_ratios(ticker, stock)

        r_obj = {
            "pe": float(pe),
            "pb": float(pb),
            "market_cap": float(market_cap),
            "roe": roe,
            "roa": roa
        }
        
        # Save to Caches (7 days = 604800s)
        memory_cache_set_fn(cache_key, r_obj, 604800)
        if REDIS_AVAILABLE:
            redis_client.setex(cache_key, 604800, json.dumps(r_obj))
            
        return r_obj

    except Exception as e:
        print(f"[ADAPTER] General error for {ticker}: {e}")
        # Last resort fallback
        try:
            return _calculate_fallback_ratios(ticker, Vnstock().stock(symbol=ticker))
        except:
            pass
        
    return {"pe": 0, "pb": 0, "market_cap": 0, "roe": 0, "roa": 0}

def _calculate_fallback_ratios(ticker: str, stock_obj) -> dict:
    """Fallback: Calculate ratios from raw Financial Reports."""
    try:
        # 1. Fetch Quarterly Data (4 quarters) with Safe Guards
        try:
            df_is = stock_obj.finance.income_statement(period='quarterly', lang='vi')
            df_bs = stock_obj.finance.balance_sheet(period='quarterly', lang='vi')
        except BaseException as e:
             print(f"[ADAPTER] Fallback BCTC fetch error (Rate Limit?): {e}")
             return {"pe": 0, "pb": 0, "market_cap": 0, "roe": 0, "roa": 0}
        
        if df_is.empty or df_bs.empty:
            return {"pe": 0, "pb": 0, "market_cap": 0, "roe": 0, "roa": 0}
            
        # Get latest 4 quarters
        df_is = df_is.head(4)
        df_bs_latest = df_bs.iloc[0]
        
        # Identify Columns (Dynamic for different sectors)
        cols_equity = [c for c in df_bs.columns if 'VỐN CHỦ SỞ HỮU' in c.upper() or 'EQUITY' in c.upper()]
        cols_assets = [c for c in df_bs.columns if 'TỔNG CỘNG TÀI SẢN' in c.upper() or 'ASSETS' in c.upper()]
        
        # Profit keywords: 'SAU THUẾ CỦA CỔ ĐÔNG' (standard), 'LỢI NHUẬN SAU THUẾ' (MBS/Securities generic), 'NET INCOME'
        cols_profit = [
            c for c in df_is.columns 
            if 'SAU THUẾ CỦA CỔ ĐÔNG' in c.upper() 
            or 'NET INCOME' in c.upper()
            or ('LỢI NHUẬN SAU THUẾ' in c.upper() and 'CỔ ĐÔNG' not in c.upper() and 'PHÂN BỔ' not in c.upper()) # Catch generic LNST
        ]
        
        # If generic found, prefer the most specific one if available, but for MBS often it's just 'Lợi nhuận sau thuế...'
        # Sort to prioritize standard names if multiple matches
        cols_profit.sort(key=lambda x: 0 if 'CỔ ĐÔNG' in x.upper() else 1)
        
        equity = df_bs_latest[cols_equity[0]] if cols_equity else 0
        total_assets = df_bs_latest[cols_assets[0]] if cols_assets else 0
        
        # Sum 4 quarters profit (Trailing 12M)
        total_profit = 0
        if cols_profit:
             total_profit = df_is[cols_profit[0]].sum()
             
        # Get Market Data
        # Need current price and shares outstanding
        profile = stock_obj.company.overview()
        issues_share = 0
        if not profile.empty:
            share_col = [c for c in profile.columns if 'issue_share' in c.lower()]
            if share_col:
                issues_share = float(profile.iloc[0][share_col[0]])
        
        # Fetch current price from crawler (VPS/VCI source is much more reliable)
        try:
             from crawler import get_current_prices
             price_data = get_current_prices([ticker])
             price = float(price_data.get(ticker, {}).get("price", 0))
        except:
             price = 0
             
        market_cap = price * issues_share
        
        # Calculate Ratios
        roe = (total_profit / equity * 100) if equity > 0 else 0
        roa = (total_profit / total_assets * 100) if total_assets > 0 else 0
        pb = (market_cap / equity) if equity > 0 else 0
        pe = (price / (total_profit / issues_share)) if (issues_share > 0 and total_profit > 0) else 0
        
        print(f"[ADAPTER] Fallback Calc for {ticker}: ROE={roe:.2f}%, ROA={roa:.2f}%, P/B={pb:.2f}")
        
        return {
            "pe": float(pe),
            "pb": float(pb),
            "market_cap": float(market_cap),
            "roe": float(roe), # Already percentage
            "roa": float(roa)  # Already percentage
        }
        
    except Exception as e:
        print(f"[ADAPTER] Fallback failed for {ticker}: {e}")
        return {"pe": 0, "pb": 0, "market_cap": 0, "roe": 0, "roa": 0}

def get_all_symbols():
    """Fetch all symbols by exchange (HSX, HNX, UPCOM)."""
    try:
        ls = Vnstock().stock(symbol="FPT").listing
        df = ls.symbols_by_exchange()
        return df
    except Exception as e:
        print(f"[ADAPTER] Vnstock listing error: {e}")
        return None

def _fetch_ratios_vci(ticker: str) -> dict | None:
    """Try fetching ratios specifically from VCI source."""
    try:
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        df = stock.finance.ratio(period='yearly', lang='vi')
        
        if df is None or df.empty: return None
        
        latest = df.iloc[0]
        # VCI Mapping might be same, need to be generic
        # ratio() usually returns consistent structure regardless of source in vnstock wrapper
        
        pe = latest.get(('Chỉ tiêu định giá', 'P/E')) or 0
        pb = latest.get(('Chỉ tiêu định giá', 'P/B')) or 0
        roe = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROE (%)')) or 0
        roa = latest.get(('Chỉ tiêu khả năng sinh lợi', 'ROA (%)')) or 0
        
        # VCI Market Cap might not be directly available in ratio or named differently
        # We can re-use the market cap calc from crawler if needed, or check column
        mc_bil = latest.get(('Chỉ tiêu định giá', 'Vốn hóa (Tỷ đồng)'))
        market_cap = 0
        if mc_bil:
            val = float(mc_bil)
            market_cap = val if val > 1e9 else val * 1e9
            
        return {
            "pe": float(pe),
            "pb": float(pb),
            "market_cap": float(market_cap),
            "roe": float(roe) * 100 if abs(float(roe)) < 1 else float(roe), # Apply logic
            "roa": float(roa) * 100 if abs(float(roa)) < 1 else float(roa)
        }
    except:
        return None
