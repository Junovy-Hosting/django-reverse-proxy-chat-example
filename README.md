# Faerie Chat - Django WebSocket Chat Behind Nginx Reverse Proxy

A fully working Django Channels chat application that demonstrates an example configuration for running Django behind an Nginx reverse proxy with Ngrok tunneling.

This repo exists because getting CSRF, WebSocket, sessions, and fail2ban to all work correctly behind a reverse proxy is surprisingly tricky — and the errors are confusing. Every setting is heavily commented to explain _why_ it's needed.

## Architecture

```
Internet → Ngrok (https://faeries.ngrok.app)
         → localhost:80
         → Nginx (reverse proxy + static files + access logging)
         → Daphne/Django (HTTP + WebSocket via ASGI)
         → PostgreSQL (database)
         → Redis (WebSocket channel layer)
```

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/Junovy-Hosting/django-reverse-proxy-chat-example.git
cd django-reverse-proxy-chat-example
cp .env.example .env

# 2. Build, start, and seed data
make dev

# 3. Open http://localhost and log in
#    Username: titania
#    Password: faerie123
```

To expose via Ngrok (in a separate terminal):

```bash
make ngrok
```

## Test Users

All users have the password `faerie123` unless noted otherwise.

| Username    | Full Name              | Role  | Password  |
| ----------- | ---------------------- | ----- | --------- |
| admin       | Admin Fae              | Admin | faerie123 |
| titania     | Titania Moonweaver     | User  | faerie123 |
| oberon      | Oberon Shadowthorn     | User  | faerie123 |
| puck        | Puck Trickfoot         | User  | faerie123 |
| morgana     | Morgana Mistbloom      | User  | faerie123 |
| thistle     | Thistle Duskwing       | User  | faerie123 |
| bramble     | Bramble Thornheart     | User  | faerie123 |
| luna        | Luna Starfire          | User  | faerie123 |
| fern        | Fern Dewdrop           | User  | faerie123 |
| cobweb      | Cobweb Silkspinner     | User  | faerie123 |
| mustardseed | Mustardseed Goldenleaf | User  | faerie123 |
| omni        | Omni Voidwalker        | User  | omnifae42 |

## The CSRF Problem Explained

When Django sits behind Nginx (and optionally Ngrok), `POST` requests to `/accounts/login/` return **403 Forbidden** with the error:

> Origin checking failed - https://faeries.ngrok.app does not match any trusted origins.

### Why This Happens

The browser sends:

```
POST /accounts/login/ HTTP/1.1
Host: faeries.ngrok.app
Origin: https://faeries.ngrok.app
```

But by the time this reaches Django (through Ngrok → Nginx → Docker), Django sees:

```
Host: web:8000          ← Docker's internal hostname
Scheme: http            ← No TLS inside the Docker network
Origin: https://faeries.ngrok.app  ← Still the original browser value
```

Django's CSRF middleware compares `Origin` against `scheme + Host` and rejects the mismatch.

### The Solution (4 Django Settings + Nginx Headers)

**In `nginx.conf`** — forward the real Host and protocol:

```nginx
proxy_set_header Host $http_host;              # Real host, not "web:8000"
proxy_set_header X-Forwarded-Proto $scheme;    # Real protocol (http/https)
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # Real client IP
```

**In `settings.py`** — trust those headers and whitelist origins:

```python
# 1. Trust Nginx's X-Forwarded-Proto header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# 2. Use the forwarded Host, not Docker's internal hostname
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# 3. Explicitly whitelist your public domain (Django 4.0+ requirement)
CSRF_TRUSTED_ORIGINS = ["https://faeries.ngrok.app"]

# 4. Secure cookies only in production (HTTPS via Ngrok)
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
```

All four are needed. Missing any one will result in CSRF failures or insecure cookies.

## fail2ban Pitfalls

A common `nginx-4xx` fail2ban jail will **ban your real users**. Here's why:

1. User's session expires
2. Django returns 302 → redirect to login
3. User submits login form, but CSRF token is stale
4. Django returns 403 (CSRF failure)
5. fail2ban sees 403 from this IP → **ban**

The CSRF 403 is a legitimate error, not an attack. See [`nginx/fail2ban-notes.md`](nginx/fail2ban-notes.md) for recommended fail2ban configurations that avoid this problem.

## WebSocket Through Nginx

WebSocket requires HTTP/1.1 with the Upgrade mechanism. Three things must be configured:

**1. Map directive** — conditionally set the Connection header:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ""      close;
}
```

**2. Proxy settings** — forward the upgrade headers:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

**3. Timeout** — keep WebSocket connections alive:

```nginx
proxy_read_timeout 86400s;  # 24 hours instead of default 60s
```

**4. Client-side** — use the correct protocol:

```javascript
// Must match the page protocol or the browser blocks it
const wsScheme = window.location.protocol === "https:" ? "wss:" : "ws:";
```

## Logout Flow

Django's `LogoutView` clears the session and sets an expired session cookie. Behind a reverse proxy, this works correctly as long as the `Host` header is forwarded properly (which our Nginx config does). The browser receives the `Set-Cookie` with `expires=Thu, 01 Jan 1970` and removes the session cookie.

`LOGOUT_REDIRECT_URL = "/accounts/login/"` sends the user back to the login page after logout.

## Makefile Commands

| Command        | Description                            |
| -------------- | -------------------------------------- |
| `make help`    | Show all available commands            |
| `make dev`     | Full setup: build + start + seed data  |
| `make build`   | Build Docker images                    |
| `make up`      | Start all services                     |
| `make down`    | Stop all services                      |
| `make logs`    | Tail logs for all services             |
| `make shell`   | Open Django shell                      |
| `make migrate` | Run migrations                         |
| `make seed`    | Seed users and chat rooms              |
| `make ngrok`   | Start Ngrok tunnel                     |
| `make clean`   | Remove containers, volumes, and images |
| `make restart` | Restart all services                   |
| `make test`    | Run Django tests                       |

## Troubleshooting

### CSRF 403 on Login

- Verify `CSRF_TRUSTED_ORIGINS` in `.env` includes your domain with scheme (`https://...`)
- Verify `nginx.conf` has `proxy_set_header Host $http_host`
- Check Django logs: `make logs` and look for CSRF error details

### WebSocket Won't Connect

- Check browser console for mixed content errors (http page trying wss://)
- Verify `nginx.conf` has the `map` directive and Upgrade headers
- Verify `ALLOWED_HOSTS` includes your domain
- Check `proxy_read_timeout` isn't too short

### "Connection Refused" After Docker Restart

- Wait for health checks: `docker compose ps` should show all services as "healthy"
- Check if migrations ran: `make logs` and look for migration output

### Session Expires Immediately

- If using Ngrok (HTTPS) with `DEBUG=True`, session cookies won't have the `Secure` flag, which is correct for development
- If using Ngrok with `DEBUG=False`, ensure `SESSION_COOKIE_SECURE=True` is set (it is by default when `DEBUG=False`)

## Tech Stack

| Component     | Choice                          | Why                                  |
| ------------- | ------------------------------- | ------------------------------------ |
| ASGI Server   | Daphne                          | Native Django Channels integration   |
| Channel Layer | Redis (channels_redis)          | Only production-supported option     |
| Database      | PostgreSQL 16 + psycopg3        | Modern async-capable adapter         |
| Frontend      | Django templates + Tailwind CDN | Zero build step                      |
| Auth          | Django built-in                 | Handles CSRF correctly by default    |
| Proxy         | Nginx                           | Industry standard, WebSocket support |
| Tunnel        | Ngrok                           | Free HTTPS tunneling for development |
