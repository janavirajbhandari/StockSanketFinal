from django.core.management.base import BaseCommand
from stocks.models import Stock
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from webdriver_manager.chrome import ChromeDriverManager

class Command(BaseCommand):
    help = "Scrape stocks from Merolagani and fetch full data from NepalStock"

    def handle(self, *args, **kwargs):

        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("user-agent=Mozilla/5.0")
        service = Service(ChromeDriverManager().install())

        service = Service(executable_path=chrome_driver_path)
        main_driver = webdriver.Chrome(service=service, options=options)
        nepse_driver = webdriver.Chrome(service=service, options=options)

        try:
            print("\U0001F310 Opening Merolagani...")
            main_driver.get("https://merolagani.com/CompanyList.aspx")
            self.dismiss_alert(main_driver)

            wait = WebDriverWait(main_driver, 15)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".panel-title a")))

            sectors = main_driver.find_elements(By.CSS_SELECTOR, ".panel-title a")
            total_sectors = len(sectors)
            print(f"Found {total_sectors} sectors")

            added, updated = 0, 0

            for sector_index in range(total_sectors):
                sectors = main_driver.find_elements(By.CSS_SELECTOR, ".panel-title a")
                sector = sectors[sector_index]
                sector_name = sector.text.strip()

                print(f"\U0001F4C2 Opening sector: {sector_name}")
                main_driver.execute_script("arguments[0].click();", sector)
                time.sleep(2)
                self.dismiss_alert(main_driver)

                rows = main_driver.find_elements(By.CSS_SELECTOR, "table.table-hover tbody tr")

                for row in rows:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) < 2:
                            continue

                        symbol = cols[0].text.strip()
                        company = cols[1].text.strip()

                        if not symbol or not company:
                            print("⚠️ Empty symbol/company. Skipping row...")
                            continue

                        company_data = self.fetch_nepse_data(nepse_driver, symbol)

                        if not company_data:
                            print(f"⚠️ Failed fetching NEPSE data for {symbol}. Skipping...")
                            continue

                        stock, created = Stock.objects.get_or_create(symbol=symbol)

                        stock.company = company
                        stock.company_id = company_data.get("company_id")
                        stock.industry = sector_name
                        stock.sector = company_data.get("sector")
                        stock.market_cap = company_data.get("market_cap")
                        stock.listed_shares = company_data.get("listed_shares")
                        stock.last_price = company_data.get("last_price")
                        stock.save()

                        if created:
                            added += 1
                            print(f"✅ Added {symbol} - {company}")
                        else:
                            updated += 1
                            print(f"🔄 Updated {symbol} - {company}")

                    except Exception as e:
                        print(f"❌ Error parsing stock row: {str(e)}")

            print(f"\n\U0001F3AF Done. Total Added: {added}, Total Updated: {updated}")

        finally:
            main_driver.quit()
            nepse_driver.quit()

    def dismiss_alert(self, driver):
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.dismiss()
            print("⚡ Dismissed popup alert")
        except:
            print("✅ No popup alert")

    def fetch_nepse_data(self, driver, symbol):
        try:
            driver.get("https://www.nepalstock.com")
            wait = WebDriverWait(driver, 10)

            search_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="Symbol or Company Name"]'))
            )
            search_box.clear()
            search_box.send_keys(symbol)
            time.sleep(1)

            first_option = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".dropdown-item"))
            )
            driver.execute_script("arguments[0].click();", first_option)

            wait.until(lambda d: "/company/detail/" in d.current_url)
            current_url = driver.current_url

            match = re.search(r"/company/detail/(\d+)", current_url)
            company_id = int(match.group(1)) if match else None

            def get_value(label):
                rows = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")
                for row in rows:
                    try:
                        th = row.find_element(By.TAG_NAME, "th")
                        td = row.find_element(By.TAG_NAME, "td")
                        if label.lower() in th.text.lower():
                            return td.text.strip()
                    except:
                        continue
                return ""

            sector = get_value("Sector:")
            market_cap = get_value("Market Capitalization")
            listed_shares = get_value("Total Listed Shares")

            raw_price = get_value("Last Traded Price")
            last_price = 0.0
            if raw_price:
                price_match = re.match(r"([\d,]+\.\d+)", raw_price)
                if price_match:
                    last_price = float(price_match.group(1).replace(",", ""))

            return {
                "company_id": company_id,
                "sector": sector,
                "market_cap": market_cap,
                "listed_shares": listed_shares,
                "last_price": last_price,
            }

        except Exception as e:
            print(f"⚠️ NEPSE fetch error for {symbol}: {str(e)}")
            return None