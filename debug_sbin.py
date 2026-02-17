import scanner
import pandas as pd

# Mock the ticker loader
def mock_load():
    return ['SBIN.NS']

# Monkey patch
scanner.get_nifty_500_tickers = mock_load

print("Scanning SBIN.NS only...")
results = scanner.scan_market()
print(f"Results: {results}")
