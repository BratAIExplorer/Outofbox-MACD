import pandas as pd
import os

def check_duplicates():
    if not os.path.exists("all_nse_stocks.csv"):
        print("all_nse_stocks.csv not found.")
        return

    df = pd.read_csv("all_nse_stocks.csv")
    if 'Symbol' not in df.columns:
        print("Symbol column missing.")
        return

    symbols = df['Symbol'].tolist()
    total = len(symbols)
    unique = len(set(symbols))
    
    print(f"Total symbols: {total}")
    print(f"Unique symbols: {unique}")
    
    if total != unique:
        print(f"Found {total - unique} duplicates.")
        seen = set()
        dupes = set()
        for s in symbols:
            if s in seen:
                dupes.add(s)
            seen.add(s)
        print(f"Duplicate examples: {list(dupes)[:10]}")
    else:
        print("No duplicates found in source file.")

if __name__ == "__main__":
    check_duplicates()
