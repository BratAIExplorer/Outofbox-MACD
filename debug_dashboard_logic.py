from scanner import scan_market
import pandas as pd

def mock_callback(progress, text):
    print(f"Callback: {progress*100:.0f}% - {text}")

print("Starting Mock Scan...")
results = scan_market(progress_callback=mock_callback)

print(f"Scan Finished. Matches: {len(results)}")
if len(results) > 0:
    print(results[0])
else:
    print("Zero results found via scan_market(). Investigating...")
    
    from nifty500_stocks import get_nifty_500_tickers
    tickers = get_nifty_500_tickers()
    print(f"Tickers returned by loader: {len(tickers)}")
