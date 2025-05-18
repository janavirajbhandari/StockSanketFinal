from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def notify_clients(alerts):
    print(f"📤 Sending alerts to clients: {alerts}")
    channel_layer = get_channel_layer()
    
    # Send each alert individually
    for alert in alerts:
        async_to_sync(channel_layer.group_send)(
            "price_alerts",
            {
                "type": "send_price_alert",
                "message": alert,
            }
        )
