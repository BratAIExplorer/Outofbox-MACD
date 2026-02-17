import yfinance as yf
import pandas as pd
import ta
from nifty500_stocks import get_nifty_500_tickers
from scanner import fetch_data_batch, analyze_stock

def debug_scan():
    print("--- DEBUGGING SCANNER (FULL SWEEP) ---")
    
    # 1. Check Tickers
    tickers = get_nifty_500_tickers()
    print(f"1. Loaded Tickers: {len(tickers)}")
    
    if len(tickers) == 0:
        print("   [ERROR] No tickers found!")
        return

    # 2. Fetch Data (All)
    print(f"\n2. Fetching data for {len(tickers)} stocks...")
    data = fetch_data_batch(tickers)
    print(f"   Fetched {len(data)} DataFrames.")

    # 3. Analyze Logic Stats
    print("\n3. Analyzing Criteria Stats:")
    
    stats = {
        "Total": 0,
        "Pass_MACD_Bullish": 0,
        "Pass_MA_Trend": 0,
        "Pass_Crossover_Search": 0,
        "Matches": []
    }
    
    for sym, df in data.items():
        stats["Total"] += 1
        try:
            close = df['Close']
            if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
            
            # Indicators
            macd_obj = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
            macd_line = macd_obj.macd().dropna()
            sig_line = macd_obj.macd_signal().dropna()
            
            sma20_series = ta.trend.SMAIndicator(close=close, window=20).sma_indicator()
            sma50_series = ta.trend.SMAIndicator(close=close, window=50).sma_indicator()
            
            if sma50_series.empty or sma20_series.empty: continue

            # Latest Values
            curr_price = close.iloc[-1]
            curr_macd = macd_line.iloc[-1]
            curr_sig = sig_line.iloc[-1]
            sma20 = sma20_series.iloc[-1]
            sma50 = sma50_series.iloc[-1]
            
            # Check 1: MACD Bullish
            check_macd = curr_macd > curr_sig
            if check_macd: stats["Pass_MACD_Bullish"] += 1
            
            # Check 2: Above MA
            above_20 = curr_price > sma20
            above_50 = curr_price > sma50
            check_ma = above_20 or above_50
            if check_ma: stats["Pass_MA_Trend"] += 1
            
            # Check 3: Crossover Logic (Only check if Macd passed)
            crossover_found = False
            if check_macd:
                lookback = min(60, len(macd_line))
                for i in range(1, lookback):
                    idx = -1 * i
                    prev_idx = -1 * (i + 1)
                    if (macd_line.iloc[idx] > sig_line.iloc[idx]) and (macd_line.iloc[prev_idx] <= sig_line.iloc[prev_idx]):
                        crossover_found = True
                        break
            
            if crossover_found: stats["Pass_Crossover_Search"] += 1
            
            # Final Result
            if check_macd and check_ma and crossover_found:
                 stats["Matches"].append(sym)
                 print(f"   >>> MATCH FOUND: {sym} <<<")
                 
        except Exception as e:
            pass # Skip errors for stats

    print("\n--- RESULTS SUMMARY ---")
    print(f"Total Scanned: {stats['Total']}")
    print(f"MACD Bullish:  {stats['Pass_MACD_Bullish']}")
    print(f"Price > MA:    {stats['Pass_MA_Trend']}")
    print(f"Valid Crossover: {stats['Pass_Crossover_Search']}")
    print(f"FINAL MATCHES: {len(stats['Matches'])}")
    if stats['Matches']:
        print(f"List: {stats['Matches']}")
    else:
        print("Reason: Logic is strict. No stocks in this list meet ALL 3 conditions right now.")

if __name__ == "__main__":
    debug_scan()
