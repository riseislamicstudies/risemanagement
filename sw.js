/* Risenegar service worker: فقط «پوسته‌ی برنامه» را کش می‌کند. داده‌ها (Supabase) هرگز کش نمی‌شوند. */
var CACHE = "risenegar-v1.7";
var SHELL = ["./", "index.html", "manifest.json", "icon-192.png", "icon-512.png", "icon-maskable-512.png"];
self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return Promise.all(SHELL.map(function (u) { return c.add(u).catch(function () {}); }));
  }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener("fetch", function (e) {
  var r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== location.origin) return;           // Supabase و هر سایت دیگر: دست نمی‌زنیم
  if (r.mode === "navigate") {                                                // صفحه: اول شبکه (نسخه‌ی تازه)، اگر قطع بود کش
    e.respondWith(fetch(r).then(function (res) {
      var cp = res.clone(); caches.open(CACHE).then(function (c) { c.put("index.html", cp); }); return res;
    }).catch(function () { return caches.match("index.html").then(function (m) { return m || caches.match("./"); }); }));
    return;
  }
  e.respondWith(caches.match(r).then(function (m) {                           // آیکون و manifest: اول کش
    return m || fetch(r).then(function (res) { var cp = res.clone(); caches.open(CACHE).then(function (c) { c.put(r, cp); }); return res; });
  }));
});
