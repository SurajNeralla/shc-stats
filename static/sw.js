const CACHE_NAME = 'cricket-stats-v4';
const urlsToCache = [
  '/manifest.json'
];

self.addEventListener('install', event => {
  // Force new service worker to activate immediately
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('activate', event => {
  // Take control immediately
  event.waitUntil(clients.claim());
  var cacheAllowlist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheAllowlist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Network-First Strategy for Dynamic Apps
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // We received a valid network response, put it in cache and return it
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        var responseToCache = response.clone();
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, responseToCache);
        });
        return response;
      })
      .catch(err => {
        // If network fails, serve from cache
        console.log("Network unreachable, serving from cache", err);
        return caches.match(event.request).then(response => {
            if (response) {
                return response;
            }
            return new Response("You are currently offline. Please check your internet connection.", {
                status: 503,
                statusText: "Service Unavailable",
                headers: new Headers({ "Content-Type": "text/plain" })
            });
        });
      })
  );
});
