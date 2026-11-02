var CACHE = 'ucplan-v3';
var FILES = ['index.html', 'transfer-os.html', 'uc-course.html', 'styles.css', 'app.js', 'i18n.js', 'manifest.webmanifest', 'favicon.svg', 'logo.svg', 'lang/en.json', 'lang/es.json', 'lang/zh-CN.json', 'lang/zh-TW.json', 'lang/ko.json', 'lang/ja.json'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(FILES); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }));
});
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') { return; }
  e.respondWith(caches.match(e.request).then(function (r) { return r || fetch(e.request); }));
});
