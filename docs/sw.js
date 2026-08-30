const CACHE="portfolio-intelligence-v5";const ASSETS=["./","./index.html","./assets/style.css","./assets/app.js","./manifest.webmanifest"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener("fetch",e=>{if(e.request.url.includes("/data/dashboard.json") || e.request.url.includes("/data/trend.json") || e.request.url.includes("/data/alerts.json")){e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));return;}e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));});
