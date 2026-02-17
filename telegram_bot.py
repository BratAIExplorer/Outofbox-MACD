import os
import time
import asyncio
import threading
import json
from telegram import Bot
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from scanner import scan_market
from research_fetcher import get_stock_research

# Load credentials
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
HISTORY_FILE = "sent_history.json"

class ResearchBot:
    def __init__(self):
        # Hot-Reload Credentials on init
        load_dotenv(override=True)
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
        
        if not self.token:
            print("ERROR: Telegram Token missing!")
            
        # self.bot = Bot(token=self.token) # MOVED to local scope in send_message_async to avoid Event Loop errors
        self.publish_queue = []
        self.history = self.load_history()
        self.is_running = False
        
    def load_history(self):
        """Loads sent stocks history for cooldown check"""
        # Dictionary format: {'SYMBOL': 'YYYY-MM-DD', ...}
        history = {}
        
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    
                    # Check if it's the new format
                    if "history" in data:
                        history = data["history"]
                    # Legacy migration logic
                    elif "date" in data and "sent" in data:
                        date = data["date"]
                        print("Migrating legacy history...")
                        for sym in data["sent"]:
                            history[sym] = date
            except Exception as e:
                print(f"Error loading history: {e}")
        return history

    def save_history(self):
        """Saves current sent history with pruning"""
        # Prune old entries (> 7 days to keep file small)
        try:
            today = datetime.now().date()
            pruned = {}
            
            for sym, date_str in self.history.items():
                try:
                    d = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if (today - d).days <= 7:
                        pruned[sym] = date_str
                except:
                    pass
                    
            self.history = pruned
            
            data = {
                'history': self.history,
                'last_updated': today.strftime('%Y-%m-%d')
            }
            with open(HISTORY_FILE + ".tmp", 'w') as f:
                json.dump(data, f)
            os.replace(HISTORY_FILE + ".tmp", HISTORY_FILE)
        except Exception as e:
            print(f"Error saving history: {e}")

    def update_status(self, msg):
        """Writes status to a file for UI to read (Rolling Log)"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        new_line = f"[{timestamp}] {msg}\n"
        try:
            print(new_line.strip())
        except Exception:
            pass
        
        try:
            # Read existing
            lines = []
            if os.path.exists("bot_status.txt"):
                with open("bot_status.txt", "r") as f:
                    lines = f.readlines()
            
            # Append new
            lines.append(new_line)
            
            # Keep last 10
            if len(lines) > 10:
                lines = lines[-10:]
                
            # Atomic Write
            temp_file = "bot_status.tmp"
            with open(temp_file, "w") as f:
                f.writelines(lines)
            
            # Use os.replace for atomic rename on Windows
            if os.path.exists("bot_status.txt"):
                os.replace(temp_file, "bot_status.txt")
            else:
                os.rename(temp_file, "bot_status.txt")
        except Exception as e:
            print(f"Status Write Error: {e}")

    def refresh_queue(self):
        """Scans market and populates queue"""
        self.update_status("Refreshing Scanner Queue...")
        try:
            # We need to pass a callback to capture progress from scanner
            def scan_progress(val, text):
                self.update_status(text)
                
            results = scan_market(progress_callback=scan_progress)
            
            active = self.load_active_trades()
            
            new_finds = 0
            today = datetime.now().date()
            
            for item in results:
                sym = item['Symbol']
                
                # Check History Cooldown (3 Days)
                is_cooldown = False
                if sym in self.history:
                    try:
                        last_sent = datetime.strptime(self.history[sym], '%Y-%m-%d').date()
                        if (today - last_sent).days < 3:
                            is_cooldown = True
                    except:
                         pass
                
                # Strict check: 
                # 1. Not in Cooldown
                # 2. Not in Active Trades (Already bought/tracking)
                # 3. Not in Queue already
                if (not is_cooldown and 
                    sym not in active and 
                    not any(q['Symbol'] == sym for q in self.publish_queue)):
                    
                    self.publish_queue.append(item)
                    new_finds += 1
            
            self.update_status(f"Scanner done. Added {new_finds} new stocks.")
            print(f"Scanner done. Added {new_finds} new stocks. Queue size: {len(self.publish_queue)}")
            return new_finds
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.update_status(f"Scanner Error: {e}")
            try:
                print(f"Scanner Error: {e}")
            except:
                pass
            return 0

    async def send_message_async(self, message):
        """Async sender with Flood Control"""
        try:
            # Fix Channel ID format if needed
            cid = self.channel_id
            
            # Add small delay to define rate limit (max 20 msgs/min per chat normally)
            time.sleep(1.5) 
            
            # Create bot instance LOCAL to this async/loop context to avoid EventLoopClosed on http client
            async with Bot(token=self.token) as bot:
                await bot.send_message(chat_id=cid, text=message)
            print(f"Sent message to {cid}")
            return True
            
        except RuntimeError as re:
            if "Event loop is closed" in str(re) or "Event loop" in str(re):
                err = f"Telegram Send Error: Event loop closed unexpectedly"
                print(err)
                self.update_status(err)
                return False
            raise
        except Exception as e:
            err_str = str(e)
            if "Retry in" in err_str:
                # Extract seconds
                import re
                seconds = 30 # Default safety
                match = re.search(r'Retry in (\d+) seconds', err_str)
                if match:
                    seconds = int(match.group(1)) + 2 # Add buffer
                
                self.update_status(f"⚠️ Flood limit. Sleeping {seconds}s...")
                print(f"Flood limit hit. Sleeping {seconds}s")
                time.sleep(seconds)
                
                # Retry ONCE recursively
                return await self.send_message_async(message)
                
            err = f"Telegram Send Error: {e}"
            print(err)
            self.update_status(err) # Show error in UI
            return False

    def format_report(self, technical, fundamental):
        """Formats the Telegram message (Simplified User Request)"""
        
        # Clean Stoploss/Target text (Rounded)
        try:
           sl = f"{float(technical['Support'].split('(')[0].strip()):.2f}"
           tgt = f"{float(technical['Resistance'].split('(')[0].strip()):.2f}"
           cmp_val = f"{float(technical['Price']):.2f}"
        except:
           sl = technical['Support'].split('(')[0].strip()
           tgt = technical['Resistance'].split('(')[0].strip()
           cmp_val = technical['Price']

        # Clean Name (Remove .NS)
        clean_name = fundamental['name'].replace('.NS', '')

        msg = f"""Stock: {clean_name}
