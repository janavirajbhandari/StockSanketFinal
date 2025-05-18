from django.urls import path
from . import views

urlpatterns = [
    path('get_stock_data/<str:symbol>/', views.get_stock_data, name='get_stock_data'),
    path('get_market_data/<str:symbol>/', views.get_market_data, name='get_market_data'),
] 