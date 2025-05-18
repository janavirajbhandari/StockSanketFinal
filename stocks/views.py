import re
import feedparser  
import os
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from .models import Watchlist, Stock
from django.shortcuts import render, get_object_or_404
import requests
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from django.db.models import Q
from .models import Stock 
from django.conf import settings



def ajax_search_stocks(request):
    query = request.GET.get('query', '').upper()
    if query:
        stocks = Stock.objects.filter(
            Q(symbol__istartswith=query) |
            Q(security_name__icontains=query)
        )[:7]

        results = [
            {'symbol': stock.symbol, 'name': stock.security_name}
            for stock in stocks
        ]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})


def stock_history_partial(request):
    symbol = request.GET.get("symbol")
    page = request.GET.get("page")

    csv_path = os.path.join(BASE_DIR, "stock_history", f"{symbol.upper()}.csv")
    try:
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("date", ascending=False)

        df = df.rename(columns={
            "Open": "open_price",
            "High": "high_price",
            "Low": "low_price",
            "Close": "close_price",
            "% change": "adj_close_price",
            "Volume": "volume"
        })

        historical_data = df.to_dict(orient="records")
        paginator = Paginator(historical_data, 10)
        page_obj = paginator.get_page(page)

        html = render_to_string("partials/history_table.html", {
            "historical_data": page_obj,
            "stock": {"symbol": symbol}
        })
        return JsonResponse({"html": html})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def fetch_live_data_from_nepseapi(symbol):
    try:
        combined_data = {}
        timeout_duration = 5  # Increased timeout to 5 seconds
        api_success = False

        # Try to get data from PriceVolume
        try:
            price_volume_url = "http://localhost:8001/PriceVolume"
            price_volume_response = requests.get(price_volume_url, timeout=timeout_duration)
            if price_volume_response.status_code == 200:
                price_volume_data = price_volume_response.json()
                # Find matching symbol
                for item in price_volume_data:
                    if item["symbol"].upper() == symbol.upper():
                        combined_data.update({
                            "last_traded_price": item.get("lastTradedPrice"),
                            "percentage_change": item.get("percentageChange"),
                            "previous_close": item.get("previousClose"),
                            "total_trade_quantity": item.get("totalTradeQuantity"),
                        })
                        api_success = True
                        break
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching PriceVolume data: {e}")

        # Try to get data from LiveMarket
        try:
            live_market_url = "http://localhost:8001/LiveMarket"
            live_market_response = requests.get(live_market_url, timeout=timeout_duration)
            if live_market_response.status_code == 200:
                live_market_data = live_market_response.json()
                # Find matching symbol
                for item in live_market_data:
                    if item["symbol"].upper() == symbol.upper():
                        combined_data.update({
                            "open_price": item.get("openPrice"),
                            "high_price": item.get("highPrice"),
                            "low_price": item.get("lowPrice"),
                            "volume": item.get("totalTradeQuantity"),
                            "total_trade_value": item.get("totalTradeValue"),
                            "last_traded_price": item.get("lastTradedPrice"),
                            "percentage_change": item.get("percentageChange"),
                            "previous_close": item.get("previousClose"),
                        })
                        api_success = True
                        break
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching LiveMarket data: {e}")

        # Try to get company details
        try:
            details_url = f"http://localhost:8001/CompanyDetails?symbol={symbol}"
            detail_response = requests.get(details_url, timeout=timeout_duration)
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                daily = detail_data.get("securityDailyTradeDto", {})
                combined_data.update({
                    "businessDate": daily.get("businessDate"),
                    "fifty_two_week_high": daily.get("fiftyTwoWeekHigh"),
                    "fifty_two_week_low": daily.get("fiftyTwoWeekLow"),
                    "market_cap": detail_data.get("marketCapitalization"),
                    "public_shares": detail_data.get("publicShares"),
                    "promoter_shares": detail_data.get("promoterShares")
                })
                api_success = True
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching SecurityDetails: {e}")

        # If no API calls succeeded, try CSV
        if not api_success:
            print("⚠️ API calls failed, trying to get data from CSV...")
            try:
                csv_path = os.path.join(BASE_DIR, "stock_history", f"{symbol.upper()}.csv")
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    if not df.empty:
                        latest_row = df.iloc[-1]
                        combined_data.update({
                            "last_traded_price": latest_row.get("Close"),
                            "percentage_change": latest_row.get("% change", 0),
                            "open_price": latest_row.get("Open"),
                            "high_price": latest_row.get("High"),
                            "low_price": latest_row.get("Low"),
                            "volume": latest_row.get("Volume", 0),
                            "previous_close": df.iloc[-2].get("Close") if len(df) > 1 else latest_row.get("Close"),
                        })
                        print("✅ Successfully loaded data from CSV")
            except Exception as e:
                print(f"❌ Error loading from CSV: {e}")

        # Always return combined_data, even if some fields are missing
        return combined_data

    except Exception as e:
        print(f"❌ Error in fetch_live_data_from_nepseapi: {str(e)}")
        return {}



