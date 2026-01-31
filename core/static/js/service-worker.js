const CACHE_NAME = 'kmzh-cache-v1';
const urlsToCache = [
  '/'
  // Add more assets as needed (use paths that exist to avoid install failure)
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
