from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from control.models import ChildLocation
from datetime import datetime
import uuid, hashlib

class GeneralConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.child_id = self.scope["url_route"]["kwargs"].get("child_id", None)
        if not self.child_id:
            await self.close()
            return
        
        # Validate child_id is a valid UUID
        try:
            uuid.UUID(self.child_id)
        except ValueError:
            await self.close()
            return
        
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
        else:
            # Verify user has permission to control this child_id
            if not await self.has_permission(user, self.child_id):
                await self.close()
                return
            
            self.group_name = f"general_{self.child_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
    async def receive_json(self, text_data):
        message_type = text_data.get('type')

        if message_type == 'PIN_CHANGE':
            new_pin = text_data.get('new_pin')
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
            data = text_data.get('location')
            if not isinstance(data, dict) or not all(key in data for key in ['lat', 'lng', 'accuracy', 'timestamp']):
                await self.send_json({'type': 'ERROR', 'message': 'Invalid location data'})
                return
            try:
                # Validate data types
                data['lat'] = float(data['lat'])
                data['lng'] = float(data['lng'])
                data['accuracy'] = float(data['accuracy'])
                data['timestamp'] = int(data['timestamp'])
            except (ValueError, TypeError):
                await self.send_json({'type': 'ERROR', 'message': 'Invalid location data types'})
                return

            user = self.scope["user"]
            print(data)

            await self.set_location(user, data)
            
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'location',
                    'location': data
                }
            )
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
        # Send PIN_CHANGE message to the child (client)
        await self.send_json({
            'type': 'PIN_CHANGE',
            'new_pin': event['new_pin']
        })
  
    @database_sync_to_async
    def set_location(self, user, data):
        try:
            # Check if user has a valid child
            from accounts.models import Child
            child = getattr(user, 'child', None)
            if not child or not isinstance(child, Child):
                raise ValueError("User is not associated with a valid child")
            dt = datetime.fromtimestamp(data['timestamp'] / 1000.0)
            ChildLocation.objects.create(
                child=child,
                latitude=data['lat'],
                longitude=data['lng'],
                accuracy=data['accuracy'],
                timestamp=dt
            )
            
            return True
        except Exception as e:
            print(f"Error saving location: {e}")
            return False
        
    @database_sync_to_async
    def has_permission(self, user, child_id):
        from accounts.models import Child, Parent
        parent = Parent.objects.filter(user=user).first()
        child = Child.objects.filter(id=child_id).first()

        if parent is None and child is None:
            return False
        if parent is None:
            return child.user == user
        return child.my_family == parent.my_family 