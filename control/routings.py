from django.urls import re_path, path

from .consumers.notifications import NotificationConsumer
from .consumers.general import GeneralConsumer

websocket_urlpatterns = [
        re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
        re_path(r'^ws/general/(?P<child_id>[0-9a-f-]+)/$', GeneralConsumer.as_asgi()),

    # path("wss/notifications/", consumers.NotificationConsumer.as_asgi()),
    # path("wss/notifications/navbar/", consumers.NotificationNavBarConsumer.as_asgi()),
    # re_path(r"wss/chat/room/(?P<room_id>\w+)/$", consumers.ChatConsumer.as_asgi()),
]
