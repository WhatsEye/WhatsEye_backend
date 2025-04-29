from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from control.models import ChildLocation
from datetime import datetime
import uuid, hashlib
import logging

logger = logging.getLogger(__name__)

class GeneralConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.child_id = self.scope["url_route"]["kwargs"].get("child_id")
        
        if not self.child_id or not await self.validate_connection():
            await self.close(code=4001)
            return

        self.group_name = f"notification_{self.child_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def validate_connection(self):
        try:
            uuid.UUID(self.child_id)
        except ValueError:
            return False

        user = self.scope["user"]
        if user.is_anonymous:
            return False

        return await self.has_permission(user, self.child_id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):  # Fixed parameter name
        message_type = content.get('type')

        if message_type == 'PIN_CHANGE':
            new_pin = content.get('new_pin')
            if not new_pin:
                await self.send_json({'type': 'ERROR', 'message': 'Missing new_pin'})
                return
            hash_object = hashlib.sha512(new_pin.encode('utf-8')) 
            new_pin_hashed = hash_object.hexdigest()
            
            if new_pin_hashed and self.group_name:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'pin_change',
                        'new_pin': new_pin_hashed
                    }
                )
        elif message_type == 'CONFIRM_PIN':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'pin_confirm',
                }
            )
        elif message_type == 'GET_LOCATION':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'get_location',
                }
            )
        elif message_type == 'LOCATION':
            data = content.get('location')
            if not isinstance(data, dict) or not all(key in data for key in ['lat', 'lng', 'accuracy', 'timestamp']):
                await self.send_json({'type': 'ERROR', 'message': 'Invalid location data'})
                return
            try:
                data['lat'] = float(data['lat'])
                data['lng'] = float(data['lng'])
                data['accuracy'] = float(data['accuracy'])
                data['timestamp'] = int(data['timestamp'])
            except (ValueError, TypeError):
                await self.send_json({'type': 'ERROR', 'message': 'Invalid location data types'})
                return

            user = self.scope["user"]
            success = await self.set_location(user, data)  # Added await
            if not success:
                await self.send_json({'type': 'ERROR', 'message': 'Failed to save location'})
                return
            
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'location',
                    'location': data
                }
            )
        elif message_type == 'LOCATION_ERROR':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'location_error',
                    'error': content.get('error')
                }
            )
    
    async def location_error(self, event):
        await self.send_json({
            'type': 'LOCATION_ERROR',
            'error': event['error']
        })

    async def location(self, event):
        await self.send_json({
            'type': 'LOCATION',
            'location': event['location']
        }) 
   
    async def get_location(self, event):
        await self.send_json({
            'type': 'GET_LOCATION',
        })      
    
    async def pin_confirm(self, event):
        await self.send_json({
            'type': 'CONFIRM_PIN',
        })

    async def pin_change(self, event):
        await self.send_json({
            'type': 'PIN_CHANGE',
            'new_pin': event['new_pin']
        })
  
    @database_sync_to_async
    def set_location(self, user, data):
        from accounts.models import Child  # Import inside sync function
        try:            
            child = Child.objects.get(id=self.child_id)  # Fetch Child instance
            dt = datetime.fromtimestamp(data['timestamp'] / 1000.0)
            ChildLocation.objects.create(
                child=child,  # Use Child instance
                latitude=data['lat'],
                longitude=data['lng'],
                accuracy=data['accuracy'],
                timestamp=dt
            )
            return True
        except Exception as e:
            logger.error(f"Error saving location: {e}")  # Proper logging
            return False
        
    @database_sync_to_async
    def has_permission(self, user, child_id):
        from accounts.models import Child, Parent
        child = Child.objects.filter(id=child_id).first()
        if not child:  # Immediate check for child existence
            return False

        parent = Parent.objects.filter(user=user).first()
        if not parent:
            return child.user == user  # Direct user comparison
        return child.my_family == parent.my_family