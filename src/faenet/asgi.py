"""
ASGI config for Faerie Chat.

This file configures Django Channels to handle both HTTP and WebSocket
connections through a single ASGI application.

The ProtocolTypeRouter dispatches:
  - "http"      -> Django's standard HTTP handling
  - "websocket" -> Our chat WebSocket consumer, wrapped in auth middleware

AllowedHostsOriginValidator ensures WebSocket connections only come from
origins matching ALLOWED_HOSTS, preventing cross-site WebSocket hijacking.

AuthMiddlewareStack populates scope["user"] from the session cookie, so
our consumer can identify who is connected without a separate auth flow.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faenet.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing consumers.
django_asgi_app = get_asgi_application()

from faenet.chat.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        ),
    }
)
