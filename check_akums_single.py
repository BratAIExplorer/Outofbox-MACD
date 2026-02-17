import yfinance as yf
import time

print("Checking AKUMS.NS single...")
try:
    # Single ticker check - should pass rate limit easily
    data = yf.download("AKUMS.NS", period="1d", progress=False)
    if not data.empty:
        h = float(data.iloc[-1]['High'])
        print(f"AKUMS High: {h}")
        print(f"Target: 444.98")
        if h >= 444.98:
            print("STATUS: HIT")
        else:
            print("STATUS: MISS")
    else:
        print("Empty Data")
except Exception as e:
    print(f"Error: {e}")
