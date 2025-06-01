import os
import django

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from channels.security.websocket import OriginValidator
from channels.routing import URLRouter

from control.routings import websocket_urlpatterns
from core.channelsmiddleware import TokenAuthMiddleware

django_asgi_app = get_asgi_application()
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "https": get_asgi_application(),
        # "websocket": URLRouter(websocket_urlpatterns),
        "websocket": OriginValidator(
            TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
            [
                "*",
            ],
        ),
    }
)