Recommendation: Buy
CMP: {cmp_val}
Short term target: {tgt}
Stoploss: {sl}

If entering a Day or Swing trade, make sure to use the specified Stoploss."""
        return msg.strip()

    def process_queue_item(self):
        """Picks one item and publishes it"""
        if not self.publish_queue:
            print("Queue empty.")
            return False
            
        # Check if publishing is enabled
        if hasattr(self, 'publishing_enabled') and not self.publishing_enabled:
            self.update_status("Publishing skipped (Disabled).")
            return False

        item = self.publish_queue.pop(0)
        symbol = item['Symbol']
        
        # Double check duplication before sending
        if symbol in self.history:
             try:
                last_sent = datetime.strptime(self.history[symbol], '%Y-%m-%d').date()
                if (datetime.now().date() - last_sent).days < 3:
                     # Double check failed, skip
                     return self.process_queue_item()
             except:
                 pass

        self.update_status(f"Processing {symbol}... Fetching Research")
        print(f"Researching {symbol}...")
        
        try:
            fund_data = get_stock_research(symbol)
            msg = self.format_report(item, fund_data)
            
            self.update_status(f"Sending {symbol} to Telegram...")
            
            # Async run wrapper
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = False
            try:
                # Check loop is running before executing
                if not loop.is_closed():
                    success = loop.run_until_complete(self.send_message_async(msg))
                else:
                    self.update_status(f"Event loop error for {symbol}")
                    return False
                
                if success:
                    # Mark as sent ONLY if successful
                    self.history[symbol] = datetime.now().strftime('%Y-%m-%d')
                    self.save_history()
                    self.update_status(f"Sent {symbol} successfully!")
                    
                    # Save to Active Trades (DISABLED by User Request)
                    # try:
                    #     tgt_str = item['Resistance'].split('(')[0].strip()
                    #     sl_str = item['Support'].split('(')[0].strip()
                    #     trade_entry = {
                    #         'Target': float(tgt_str),
                    #         'Stoploss': float(sl_str),
                    #         'Name': fund_data['name'],
                    #         'EntryPrice': float(item['Price']),
                    #         'EntryDate': datetime.now().strftime('%Y-%m-%d')
                    #     }
                    #     trades = self.load_active_trades()
                    #     trades[symbol] = trade_entry
                    #     self.save_active_trades(trades)
                    # except Exception as e:
                    #     print(f"Tracking error: {e}")
                else:
                    self.update_status(f"Failed to send {symbol}. Not adding to tracking.")
                    
            finally:
                # Allow time for async cleanup before closing loop
                time.sleep(0.5)
                loop.close()
            
            return success
            
        except Exception as e:
            self.update_status(f"Error processing {symbol}: {e}")
            print(f"Process Error: {e}")
            return False

    def load_active_trades(self):
        """Loads active trades to track"""
        if os.path.exists("active_trades.json"):
            try:
                with open("active_trades.json", 'r') as f:
                    return json.load(f)
            except:
                pass
        return {} # Dict: Symbol -> {Target, Stoploss, Name}

    def save_active_trades(self, trades):
        with open("active_trades.json", 'w') as f:
            json.dump(trades, f)

    def monitor_active_trades(self):
        """Checks if any active trade hit Target or SL"""
        trades = self.load_active_trades()
        if not trades: return

        if not trades: return

        self.update_status(f"Monitoring {len(trades)} active trades...")
        print(f"Monitoring {len(trades)} active trades...")
        import yfinance as yf
        import time

        tickers = list(trades.keys())
        completed_trades = []
        
        try:
            # OPTIMIZATION: Download ALL at once. 250 tickers is fine for yfinance in one go.
            # Timeout increased to 60s
            data = yf.download(tickers, period="1d", progress=False, group_by='ticker', threads=True, timeout=60)
            
            # Debug: Check if data was actually downloaded for expected hits
            if "INDIAMART.NS" in tickers:
                if "INDIAMART.NS" in data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else data:
                     print("DEBUG: INDIAMART.NS is in data columns.")
                else:
                     print("DEBUG: INDIAMART.NS MISSING from data columns!")

            # Create Loop ONCE for the batch
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                for sym in tickers:
                    try:
                        # Access Data
                        # If multiple tickers, data is MultiIndex or Dict-like
                        if len(tickers) == 1:
                            df = data
                        else:
                             # key might be missing if download failed
                            try:
                                df = data[sym]
                            except KeyError:
                                # print(f"Missing data for {sym}")
                                continue

                        if df.empty: continue
                        
                        # Check Latest Candle
                        latest = df.iloc[-1]
                        
                        def get_val(item):
                            return item.item() if hasattr(item, "item") else item
                            
                        curr_close = get_val(latest['Close'])
                        curr_high = get_val(latest['High'])
                        
                        trade = trades[sym]
                        target = float(trade['Target'])
                        
                        # Specific Debug for INDIAMART
                        if sym == "INDIAMART.NS":
                            print(f"DEBUG: Checking INDIAMART.NS | High: {curr_high} ({type(curr_high)}) | Target: {target} ({type(target)})")

                        curr_low = get_val(latest['Low']) 
                        
                        trade = trades[sym] # Redundant reload but harmless
                        target = float(trade['Target'])
                        sl = float(trade['Stoploss'])
                        
                        # Clean Name for Alert
                        raw_name = trade.get('Name', sym)
                        name = raw_name.replace('.NS', '')
                        
                        # Get Entry Price (Handle legacy data)
                        entry_price = trade.get('EntryPrice', 'N/A')
                        if entry_price != 'N/A':
                            entry_price = f"{float(entry_price):.2f}"
                        
                        msg = ""
                        if curr_high >= target:
                            msg = f"""Stock: {name}
