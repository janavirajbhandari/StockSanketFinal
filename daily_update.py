import os
import subprocess
import sys
from datetime import datetime

def run_command(cmd, label=None):
    print(f"📦 Running: {label or cmd}")
    result = subprocess.run(cmd, shell=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed: {label or cmd}")
    else:
        print(f"✅ Done: {label or cmd}")

if __name__ == "__main__":
    print("🕒 Update started at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # Move to project base dir just in case it's run from Task Scheduler
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR) 

    # 1. Update stock table from Merolagani + NEPSE
    run_command("python manage.py update_stocks", "Update stock details")

    # 2. Update historical stock data
    run_command("python manage.py update_stock_history", "Update historical data")

    # 3. Update Merolagani news CSV by scraping new news only
    run_command("python update_news_sentiment.py", "Update MeroLagani news")

    # 4. Run sentiment notebook to refresh stock sentiments
    run_command("jupyter nbconvert --to notebook --execute --inplace stock_sentiment_score.ipynb", "Run sentiment analysis")

    # 5. Run stock prediction notebook for all stocks
    run_command("python run_all_prediction.py", "Run stock predictions")

    print("🏁 Update finished at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
