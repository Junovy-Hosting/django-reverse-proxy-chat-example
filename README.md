# Faerie Chat - Django WebSocket Chat Behind Nginx Reverse Proxy

A fully working Django Channels chat application that demonstrates an example configuration for running Django behind an Nginx reverse proxy with Ngrok tunneling.

This repo exists because getting CSRF, WebSocket, sessions, and fail2ban to all work correctly behind a reverse proxy is surprisingly tricky — and the errors are confusing. Every setting is heavily commented to explain _why_ it's needed.

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Test Users](#test-users)
- [Chat Features](#chat-features)
  - [Real-Time Messaging](#real-time-messaging)
  - [Reactions and Replies](#reactions-and-replies)
  - [Emoji-Only Messages](#emoji-only-messages)
  - [GIF Search (Giphy)](#gif-search-giphy)
  - [SVG Avatars](#svg-avatars)
  - [Online Presence](#online-presence)
- [PWA Support](#pwa-support)
  - [Manifest and Icons](#manifest-and-icons)
  - [Service Worker Caching](#service-worker-caching)
  - [Push Notification Plumbing](#push-notification-plumbing)
- [Database Migrations and Indexing](#database-migrations-and-indexing)
  - [Models](#models)
  - [Indexes](#indexes)
  - [Running Migrations](#running-migrations)
- [The CSRF Problem Explained](#the-csrf-problem-explained)
- [fail2ban Pitfalls](#fail2ban-pitfalls)
- [WebSocket Through Nginx](#websocket-through-nginx)
- [Logout Flow](#logout-flow)
- [Mobile Viewport](#mobile-viewport)
- [Makefile Commands](#makefile-commands)
- [Troubleshooting](#troubleshooting)
- [Tech Stack](#tech-stack)

## Architecture

```
Internet → Ngrok (https://faeries.ngrok.app)
         → localhost:80
         → Nginx (reverse proxy + static files + access logging)
         → Daphne/Django (HTTP + WebSocket via ASGI)
         → PostgreSQL (database)
         → Redis (WebSocket channel layer + presence tracking)
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

## Chat Features

### Real-Time Messaging

Messages are sent over WebSocket using Django Channels with a Redis channel layer. Each chat room maps to a channel layer group (`chat_{slug}`). Messages are persisted to PostgreSQL and broadcast to all connected users in real time.

The last 50 messages are loaded on page entry (newest at the bottom), and new messages stream in via WebSocket. A floating scroll-to-bottom button appears when the user scrolls up, and auto-scroll only triggers when the user is near the bottom of the chat to avoid disrupting reading.

### Reactions and Replies

Users can react to messages with emoji. Clicking a reaction badge toggles it (add/remove). The reaction state is stored per user per emoji per message via a `UniqueConstraint`, and counts are broadcast to all users in real time.

Replies are supported through a swipe-right gesture on mobile or a reply button on hover (desktop). A reply preview bar appears above the input showing the parent message, and the reply is rendered inline with a purple left border linking back to the original.

### Emoji-Only Messages

Messages containing only emoji characters render at a larger size for visual impact — similar to iMessage and WhatsApp:

| Emoji Count | Size Class |
| ----------- | ---------- |
| 1–3 emoji   | `text-4xl` |
| 4–6 emoji   | `text-2xl` |
| 7+ emoji    | Normal     |

Detection uses the `Extended_Pictographic` Unicode property with handling for ZWJ sequences, variation selectors, and skin tone modifiers.

### GIF Search (Giphy)

If a `GIPHY_API_KEY` is set in the environment, a GIF button appears in the chat input bar. It opens a panel with trending GIFs and a search field. Selecting a GIF sends its URL as a message, which is unfurled inline as an embedded image for all users.

### SVG Avatars

Every user gets a deterministic SVG avatar generated client-side from their username. The generator uses FNV-1a hashing to select:

- A gradient color pair from a curated palette of purples, teals, and ambers
- A gradient angle (0°, 90°, 180°, 270°)
- An eye style (circles, dots, closed, wink)
- A mouth style (smile, grin, cat, line)

Avatars appear in the navbar, chat messages, room list cards, and the online users panel. No external service or image storage is required — the same username always produces the same avatar.

### Online Presence

A live "Online" sidebar shows who's currently connected to each chat room.

**How it works:**

- Each WebSocket connection is tracked in a Redis HASH (`presence:{slug}`), keyed by `channel_name` with the `username` as the value
- This handles multi-tab correctly — the same user with 3 tabs appears once in the list, and is only removed when all tabs close
- On server startup, `flush_all_presence()` clears all stale entries from a previous process that exited without clean disconnects
- Join/leave system messages ("has entered the chamber" / "has left the chamber") are debounced with a 120-second cooldown using `SET NX EX` to suppress spam from page refreshes and reconnects

**UI:**

- **Desktop**: Sidebar is always visible to the right of the chat (w-56)
- **Mobile**: Hidden by default, toggled via a users icon in the room header, renders as a slide-in overlay

## PWA Support

The app is installable as a Progressive Web App on mobile and desktop. All PWA assets are served as Django views — no static files or build step required.

### Manifest and Icons

`/manifest.json` serves the PWA manifest with app metadata (name, theme color, display mode). Icons at `/pwa/icon-192.svg` and `/pwa/icon-512.svg` are generated on-the-fly as SVG with a purple-to-teal gradient and the letter "F".

```
GET /manifest.json    → pwa.manifest()
GET /pwa/icon-192.svg → pwa.pwa_icon(size=192)
GET /pwa/icon-512.svg → pwa.pwa_icon(size=512)
```

### Service Worker Caching

`/sw.js` registers a service worker with two caching strategies:

| Resource Type          | Strategy      | Why                                       |
| ---------------------- | ------------- | ----------------------------------------- |
| CDN assets (Tailwind, fonts, icons) | Cache-first   | Versioned URLs, safe to cache long-term |
| HTML pages             | Network-first | Serves latest content; falls back to cache offline |
| WebSocket connections  | Ignored       | Service workers cannot proxy WebSocket    |
| Non-GET requests       | Pass-through  | POST/PUT are dynamic by nature            |

On install, the service worker pre-caches all CDN URLs. On activate, it cleans up old cache versions.

### Push Notification Plumbing

The service worker includes `push` and `notificationclick` event handlers, ready for a future push notification backend. In the chat room, a dismissable banner prompts users to enable notification permissions (choice persisted in `localStorage`).

## Database Migrations and Indexing

### Models

The chat app has three models:

| Model      | Purpose                | Key Fields                                        |
| ---------- | ---------------------- | ------------------------------------------------- |
| `ChatRoom` | Chat room container    | `name`, `slug`, `description`, `created_by`       |
| `Message`  | Individual messages    | `room` (FK), `user` (FK), `content`, `parent` (self-FK for replies), `created_at` |
| `Reaction` | Emoji reactions        | `message` (FK), `user` (FK), `emoji`              |

### Indexes

Database indexes are defined in the model `Meta` classes and created via Django migrations:

```python
# Message — composite index for the main room detail query
# (fetch last 50 messages per room, ordered by newest first)
class Meta:
    ordering = ["created_at"]
    indexes = [
        models.Index(
            fields=["room", "-created_at"],
            name="idx_message_room_created",
        ),
    ]

# Reaction — composite index for counting reactions per emoji
class Meta:
    indexes = [
        models.Index(
            fields=["message", "emoji"],
            name="idx_reaction_msg_emoji",
        ),
    ]
    constraints = [
        models.UniqueConstraint(
            fields=["message", "user", "emoji"],
            name="unique_user_reaction_per_emoji",
        ),
    ]
```

**Why these indexes matter:**

- `idx_message_room_created` — The room detail view runs `room.messages.order_by("-created_at")[:50]`. Without this composite index, PostgreSQL would scan all messages for the room and sort them. With the index, it's an index-only scan that returns the 50 newest directly.
- `idx_reaction_msg_emoji` — After toggling a reaction, the consumer counts reactions per emoji: `Reaction.objects.filter(message=message, emoji=emoji).count()`. This index covers that exact query.
- `unique_user_reaction_per_emoji` — Enforces at the database level that a user can only have one reaction of each emoji type per message (also creates an implicit index).

### Running Migrations

Migrations run automatically on container startup via the entrypoint script. To run them manually:

```bash
# Via Makefile
make migrate

# Or directly
docker compose exec web python manage.py migrate

# To create new migrations after model changes
docker compose exec web python manage.py makemigrations chat
```

Migration history:

| Migration | Description |
| --------- | ----------- |
| `0001_initial` | ChatRoom and Message models |
| `0002_reactions_and_replies` | Reaction model, Message.parent self-FK |
| `0003_add_message_room_created_index` | Composite index on `(room, -created_at)` |

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

## Mobile Viewport

The app handles mobile browser chrome (Safari's dynamic toolbar, Android's navigation bar) with several techniques:

- `viewport-fit=cover` in the viewport meta tag to extend into safe areas
- `env(safe-area-inset-*)` CSS functions for notch and home indicator spacing on the nav bar and chat input
- `100svh` (small viewport height) for the chat container to avoid content hiding behind the browser's bottom toolbar
- Responsive GIF images with `max-width: min(20rem, 100%)` to prevent overflow on narrow screens
- `overflow-x: hidden` and `max-width: 100vw` on the body to prevent horizontal scroll

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

### Online Panel Shows Stale Users

- Presence data is flushed on server startup via `flush_all_presence()` in `ChatConfig.ready()`
- If users appear stuck after a crash or force-stop, restart the web container: `docker compose restart web`
- Multi-tab is handled correctly — a user is only removed from the panel when all their tabs disconnect

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
| Presence      | Redis HASH                      | Ephemeral, no DB overhead            |
| PWA           | Django views (inline JS/JSON)   | No static files or build step        |
| Icons         | Phosphor Icons (CDN)            | Lightweight, consistent style        |
| Emoji Picker  | emoji-picker-element (CDN)      | Web component, no framework needed   |
