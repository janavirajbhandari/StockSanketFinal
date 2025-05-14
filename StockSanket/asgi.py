import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import alerts.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "StockSanket.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(alerts.routing.websocket_urlpatterns),
})
