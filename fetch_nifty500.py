import pandas as pd
import requests
import io

def fetch_nifty500_official():
    print("Downloading Official Nifty 500 list from NSE Archives...")
    # Official NSE Archive Link (Stable)
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            
            # Column is usually 'Symbol'
            if 'Symbol' in df.columns:
                symbols = df['Symbol'].tolist()
                # Clean up
                symbols = [s.strip() for s in symbols]
                
                # Save
                new_df = pd.DataFrame(symbols, columns=['Symbol'])
                new_df.to_csv("nifty500.csv", index=False)
                
                print(f"SUCCESS: Saved {len(symbols)} tickers to nifty500.csv")
                return True
            else:
                print("Column 'Symbol' not found in CSV.")
        else:
            print(f"Failed to download: {response.status_code}")
            
    except Exception as e:
        print(f"Error fetching list: {e}")
        
    return False

if __name__ == "__main__":
    fetch_nifty500_official()
