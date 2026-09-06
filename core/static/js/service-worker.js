const CACHE_NAME = 'kmzh-cache-v8';
const urlsToCache = [
  '/',
  '/static/css/pwa_fullscreen.css?v=8',
  '/static/css/mobile_bottom_nav.css?v=8',
  '/static/css/premium.css?v=8'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys
        .filter(key => key.startsWith('kmzh-cache-') && key !== CACHE_NAME)
        .map(key => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request).then(response => response || caches.match('/')))
    );
    return;
  }

  // Prefer the network for deployable assets so an installed PWA cannot keep
  // an old stylesheet indefinitely after a new Render deployment.
  if (new URL(event.request.url).pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(event.request)
        .then(networkResponse => {
          if (event.request.method === 'GET' && networkResponse.ok) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          }
          return networkResponse;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request).then(networkResponse => {
        if (event.request.method === 'GET' && networkResponse.ok) {
          const copy = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        }
        return networkResponse;
      }))
  );
});
