import logging
import uuid

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ValidationError

from control.models import Notification

logger = logging.getLogger(__name__)


class NotificationConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.child_id = self.scope["url_route"]["kwargs"].get("child_id")

        if not self.child_id or not self.validate_connection():
            self.close(code=4001)  # Invalid parameters or unauthorized
            return

        self.group_name = f"notification_{self.child_id}_notification"

        try:
            async_to_sync(self.channel_layer.group_add)(
                self.group_name, self.channel_name
            )
        except Exception as e:
            logger.error(f"Failed to join group {self.group_name}: {e}")
            self.close(code=1011)
            return

        self.accept()

    def validate_connection(self):
        try:
            uuid.UUID(self.child_id)
        except ValueError:
            return False

        user = self.scope["user"]
        if user.is_anonymous:
            return False

        return self.has_permission(user, self.child_id)

    def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            try:
                async_to_sync(self.channel_layer.group_discard)(
                    self.group_name, self.channel_name
                )
            except Exception as e:
                logger.error(f"Failed to leave group {self.group_name}: {e}")

    def receive_json(self, content, **kwargs):
        """Handle incoming WebSocket messages."""
        message_type = content.get("type")

        if message_type == "NOTIFICATION":
            notification_data = content.get("notification")
            if not self.validate_notification_data(notification_data):
                self.send_error("Invalid notification data.")
                return

            self.save_notification(notification_data)
            print(notification_data["timestamp"])
            try:
                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {"type": "notification_message", "notification": notification_data},
                )
            except Exception as e:
                logger.error(f"Error sending group message: {e}")
                self.send_error("Internal server error.")

    def notification_message(self, event):
        """Send notification to the WebSocket client."""

        self.send_json({"type": "NOTIFICATION", "notification": event["notification"]})

    def send_error(self, message):
        """Send an error message to the client."""
        self.send_json({"type": "ERROR", "error": message})

    def validate_notification_data(self, data):
        """Ensure required fields are present in the notification."""
        if not isinstance(data, dict):
            return False
        required_fields = ["title", "content", "timestamp"]
        return all(field in data for field in required_fields)

    def save_notification(self, notification_data):
        """Persist the notification in the database."""
        try:
            Notification.objects.create(
                title=notification_data.get("title", ""),
                content=notification_data.get("content", ""),
                timestamp=notification_data.get("timestamp"),
                type=notification_data.get("type"),
                child_id=self.child_id,
            )
        except ValidationError as e:
            logger.error(f"Validation error saving notification: {e}")
        except Exception as e:
            logger.exception("Unexpected error while saving notification")

    def has_permission(self, user, child_id):
        """Check if the user has access to the child's notifications."""
        from accounts.models import Child, Parent

        try:
            parent = Parent.objects.filter(user=user).first()
            child = Child.objects.filter(id=child_id).first()

            if not child:
                return False

            if not parent:
                return child.user == user

            return child.my_family == parent.my_family
        except Exception as e:
            logger.exception("Error checking permissions")
            return False
