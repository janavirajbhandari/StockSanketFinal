from channels.generic.websocket import AsyncWebsocketConsumer
import json

class StockAlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("🔌 WebSocket client connecting...")
        # Join the price alerts group
        await self.channel_layer.group_add("price_alerts", self.channel_name)
        await self.accept()
        print("✅ WebSocket client connected!")

    async def disconnect(self, close_code):
        print(f"❌ WebSocket client disconnected with code: {close_code}")
        await self.channel_layer.group_discard("price_alerts", self.channel_name)

    async def send_price_alert(self, event):
        """Handle incoming price alerts"""
        try:
            print(f"📨 Sending price alert to client: {event['message']}")
            # Send the alert to the WebSocket
            await self.send(text_data=json.dumps(event["message"]))
        except Exception as e:
            print(f"❌ Error sending price alert: {e}")

    # Legacy handler for backward compatibility
    async def send_alert(self, event):
        """Handle legacy alert format"""
        try:
            if isinstance(event.get('data'), list):
                for alert in event['data']:
                    await self.send(text_data=json.dumps(alert))
            else:
                await self.send(text_data=json.dumps(event["data"]))
        except Exception as e:
            print(f"❌ Error sending legacy alert: {e}")
