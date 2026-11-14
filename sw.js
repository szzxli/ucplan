var CACHE = 'ucplan-v19';
var FILES = ['/', '/transfer-os', '/uc-course', 'styles.css', 'app.js', 'i18n.js', 'manifest.webmanifest', 'favicon.svg', 'logo.svg', 'lang/en.json', 'lang/es.json', 'lang/zh-CN.json', 'lang/zh-TW.json', 'lang/ko.json', 'lang/ja.json'];
self.addEventListener('install', function (e) {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(FILES); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') { return; }
  // Navigations always go to the network first: a cached page that came
  // from a redirect must never be served for a navigation.
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(function () { return caches.match(e.request); }));
    return;
  }
  e.respondWith(caches.match(e.request).then(function (r) { return r || fetch(e.request); }));
});
