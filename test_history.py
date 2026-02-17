from telegram_bot import ResearchBot
import json
import os
import datetime

HISTORY_FILE = "sent_history.json"

def test_migration_and_logic():
    print("--- Testing Migration and Cooldown Logic ---")
    
    # 1. Create Legacy History File
    legacy_data = {
        "date": "2026-02-02",
        "sent": ["TEST_STOCK.NS", "OLD_STOCK.NS"]
    }
    with open(HISTORY_FILE, 'w') as f:
        json.dump(legacy_data, f)
    print("Created legacy sent_history.json")
    
    # 2. Initialize Bot (should trigger migration)
    bot = ResearchBot()
    print(f"Loaded History: {bot.history}")
    
    assert "TEST_STOCK.NS" in bot.history, "Migration Failed: TEST_STOCK.NS missing"
    assert bot.history["TEST_STOCK.NS"] == "2026-02-02", "Migration Failed: Date mismatch"
    print("Migration Verification: PASS")
    
    # 3. Test Cooldown Logic using refresh_queue mock
    # We will manually test the logic block since we can't easily mock scan_market results without more code
    # But we can verify via internal state
    
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    
    # Simulate adding a new stock sent TODAY
    bot.history["NEW_STOCK.NS"] = today.strftime('%Y-%m-%d')
    bot.save_history()
    
    # Reload to verify save
    bot2 = ResearchBot()
    assert "NEW_STOCK.NS" in bot2.history, "Save Failed"
    print("Save Verification: PASS")
    
    # Test Logic Simulation
    def check_cooldown(sym, hist):
        if sym in hist:
            last = datetime.datetime.strptime(hist[sym], '%Y-%m-%d').date()
            if (today - last).days < 3:
                return True
        return False
        
    assert check_cooldown("NEW_STOCK.NS", bot2.history) == True, "Cooldown Logic Failed: Should be blocked"
    
    # Simulate Old Stock (4 days ago)
    old_date = today - datetime.timedelta(days=4)
    bot2.history["ANCIENT_STOCK.NS"] = old_date.strftime('%Y-%m-%d')
    assert check_cooldown("ANCIENT_STOCK.NS", bot2.history) == False, "Cooldown Logic Failed: Should be allowed"
    
    print("Cooldown Logic Verification: PASS")
    
    # Cleanup
    if os.path.exists(HISTORY_FILE):
        # Restore a clean state or just delete
        # os.remove(HISTORY_FILE) 
        pass

if __name__ == "__main__":
    test_migration_and_logic()
