import os
import sys
from datetime import datetime
import subprocess
import pandas as pd
def run_command(command, description):
    """Run a command and print its output in real-time"""
    print(f"\n🚀 {description}...")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
        if process.poll() != 0:
            print(f"❌ {description} failed!")
            return False
        print(f"✅ {description} completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def should_run_sentiment_analysis():
    """Check if there are new news items that require sentiment analysis"""
    try:
        # Check if both required files exist
        if not os.path.exists("merolagani_news.csv") or not os.path.exists("stock_sentiment_news.csv"):
            return True  # Run if either file doesn't exist
            
        # Get modification times
        merolagani_mod_time = os.path.getmtime("merolagani_news.csv")
        sentiment_mod_time = os.path.getmtime("stock_sentiment_news.csv")
        
        # If merolagani_news.csv is newer, we have new news to process
        return merolagani_mod_time > sentiment_mod_time
    except Exception as e:
        print(f"Error checking file modifications: {e}")
        return True  # Run analysis if there's any error checking



if __name__ == "__main__":
    print("Update started at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # Move to project base dir just in case it's run from Task Scheduler
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)

    # 1. Update Merolagani news and translate
    news_update_success = run_command(
        "python manage.py update_news_sentiment",
        "Update and translate MeroLagani news"
    )

    # 2. Run sentiment analysis only if there are new news items
    if news_update_success and should_run_sentiment_analysis():
        run_command(
            "python stock_sentiment_analysis.py",
            "Run sentiment analysis"
        )
    else:
        print("\nℹ️ No new news updates, skipping sentiment analysis.")

    print("\nUpdate finished at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

