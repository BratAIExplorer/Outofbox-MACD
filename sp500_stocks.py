"""
sp500_stocks.py — US Market Ticker List (Task B3)

Provides get_sp500_tickers() for the US market scanner.
- Primary: reads from sp500.csv (committed to repo, no network needed)
- Fallback: scrapes Wikipedia's List of S&P 500 companies and caches result
"""
import os
import pandas as pd

# Module-level cache (avoids re-reading CSV on repeated calls in same process)
_SP500_TICKERS = []


def get_sp500_tickers() -> list[str]:
    """
    Returns a list of S&P 500 ticker symbols.
    No suffix needed — US tickers are passed directly to yfinance (e.g. 'AAPL', 'BRK-B').

    Source priority:
      1. sp500.csv in the same directory (preferred — fast, offline-safe)
      2. Wikipedia scrape → cached to sp500.csv for next run
      3. Hardcoded top-30 fallback (last resort, unit-test-safe)
    """
    global _SP500_TICKERS
    if _SP500_TICKERS:
        return _SP500_TICKERS

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "sp500.csv")

    try:
        # ── Option 1: Local CSV ────────────────────────────────────────────
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if "Symbol" in df.columns:
                # BRK.B → BRK-B (yfinance convention)
                tickers = (
                    df["Symbol"]
                    .str.replace(".", "-", regex=False)
                    .str.strip()
                    .tolist()
                )
                tickers = [t for t in tickers if t]  # drop blanks
                if tickers:
                    print(f"[US] Loaded {len(tickers)} tickers from sp500.csv")
                    _SP500_TICKERS = tickers
                    return _SP500_TICKERS

        # ── Option 2: Wikipedia scrape + cache ────────────────────────────
        print("[US] sp500.csv not found — fetching from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]  # first table is always the constituents list

        # Wikipedia columns: 'Symbol', 'Security', 'GICS Sector', ...
        if "Symbol" not in df.columns:
            raise ValueError("Wikipedia table schema changed — 'Symbol' column missing.")

        tickers = (
            df["Symbol"]
            .str.replace(".", "-", regex=False)
            .str.strip()
            .tolist()
        )
        tickers = [t for t in tickers if t]

        # Cache to CSV so next run doesn't need network
        df.to_csv(csv_path, index=False)
        print(f"[US] Cached {len(tickers)} tickers to sp500.csv")

        _SP500_TICKERS = tickers
        return _SP500_TICKERS

    except Exception as e:
        print(f"[US] Warning: Could not load full S&P 500 list ({e}). Using top-30 fallback.")

    # ── Option 3: Top-30 Hardcoded Fallback ──────────────────────────────
    _SP500_TICKERS = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
        "META", "TSLA", "BRK-B", "JPM", "V",
        "UNH", "XOM", "LLY", "JNJ", "AVGO",
        "PG", "MA", "HD", "COST", "MRK",
        "CVX", "ABBV", "KO", "PEP", "ADBE",
        "CRM", "NFLX", "WMT", "BAC", "TMO",
    ]
    return _SP500_TICKERS


def get_stock_count() -> int:
    return len(get_sp500_tickers())


if __name__ == "__main__":
    tickers = get_sp500_tickers()
    print(f"Total US tickers: {len(tickers)}")
    print("Sample:", tickers[:10])
