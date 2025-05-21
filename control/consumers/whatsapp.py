# import hashlib
# import logging
# import uuid
# import json
# from datetime import datetime, date, time
# from django.db import transaction
# from channels.db import database_sync_to_async
# from channels.generic.websocket import AsyncJsonWebsocketConsumer
# from django.contrib.auth.models import User

# from control.api.serializers import ScheduleSerializer
# from control.models import ChildLocation, ChildBadWords, Schedule
# from accounts.models import Child

# logger = logging.getLogger(__name__)


# class WhatsApponsumer(AsyncJsonWebsocketConsumer):
#     async def connect(self):
#         self.child_id = self.scope["url_route"]["kwargs"].get("child_id")

#         if not self.child_id or not await self.validate_connection():
#             await self.close(code=4001)
#             return

#         self.group_name = f"notification_{self.child_id}"
#         await self.channel_layer.group_add(self.group_name, self.channel_name)
#         await self.accept()

#     async def validate_connection(self):
#         try:
#             uuid.UUID(self.child_id)
#         except ValueError:
#             return False

#         user = self.scope["user"]
#         if user.is_anonymous:
#             return False

#         return await self.has_permission(user, self.child_id)

#     async def disconnect(self, close_code):
#         if hasattr(self, "group_name"):
#             await self.channel_layer.group_discard(self.group_name, self.channel_name)

#     async def receive_json(self, content, **kwargs):  # Fixed parameter name
#         message_type = content.get("type")

#         if message_type == "REQUEST_CONTACT":
#             await self.channel_layer.group_send(
#                     self.group_name, {"type": "pin_change"}
#                 )
#         elif message_type == "REQUEST_CURRENT_CHATS":
#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {
#                     "type": "pin_confirm",
#                 },
#             )
#         elif message_type == "REQUEST_BLOCK_USER":
#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {
#                     "type": "get_location",
#                 },
#             )
#         elif message_type == "REQUEST__CHAT":
#             await self.channel_layer.group_send(
#                 self.group_name, {"type": "location", "location": data}
#             )
#         elif message_type == "RESPONSE_CONTACT":
#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {"type": "location_error", "error": content.get("error")},
#             )   
#         elif message_type == "RESPONSE_CURRENT_CHATS":           
#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {"type": "bad_words"},
#             )
#         elif message_type == "RESPONSE_BLOCK_USER":
#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {"type": "bad_words_confirm"}
#             )
#         elif message_type == "RESPONSE_CHAT":
#             phone_locked = await self.lock_phone_status()
#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {"type": "lock_phone", "phone_locked":phone_locked},
#             )

#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {"type": "delete_schedule_confirm"}
#             )
    
    
#     ### SCHEDULE ###
#     async def delete_schedule(self, event):
#         await self.send_json({"type": "DELETE_SCHEDULE", "id":event["id"]})
    
#     @database_sync_to_async
#     def delete_schedule_db(self, id):
#         obj = Schedule.objects.filter(id=id).first()
#         if (obj==None):
#             return False
#         obj.is_deleted=True
#         obj.save()
#         return True
    
#     @database_sync_to_async
#     def has_permission(self, user, child_id):
#         from accounts.models import Child, Parent

#         child = Child.objects.filter(id=child_id).first()
#         if not child:  # Immediate check for child existence
#             return False

#         parent = Parent.objects.filter(user=user).first()
#         if not parent:
#             return child.user == user  # Direct user comparison
#         return child.my_family == parent.my_family
