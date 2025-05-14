import time
from alerts.scraper import scrape_nepalstock_live
from alerts.utils import filter_tracked_symbols
from alerts.notify import notify_clients

def run_alert_loop():
    while True:
        try:
            print("⏳ Scraping Nepse...")  # 👈 ADD THIS
            all_alerts = scrape_nepalstock_live()
            filtered = filter_tracked_symbols(all_alerts)
            if filtered:
                print(f"🚨 ALERTS: {filtered}")  # 👈 AND THIS
                notify_clients(filtered)
            else:
                print("✅ No major fluctuations.")
        except Exception as e:
            print(f"❌ Error in alert loop: {e}")
        time.sleep(30)
