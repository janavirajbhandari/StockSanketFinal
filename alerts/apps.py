from django.apps import AppConfig
import os

class AlertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alerts'
    alert_thread_started = False  # Class variable to track thread state

    def ready(self):
        # Check if this is the main process
        if os.environ.get('RUN_MAIN') != 'true':
            return

        # Only start if thread hasn't been started
        if not self.__class__.alert_thread_started:
            try:
                from .tasks import run_alert_loop
                import threading
                alert_thread = threading.Thread(target=run_alert_loop, daemon=True)
                alert_thread.start()
                self.__class__.alert_thread_started = True  # Mark as started using class variable
                print("✅ Alert thread started successfully")
            except ImportError:
                print("❌ Could not start alert thread - tasks.py not found")
                pass  # Handle the case where tasks.py doesn't exist yet 