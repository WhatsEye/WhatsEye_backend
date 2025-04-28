import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("✅ WebSocket connected")

    async def disconnect(self, close_code):
        print("❌ WebSocket disconnected")

    async def receive(self, text_data):
        data = json.loads(text_data)
        print("📲 WhatsApp Notification:")
        print(f"Title: {data.get('title')}")
        print(f"Text: {data.get('content')}")
        print(f"Timestamp: {data.get('timestamp')}")

        await self.send(text_data=json.dumps({
            "status": "received",
            "type": data.get("type")
        }))
