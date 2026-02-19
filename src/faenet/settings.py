"""
Faerie Chat Django Settings
======================

This settings file is heavily commented to explain how Django works behind
a reverse proxy (Nginx) and a TLS-terminating tunnel (Ngrok).

THE PROBLEM
-----------
When Django sits behind Nginx (and optionally Ngrok), requests arrive at
Django with:
  - Host: "web:8000" (the Docker internal hostname, NOT the public domain)
  - Scheme: "http" (because Nginx -> Django is plain HTTP inside Docker)

This causes CSRF verification to fail because Django sees:
  - Origin header: "https://faeries.ngrok.app" (from the browser)
  - Host header: "web:8000" (from Docker networking)
  - Scheme: "http" (no TLS inside Docker)

Django's CSRF middleware compares Origin against the request's scheme+host
and rejects the mismatch with a 403 Forbidden.

THE SOLUTION (4 settings + Nginx headers)
-----------------------------------------
1. SECURE_PROXY_SSL_HEADER - Trust Nginx's X-Forwarded-Proto header
2. USE_X_FORWARDED_HOST/PORT - Use the forwarded Host, not Docker's
3. CSRF_TRUSTED_ORIGINS - Explicitly whitelist your public domain(s)
4. Cookie security flags - Conditional on DEBUG for local dev flexibility
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

# Hosts that Django will serve. Must include your public domain AND the
# Docker-internal hostname (so Nginx -> Django health checks work).
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# REVERSE PROXY FIX #1: Trust the proxy's protocol header
# ---------------------------------------------------------------------------
# Nginx sets "X-Forwarded-Proto: https" when the original request was HTTPS.
# Without this, Django thinks every request is HTTP (because Nginx -> Django
# is plain HTTP inside Docker) and generates http:// URLs, which breaks CSRF
# when the browser sends an Origin of https://...
#
# This tells Django: "If you see the header X-Forwarded-Proto with value
# 'https', treat the request as if it arrived over HTTPS."
#
# SECURITY: Only enable this if you trust your proxy. In Docker Compose,
# only Nginx can reach Django, so this is safe.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# REVERSE PROXY FIX #2: Use forwarded Host and Port
# ---------------------------------------------------------------------------
# Without these, Django sees Host: "web:8000" (the Docker service name).
# With these, Django reads the X-Forwarded-Host header that Nginx sets to
# the original Host the browser sent (e.g., "faeries.ngrok.app").
#
# This is critical for:
# - CSRF validation (Origin must match Host)
# - Generating correct absolute URLs (e.g., password reset links)
# - Django's request.get_host() returning the right value
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# ---------------------------------------------------------------------------
# REVERSE PROXY FIX #3: Explicitly trust origins for CSRF
# ---------------------------------------------------------------------------
# Starting with Django 4.0, CSRF protection checks the Origin header against
# a whitelist. Even if Host matching works, you MUST add your public URL here.
#
# Format: scheme + domain (e.g., "https://faeries.ngrok.app")
# You can list multiple origins for different access methods.
#
# Without this, POST requests (login, form submissions) return 403 Forbidden
# with the error: "Origin checking failed - https://faeries.ngrok.app does not
# match any trusted origins."
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost").split(
    ","
)

# ---------------------------------------------------------------------------
# REVERSE PROXY FIX #4: Cookie security (conditional on DEBUG)
# ---------------------------------------------------------------------------
# When serving over HTTPS (via Ngrok), cookies should have the Secure flag
# so browsers only send them over HTTPS. But in local dev (http://localhost),
# Secure cookies won't work.
#
# Solution: Set Secure flags only when DEBUG is False (production-like).
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# ---------------------------------------------------------------------------
# APPLICATION DEFINITION
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # Daphne MUST be before django.contrib.staticfiles so it can serve
    # static files during development AND provides the ASGI server.
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "faenet.chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "faenet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "faenet" / "chat" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# ASGI / CHANNELS
# ---------------------------------------------------------------------------
# Django Channels requires ASGI. Daphne serves both HTTP and WebSocket.
ASGI_APPLICATION = "faenet.asgi.application"

# Channel layer backed by Redis. This is what enables real-time messaging:
# when one WebSocket consumer sends a message, it goes through Redis to
# all other consumers in the same "group" (chat room).
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}

# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "faenet"),
        "USER": os.environ.get("POSTGRES_USER", "faenet"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "faenet_secret"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# After login, redirect to the chat room list (not the default /accounts/profile/)
LOGIN_REDIRECT_URL = "/"
# After logout, redirect back to the login page
LOGOUT_REDIRECT_URL = "/accounts/login/"
LOGIN_URL = "/accounts/login/"

# ---------------------------------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# GIPHY API
# ---------------------------------------------------------------------------
GIPHY_API_KEY = os.environ.get("GIPHY_API_KEY", "")
