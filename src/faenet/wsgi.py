"""
WSGI config for Faerie Chat.

Note: This project uses ASGI (via Daphne) for both HTTP and WebSocket.
This WSGI file exists for compatibility but is not used in production.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faenet.settings")

application = get_wsgi_application()
