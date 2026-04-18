import yfinance as yf
import pandas as pd
import ta
import datetime
import concurrent.futures
import time
from nifty500_stocks import get_nifty_500_tickers
from sp500_stocks import get_sp500_tickers

def fetch_data_batch_old(tickers, period="6mo"):
    # Keeping old function for safety if needed, but the main logic is now inside scan_market or will be patched fully
    pass

def find_crossover_date(macd_line, signal_line):
    """
    Finds the date when MACD crossed above Signal line (looking back 60 days).
    """
    try:
        # Ensure input series are valid
        if macd_line is None or signal_line is None or macd_line.empty:
            return None

        if macd_line.iloc[-1] <= signal_line.iloc[-1]:
            return None # Not currently bullish
            
        # Look back 60 days
        lookback = min(60, len(macd_line))
        for i in range(1, lookback):
            idx = -1 * i
            prev_idx = -1 * (i + 1)
            
            # Check for cross: Current > Signal AND Prev <= Signal
            # Using iat for scalar access speed
            curr_macd = macd_line.iloc[idx]
            curr_sig = signal_line.iloc[idx]
            prev_macd = macd_line.iloc[prev_idx]
            prev_sig = signal_line.iloc[prev_idx]
            
            if (curr_macd > curr_sig) and (prev_macd <= prev_sig):
                return macd_line.index[idx].strftime('%Y-%m-%d')
                
        return "Long Term Bull"
    except Exception as e:
        # print(f"Crossover check error: {e}")
        return None

