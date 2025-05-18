from django.shortcuts import render,HttpResponse,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from stocks.models import Stock
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
import pandas as pd
from bs4 import BeautifulSoup
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



import requests
from django.http import JsonResponse
from django.db.models import Q

def search_stocks(request):
    query = request.GET.get('q', '')
    if query:
        stocks = Stock.objects.filter(
           Q(symbol__istartswith=query) |
            Q(security_name__icontains=query)
        )[:7]

        data = [
            {'name': stock.security_name, 'symbol': stock.symbol}
            for stock in stocks
        ]
        return JsonResponse({'results': data})
    return JsonResponse({'results': []})


def HomePages(request):
      
      # ✅ Add this inside HomePages view before return statement
        news_df = pd.read_csv(r"C:\Users\Bishal\Desktop\Final Project\StockSanket\merolagani_news.csv")
        news_df = news_df.dropna(subset=["title", "link"])  # Ensure clean rows

        # Convert "date" to datetime safely
        # Parse multiple date formats
        from dateutil import parser

        def parse_date_safe(date_str):
            try:
                return parser.parse(date_str)
            except:
                return pd.NaT

        news_df["date"] = news_df["date"].apply(parse_date_safe)
        news_df = news_df.dropna(subset=["date"])
        news_df = news_df.sort_values(by="date", ascending=False)


        # Convert datetime to string before sending to template
        news_df["date"] = news_df["date"].dt.strftime("%Y-%m-%d %H:%M")

        # Build dictionary list
        # Add csv_index to each article
        articles = []
        for idx, row in news_df.iterrows():
            article = row.to_dict()
            article["csv_index"] = idx  # ✅ Add index
            articles.append(article)

        trending = articles[:7] 

        top_gainers = []
        top_losers = []

        # --- Fetch Top Gainers ---
        try:
            gainers_response = requests.get("http://localhost:8001/TopGainers")
            gainers_response.raise_for_status()
            gainers_data = gainers_response.json()[:10]  # ⬅️ Limit to top 10

            for item in gainers_data:
                top_gainers.append({
                    "symbol": item.get("symbol"),
                    "name": item.get("securityName"),
                    "price": item.get("ltp"),
                    "percentage": item.get("percentageChange"),
                })
        except Exception as e:
            print("❌ Failed to fetch Top Gainers:", e)

        # --- Fetch Top Losers ---
        try:
            losers_response = requests.get("http://localhost:8001/TopLosers")
            losers_response.raise_for_status()
            losers_data = losers_response.json()[:10]  # ⬅️ Limit to top 10

            for item in losers_data:
                top_losers.append({
                    "symbol": item.get("symbol"),
                    "name": item.get("securityName"),
                    "price": item.get("ltp"),
                    "percentage": item.get("percentageChange"),
                })
        except Exception as e:
            print("❌ Failed to fetch Top Losers:", e)

        try:
            response = requests.get("http://localhost:8001/PriceVolume")
            response.raise_for_status()
            live_data = response.json()
            print("✅ Live Market Data:", live_data)  # Add this line
        except Exception as e:
            print("❌ Error fetching LiveMarket data:", e)
            live_data = []

        ticker_data = []
        for item in live_data:
            if item.get("symbol") and item.get("lastTradedPrice") is not None:
                ticker_data.append({
                    "symbol": item["symbol"],
                    "price": item["lastTradedPrice"],
                    "change": round(item["percentageChange"], 2),
                    "is_up": item["percentageChange"] >= 0
                })

        print("✅ Parsed Ticker Data:", ticker_data)  # Add this line

        context = {
            "ticker_data": ticker_data,
            "recent_news": trending,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
        }
        return render(request, 'home.html', context)


def news_detail(request, news_id):
    df = pd.read_csv("StockSanket/merolagani_news.csv")
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



def SignupPage(request):
    if request.method=='POST':
        uname=request.POST.get('username')
        email=request.POST.get('email')
        pass1=request.POST.get('password1')
        pass2=request.POST.get('password2')

        # Validate username
        if User.objects.filter(username=uname).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'signup.html')

        # Validate email
        try:
            validate_email(email)
            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already registered!")
                return render(request, 'signup.html')
        except ValidationError:
            messages.error(request, "Please enter a valid email address!")
            return render(request, 'signup.html')

        # Validate password
        if len(pass1) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, 'signup.html')

        if pass1 != pass2:
            messages.error(request, "Passwords do not match!")
            return render(request, 'signup.html')

        # If all validations pass, create user
        try:
            my_user = User.objects.create_user(uname, email, pass1)
            my_user.save()
            messages.success(request, "Account created successfully! Please login.")
            return redirect('login')
        except Exception as e:
            messages.error(request, "An error occurred while creating your account.")
            return render(request, 'signup.html')

    return render(request, 'signup.html')

def LoginPage(request):
    if request.method=='POST':
        username=request.POST.get('username')
        pass1=request.POST.get('pass')
        user=authenticate(request,username=username,password=pass1)
        if user is not None:
            login(request,user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password!")
            return render(request, 'login.html')

    return render(request,'login.html')

def LogoutPage(request):
    logout(request)
    return redirect(request.META.get('HTTP_REFERER', 'home'))  # reloads same page or fallback to home




def StocksView(request):
    stocks_list = Stock.objects.all()  # ✅ Load from database instead of API

    # ✅ Paginate results (10 per page)
    paginator = Paginator(stocks_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'stocks.html', {"stocks": page_obj})  # ✅ Send database results




