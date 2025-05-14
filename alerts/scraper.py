from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_nepalstock_live():
    print("🔧 Launching Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print("🌐 Opening NEPSE live market page...")
        driver.get("https://nepalstock.com.np/live-market")
        time.sleep(7)  # Wait for JavaScript to run
        print("📄 Parsing HTML...")
        soup = BeautifulSoup(driver.page_source, "html.parser")

        rows = soup.select("table.table tbody tr")
        print(f"🧪 Rows found: {len(rows)}")

        alerts = []

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            symbol = cols[1].text.strip()
            ltp = float(cols[3].text.strip().replace(",", "") or 0)
            change = float(cols[4].text.strip().replace(",", "") or 0)

            if abs(change) >= 3:
                alerts.append({
                    "symbol": symbol,
                    "ltp": ltp,
                    "change": change,
                })

        print(f"✅ Alerts: {alerts}")
        return alerts

    except Exception as e:
        print(f"❌ Scraping error: {e}")

    finally:
        driver.quit()
