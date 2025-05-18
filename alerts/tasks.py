import time
from alerts.scraper import scrape_nepalstock_live
from alerts.utils import filter_tracked_symbols
from alerts.notify import notify_clients
import logging

logger = logging.getLogger(__name__)

def run_alert_loop():
    print("🚀 Starting alert loop...")
    last_run_time = 0
    INTERVAL = 120  # 2 minutes in seconds
    
    while True:
        try:
            current_time = time.time()
            # Check if enough time has passed since last run
            if current_time - last_run_time < INTERVAL:
                time_to_wait = INTERVAL - (current_time - last_run_time)
                if time_to_wait > 0:
                    print(f"⏳ Waiting {time_to_wait:.0f} seconds until next check...")
                    time.sleep(time_to_wait)
                    continue

            print("⏳ Scraping Nepse...")
            all_alerts = scrape_nepalstock_live()
            filtered = filter_tracked_symbols(all_alerts)
            
            if filtered:
                print(f"🚨 ALERTS: {filtered}")
                notify_clients(filtered)
            else:
                print("✅ No major fluctuations.")
            
            last_run_time = time.time()
            
        except Exception as e:
            logger.error(f"❌ Error in alert loop: {str(e)}", exc_info=True)
            print(f"❌ Error in alert loop: {e}")
            # Wait a bit before retrying after an error
            time.sleep(30)
