from django.urls import path, re_path

from .consumers.general import GeneralConsumer

websocket_urlpatterns = [
    # re_path(
    #     r"^ws/notifications/(?P<child_id>[0-9a-f-]+)/$", NotificationConsumer.as_asgi()
    # ),
    re_path(r"^ws/general/(?P<child_id>[0-9a-f-]+)/$", GeneralConsumer.as_asgi()),
   
]
