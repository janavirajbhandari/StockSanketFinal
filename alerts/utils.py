from stocks.models import Stock  # Import your Stock model
import time

# Store last alert times for each symbol
_last_alert_times = {}
MIN_ALERT_INTERVAL = 120  # Minimum seconds between alerts for the same symbol

def filter_tracked_symbols(alerts):
    """Filter alerts and prevent duplicates within MIN_ALERT_INTERVAL"""
    if not alerts:
        return []
        
    current_time = time.time()
    filtered_alerts = []
    
    for alert in alerts:
        symbol = alert['symbol']
        last_alert_time = _last_alert_times.get(symbol, 0)
        
        # Only include alert if enough time has passed since last alert for this symbol
        if current_time - last_alert_time >= MIN_ALERT_INTERVAL:
            filtered_alerts.append(alert)
            _last_alert_times[symbol] = current_time
            
    # Clean up old entries from _last_alert_times
    old_threshold = current_time - (MIN_ALERT_INTERVAL * 2)
    _last_alert_times.clear()  # Clear old entries periodically
    
    return filtered_alerts
