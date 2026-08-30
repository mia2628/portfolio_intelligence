const CACHE="portfolio-intelligence-v8-2";
const STATIC=["./assets/style.css?v=6","./assets/app.js?v=6","./manifest.webmanifest"];

self.addEventListener("install",event=>{
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(cache=>cache.addAll(STATIC))
  );
});

self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

self.addEventListener("fetch",event=>{
  const url=new URL(event.request.url);

  // Always network-first for HTML and live JSON to prevent stale title/data.
  if(
    event.request.mode==="navigate" ||
    url.pathname.endsWith("/index.html") ||
    url.pathname.endsWith("/data/dashboard.json") ||
    url.pathname.endsWith("/data/trend.json") ||
    url.pathname.endsWith("/data/alerts.json")
  ){
    event.respondWith(
      fetch(event.request,{cache:"no-store"})
        .catch(()=>caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached=>cached||fetch(event.request))
  );
});
