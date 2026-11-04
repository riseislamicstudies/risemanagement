/* Risenegar service worker: فقط «پوسته‌ی برنامه» را کش می‌کند. داده‌ها (Supabase) هرگز کش نمی‌شوند. */
var CACHE = "risenegar-v3.0";
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

/* ===== v3.0: اعلان پوش (حتی وقتی مرورگر بسته است) ===== */
self.addEventListener("push", function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (x) { d = { body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.title || "Rise Tracker", {
    body: d.body || "",
    icon: "icon-192.png",
    badge: "icon-192.png",
    tag: d.tag || undefined,
    dir: "rtl",
    lang: "fa",
    data: { url: d.url || "" }
  }));
});
self.addEventListener("notificationclick", function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || "";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (list) {
    for (var i = 0; i < list.length; i++) {
      if (list[i].url.indexOf(self.registration.scope) === 0) {
        list[i].postMessage({ type: "open", url: url });
        return list[i].focus();
      }
    }
    return self.clients.openWindow(self.registration.scope + (url && url.charAt(0) === "#" ? url : ""));
  }));
});
