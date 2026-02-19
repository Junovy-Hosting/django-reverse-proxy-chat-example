from django.http import HttpResponse, JsonResponse


def manifest(request):
    """Serve the PWA manifest as JSON."""
    data = {
        "name": "Faerie Chat",
        "short_name": "FaeChat",
        "description": "Real-time chat chambers for the fae realm",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0f",
        "theme_color": "#7c3aed",
        "orientation": "any",
        "icons": [
            {
                "src": f"/pwa/icon-{size}.svg",
                "sizes": f"{size}x{size}",
                "type": "image/svg+xml",
                "purpose": "any maskable",
            }
            for size in (192, 512)
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


def service_worker(request):
    """Serve the service worker JS inline."""
    js = """
// Faerie Chat Service Worker
const CACHE_NAME = 'faechat-v1';

const CDN_URLS = [
    'https://cdn.tailwindcss.com',
    'https://cdn.jsdelivr.net/npm/emoji-picker-element@^1/index.js',
    'https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.2/src/regular/style.css',
    'https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.2/src/bold/style.css',
    'https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap'
];

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(CDN_URLS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(names) {
            return Promise.all(
                names.filter(function(name) { return name !== CACHE_NAME; })
                     .map(function(name) { return caches.delete(name); })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', function(event) {
    var url = new URL(event.request.url);

    // Ignore WebSocket and non-GET requests
    if (url.protocol === 'ws:' || url.protocol === 'wss:' || event.request.method !== 'GET') {
        return;
    }

    // Cache-first for CDN assets
    var isCDN = CDN_URLS.some(function(cdn) { return url.href.startsWith(cdn); }) ||
                url.hostname.includes('fonts.gstatic.com') ||
                url.hostname.includes('cdn.jsdelivr.net');

    if (isCDN) {
        event.respondWith(
            caches.match(event.request).then(function(cached) {
                return cached || fetch(event.request).then(function(response) {
                    if (response.ok) {
                        var clone = response.clone();
                        caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
                    }
                    return response;
                });
            })
        );
        return;
    }

    // Network-first for HTML pages
    if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
        event.respondWith(
            fetch(event.request).then(function(response) {
                if (response.ok) {
                    var clone = response.clone();
                    caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
                }
                return response;
            }).catch(function() {
                return caches.match(event.request);
            })
        );
        return;
    }
});

// Push notification handler (ready for future push backend)
self.addEventListener('push', function(event) {
    var data = event.data ? event.data.json() : {};
    var title = data.title || 'Faerie Chat';
    var options = {
        body: data.body || 'You have a new message',
        icon: '/pwa/icon-192.svg',
        badge: '/pwa/icon-192.svg',
        data: { url: data.url || '/' }
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    var url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(windowClients) {
            for (var i = 0; i < windowClients.length; i++) {
                if (windowClients[i].url.includes(url) && 'focus' in windowClients[i]) {
                    return windowClients[i].focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});
"""
    return HttpResponse(js.strip(), content_type="application/javascript")


def pwa_icon(request, size):
    """Generate an SVG icon for the PWA manifest."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7c3aed"/>
      <stop offset="100%" stop-color="#2dd4bf"/>
    </linearGradient>
  </defs>
  <rect width="{size}" height="{size}" rx="{size * 0.15}" fill="url(#bg)"/>
  <text x="50%" y="54%" dominant-baseline="central" text-anchor="middle"
        font-family="serif" font-weight="700" font-size="{size * 0.5}"
        fill="white" opacity="0.95">F</text>
</svg>"""
    return HttpResponse(svg.strip(), content_type="image/svg+xml")
