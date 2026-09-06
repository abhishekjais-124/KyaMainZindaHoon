const CACHE_NAME = 'kmzh-cache-v16';
const urlsToCache = [
  '/KyaMainZindaHoon/',
  '/KyaMainZindaHoon/static/css/pwa_fullscreen.css?v=20260907-9',
  '/KyaMainZindaHoon/static/css/mobile_bottom_nav.css?v=20260907-9',
  '/KyaMainZindaHoon/static/css/premium.css?v=20260907-9'
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
        .catch(() => caches.match(event.request).then(response => response || caches.match('/KyaMainZindaHoon/')))
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
