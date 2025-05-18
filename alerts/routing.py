from django.urls import re_path
from .consumers import StockAlertConsumer

websocket_urlpatterns = [
    re_path(r"ws/stock_alerts/$", StockAlertConsumer.as_asgi()),
]