def analyze_stock(ticker, df, market="NSE"):
    """
    Analyzes a single stock dataframe for Technical Criteria using 'ta' library.
    """
    try:
        if len(df) < 200: return None  # Need enough data for 200 SMA

        # Market-aware penny stock threshold (B5)
        is_penny = False
        
        # Ensure Close column is 1D Series
        close = df['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
            
        # Calculate Indicators using 'ta' library
        
        # 1. MACD (12, 26, 9)
        # ta.trend.MACD returns a class, we need to call methods for lines
        macd_obj = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd_obj.macd()
        df['MACD_SIGNAL'] = macd_obj.macd_signal()
        
        # 2. Moving Averages (Simple Rolling Mean is faster and cleaner for basic SMA)
        # But for consistency we can use ta.trend.SMAIndicator
        df['SMA_20'] = ta.trend.SMAIndicator(close=close, window=20).sma_indicator()
        df['SMA_50'] = ta.trend.SMAIndicator(close=close, window=50).sma_indicator()
        df['SMA_100'] = ta.trend.SMAIndicator(close=close, window=100).sma_indicator()
        df['SMA_200'] = ta.trend.SMAIndicator(close=close, window=200).sma_indicator()
        
        # 3. RSI
        df['RSI'] = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        
        # Get Latest Data
        latest = df.iloc[-1]
        
        # Accessing scalars safely (handle potential Series if duplicate indices exist)
        def get_val(series_item):
            return series_item.item() if isinstance(series_item, (pd.Series, pd.DataFrame)) else series_item

        current_price = get_val(latest['Close'])
        macd_val = get_val(latest['MACD'])
        sig_val = get_val(latest['MACD_SIGNAL'])
        sma20 = get_val(latest['SMA_20'])
        sma50 = get_val(latest['SMA_50'])
        
        # 1. MACD Bullish (MACD > Signal)
        if macd_val <= sig_val:
            return None
            
        # 2. Bullish Trend (Price > 20 SMA OR Price > 50 SMA)
        above_20 = current_price > sma20
        above_50 = current_price > sma50
        
        if not (above_20 or above_50):
            return None
            
        # 3. Find Crossover Date
        crossover_date = find_crossover_date(df['MACD'], df['MACD_SIGNAL'])
        if not crossover_date:
            return None
            
        # --- PREPARE RESULT ---
        
        # Support/Resistance Logic
        mas = [
            (sma20, '20 DMA'), 
            (sma50, '50 DMA'), 
            (sma100 := get_val(latest['SMA_100']), '100 DMA'), 
            (sma200 := get_val(latest['SMA_200']), '200 DMA')
        ]
        
        supports = [m for m in mas if current_price > m[0]]
        resistances = [m for m in mas if current_price < m[0]]
        
        # Nearest Support
        support_level = max(supports, key=lambda x: x[0])[0] if supports else 0
        support_desc = max(supports, key=lambda x: x[0])[1] if supports else "None"
        
        # Nearest Resistance
        resistance_level = min(resistances, key=lambda x: x[0])[0] if resistances else current_price * 1.05
        resistance_desc = min(resistances, key=lambda x: x[0])[1] if resistances else "Blue Sky"
        
        # Market-aware penny stock classification (Task B5)
        is_penny = (
            (market == "NSE" and current_price < 10) or
            (market == "US" and current_price < 1)
        )

        # Strip .NS suffix for DB storage (store clean symbol e.g. "HDFC" not "HDFC.NS")
        clean_symbol = ticker.replace(".NS", "") if market == "NSE" else ticker

        return {
            "symbol": clean_symbol,
            "price": current_price,
            "rsi": get_val(latest['RSI']),
            "macd_cross_date": crossover_date,
            "above_20dma": above_20,
            "above_50dma": above_50,
            "support": f"{support_level:.2f} ({support_desc})",
            "resistance": f"{resistance_level:.2f} ({resistance_desc})",
            "sma_20": sma20,
            "sma_50": sma50,
            "sma_100": sma100,
            "sma_200": sma200,
            "is_penny": is_penny,
            # DB contract fields
            "mb_score": 0,        # Placeholder — MB scoring not yet ported
            "mb_tier": "Builder", # Default tier
            "total_score": 0,
            "sector": "Unknown",
            "category": "STANDARD",
            "l1": above_20,       # Price > 20 DMA
            "l2": above_50,       # Price > 50 DMA
            "l3": bool(get_val(latest['RSI']) > 50) if get_val(latest['RSI']) else False,
            "l4": bool(macd_val > 0),
            "l5": bool(macd_val > sig_val),
            "l6": False,          # Reserved for future criteria
        }
        
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def fetch_data_batch(tickers, period="1y", progress_callback=None):
    """
    Fetches historical data for multiple tickers in batches.
    """
    data_dict = {}
    BATCH_SIZE = 50 # Reverting to Safe 50
    total_tickers = len(tickers)
    total_batches = (total_tickers + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"Scanning {total_tickers} stocks in {total_batches} batches...")
    start_time = time.time()
    
    for i in range(0, total_tickers, BATCH_SIZE):
        batch = tickers[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        # UI Update
        if progress_callback:
            elapsed = time.time() - start_time
            if batch_num > 1:
                avg_time_per_batch = elapsed / (batch_num - 1)
                remaining_batches = total_batches - batch_num + 1
                eta = remaining_batches * avg_time_per_batch
                eta_str = f"{int(eta//60)}m {int(eta%60)}s"
            else:
                eta_str = "Calculating..."
                
            prog = 0.05 + (0.35 * (i / total_tickers)) # 5% to 40% of total bar
            progress_callback(prog, f"Scanning Batch {batch_num}/{total_batches}... Publishing starts in approx {eta_str}")

        try:
            # Fetch batch - threads=False to prevent hanging
            df = yf.download(batch, period=period, progress=False, group_by='ticker', threads=False, timeout=10)
            
            # Anti-Throttle Delay
            time.sleep(0.5)
            
            # Process batch
            if len(batch) == 1:
                data_dict[batch[0]] = df
            else:
                for ticker in batch:
                    try:
                        t_df = df[ticker].dropna()
                        if not t_df.empty:
                            data_dict[ticker] = t_df
                    except KeyError:
                        pass
        except Exception as e:
            print(f"Batch error: {e}")
            
    return data_dict

def scan_market(market: str = "NSE", progress_callback=None):
    """
    Runs the technical scanner for the given market.
    market: "NSE" | "US"
    Returns a list of dicts with DB-ready fields.
    """
    if market == "NSE":
        tickers = get_nifty_500_tickers()
    elif market == "US":
        tickers = get_sp500_tickers()
    else:
        raise ValueError(f"Unknown market: {market}. Use 'NSE' or 'US'.")

    print(f"[{market}] Loaded {len(tickers)} tickers.")

    # 1. Fetch Data
    if progress_callback: progress_callback(0.05, f"[{market}] Starting Data Download...")
    data = fetch_data_batch(tickers, progress_callback=progress_callback)

    results = []
    total_stocks = len(data)
    if total_stocks == 0:
        print(f"[{market}] No data fetched — aborting.")
        return []

    # 2. Parallel Analysis
    if progress_callback: progress_callback(0.4, f"[{market}] Analyzing Indicators...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_stock = {
            executor.submit(analyze_stock, ticker, df, market): ticker
            for ticker, df in data.items()
        }

        completed = 0
        for future in concurrent.futures.as_completed(future_to_stock):
            res = future.result()
            if res:
                results.append(res)

            completed += 1
            if progress_callback and completed % 50 == 0:
                prog = 0.4 + (0.5 * (completed / total_stocks))
                progress_callback(prog, f"[{market}] Analyzed {completed}/{total_stocks}")

    # Sort by Latest Crossover Date desc
    results.sort(key=lambda x: x['macd_cross_date'], reverse=True)

    if progress_callback: progress_callback(1.0, "Done!")
    print(f"[{market}] Scan produced {len(results)} results.")
    return results

if __name__ == "__main__":
    import sys
    market_arg = sys.argv[1] if len(sys.argv) > 1 else "NSE"
    print(f"Running usage test for market: {market_arg}")
    hits = scan_market(market=market_arg)
    print(f"Found {len(hits)} stocks matching criteria.")
    for h in hits[:5]:
        print(h)
