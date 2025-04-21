from django.core.management.base import BaseCommand
from stocks.models import Stock
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from webdriver_manager.chrome import ChromeDriverManager

class Command(BaseCommand):
    help = "Update or add all stocks from Merolagani & verify with NEPSE"

    def handle(self, *args, **kwargs)

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("user-agent=Mozilla/5.0")
        service = Service(ChromeDriverManager().install())

        main_driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
        nepse_driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)

        wait = WebDriverWait(main_driver, 10)

        try:
            self.stdout.write("🌐 Opening Merolagani...")
            main_driver.get("https://merolagani.com/CompanyList.aspx")
            time.sleep(5)

            panels = main_driver.find_elements(By.CSS_SELECTOR, ".panel-title a")
            for panel in panels:
                try:
                    main_driver.execute_script("arguments[0].click();", panel)
                    time.sleep(0.5)
                except:
                    continue

            rows = main_driver.find_elements(By.CSS_SELECTOR, "table.table-hover tbody tr")
            added, updated = 0, 0

            for row in rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 2:
                        continue

                    symbol = cols[0].text.strip()
                    company = cols[1].text.strip()
                    industry = row.find_element(
                        By.XPATH, "ancestor::div[contains(@class, 'panel-collapse')]/preceding-sibling::div//a"
                    ).text.strip()

                    # Fetch NEPSE company_id
                    nepse_driver.get("https://www.nepalstock.com")
                    try:
                        nepse_wait = WebDriverWait(nepse_driver, 10)
                        search_box = nepse_wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'input[placeholder*="Symbol or Company Name"]')
                        ))
                        search_box.clear()
                        search_box.send_keys(symbol)
                        time.sleep(1)

                        first_option = nepse_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".dropdown-item")))
                        nepse_driver.execute_script("arguments[0].click();", first_option)
                        nepse_wait.until(lambda d: "/company/detail/" in d.current_url)
                        current_url = nepse_driver.current_url

                        match = re.search(r"/company/detail/(\d+)", current_url)
                        company_id = int(match.group(1)) if match else None

                        def safe_find(label):
                            try:
                                return nepse_driver.find_element(By.XPATH, f"//td[text()='{label}']/following-sibling::td").text.strip()
                            except:
                                return ""

                        sector = safe_find("Sector:")
                        market_cap = safe_find("Market Capitalization")
                        revenue = safe_find("Revenue")

                        stock, created = Stock.objects.get_or_create(symbol=symbol)
                        changed = False

                        # Always update company name, company_id, industry
                        stock.company = company
                        stock.company_id = company_id
                        stock.industry = industry

                        # Only update if missing or blank
                        if not stock.sector:
                            stock.sector = sector
                            changed = True
                        if not stock.market_cap:
                            stock.market_cap = market_cap
                            changed = True
                        if not stock.revenue:
                            stock.revenue = revenue
                            changed = True

                        stock.save()

                        if created:
                            added += 1
                            self.stdout.write(self.style.SUCCESS(f"✅ Added {symbol} - {company} [ID: {company_id}]"))
                        elif changed:
                            updated += 1
                            self.stdout.write(self.style.SUCCESS(f"🔄 Updated {symbol} with new fields"))

                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"⚠️ NEPSE fetch error for {symbol}: {e}"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Row parse error: {e}"))

            self.stdout.write(self.style.SUCCESS(f"🎉 Done. Added: {added}, Updated: {updated}"))

        finally:
            main_driver.quit()
            nepse_driver.quit()
