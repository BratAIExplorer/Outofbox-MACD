import yfinance as yf
print("Fetching AKUMS.NS data...")
data = yf.download("AKUMS.NS", period="1d", progress=False)
if not data.empty:
    latest = data.iloc[-1]
    high = float(latest['High'])
    close = float(latest['Close'])
    print(f"AKUMS.NS High: {high}")
    print(f"AKUMS.NS Close: {close}")
    print(f"Target: 444.98")
    if high >= 444.98:
        print("RESULT: TARGET HIT (Logic should trigger)")
    else:
        print("RESULT: TARGET NOT YET HIT according to yfinance")
else:
    print("No data found for AKUMS.NS")
