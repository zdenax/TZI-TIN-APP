const CACHE_NAME = 'tzi-pwa-v24';
const STATIC_ASSETS = [
  '/manifest.webmanifest',
  '/icon.svg',
  '/static/vendor/katex/katex.min.css',
  '/static/vendor/katex/katex.min.js',
  '/static/css/style.css?v=22',
  '/static/css/glosar.css?v=22',
  '/static/js/core.js?v=14',
  '/static/js/format.js?v=16',
  '/static/js/glosar.js?v=20',
  '/static/js/shell.js?v=16',
  '/static/js/arena.js?v=14',
  '/static/js/account.js?v=14',
  '/static/js/offline.js?v=14',
  '/static/js/gamification.js?v=14',
  '/static/js/rooms.js?v=15',
  '/static/js/menu.js?v=15',
  '/static/js/chunks.js?v=14',
  '/static/js/modes.js?v=14',
  '/static/js/comp_modes.js?v=14',
  '/static/js/recall.js?v=14',
  '/static/js/quiz.js?v=15'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (['/login', '/register', '/logout', '/trial', '/admin', '/quiz.wasm', '/automat', '/teorie', '/api/teorie', '/glosar', '/api/glosar', '/automat-delta.jpg', '/fmt.js', '/automat-core.js'].some(p => url.pathname.startsWith(p))) return;

    if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async cache => {
        return fetch(req).then(networkRes => {
          if (networkRes.ok) cache.put(req, networkRes.clone());
          return networkRes;
        }).catch(() => cache.match(req));
      })
    );
    return;
  }

  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then(res => {
        if (res.ok && !res.redirected) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
        }
        return res;
      }).catch(async () => {
        const cached = await caches.match(req);
        if (cached) return cached;
        return caches.match('/');
      })
    );
    return;
  }

  if (url.pathname === '/api/sources' || url.pathname === '/api/questions' || url.pathname === '/api/recall') {
    event.respondWith(
      caches.open(CACHE_NAME).then(async cache => {
        const fetchPromise = fetch(req).then(networkRes => {
          if (networkRes.ok) cache.put(req, networkRes.clone());
          return networkRes;
        }).catch(() => cache.match(req));
        return fetchPromise;
      })
    );
    return;
  }

  event.respondWith(
    fetch(req).catch(async () => {
      const match = await caches.match(req);
      if (match) return match;
      return new Response('', { status: 408, statusText: 'Offline' });
    })
  );
});