def calculate_nepse_start_date(timeframe):
    today = datetime.today()
    if timeframe == "1M":
        return today - timedelta(days=30)
    elif timeframe == "6M":
        return today - timedelta(days=180)
    elif timeframe == "YTD":
        return datetime(today.year, 1, 1)
    elif timeframe == "1Y":
        return today - timedelta(days=365)
    elif timeframe == "5Y":
        return today - timedelta(days=5 * 365)
    elif timeframe == "10Y":
        return today - timedelta(days=10 * 365)
    return today - timedelta(days=30)



import os


import pandas as pd
from datetime import datetime

import json
import os
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import os, json
from .models import Stock


CSV_PATH = r"C:\Users\Bishal\Desktop\Final Project\StockSanket\merolagani_news.csv"

def mero_news_view(request):
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["title", "link"])  # Ensure clean rows

    # Convert "date" to datetime safely
    # Parse multiple date formats
    from dateutil import parser

    def parse_date_safe(date_str):
        try:
            return parser.parse(date_str)
        except:
            return pd.NaT

    df["date"] = df["date"].apply(parse_date_safe)
    df = df.dropna(subset=["date"])
    df = df.sort_values(by="date", ascending=False)


    # Convert datetime to string before sending to template
    df["date"] = df["date"].dt.strftime("%Y-%m-%d %H:%M")

    # Build dictionary list
    # Add csv_index to each article
    articles = []
    for idx, row in df.iterrows():
        article = row.to_dict()
        article["csv_index"] = idx  # ✅ Add index
        articles.append(article)


    # Pagination (8 per page)
    paginator = Paginator(articles, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    trending = articles[:5]  # Just top 5 articles (no pagination)

    return render(request, "news.html", {
        "news": page_obj,
        "trending": trending
    })


def news_detail(request, news_id):
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["link", "title", "date"]).reset_index(drop=True)

    try:
        article_data = df.iloc[int(news_id)]
        url = article_data["link"]

        response = requests.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        img_tag = soup.find("img")
        featured_image_url = img_tag['src'] if img_tag else None

        content_div = soup.find("div", id="ctl00_ContentPlaceHolder1_newsDetail")
        content_html = content_div.decode_contents() if content_div else "Content not available"

        context = {
            "article": {
                "title": article_data["title"],
                "date": article_data["date"], 
                "content": content_html,
                "image_url": featured_image_url
            }
        }

        return render(request, "news_detail.html", context)

    except Exception as e:
        return render(request, "news_detail.html", {
            "article": {
                "title": "Error loading article",
                "date": "",
                "content": f"❌ Error: {str(e)}"
            }
        })


def compare_stocks_view(request):
    symbol = request.GET.get("symbol", "").upper()
    timeframe = request.GET.get("timeframe", "10Y")

    # ✅ Load from local CSV instead of API
    historical_data = []
    csv_path = os.path.join(BASE_DIR, "stock_history", f"{symbol.upper()}.csv")

    # 1. Try loading from CSV first
    try:
        df = pd.read_csv(csv_path)
    
        
        # ✅ Clean and process the DataFrame
        df.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
        df.dropna(subset=["date", "open", "high", "low", "close"], inplace=True)
        df.sort_values("date", inplace=True)
        df.drop_duplicates(subset=["date"], keep="first", inplace=True)

        # Generate chart data
        historical_chart_data = []
        for _, row in df.iterrows():
            if all(x > 0 and pd.notna(x) for x in [row["open"], row["high"], row["low"], row["close"]]):
                historical_chart_data.append({
                    "time": int(row["date"].timestamp()),
                    "open": round(row["open"], 2),
                    "high": round(row["high"], 2),
                    "low": round(row["low"], 2),
                    "close": round(row["close"], 2),
                })
    except Exception as e:
        print("⚠️ Error loading chart history from CSV or API:", e)
        historical_chart_data = []



    return render(request, "compares.html", {
        "symbol": symbol,
        "historical_data": historical_data,
        "timeframe": timeframe,
    })


