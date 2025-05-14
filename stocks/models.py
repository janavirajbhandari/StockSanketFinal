
from django.utils.timezone import now

from django.db import models

# models.py
from django.core.paginator import Paginator
# models.py


class Stock(models.Model):
    company_id = models.IntegerField(null=True, blank=True)
    company_name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=20, unique=True)
    security_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10)
    company_email = models.CharField(max_length=255, null=True, blank=True)
    website = models.URLField(max_length=255, null=True, blank=True)
    sector_name = models.CharField(max_length=255)
    regulatory_body = models.CharField(max_length=255)
    instrument_type = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.symbol} - {self.company_name}"


# ✅ Now it’s safe to reference Stock
class HistoricalStockData(models.Model):
    stock = models.ForeignKey(Stock, related_name="historical_data", on_delete=models.CASCADE)
    date = models.DateField(default=now)
    open_price = models.FloatField()
    high_price = models.FloatField()
    low_price = models.FloatField()
    close_price = models.FloatField()
    adj_close_price = models.FloatField()
    volume = models.BigIntegerField()

    def __str__(self):
        return f"{self.stock.symbol} - {self.date}"



class StockPrediction(models.Model):
    stock = models.ForeignKey(Stock, related_name="predictions", on_delete=models.CASCADE)
    date = models.DateField(default=now)
    predicted_price = models.FloatField()

    def __str__(self):
        return f"Prediction for {self.stock.symbol} on {self.date}"


class StockSentiment(models.Model):
    stock = models.ForeignKey(Stock, related_name="sentiment_score", on_delete=models.CASCADE)
    sentiment_score = models.FloatField()
    date = models.DateField(default=now)

    def __str__(self):
        return f"Sentiment for {self.stock.symbol} on {self.date}"



class Watchlist(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    company = models.CharField(max_length=100)
    price = models.FloatField(default=0, null=True, blank=True)
    volume = models.BigIntegerField(default=0, null=True, blank=True)
    public_shares = models.CharField(max_length=100, null=True, blank=True)
    week_52 = models.CharField(max_length=100, null=True, blank=True)
    market_cap = models.BigIntegerField(default=0, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company} ({self.symbol})"



