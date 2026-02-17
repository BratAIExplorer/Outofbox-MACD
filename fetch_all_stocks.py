import pandas as pd
import requests
import io

def fetch_all_nse_stocks():
    print("Downloading Full NSE Equity List (~2000 stocks)...")
    # Official NSE "Securities available for Trading" list
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            
            # Column is 'SYMBOL' in EQUITY_L.csv
            if 'SYMBOL' in df.columns:
                symbols = df['SYMBOL'].tolist()
                # Clean up and add .NS suffix just in case caller needs it, 
                # but nifty500_stocks.py adds it dynamically. Let's store raw symbols.
                symbols = [s.strip() for s in symbols]
                
                # Save
                new_df = pd.DataFrame(symbols, columns=['Symbol'])
                new_df.to_csv("all_nse_stocks.csv", index=False)
                
                print(f"SUCCESS: Saved {len(symbols)} tickers to all_nse_stocks.csv")
                return True
            else:
                print(f"Column 'SYMBOL' not found. Available: {df.columns}")
        else:
            print(f"Failed to download: {response.status_code}")
            
    except Exception as e:
        print(f"Error fetching list: {e}")
        
    return False

if __name__ == "__main__":
    fetch_all_nse_stocks()
