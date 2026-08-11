const CACHE_NAME = "finanzas-shell-v2";
const APP_SHELL = ["/accounts", "/movimientos", "/login", "/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

// Solo cachea peticiones GET al propio origen (el backend vive en otro origen
// y sus respuestas -saldo, movimientos- nunca deben servirse desde cache).
//
// Network-first, no cache-first: siempre se intenta la red primero para que
// un despliegue nuevo se vea al instante. La cache solo se usa como
// respaldo si no hay conexion (offline).
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match(request))
  );
});
