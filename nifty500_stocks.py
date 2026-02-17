import pandas as pd
import os
import requests
import io

# Global cache
ALL_STOCKS = []

def get_nifty_500_tickers():
    """
    Returns a list of Nifty 500 tickers with .NS suffix.
    Tries to fetch from online source or falls back to a hardcoded Top 50 list for testing.
    """
    global ALL_STOCKS
    if ALL_STOCKS:
        return ALL_STOCKS
        
    try:
        # 1. Check for Nifty 500 First (Faster UI experience)
        if os.path.exists("nifty500.csv"):
            df = pd.read_csv("nifty500.csv")
            if 'Symbol' in df.columns:
                ALL_STOCKS = [f"{sym}.NS" for sym in df['Symbol'].tolist()]
                print(f"Loaded {len(ALL_STOCKS)} stocks from nifty500.csv")
                return ALL_STOCKS

        # 2. Check for Full Universe (Only if Nifty 500 is missing)
        if os.path.exists("all_nse_stocks.csv"):
            df = pd.read_csv("all_nse_stocks.csv")
            if 'Symbol' in df.columns:
                ALL_STOCKS = [f"{sym}.NS" for sym in df['Symbol'].tolist()]
                print(f"Loaded {len(ALL_STOCKS)} stocks from all_nse_stocks.csv")
                return ALL_STOCKS
                
        # Fallback: Top 30 Heavyweights (good for initial testing)
        # We can implement a full fetcher later
        ALL_STOCKS = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS",
            "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "HCLTECH.NS", "ASIANPAINT.NS",
            "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS",
            "ONGC.NS", "NTPC.NS", "TATAMOTORS.NS", "POWERGRID.NS", "JSWSTEEL.NS",
            "ADANIENT.NS", "M&M.NS", "COALINDIA.NS", "WIPRO.NS", "BAJAJFINSV.NS"
        ]
        return list(set(ALL_STOCKS))
        
    except Exception as e:
        print(f"Error loading tickers: {e}")
        return []

def get_stock_count():
    return len(get_nifty_500_tickers())
