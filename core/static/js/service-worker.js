const CACHE_NAME = 'kmzh-cache-v22';
const urlsToCache = [
  new URL('../css/tailwind.css?v=20260909-1', self.location).toString(),
  new URL('../css/pwa_fullscreen.css?v=20260909-2', self.location).toString(),
  new URL('../css/mobile_bottom_nav.css?v=20260909-1', self.location).toString(),
  new URL('../css/premium.css?v=20260909-7', self.location).toString()
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
  if (event.request.method !== 'GET') return;

  const requestUrl = new URL(event.request.url);
  const staticRoot = new URL('../', self.location).pathname;
  if (
    requestUrl.origin !== self.location.origin ||
    !requestUrl.pathname.startsWith(staticRoot)
  ) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        const refresh = fetch(event.request).then(networkResponse => {
          if (networkResponse.ok) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          }
          return networkResponse;
        });
        if (response) {
          refresh.catch(() => undefined);
          return response;
        }
        return refresh;
      })
  );
});
