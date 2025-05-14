from django.core.management.base import BaseCommand
from stocks.models import Stock
import sys
import os
sys.path.append(os.path.abspath("C:/Users/Bishal/Desktop/Final Project/StockSanket/nepse-data"))


from nepse_data.utils import NepseData
import pandas as pd
import os

class Command(BaseCommand):
    help = "Update or create historical CSV for each stock from NEPSE API."

    def handle(self, *args, **options):
        folder_path = "stock_history"
        os.makedirs(folder_path, exist_ok=True)

        stocks = Stock.objects.exclude(company_id__isnull=True)
        total = stocks.count()
        self.stdout.write(f"Updating historical data for {total} stocks...\n")
        sys.stdout.flush()

        for i, stock in enumerate(stocks, start=1):
            try:
                self.stdout.write(f"[{i}/{total}] Processing {stock.symbol}")
                file_path = os.path.join(folder_path, f"{stock.symbol}.csv")

                existing_df = None
                latest_date = None

                if os.path.exists(file_path):
                    try:
                        existing_df = pd.read_csv(file_path)
                        if "Date" in existing_df.columns and not existing_df.empty:
                            existing_df["Date"] = pd.to_datetime(existing_df["Date"], errors="coerce")
                            latest_date = existing_df["Date"].max()
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Couldn't read existing CSV for {stock.symbol}: {e}"))

                history = NepseData(stock.symbol)
                new_df = history.price_history(latest_date=latest_date)


                if new_df is None or new_df.empty:
                    self.stdout.write(self.style.WARNING(f"No data returned for {stock.symbol}"))
                    sys.stdout.flush()
                    continue

                if "Date" not in new_df.columns:
                    self.stdout.write(self.style.ERROR(f"'Date' column missing for {stock.symbol}"))
                    sys.stdout.flush()
                    continue

                new_df["Date"] = pd.to_datetime(new_df["Date"], errors="coerce")
                new_df.dropna(subset=["Date"], inplace=True)

                if latest_date:
                    new_df = new_df[new_df["Date"] > latest_date]

                if new_df.empty:
                    self.stdout.write(self.style.WARNING(f" {stock.symbol} already up to date"))
                    sys.stdout.flush()
                    continue

                if existing_df is not None:
                    combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset="Date").sort_values("Date")
                else:
                    combined_df = new_df

                combined_df.to_csv(file_path, index=False)
                self.stdout.write(self.style.SUCCESS(f"Updated {stock.symbol} ({len(new_df)} new rows)"))
                sys.stdout.flush()

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating {stock.symbol}: {e}"))
                sys.stdout.flush()

        self.stdout.write(self.style.SUCCESS("\nAll stocks processed. Historical data is now up to date."))
        sys.stdout.flush()
