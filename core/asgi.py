import os

from core.channelsmiddleware import TokenAuthMiddleware
from control.routings import websocket_urlpatterns
# from django.conf.urls import url

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.security.websocket import OriginValidator
from django.urls import re_path

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        #"https": get_asgi_application(),
        # "websocket": URLRouter(websocket_urlpatterns),
        "websocket": OriginValidator(
            TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
            ["*",],
        ),
    }
)

