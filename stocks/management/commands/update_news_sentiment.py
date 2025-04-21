
import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "merolagani_news.csv")
NOTEBOOK_PATH = os.path.join(BASE_DIR, "stock_sentiment_score.ipynb")

def scrape_latest_news():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        print("❌ Chrome failed to launch:", e)
        return

    try:
        url = "https://merolagani.com/NewsList.aspx?catid=all"
        driver.get(url)
        time.sleep(2)

        while True:
            try:
                load_more = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lbtnMore")
                if not load_more.is_displayed():
                    break
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(1)
            except:
                break

        soup = BeautifulSoup(driver.page_source, "html.parser")
        articles = soup.select(".media-news")
        scraped = []

        for art in articles:
            try:
                title = art.find("h4").get_text(strip=True)
                link = art.find("a")["href"]
                date = art.select_one(".media-date").get_text(strip=True)
                full_link = f"https://merolagani.com{link}"
                scraped.append({"title": title, "link": full_link, "date": date})
            except:
                continue

        if not scraped:
            print("⚠️ No new articles found.")
            return

        new_df = pd.DataFrame(scraped)
        new_df = new_df.drop_duplicates(subset="link")

        if os.path.exists(CSV_PATH):
            old_df = pd.read_csv(CSV_PATH)
            combined = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates(subset="link")
        else:
            combined = new_df

        combined.to_csv(CSV_PATH, index=False)
        print(f"✅ Scraped {len(new_df)} new articles. Total: {len(combined)} saved.")

    except Exception as e:
        print("❌ Scraping failed:", e)
    finally:
        driver.quit()

def run_sentiment_notebook():
    try:
        with open(NOTEBOOK_PATH) as f:
            nb = nbformat.read(f, as_version=4)

        ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
        ep.preprocess(nb, {'metadata': {'path': BASE_DIR}})

        with open(NOTEBOOK_PATH, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)

        print("✅ Sentiment notebook executed successfully.")
    except Exception as e:
        print("❌ Error running notebook:", e)

if __name__ == "__main__":
    print("🚀 Starting update_news_sentiment.py")
    scrape_latest_news()
    run_sentiment_notebook()
    print("🏁 Done.")
