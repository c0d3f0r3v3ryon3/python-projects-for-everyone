// web_panel/static/sw.js
const CACHE_NAME = 'admin-panel-v1';
const urlsToCache = [
  '/',
  '/static/style.css', // Если у вас есть
  '/static/script.js',
  '/static/manifest.json',
  '/login'
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
