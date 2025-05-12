import hashlib
import logging
import uuid
import json
from django.shortcuts import get_object_or_404
from datetime import datetime, date, time
from django.db import transaction
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import User

from control.api.serializers import ScheduleSerializer
from control.models import ChildLocation, ChildBadWords, Schedule
from accounts.models import Child

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
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):  # Fixed parameter name
        message_type = content.get("type")

        if message_type == "PIN_CHANGE":
            new_pin = content.get("new_pin")
            if not new_pin:
                await self.send_json({"type": "ERROR", "message": "Missing new_pin"})
                return
            hash_object = hashlib.sha512(new_pin.encode("utf-8"))
            new_pin_hashed = hash_object.hexdigest()

            if new_pin_hashed and self.group_name:
                await self.channel_layer.group_send(
                    self.group_name, {"type": "pin_change", "new_pin": new_pin_hashed}
                )
        elif message_type == "CONFIRM_PIN":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "pin_confirm",
                },
            )
        elif message_type == "GET_LOCATION":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "get_location",
                },
            )
        elif message_type == "LOCATION":
            data = content.get("location")
            if not isinstance(data, dict) or not all(
                key in data for key in ["lat", "lng", "accuracy", "timestamp"]
            ):
                await self.send_json(
                    {"type": "ERROR", "message": "Invalid location data"}
                )
                return
            try:
                data["lat"] = float(data["lat"])
                data["lng"] = float(data["lng"])
                data["accuracy"] = float(data["accuracy"])
                data["timestamp"] = int(data["timestamp"])
            except (ValueError, TypeError):
                await self.send_json(
                    {"type": "ERROR", "message": "Invalid location data types"}
                )
                return

            success = await self.set_location(data)  # Added await
            if not success:
                await self.send_json(
                    {"type": "ERROR", "message": "Failed to save location"}
                )
                return

            await self.channel_layer.group_send(
                self.group_name, {"type": "location", "location": data}
            )
        elif message_type == "LOCATION_ERROR":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "location_error", "error": content.get("error")},
            )   
        elif message_type == "BAD_WORDS":           
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "bad_words"},
            )
        elif message_type == "CONFIRM_BAD_WORDS":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "bad_words_confirm"}
            )
        elif message_type == "LOCK_PHONE":
            phone_locked = await self.lock_phone_status()
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "lock_phone", "phone_locked":phone_locked},
            )
        elif message_type == "CONFIRM_LOCK_PHONE":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "lock_phone_confirm"}
            )
        elif message_type == "SCHEDULE":           
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "schedules"},
            )
        elif message_type == "CONFIRM_SCHEDULES":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "schedules_confirm"}
            )
        elif message_type == "ADD_SCHEDULE":
            if not isinstance(content, dict) or not all(
                key in content for key in ["name", "start_time", "end_time", "start_date","end_date","days"]
            ):
                await self.send_json(
                    {"type": "ERROR", "message": "Invalid Schedule data"}
                )
                return
            schedule = await self.add_schedule_db(content)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "add_schedule", "schedule":schedule},
            )
        elif message_type == "CONFIRM_ADD_SCHEDULE":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "add_schedule_confirm"}
            )
        elif message_type == "DELETE_SCHEDULE":
            if not isinstance(content, dict) or not all(
                key in content for key in ["id"]
            ):
                await self.send_json(
                    {"type": "ERROR", "message": "Invalid Schedule id"}
                )
                return     
            deleted = await self.delete_schedule_db(content["id"])  
            if (not deleted):
                self.send_json(
                    {"type": "ERROR", "message": "Invalid Schedule id"}
                )
                return
            
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "delete_schedule", "id":content["id"]},
            )
        elif message_type == "CONFIRM_DELETE_SCHEDULE":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "delete_schedule_confirm"}
            )
    
    
    ### SCHEDULE ###
    async def schedules_confirm(self, event):
        await self.send_json({"type": "CONFIRM_SCHEDULES"})

    async def schedules(self, event):
        bad_words = await self.get_schedules()
        await self.send_json({"type": "SCHEDULE", "schedules": bad_words})

    @database_sync_to_async
    def get_schedules(self):
        if not self.child_id:
            raise ValueError("child_id must be set before calling get_bad_words")
        child = get_object_or_404(Child, id=self.child_id)
        obj = Schedule.objects.filter(is_deleted=False)
        data = obj.filter(child=child)
        listdata = []
        for obj in data:
            schedule_dict = {
                "id": obj.id,
                "name": obj.name,
                "start_time": obj.start_time.strftime("%H:%M:%S") if isinstance(obj.start_time, time) else str(obj.start_time),
                "end_time": obj.end_time.strftime("%H:%M:%S") if isinstance(obj.end_time, time) else str(obj.end_time),
                "start_date": obj.start_date.strftime("%Y-%m-%d") if isinstance(obj.start_date, date) else str(obj.start_date),
                "end_date": obj.end_date.strftime("%Y-%m-%d") if isinstance(obj.end_date, date) else str(obj.end_date),
                "days": list(obj.days.values_list('value', flat=True)), 
            }
            listdata.append(schedule_dict)
        return listdata

    async def delete_schedule(self, event):
        await self.send_json({"type": "DELETE_SCHEDULE", "id":event["id"]})
    
    @database_sync_to_async
    def delete_schedule_db(self, id):
        obj = Schedule.objects.filter(id=id).first()
        if (obj==None):
            return False
        obj.is_deleted=True
        obj.save()
        return True
    
    async def delete_schedule_confirm(self, event):
        await self.send_json({"type": "CONFIRM_DELETE_SCHEDULE"})


    async def add_schedule(self, event):
        await self.send_json({"type": "ADD_SCHEDULE", "schedule":event["schedule"]})

    @database_sync_to_async
    def add_schedule_db(self, data):
        child = Child.objects.get(id=self.child_id)
        obj = Schedule.objects.create(
            child=child,
            name=data["name"],
            start_time=data["start_time"], 
            end_time=data["end_time"], 
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
        obj.days.set(data["days"])

        schedule_dict = {
                "id": obj.id,
                "name": obj.name,
                "start_time": obj.start_time.strftime("%H:%M:%S") if isinstance(obj.start_time, time) else str(obj.start_time),
                "end_time": obj.end_time.strftime("%H:%M:%S") if isinstance(obj.end_time, time) else str(obj.end_time),
                # Convert date objects to strings for JSON
                "start_date": obj.start_date.strftime("%Y-%m-%d") if isinstance(obj.start_date, date) else str(obj.start_date),
                "end_date": obj.end_date.strftime("%Y-%m-%d") if isinstance(obj.end_date, date) else str(obj.end_date),
                # You'll likely need to fetch and serialize the 'days' relationship as well
                "days": list(obj.days.values_list('value', flat=True)), # Example: get a list of day values
            }
        return schedule_dict
    
    async def add_schedule_confirm(self, event):
        await self.send_json({"type": "CONFIRM_ADD_SCHEDULE"})
    ### SCHEDULE ###

    ### LOCK ###
    async def lock_phone_confirm(self, event):
        await self.send_json({"type": "CONFIRM_LOCK_PHONE"})

    async def lock_phone(self, event):
        await self.send_json({"type": "LOCK_PHONE", "phone_locked": event["phone_locked"]})
    
    @database_sync_to_async
    def lock_phone_status(self):
        try:
            child = Child.objects.get(id=self.child_id)
            child.phone_locked = not child.phone_locked
            child.save()
            return child.phone_locked
        except Child.DoesNotExist:
            logger.error(f"Child with id {self.child_id} not found")
            raise
    ### LOCK ###

    ### BAD WORDS ###
    async def bad_words_confirm(self, event):
        await self.send_json({"type": "CONFIRM_BAD_WORDS"})

    async def bad_words(self, event):
        bad_words = await self.get_bad_words()
        await self.send_json({"type": "BAD_WORDS", "bad_words": bad_words})

    @database_sync_to_async
    def get_bad_words(self):
        if not self.child_id:
            raise ValueError("child_id must be set before calling get_bad_words")
        child = get_object_or_404(Child, id=self.child_id)
        cbw, _ = ChildBadWords.objects.get_or_create(child=child)
        return list(cbw.bad_words.values_list('word', flat=True))

    ### BAD WORDS ###

    ### LOCATION ###
    async def location_error(self, event):
        await self.send_json({"type": "LOCATION_ERROR", "error": event["error"]})

    async def location(self, event):
        await self.send_json({"type": "LOCATION", "location": event["location"]})

    async def get_location(self, event):
        await self.send_json(
            {
                "type": "GET_LOCATION",
            }
        )
    
    @database_sync_to_async
    def set_location(self, data):
        try:
            child = Child.objects.get(id=self.child_id)  # Fetch Child instance
            dt = datetime.fromtimestamp(data["timestamp"] / 1000.0)
            ChildLocation.objects.create(
                child=child,  # Use Child instance
                latitude=data["lat"],
                longitude=data["lng"],
                accuracy=data["accuracy"],
                timestamp=dt,
            )
            return True
        except Exception as e:
            logger.error(f"Error saving location: {e}")  # Proper logging
            return False
        
    ### LOCATION ###

    ### PIN ###
    async def pin_confirm(self, event):
        await self.send_json(
            {
                "type": "CONFIRM_PIN",
            }
        )

    async def pin_change(self, event):
        await self.send_json({"type": "PIN_CHANGE", "new_pin": event["new_pin"]})
    ### PIN ###



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
