from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def notify_clients(alerts):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "stock_alerts",
        {
            "type": "send_alert",
            "data": alerts,
        }
    )
