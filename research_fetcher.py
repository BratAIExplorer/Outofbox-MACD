import yfinance as yf

def get_stock_research(symbol):
    """
    Fetches fundamental data for a stock:
    - Sector
    - Market Cap
    - Quarterly Results (EPS/Revenue growth logic)
    - Corporate Actions (Dividends/Splits)
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 1. Basic Info
        sector = info.get('sector', 'Unknown')
        name = info.get('longName', symbol)
        
        # 2. Corporate Actions & Calendar
        actions_str = ""
        
        # A. Dividends & Splits (Last 1 year)
        try:
            acts = ticker.actions
            if not acts.empty:
                # Filter for UPCOMING (Future or Today)
                today = pd.Timestamp.now().normalize()
                upcoming_acts = acts[acts.index >= today]
                
                for date, row in upcoming_acts.iterrows():
                    d_str = date.strftime('%d-%b')
                    if row['Dividends'] > 0:
                        actions_str += f"Upcoming Div {row['Dividends']} (Ex: {d_str}), "
                    if row['Stock Splits'] > 0:
                        actions_str += f"Upcoming Split {row['Stock Splits']} (Ex: {d_str}), "
        except:
            pass
            
        # B. Next Earnings Date (Calendar)
        try:
            cal = ticker.calendar
            if cal is not None and not cal.empty:
                # yfinance calendar format varies, usually dict or DF
                # dict key 0 or 'Earnings Date'
                if isinstance(cal, dict):
                    earnings = cal.get('Earnings Date')
                    if earnings:
                        actions_str += f"Earnings: {earnings[0].strftime('%d-%b')}"
                elif isinstance(cal, pd.DataFrame):
                    # Check columns or index
                    pass
        except:
            pass
            
        if not actions_str:
            actions_str = "No recent actions"

        # 3. Quarterly Results (Revenue/Earnings Growth)
        q_results = "Stable"
        rev_growth = info.get('revenueGrowth')
        if rev_growth:
            if rev_growth > 0.10:
                q_results = f"Rev Growth {(rev_growth*100):.1f}%"
            elif rev_growth < -0.05:
                q_results = f"Rev Decline {(rev_growth*100):.1f}%"
            
        return {
            "name": name,
            "sector": sector,
            "actions": actions_str.strip(", "),
            "q_results": q_results
        }
        
    except Exception as e:
        return {
            "name": symbol,
            "sector": "N/A", 
            "actions": "Error", 
            "q_results": "N/A"
        }
