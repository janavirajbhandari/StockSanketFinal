import os
import pandas as pd
from deep_translator import GoogleTranslator
from django.conf import settings
import django

# Step 1: Setup Django
print("⚙️ Setting up Django environment...")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "StockSanket.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from stocks.models import Stock
print("✅ Django environment loaded.\n")

# Step 2: Define file paths
NEWS_FILE = "merolagani_news.csv"
SENTIMENT_FILE = "stock_sentiment_news.csv"

# Step 3: Load all news
if not os.path.exists(NEWS_FILE):
    print("❌ merolagani_news.csv not found. Aborting.")
else:
    print("📂 Loading news from merolagani_news.csv...")
    news_df = pd.read_csv(NEWS_FILE)
    
    if "title" not in news_df.columns:
        print("❌ 'title' column is missing in merolagani_news.csv. Aborting.")
    else:
        print(f"📄 Total news items found: {len(news_df)}")

        # Step 4: Load stock company names
        print("🏢 Fetching company names from Stock table...")
        companies = list(Stock.objects.values_list("company_name", flat=True))
        print(f"✅ {len(companies)} companies loaded.\n")

        # Step 5: Load already processed sentiment entries
        if os.path.exists(SENTIMENT_FILE):
            print("📑 Loading previously processed sentiment data...")
            existing_df = pd.read_csv(SENTIMENT_FILE)
            processed_titles = set(existing_df["title"].dropna().tolist())
            print(f"🔁 Already processed news count: {len(processed_titles)}")
        else:
            print("📄 No existing sentiment file found. Starting fresh.")
            existing_df = pd.DataFrame()
            processed_titles = set()

        # Step 6: Translate and match news
        new_records = []
        print("🔍 Starting news translation and company match...")
        for idx, row in news_df.iterrows():
            original_title = row["title"]
            if original_title in processed_titles:
                continue

            try:
                translated = GoogleTranslator(source='auto', target='en').translate(original_title)
                print(f"🌐 Translated [{idx + 1}/{len(news_df)}]: {original_title} ➝ {translated}")
                for company in companies:
                    if company.lower() in translated.lower():
                        print(f"✅ Match found for company: {company}")
                        new_records.append({
                            "original": original_title,
                            "translated": translated,
                            "company": company,
                            "link": row.get("link", ""),
                            "date": row.get("date", ""),
                            "image": row.get("image", "")
                        })
                        break
            except Exception as e:
                print(f"❌ Translation failed for: {original_title} — {e}")
                continue

        # Step 7: Save matched sentiment data
        if new_records:
            print("\n💾 Saving new sentiment records...")
            new_df = pd.DataFrame(new_records)
            combined = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates(subset=["original", "company"])
            combined.to_csv(SENTIMENT_FILE, index=False, encoding="utf-8-sig")
            print(f"✅ {len(new_df)} new sentiment records saved to stock_sentiment_news.csv")
        else:
            print("📭 No new sentiment data to update.")
