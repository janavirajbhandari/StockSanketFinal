from django.urls import path
from . import views

urlpatterns = [
    # Watchlist functionality (putting these first to ensure they match)
    path('watchlists/', views.watchlist_view, name='watchlists'),
    path('add_to_watchlist/', views.add_to_watchlist, name='add_to_watchlist'),
    path('remove_from_watchlist/', views.remove_from_watchlist, name='remove_from_watchlist'),

    # Stock data endpoints
    path('get_stock_data/<str:symbol>/', views.get_stock_data, name='get_stock_data'),
    path('get_market_data/<str:symbol>/', views.get_market_data, name='get_market_data'),
    path('get_prediction_data/<str:symbol>/', views.get_prediction_data, name='get_prediction_data'),
    path('stock/history_partial/', views.stock_history_partial, name='stock_history_partial'),
    
    # Stock views
    path('stocks/', views.StocksView, name='stocks'),
    path('stockDetail/', views.StockDetail, name='stockDetail'),
    path('compare_stocks/', views.compare_stocks_view, name='compare_stocks'),
    path('ajax/search-stocks/', views.ajax_search_stocks, name='ajax_search_stocks_for_sidebar'),
    
    # News and articles
    path('news/', views.mero_news_view, name='news'),
    path('news/detail/<int:news_id>/', views.news_detail, name='news_detail'),
    path('articles/', views.blog_articles_view, name='articles'),
    path('sentiment/<str:symbol>/', views.StockDetail, name='sentiment_stock'),
] 