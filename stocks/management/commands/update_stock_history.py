from django.core.management.base import BaseCommand
from stocks.models import Stock
from nepse_data import NepseData
import pandas as pd
import os
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

folder_path = os.path.join(BASE_DIR, "stock_history")

class Command(BaseCommand):
    help = "Update historical stock data: appends if CSV exists, creates new if not."

    def handle(self, *args, **options):
        folder_path = "stock_history"
        os.makedirs(folder_path, exist_ok=True)

        stocks = Stock.objects.exclude(company_id__isnull=True)
        total = stocks.count()
        self.stdout.write(f"🔁 Updating history for {total} stocks...")

        for i, stock in enumerate(stocks, start=1):
            try:
                self.stdout.write(f"[{i}/{total}] 📈 {stock.symbol}")
                file_path = os.path.join(folder_path, f"{stock.symbol}.csv")

                existing_df = None
                latest_date = None

                if os.path.exists(file_path):
                    existing_df = pd.read_csv(file_path)
                    if not existing_df.empty:
                        latest_date = pd.to_datetime(existing_df["Date"]).max()

                history = NepseData(stock.symbol)
                new_df = history.price_history()

                if new_df is None or new_df.empty:
                    self.stdout.write(self.style.WARNING(f"⚠️ No data for {stock.symbol}"))
                    continue

                new_df["Date"] = pd.to_datetime(new_df["Date"])

                if latest_date:
                    new_df = new_df[new_df["Date"] > latest_date]

                if new_df.empty:
                    self.stdout.write(self.style.WARNING(f"⏩ {stock.symbol} already up to date"))
                    continue

                if existing_df is not None:
                    combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset="Date").sort_values("Date")
                else:
                    combined_df = new_df

                combined_df.to_csv(file_path, index=False)
                self.stdout.write(self.style.SUCCESS(f"✅ Updated {stock.symbol} ({len(new_df)} new rows)"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error updating {stock.symbol}: {e}"))

        self.stdout.write(self.style.SUCCESS("🎉 Finished updating stock history for all stocks."))
