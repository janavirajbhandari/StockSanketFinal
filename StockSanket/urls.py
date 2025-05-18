from django.contrib import admin
from django.urls import path, include
from authentication import views as auth_views  
from stocks import views as stock_views  


urlpatterns = [
    path('admin/', admin.site.urls),

    # Public Pages
    path('', auth_views.HomePages, name='home'),  # ✅ Now homepage is root
    path('signup/', auth_views.SignupPage, name='signup'),
    path('login/', auth_views.LoginPage, name='login'),
    path('logout/', auth_views.LogoutPage, name='logout'),
    path("stock/history_partial/", stock_views.stock_history_partial, name="stock_history_partial"),
    
    # urls.py
    path('ajax/search-stocks-for-home/', auth_views.search_stocks, name='ajax_search_stocks_for_home'),

    # Stocks-related Pages (Login required inside views)
    path('stocks/', stock_views.StocksView, name='stocks'),
    path("compare_stocks/", stock_views.compare_stocks_view, name="compare_stocks"),
    path('get_stock_data/<str:symbol>/', stock_views.get_stock_data, name='get_stock_data'),

    path('stockDetail/', stock_views.StockDetail, name='stockDetail'),  
    path("ajax/search-stocks/", stock_views.ajax_search_stocks, name="ajax_search_stocks_for_sidebar"),

    path('get_stock_data/<str:symbol>/', stock_views.get_stock_data, name='get_stock_data'),
    path('get_market_data/<str:symbol>/', stock_views.get_market_data, name='get_market_data'),
    path('get_prediction_data/<str:symbol>/', stock_views.get_prediction_data, name='get_prediction_data'),


    path("news/", stock_views.mero_news_view, name="news"),
    path("news/detail/<int:news_id>/", stock_views.news_detail, name="news_detail"),

    path('articles/', stock_views.blog_articles_view, name="articles"),
    path("sentiment/<str:symbol>/", stock_views.StockDetail, name="sentiment_stock"),

    # Watchlist Paths
    path('watchlists/', stock_views.watchlist_view, name='watchlists'),
    path('add_to_watchlist/', stock_views.add_to_watchlist, name='add_to_watchlist'),
    path('remove_from_watchlist/', stock_views.remove_from_watchlist, name='remove_from_watchlist'),
]
