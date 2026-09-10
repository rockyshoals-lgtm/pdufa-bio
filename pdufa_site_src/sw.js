/* pdufa.bio service worker.
 *
 * v4 (2026-09-10). WHAT v3 DID WRONG, because it is worth not repeating.
 *
 * v3 routed by this test:
 *     req.mode === "navigate" || path.endsWith(".html") || path === "/" || path === "/api/data"
 *       -> network-first
 *     everything else -> CACHE-FIRST, and every 200 was written into the cache forever.
 *
 * A top-level navigation has mode "navigate", so clicking a link was fine. But a `fetch()`
 * from page script has mode "cors"/"same-origin", and our hub URLs ("/calendar",
 * "/decisions", "/learn/what-is-a-pdufa-date") end in no extension. They fell through to
 * cache-first and were stored permanently the first time any script requested them.
 *
 * Consequences, all observed on 2026-09-10:
 *   - a browser that visited in June kept serving the JUNE COPY of /calendar to every
 *     fetch(), complete with the stored June response headers (last-modified 27 Jun,
 *     age 0, x-vercel-cache MISS), which made it look like a live server response;
 *   - "/calendar/" was fresh because the trailing slash is a different cache key that was
 *     never stored, so the same page appeared to exist in two versions;
 *   - pages created after June were fresh at both forms, because they were never cached;
 *   - /build-info.json was pinned at its 2026-08-08 copy, so the freshness stamp on every
 *     page hydrated from a month-old file even though the fetch asks for cache:'no-store'
 *     (that flag controls the HTTP cache; it does not bypass this worker).
 *
 * The site's product is the date. A worker that can serve a months-old document is a
 * correctness bug, not a performance feature. So: documents and data are NEVER served from
 * this cache. Only genuinely static, content-addressed-ish assets are cached, and only when
 * the request is not a document.
 *
 * Bumping the cache name is load-bearing: the activate handler deletes every cache whose key
 * is not C, which is what evicts the poisoned v3 entries from browsers already carrying them.
 */
const C = "pdufa-v4";
const STATIC = ["/manifest.webmanifest", "/icon-192.png", "/icon-512.png", "/og.png"];

/* Images and fonts only. No .html, no .json, no extensionless paths -- those are documents
 * and data, and they always go to the network. */
const ASSET = /\.(?:png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot)$/i;

self.addEventListener("install", e => {
  self.skipWaiting();
  e.waitUntil(caches.open(C).then(c => c.addAll(STATIC).catch(() => {})));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;                 // let the network handle it

  let u;
  try { u = new URL(req.url); } catch (_) { return; }
  if (u.origin !== location.origin) return;         // never touch third-party requests

  const isDocument = req.mode === "navigate" || req.destination === "document";
  const cacheable = !isDocument && ASSET.test(u.pathname);

  if (!cacheable) {
    /* Documents, JSON, the API, and anything extensionless: network, always. On a network
     * failure fall back to the cache ONLY if something is there (the STATIC list), which
     * for a document means nothing -- an error is honest; a June calendar is not. */
    e.respondWith(fetch(req).catch(() => caches.match(req)));
    return;
  }

  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(resp => {
      if (resp && resp.status === 200 && resp.type === "basic") {
        const copy = resp.clone();
        caches.open(C).then(c => c.put(req, copy));
      }
      return resp;
    }))
  );
});
