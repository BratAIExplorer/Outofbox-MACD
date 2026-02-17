import yfinance as yf
import pandas as pd

def check_structure():
    tickers = ["INDIAMART.NS", "RELIANCE.NS"]
    print("Downloading...")
    # Exact params from bot
    data = yf.download(tickers, period="1d", progress=False, group_by='ticker', threads=True, timeout=60)
    
    print("\nShape:", data.shape)
    print("Columns:", data.columns)
    
    try:
        df = data["INDIAMART.NS"]
        print("\nINDIAMART.NS DataFrame Head:")
        print(df.head())
        print("\nColumns:", df.columns)
        
        latest = df.iloc[-1]
        print("\nLatest Row Type:", type(latest))
        print("Latest High:", latest['High'])
        print("Latest High Type:", type(latest['High']))
        
        val = latest['High']
        if hasattr(val, "item"):
            print("Item value:", val.item())
        else:
            print("Scalar value:", val)
            
    except Exception as e:
        print(f"Error accessing symbol: {e}")

if __name__ == "__main__":
    check_structure()
