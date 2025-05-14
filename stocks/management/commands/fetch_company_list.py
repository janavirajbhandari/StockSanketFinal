# management/commands/fetch_company_list.py

import requests
from django.core.management.base import BaseCommand
from stocks.models import Stock

class Command(BaseCommand):
    help = 'Fetch and save companies from Nepse API'

    def handle(self, *args, **kwargs):
        url = "http://localhost:8000/CompanyList"
        response = requests.get(url)
        if response.status_code == 200:
            companies = response.json()
            added = 0
            updated = 0
            for company in companies:
                stock, created = Stock.objects.update_or_create(
                    symbol=company['symbol'],
                    defaults={
                        'company_id': company['id'],
                        'company_name': company['companyName'],
                        'security_name': company['securityName'],
                        'status': company['status'],
                        'company_email': company.get('companyEmail', ''),
                        'website': company.get('website', ''),
                        'sector_name': company['sectorName'],
                        'regulatory_body': company['regulatoryBody'],
                        'instrument_type': company['instrumentType'],
                    }
                )
                if created:
                    added += 1
                else:
                    updated += 1
            self.stdout.write(self.style.SUCCESS(f"✅ Added {added}, Updated {updated} companies"))
        else:
            self.stdout.write(self.style.ERROR("❌ Failed to fetch Company List"))
