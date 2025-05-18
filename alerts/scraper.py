import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

def setup_chrome_options():
    """Setup Chrome options with necessary arguments"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # New headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return chrome_options

def scrape_nepalstock_live(max_retries=3):
    """
    Scrape live market data from NEPSE
    Returns alerts for stocks with price changes >= 7%
    """
    retry_count = 0
    
    while retry_count < max_retries:
        driver = None
        try:
            print(f"🔄 Attempt {retry_count + 1}/{max_retries}")
            print("🔧 Setting up Chrome...")
            
            chrome_options = setup_chrome_options()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            wait = WebDriverWait(driver, 15)  # Increased wait time

            print("🌐 Opening NEPSE live market page...")
            driver.get("https://nepalstock.com.np/live-market")
            
            # Wait for table to load
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr")))
            if not table:
                raise TimeoutException("Table not found")
            
            print("📄 Parsing market data...")
            soup = BeautifulSoup(driver.page_source, "html.parser")

            rows = soup.select("table.table tbody tr")
            if not rows:
                raise ValueError("No market data rows found")
                
            print(f"📊 Found {len(rows)} stocks in market")

            alerts = []
            threshold = 7.0  # 7% threshold for significant changes

            for row in rows:
                try:
                    cols = row.find_all("td")
                    if len(cols) < 6:  # Ensure we have enough columns
                        continue

                    symbol = cols[1].text.strip()
                    ltp = float(cols[2].text.strip().replace(",", "") or 0)  # LTP column
                    point_change = float(cols[4].text.strip().replace(",", "") or 0)  # Point Change column
                    percent_change = float(cols[5].text.strip().replace(",", "") or 0)  # % Change column

                    # Use percentage change for threshold
                    if abs(percent_change) >= threshold:
                        alerts.append({
                            "symbol": symbol,
                            "ltp": ltp,
                            "change": percent_change,  # Changed to match UI expectations
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                        print(f"🚨 Alert: {symbol} changed by {percent_change}% ({point_change} points)")
                except ValueError as e:
                    print(f"⚠️ Error parsing row data: {e}")
                    continue

            print(f"✅ Found {len(alerts)} alerts for stocks with ≥{threshold}% change")
            return alerts

        except TimeoutException as e:
            print(f"⏳ Timeout error: {e}")
        except WebDriverException as e:
            print(f"🌐 WebDriver error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            if driver:
                try:
                    print("🔒 Closing browser...")
                    driver.quit()
                except Exception as e:
                    print(f"⚠️ Error closing browser: {e}")

        retry_count += 1
        if retry_count < max_retries:
            print(f"😴 Waiting 5 seconds before retry...")
            time.sleep(5)

    print("❌ All retry attempts failed")
    return []  # Return empty list after all retries fail