from .models import Watchlist


@csrf_exempt
def add_to_watchlist(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            symbol = data.get("symbol")
            company = data.get("company")
            price = data.get("price")
            volume = data.get("volume")
            market_cap = data.get("market_cap")
            public_shares = data.get("public_shares")
            week_52 = data.get("week_52")

            print("🔍 Data received:", data)

            if Watchlist.objects.filter(symbol=symbol).exists():
                return JsonResponse({
                    "success": True,
                    "message": f"{symbol} is already in your watchlist."
                })

            Watchlist.objects.create(
                symbol=symbol,
                company=company,
                price=price,
                volume=volume,
                market_cap=int(float(str(market_cap).replace(",", ""))),  # 🛠 FIXED HERE
                public_shares=public_shares,
                week_52=week_52,
            )

            return JsonResponse({
                "success": True,
                "message": f"{symbol} was successfully added to your watchlist!"
            })

        except Exception as e:
            print("❌ Error adding to watchlist:", e)
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)



def watchlist_view(request):
    watchlist_stocks = Watchlist.objects.all()

    watchlist_data = []
    for stock in watchlist_stocks:
        watchlist_data.append({
            "symbol": stock.symbol,
            "company": stock.company,
            "price": stock.price or "N/A",
            "volume": stock.volume or "N/A",
            "public_shares": stock.public_shares or "N/A",
            "week_52": stock.week_52 or "N/A",
            "market_cap": stock.market_cap or "N/A",
        })

    return render(request, "watchlists.html", {"watchlist": watchlist_data})



