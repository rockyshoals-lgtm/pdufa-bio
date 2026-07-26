const C="pdufa-v3";
const STATIC=["/manifest.webmanifest","/icon-192.png","/icon-512.png","/og.png"];
self.addEventListener("install",e=>{self.skipWaiting();e.waitUntil(caches.open(C).then(c=>c.addAll(STATIC).catch(()=>{})));});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener("fetch",e=>{
  const req=e.request,u=new URL(req.url);
  // HTML / navigations / api: NETWORK-FIRST so new deploys always win (never serve a stale gate)
  if(req.mode==="navigate"||u.pathname.endsWith(".html")||u.pathname==="/"||u.pathname==="/api/data"){
    e.respondWith(fetch(req).catch(()=>caches.match(req)));return;
  }
  // static assets: cache-first
  e.respondWith(caches.match(req).then(r=>r||fetch(req).then(resp=>{
    if(resp&&resp.status===200&&u.origin===location.origin){const cp=resp.clone();caches.open(C).then(c=>c.put(req,cp));}
    return resp;
  })));
});
