import json
import yfinance as yf
import pandas as pd
import time

def check_active_trades():
    with open("active_trades.json", "r") as f:
        trades = json.load(f)
    
    print(f"Loaded {len(trades)} active trades.")
    
    tickers = list(trades.keys())
    # Test only first 50 to save time for quick check, or specific ones if known.
    # Let's do batch of all but in parallel or just big batch
    
    # Just check a few or all? All is better to find the "missing" ones.
    print("Downloading data...")
    
    # Download all in one go (might be faster than chunked for this debug)
    # yfinance handles batching internally somewhat
    data = yf.download(tickers, period="1d", group_by='ticker', progress=True, threads=True)
    
    hits = []
    
    for sym in tickers:
        try:
            val = data[sym]
            if val.empty: continue
            
            # LAST ROW (Current Day)
            latest = val.iloc[-1]
            
            # Handle MultiIndex headers if present
            # yfinance often returns dataframe with (Price, Ticker) columns
            # But group_by='ticker' makes it dict-like or Top Level Ticker
            
            # If we access data[sym], we get a DataFrame with OHLCV for that ticker
            
            high = float(latest['High'])
            close = float(latest['Close'])
            
            target = float(trades[sym]['Target'])
            
            print(f"{sym}: High {high} vs Target {target}")
            
            if high >= target:
                hits.append((sym, high, target))
                
        except Exception as e:
            # print(f"Error {sym}: {e}")
            pass
            
    print(f"\nFound {len(hits)} POSTENTIAL TARGET HITS:")
    for h in hits:
        print(f"{h[0]} reached {h[1]} (Target: {h[2]})")

if __name__ == "__main__":
    check_active_trades()