Status: Target Achieved 🎯
Price Hit: {curr_high:.2f}
"""
                            
                            # print(f"Trade Completed: {sym} -> {msg}") # Disabled risky print
                            print(f"Trade Completed: {sym} - Target Hit!")

                            
                            # Send Alert
                            # loop = asyncio.new_event_loop() # MOVED OUTSIDE
                            # asyncio.set_event_loop(loop)
                            success = False
                            try:
                                success = loop.run_until_complete(self.send_message_async(msg))
                            finally:
                                # loop.close()
                                pass
                            
                            # IMMEDIATE SAVE only if message was sent successfully
                            if success:
                                if sym in trades:
                                    del trades[sym]
                                    self.save_active_trades(trades)
                                    print(f"Removed {sym} from active trades.")
                                
                                completed_trades.append(sym)
                            else:
                                print(f"Failed to send alert for {sym}. Will retry next cycle.")
                            
                    except Exception as e:
                        print(f"Error checking {sym}: {e}")
                        pass
            finally:
                loop.close()

            
            # Remove completed (double check)
            if completed_trades:
                self.update_status(f"Alerted {len(completed_trades)} targets!")
            else:
                self.update_status(f"Checks done. No targets hit.")
                
        except Exception as e:
            print(f"Monitor Download Error: {e}")

    def check_global_kill_signal(self):
        """Checks if a global stop command was issued via file"""
        if os.path.exists("bot_control.json"):
            try:
                with open("bot_control.json", "r") as f:
                    cntrl = json.load(f)
                    if cntrl.get("status") != "running":
                        return True
            except:
                pass
        return False

    def start_scheduler(self):
        """Main Loop: Runs every 15 mins"""
        self.is_running = True
        print("Research Bot Started!")
        self.update_status("Bot Started. Initializing...")
        
        # Initial Scan - REMOVED to allow immediate monitoring in loop
        # self.refresh_queue()
        
        while self.is_running:
            # 0. Global Kill Switch Check
            if self.check_global_kill_signal():
                print("Global Kill Signal Received. Stopping.")
                self.update_status("Bot Stopped (Kill Signal).")
                self.is_running = False
                break

            # 1. Monitor Active Trades (DISABLED)
            # self.monitor_active_trades()
            
            # 2. Publish one item
            sent = self.process_queue_item()
            
            # 3. Check Stop
            if not self.is_running or self.check_global_kill_signal(): break

            # 3. Wait Interval (default 15m or User Defined)
            interval_secs = getattr(self, 'publish_interval', 15) * 60
            
            # If nothing sent (queue empty/disabled), wait 5 mins to retry scan
            # But if queue HAS items, we respect the interval for publishing
            if self.publish_queue:
                wait_time = interval_secs
                next_action = "Publishing Next Alert"
            else:
                 # Queue empty, wait 1 min then rescan (Reduced from 5m)
                wait_time = 60  
                next_action = "Re-Scanning Market"

            self.update_status(f"Waiting {int(wait_time/60)}m... ({next_action})")
            print(f"Waiting {wait_time/60:.1f} mins...")
            
            # Smart Sleep (Check stop signal every 1s)
            for _ in range(int(wait_time)):
                if not self.is_running or self.check_global_kill_signal():
                    print("Stop signal received. Exiting loop.")
                    self.is_running = False
                    break
                time.sleep(1)
            
            if not self.is_running: break

            # 4. Refresh queue if empty
            if not self.publish_queue:
                self.refresh_queue()

if __name__ == "__main__":
    # If run standalone, ensure control file permits it
    with open("bot_control.json", "w") as f:
        json.dump({"status": "running"}, f)
        
    bot = ResearchBot()
    bot.start_scheduler()
