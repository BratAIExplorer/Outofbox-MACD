import json
import yfinance as yf
import time
import pandas as pd
import os

def audit_trades():
    if not os.path.exists("active_trades.json"):
        print("No active_trades.json found.")
        return

    with open("active_trades.json", 'r') as f:
        trades = json.load(f)

    print(f"Auditing {len(trades)} trades...")
    
    tickers = list(trades.keys())
    chunk_size = 10 # Conservative bundle
    hits = []

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        print(f"Checking chunk {i} to {i+len(chunk)}...")
        
        try:
            data = yf.download(chunk, period="1d", progress=False, group_by='ticker', threads=False, timeout=30)
            
            for sym in chunk:
                try:
                    if len(chunk) == 1:
                        df = data
                    else:
                        if sym in data:
                            df = data[sym]
                        else:
                            continue
                            
                    if df.empty: continue
                    
                    # Check Day's High
                    latest = df.iloc[-1]
                    high = float(latest['High'])
                    
                    trade = trades[sym]
                    target = float(trade['Target'])
                    
                    if high >= target:
                        hits.append(f"{sym}: High {high:.2f} >= Target {target:.2f}")
                        
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Chunk failed: {e}")
            
        time.sleep(2)

    print("\n--- AUDIT RESULTS ---")
    if hits:
        print(f"Found {len(hits)} missed targets:")
        for h in hits:
            print(h)
    else:
        print("No missed targets found (or data fetch failed).")

if __name__ == "__main__":
    audit_trades()