@csrf_exempt
def remove_from_watchlist(request):
    """
    Removes a stock from the watchlist.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            symbol = data.get("symbol")

            Watchlist.objects.filter(symbol=symbol).delete()
            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


def fetch_blog_articles():
    """
    Fetches latest stock market blog articles from Yahoo Finance.
    """
    feed = feedparser.parse(YAHOO_FINANCE_BLOG_RSS)

    articles = []
    for entry in feed.entries[:12]:  # Fetch latest 12 articles for grid layout
        image_url = None
        if "media_content" in entry:
            image_url = entry.media_content[0]["url"] if entry.media_content else None

        articles.append({
            "title": entry.title,
            "link": entry.link,
            "image": image_url,
            "summary": entry.summary if "summary" in entry else "No summary available.",
            "author": entry.author if "author" in entry else "Unknown",
            "published_date": entry.published
        })

    return articles

def blog_articles_view(request):
    """
    View to display latest blog articles.
    """
    articles = fetch_blog_articles()
    return render(request, "articles.html", {
        "articles": articles
    })



from django.db.models import Q
from django.core.paginator import Paginator
from .models import Stock

def StocksView(request):
    query = request.GET.get("q", "").strip()
    page = request.GET.get("page")

    stocks_queryset = Stock.objects.all()
    if query:
        stocks_queryset = stocks_queryset.filter(
            Q(symbol__icontains=query) |
            Q(company_name__icontains=query)
        )

    paginator = Paginator(stocks_queryset, 40)
    stocks_page = paginator.get_page(page)

    # Get unique sector and regulatory names
    sectors = Stock.objects.values_list('sector_name', flat=True).distinct()
    regulators = Stock.objects.values_list('regulatory_body', flat=True).distinct()

    return render(request, "stocks.html", {
        "stocks": stocks_page,
        "query": query,
        "total_results": stocks_queryset.count(),
        "sectors": sectors,
        "regulators": regulators
    })


def get_stock_data(request, symbol):
    try:
        # Validate symbol
        if not symbol or symbol.isspace():
            return JsonResponse({"error": "Symbol is required"}, status=400)
            
        symbol = symbol.upper()
        timeframe = request.GET.get("timeframe", "1Y")
        start_date = calculate_nepse_start_date(timeframe)

        # Get live market data using existing function
        live_data = fetch_live_data_from_nepseapi(symbol)
        if not live_data:
            print(f"❌ No live data found for {symbol}")
            live_data = {}

        # Get turnover data
        turnover_url = "http://localhost:8001/TradeTurnoverTransactionSubindices"
        try:
            turnover_response = requests.get(turnover_url, timeout=5)
            turnover_data = turnover_response.json()
            # The API returns data in scripsDetails object
            stock_turnover_data = turnover_data.get('scripsDetails', {}).get(symbol)
            if not stock_turnover_data:
                print(f"No turnover data found for {symbol}")
        except Exception as e:
            print(f"Error fetching turnover data: {e}")
            stock_turnover_data = None

        # Ensure the stock_history directory exists
        stock_history_dir = os.path.join(BASE_DIR, "stock_history")
        if not os.path.exists(stock_history_dir):
            os.makedirs(stock_history_dir)

        csv_path = os.path.join(stock_history_dir, f"{symbol}.csv")
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
        else:
            return JsonResponse({"error": f"No historical data found for {symbol}"}, status=404)

        # Clean & transform
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date", "Close"])
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Close"])
        df = df[df["Date"] >= start_date]
        df = df.sort_values("Date")

        # Format output
        dates = df["Date"].dt.strftime("%Y-%m-%d").tolist()
        prices = df["Close"].tolist()

        # Load stock company name
        company = Stock.objects.filter(symbol=symbol).first()
        company_name = company.company_name if company else "N/A"

        # Format market cap from live_data
        market_cap = "N/A"
        if live_data.get('market_cap'):
            market_cap = f"{int(live_data['market_cap']):,}"

        # Get volume and turnover from turnover data
        volume = "N/A"
        turnover = "N/A"
        if stock_turnover_data:
            if 'volume' in stock_turnover_data:
                volume = f"{int(stock_turnover_data['volume']):,}"
            if 'Turnover' in stock_turnover_data:  # Note the capital T in Turnover
                turnover = f"{float(stock_turnover_data['Turnover']):,.2f}"

        return JsonResponse({
            "symbol": symbol,
            "dates": dates,
            "prices": prices,
            "company": company_name,
            "market_cap": market_cap,
            "price": prices[-1] if prices else "N/A",
            "change": round(prices[-1] - prices[-2], 2) if len(prices) >= 2 else "N/A",
            "volume": volume,
            "turnover": turnover
        })

    except Exception as e:
        print("❌ Error in get_stock_data:", e)
        return JsonResponse({"error": "Internal server error"}, status=500)



import os
import json
import pandas as pd
from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Stock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import os, json
import pandas as pd
from .models import Stock

def get_csv_index_from_link(link):
    CSV_PATHs = r"C:\Users\Bishal\Desktop\Final Project\StockSanket\merolagani_news.csv"
    try:
        
        df = pd.read_csv(CSV_PATHs)
        df = df.dropna(subset=["link"]).reset_index()
        row = df[df["link"] == link].iloc[0]
        return int(row["index"])
    except:
        return None
    
import os
import json

import os
import json

def get_prediction_chart_data(symbol):
    import tensorflow as tf
    file_path = os.path.join(BASE_DIR, "predictions", symbol.upper(), f"{symbol.upper()}.json")

    print("📁 Trying to load prediction JSON from:", file_path)

    if not os.path.exists(file_path):
        print("❌ File does NOT exist.")
        return []

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            print("✅ JSON file loaded. Keys:", data.keys())

        # Make sure both keys exist
        past = data.get("past_30_days", [])
        predicted = data.get("predicted_7_days", [])

        if not past and not predicted:
            print("⚠️ No 'past_30_days' or 'predicted_7_days' in JSON.")
            return []

        chart_data = []

        for item in past:
            if "date" in item:
                chart_data.append({
                    "time": int(datetime.strptime(item["date"], "%Y-%m-%d").timestamp()),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "predicted": False
                })

        for item in predicted:
            if "date" in item:
                chart_data.append({
                    "time": int(datetime.strptime(item["date"], "%Y-%m-%d").timestamp()),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "predicted": True
                })


        print(f"✅ Final chart data length: {len(chart_data)}")
        return chart_data

    except Exception as e:
        print(f"❌ Error loading or parsing prediction JSON: {e}")
        return []



from django.utils.safestring import mark_safe


def StockDetail(request):
    symbol = request.GET.get('symbol')  # <-- Get symbol from query parameters
    try:
        stock_data = Stock.objects.filter(symbol=symbol.upper()).first()
        if not stock_data:
            return render(request, "stockDetail.html", {"error": "Stock not found"})

        # Get live data - will always return a dict, even if empty
        live_data = fetch_live_data_from_nepseapi(stock_data.symbol)

        # Calculate price changes if we have the necessary data
        last_price = live_data.get("last_traded_price")
        previous_close = live_data.get("previous_close")
        price_change = "-"
        percentage_change = "-"

        if last_price is not None and previous_close is not None:
            try:
                last_price = float(last_price)
                previous_close = float(previous_close)
                price_change = round(last_price - previous_close, 2)
                percentage_change = round((price_change / previous_close) * 100, 2) if previous_close != 0 else 0
            except (ValueError, TypeError):
                pass

        # Build stock info with fallbacks for missing data
        stock_info = {
            "symbol": stock_data.symbol,
            "company": stock_data.company_name,
            "price": last_price if last_price is not None else "N/A",
            "price_change": price_change,
            "percentage_change": percentage_change,
            "volume": live_data.get("volume", "N/A"),
            "previous_close": previous_close if previous_close is not None else "N/A",
            "high_low": f"{live_data.get('high_price', 'N/A')} / {live_data.get('low_price', 'N/A')}",
            "week_52": f"{live_data.get('fifty_two_week_high', 'N/A')} / {live_data.get('fifty_two_week_low', 'N/A')}",
            "market_cap": f"{int(live_data['market_cap']):,}" if live_data.get("market_cap") else "N/A",
            "public_shares": f"{int(live_data['public_shares']):,}" if live_data.get("public_shares") else "N/A",
            "promoter_shares": f"{int(live_data['promoter_shares']):,}" if live_data.get("promoter_shares") else "N/A",
            "open_price": live_data.get("open_price", "N/A"),
            "close_price": last_price if last_price is not None else "N/A",
            "trades": live_data.get("total_trade_quantity", "N/A"),
            "todays_amount": live_data.get("total_trade_value", "N/A"),
            "date": live_data.get("businessDate", "N/A"),
            "currency": "NPR",
        }

        # Load and clean chart data for overview
        historical_chart_data = []
        csv_path = os.path.join(BASE_DIR, "stock_history", f"{symbol.upper()}.csv")
        try:
            df = pd.read_csv(csv_path)
            df.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close"}, inplace=True)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
            df.dropna(subset=["date", "open", "high", "low", "close"], inplace=True)
            df.sort_values("date", inplace=True)
            df.drop_duplicates(subset=["date"], keep="first", inplace=True)

            for _, row in df.iterrows():
                if all(x > 0 and pd.notna(x) for x in [row["open"], row["high"], row["low"], row["close"]]):
                    historical_chart_data.append({
                        "time": int(row["date"].timestamp()),
                        "open": round(row["open"], 2),
                        "high": round(row["high"], 2),
                        "low": round(row["low"], 2),
                        "close": round(row["close"], 2),
                    })
        except Exception as e:
            print("⚠️ Error loading CSV for chart data:", e)

        # Historical table for history tab
        historical_data = []
        try:
            df2 = pd.read_csv(csv_path)
            df2["date"] = pd.to_datetime(df2["Date"], errors="coerce")
            df2 = df2.sort_values("date", ascending=False)
            df2 = df2.rename(columns={
                "Open": "open_price",
                "High": "high_price",
                "Low": "low_price",
                "Close": "close_price",
                "% change": "adj_close_price",
                "Volume": "volume"
            })
            historical_data = df2.to_dict(orient="records")
            paginator = Paginator(historical_data, 10)
            page_number = request.GET.get("history_page")
            page_obj = paginator.get_page(page_number)
        except Exception as e:
            print("⚠️ CSV read error:", e)
            page_obj = []

        # Load sentiment data with proper error handling
        sentiment = {}
        sentiment_path = os.path.join(BASE_DIR, "sentiment_data", "sentiment_all_stocks.json")
        try:
            with open(sentiment_path, "r", encoding="utf-8") as f:
                all_sentiments = json.load(f)
                sentiment = all_sentiments.get("stocks", {}).get(symbol.upper(), {})
        except Exception as e:
            print("⚠️ Sentiment file error:", e)

        # Process news with proper error handling
        top_news = []
        extra_articles = []
        try:
            if sentiment.get("top_positive_news", {}).get("title"):
                top_news.append({
                    "title": sentiment["top_positive_news"]["title"],
                    "link": sentiment["top_positive_news"]["link"],
                    "timestamp": sentiment["top_positive_news"].get("date_str", ""),
                    "tag": "positive"
                })
            if sentiment.get("top_negative_news", {}).get("title"):
                top_news.append({
                    "title": sentiment["top_negative_news"]["title"],
                    "link": sentiment["top_negative_news"]["link"],
                    "timestamp": sentiment["top_negative_news"].get("date_str", ""),
                    "tag": "negative"
                })

            shown_links = {a["link"] for a in top_news}
            for a in sentiment.get("articles", []):
                if a.get("link") not in shown_links and len(extra_articles) < 5:
                    extra_articles.append({
                        "title": a.get("title", ""),
                        "link": a.get("link", "#"),
                        "timestamp": a.get("date", ""),
                        "tag": a.get("sentiment", "")
                    })

            # Add CSV Indexes
            for article in top_news + extra_articles:
                article["csv_index"] = get_csv_index_from_link(article["link"])
        except Exception as e:
            print("⚠️ Error processing news:", e)

        # Calculate sentiment scores with proper error handling
        try:
            positive_percent = float(sentiment.get("positive_percent", 0))
            neutral_percent = float(sentiment.get("neutral_percent", 0))
            negative_percent = float(sentiment.get("negative_percent", 0))
            sentiment_scores = [
                ("positive", positive_percent),
                ("neutral", neutral_percent),
                ("negative", negative_percent),
            ]
            top_sentiment_label, top_sentiment_value = max(sentiment_scores, key=lambda x: x[1])
        except Exception as e:
            print("⚠️ Error calculating sentiment scores:", e)
            positive_percent = neutral_percent = negative_percent = 0
            top_sentiment_label, top_sentiment_value = "neutral", 0

        # Check watchlist status
        is_in_watchlist = False
        if request.user.is_authenticated:
            is_in_watchlist = Watchlist.objects.filter(symbol=symbol.upper()).exists()

        # Load prediction data with proper error handling
        prediction_chart_data = []
        predicted_data = []
        try:
            prediction_chart_data = get_prediction_chart_data(symbol)
            if prediction_chart_data:
                predicted_data = [
                    {
                        "date": datetime.fromtimestamp(item["time"]).strftime("%B %d, %Y"),
                        "close": round(item["close"], 2)
                    }
                    for item in prediction_chart_data if item.get("predicted")
                ]
        except Exception as e:
            print(f"❌ Error loading prediction data: {e}")

        context = {
            "stock": stock_info,
            "historical_data": page_obj,
            "historical_chart_data": json.dumps(historical_chart_data) if historical_chart_data else "[]",
            "positive_percent": positive_percent,
            "neutral_percent": neutral_percent,
            "negative_percent": negative_percent,
            "sentiment_label": sentiment.get("sentiment_label", "N/A"),
            "bar_labels": json.dumps(sentiment.get("bar_labels", [])),
            "bar_data": {
                "positive": json.dumps(sentiment.get("bar_data", {}).get("positive", [])),
                "neutral": json.dumps(sentiment.get("bar_data", {}).get("neutral", [])),
                "negative": json.dumps(sentiment.get("bar_data", {}).get("negative", [])),
            },
            "line_sentiment_scores": json.dumps(sentiment.get("line_sentiment_scores", [])),
            "line_sentiment_labels": json.dumps(sentiment.get("line_sentiment_labels", [])),
            "top_news": top_news,
            "extra_news": extra_articles,
            "total_articles": sentiment.get("total_articles", 0),
            "last_updated": sentiment.get("last_updated", "N/A"),
            "top_sentiment_label": top_sentiment_label,
            "top_sentiment_value": top_sentiment_value,
            "is_in_watchlist": is_in_watchlist,
            "prediction_chart_data": json.dumps(prediction_chart_data) if prediction_chart_data else "[]",
            "predicted_data": predicted_data,
        }

        return render(request, "stockDetail.html", context)

    except Exception as e:
        print("❌ Error in StockDetail view:", e)
        return render(request, "stockDetail.html", {
            "error": "Something went wrong while fetching stock details.",
            "details": str(e)
        })


def get_market_data(request, symbol):
    try:
        # Fetch market data using existing function
        market_data = fetch_live_data_from_nepseapi(symbol)
        
        if not market_data:
            response = JsonResponse({'error': f'No data found for symbol {symbol}'}, status=404)
            response["Access-Control-Allow-Origin"] = "*"
            response["Content-Type"] = "application/json"
            return response
        
        # Get company name from Stock model
        stock = Stock.objects.filter(symbol=symbol.upper()).first()
        company_name = stock.security_name if stock else "N/A"
        
        # Format market cap
        market_cap = "N/A"
        if market_data.get('market_cap'):
            market_cap = f"{int(market_data['market_cap']):,}"
            
        # Format the response data
        response_data = {
            'company': company_name,
            'market_cap': market_cap,
            'price': market_data.get('last_traded_price', 'N/A'),
            'change': market_data.get('percentage_change', 'N/A'),
            'volume': f"{int(market_data.get('volume', 0)):,}" if market_data.get('volume') else 'N/A',
            'turnover': f"{float(market_data.get('total_trade_value', 0)):,.2f}" if market_data.get('total_trade_value') else 'N/A'
        }
        
        response = JsonResponse(response_data)
        response["Access-Control-Allow-Origin"] = "*"
        response["Content-Type"] = "application/json"
        return response
    except Exception as e:
        print(f"Error in get_market_data: {str(e)}")
        response = JsonResponse({'error': str(e)}, status=500)
        response["Access-Control-Allow-Origin"] = "*"
        response["Content-Type"] = "application/json"
        return response

def get_prediction_data(request, symbol):
    """Fetch prediction data from the JSON file for a given stock symbol."""
    try:
        print(f"🔍 Fetching prediction data for symbol: {symbol}")
        
        predictions_dir = os.path.join(BASE_DIR, "predictions")
        print(f"📂 Predictions directory: {predictions_dir}")
        
        if not os.path.exists(predictions_dir):
            print(f"❌ Predictions directory not found at: {predictions_dir}")
            return JsonResponse({
                "success": False,
                "error": "Predictions data not available",
                "predicted_7_days": [],
                "message": "Prediction data is not available for this stock yet."
            })
            
        prediction_file = os.path.join(predictions_dir, symbol.upper(), f"{symbol.upper()}.json")
        print(f"📁 Looking for file at: {prediction_file}")
            
        if not os.path.exists(prediction_file):
            print(f"❌ File not found: {prediction_file}")
            return JsonResponse({
                "success": False,
                "error": f"No prediction data found for {symbol}",
                "predicted_7_days": [],
                "message": "Prediction data is not available for this stock yet."
            })
            
        print(f"📖 Reading JSON file for {symbol}")
        with open(prediction_file, 'r') as f:
            prediction_data = json.load(f)
            print(f"✅ JSON data loaded. Keys found: {list(prediction_data.keys())}")
        
        predicted_days = prediction_data.get("predicted_7_days", [])
        if not predicted_days and "past_30_days" in prediction_data:
            past_days = prediction_data["past_30_days"]
            predicted_days = past_days[-7:] if len(past_days) >= 7 else past_days
        
        print(f"📊 Found {len(predicted_days)} predicted days")
        
        valid_predictions = []
        
        for pred in predicted_days:
            if all(key in pred for key in ["date", "open", "high", "low", "close"]):
                try:
                    prediction = {
                        "date": pred["date"],
                        "open": float(pred["open"]),
                        "high": float(pred["high"]),
                        "low": float(pred["low"]),
                        "close": float(pred["close"])
                    }
                    valid_predictions.append(prediction)
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Error processing prediction values: {e}")
                    continue
        
        print(f"✅ Final valid predictions count: {len(valid_predictions)}")
        if not valid_predictions:
            return JsonResponse({
                "success": False,
                "error": "No valid predictions available",
                "predicted_7_days": [],
                "message": "No valid prediction data available for this stock."
            })
        
        valid_predictions.sort(key=lambda x: x["date"])
        
        response_data = {
            "success": True,
            "predicted_7_days": valid_predictions[-7:] if len(valid_predictions) > 7 else valid_predictions,
            "message": "Prediction data loaded successfully."
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Error in get_prediction_data for {symbol}: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return JsonResponse({
            "success": False,
            "error": str(e),
            "predicted_7_days": [],
            "message": "An error occurred while fetching prediction data."
        })
