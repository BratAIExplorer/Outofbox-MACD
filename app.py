import streamlit as st
import pandas as pd
import threading
from telegram_bot import ResearchBot
from research_fetcher import get_stock_research
import time
import os
import json

st.set_page_config(page_title="Arun Research Bot", layout="wide")

# Global Bot Instance (Singleton pattern for Streamlit)
if 'bot_instance' not in st.session_state:
    st.session_state.bot_instance = ResearchBot()
    st.session_state.bot_thread = None

    # Auto-start check
    try:
        with open("bot_control.json", "r") as f:
            if json.load(f).get("status") == "running":
                # Only start if not already running
                t = threading.Thread(target=st.session_state.bot_instance.start_scheduler)
                t.daemon = True
                t.start()
                st.session_state.bot_thread = t
    except Exception as e:
        print(f"Auto-start failed: {e}")

st.title("Arun's Automated Research Bot")

# Sidebar Controls
st.sidebar.header("Bot Control")

# 1. Configuration (Always Visible)
interval = st.sidebar.slider("Publish Interval (Mins)", min_value=1, max_value=60, value=getattr(st.session_state.bot_instance, 'publish_interval', 15))
st.session_state.bot_instance.publish_interval = interval


is_pub = st.sidebar.checkbox("Enable Telegram Publishing", value=getattr(st.session_state.bot_instance, 'publishing_enabled', True))
st.session_state.bot_instance.publishing_enabled = is_pub

if st.sidebar.button("♻️ Reset Daily History"):
    import os
    if os.path.exists("sent_history.json"):
        os.remove("sent_history.json")
    st.session_state.bot_instance.published_today = set()
    st.sidebar.success("History Cleared! Bot will resend alerts.")



st.sidebar.markdown("---")

# 2. Status & Actions
status_placeholder = st.sidebar.empty()

# Live Status File Reader
status_msg = "Idle"
if os.path.exists("bot_status.txt"):
    with open("bot_status.txt", "r") as f:
        status_msg = f.read()

st.sidebar.info(f"📋 **Current Status:**\n{status_msg}")
if st.sidebar.button("Refresh Status"):
    st.rerun()

# 3. System Health
st.sidebar.markdown("---")
st.sidebar.header("🖥️ System Health")
active_python_count = len([p for p in os.popen('tasklist').read().splitlines() if 'python.exe' in p.lower()])
st.sidebar.metric("Active Python Procs", active_python_count)
if active_python_count > 3:
    st.sidebar.warning("⚠️ Multiple processes detected. Consider stopping zombies.")

if st.session_state.bot_thread and st.session_state.bot_thread.is_alive():
    status_placeholder.success(f"Bot Running (Every {interval}m)")
    
    if st.sidebar.button("Stop Bot"):
        # 1. Kill Flag
        with open("bot_control.json", "w") as f:
            json.dump({"status": "stopped"}, f)
            
        st.session_state.bot_instance.is_running = False
        st.rerun()
else:
    status_placeholder.warning("Bot Stopped")
    if st.sidebar.button("Start Bot"):
        # 1. Kill any zombies first
        with open("bot_control.json", "w") as f:
            json.dump({"status": "stopped"}, f)
        
        status_placeholder.text("Cleaning up previous instances...")
        time.sleep(2) # Give zombies time to read the file and die
        
        # 2. Start Request
        with open("bot_control.json", "w") as f:
            json.dump({"status": "running"}, f)
            
        st.session_state.bot_instance = ResearchBot() # Reset
        st.session_state.bot_instance.publishing_enabled = is_pub
        st.session_state.bot_instance.publish_interval = interval
        
        t = threading.Thread(target=st.session_state.bot_instance.start_scheduler)
        t.daemon = True
        t.start()
        st.session_state.bot_thread = t
        st.rerun()

# Main View
tab1, tab2 = st.tabs(["Publish Queue", "Manual Scanner"])

with tab1:
    st.header(f"Next in Queue ({len(st.session_state.bot_instance.publish_queue)})")
    st.info(f"The bot publishes one of these every {interval} minutes to Telegram.")
    
    if st.session_state.bot_instance.publish_queue:
        queue_data = st.session_state.bot_instance.publish_queue
        df = pd.DataFrame(queue_data)
        st.dataframe(df)
        
        if st.button("Force Publish Next Item Now"):
            st.session_state.bot_instance.process_queue_item()
            st.success("Published!")
            time.sleep(1)
            st.rerun()
    else:
        st.write("Queue is empty. Bot will scan automatically.")

with tab2:
    st.header("Test Scanner")
    if st.button("Run Manual Scan"):
        progress_bar = st.progress(0, text="Initializing...")
        
        def update_progress(val, text):
            progress_bar.progress(val, text=text)
            
        from scanner import scan_market
        results = scan_market(progress_callback=update_progress)
        
        # Enrich with Research Data (Announcements)
        if results:
            progress_bar.progress(0.9, text="Fetching Corporate Announcements...")
            for item in results:
                updates = get_stock_research(item['Symbol'])
                item['Corp Actions'] = updates['actions']
                item['Q-Results'] = updates['q_results']
                item['Sector'] = updates['sector']
        
        progress_bar.progress(1.0, text="Done!")
        st.balloons()
        st.dataframe(pd.DataFrame(results), use_container_width=True)
        st.success(f"✅ Found {len(results)} matches")
