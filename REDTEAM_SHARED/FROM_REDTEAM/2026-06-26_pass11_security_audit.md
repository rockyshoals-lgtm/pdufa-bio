# pdufa.bio — Security Audit · 2026-06-26

Live audit via Chrome (client-code scan, auth tests) + Vercel. Verdict: **the architecture is sound and no secrets leak — but the data API is wide open and the security headers are missing.** Fix those two before the Pro launch. Nothing here is a "you're owned" emergency; the attack surface is small (static site + one serverless function, no DB writes / user input yet).

## ✅ Passed (good — verified)
- **No secrets in client code.** Scanned the full `/today` bundle (631 KB): zero API keys, tokens, AWS (`AKIA…`), Google (`AIza…`), bearer tokens, or private keys. The only "ORATS" hit is the UI source-label, not a key. ORATS/FMP keys are server-side only.
- **Vercel doesn't leak function source.** `/api/data.js` returns `application/json` (the data), not the function code — confirmed. Function source is never served.
- **No exposed config/repo files.** `/.env`, `/.env.local`, `/.git/config`, `/.git/HEAD`, `/vercel.json`, `/package.json`, `/.vercel/project.json`, `/server.js`, `/middleware.js` → all **404**.
- **Auth cookie is HttpOnly** (JS can't read `document.cookie`) — good XSS hygiene.
- **HSTS present** (`max-age=63072000`). Apex→www is a clean 308. Old ODIN project deleted (prior finding) — no stale attack surface there.

## 🔴 High — the "gate" is cosmetic; `/api/data` is public
- **`/api/data` returns the full dataset with no credentials.** Tested from the page with `credentials:'omit'` → **200, 35 KB, identical to the authenticated response.** The `/today` and `/app` password gates only hide the UI; **the data they protect is one open API call away** at `https://pdufa.bio/api/data`.
- **CORS `Access-Control-Allow-Origin: *`** on `/api/data` → any website can read/scrape it cross-origin.
- **The `.js` alias bypasses the cache.** `/api/data` carries `s-maxage=16000`, but `/api/data.js` returns `cache-control: max-age=0, must-revalidate` + `x-vercel-cache: MISS` — every hit recomputes at origin (and, per the Pass-2b finding, may re-pull ORATS/FMP). That's a **denial-of-wallet / scraping vector** that sidesteps your cache.
- **Why it matters now:** you're launching **Pro ($29/mo)** whose value (live options, IV, run-up data) is exactly what `/api/data` serves for free. Anyone can rebuild your Pro product on your open API. **This is the #1 thing to fix before charging.**
- **Fix:**
  1. Put the **Pro data behind real auth** (signed session/JWT checked in the function), or split a small **free** payload (calendar facts) from the **Pro** payload (options/IV/run-up) and auth-gate the latter.
  2. **Remove `ACAO: *`** unless you intend public embedding; scope to your own origin.
  3. **Kill the uncached `/api/data.js` alias** (route only the canonical `/api/data`) so nothing bypasses the edge cache.
  4. **Rate-limit** `/api/data` (Vercel Firewall rule or edge middleware + KV counter, e.g. 60/min/IP) to stop scraping + protect the ORATS/FMP budget.

## 🟠 Medium — missing security headers
Only HSTS is set. **Missing: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.** That's clickjacking (the site can be iframed), MIME-sniffing, and no XSS containment. Add globally via `vercel.json` (it's a 5-minute fix):
```json
{ "headers": [ { "source": "/(.*)", "headers": [
  { "key": "X-Frame-Options", "value": "DENY" },
  { "key": "X-Content-Type-Options", "value": "nosniff" },
  { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
  { "key": "Permissions-Policy", "value": "geolocation=(), microphone=(), camera=(), payment=()" },
  { "key": "Content-Security-Policy-Report-Only", "value": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" }
] } ] }
```
Notes: the site uses inline `<script>`/`<style>`, so CSP needs `'unsafe-inline'` (or move to nonces/hashes later). Start in **Report-Only**, watch for breakage, then promote to enforcing `Content-Security-Policy`. If you adopt the Inter font (design pass), add `fonts.googleapis.com` to `style-src` and `fonts.gstatic.com` to `font-src`. `connect-src 'self'` is fine since ORATS/FMP are server-side.

## 🟡 Low / hygiene
- **Shared static access pass.** The `/today`+`/app` password is one static string — and it's been pasted into chats and the red-team brief. **Rotate it now**, and don't rely on it as data protection (the API is open anyway). For Pro, move to per-user auth.
- **`/today.html` (and presumably `/app.html`) resolve** alongside `/today`/`/app`. They're `noindex`'d; harmless, but ideally 301 the `.html` to the clean path.
- **No `/.well-known/security.txt`.** Add one (contact for responsible disclosure) — cheap professionalism for a finance site.
- **Env hygiene (confirm in Vercel):** ORATS/FMP/any keys are **server-only** env vars (not `NEXT_PUBLIC_…`), marked **Sensitive**. Rotate them if they were ever in the old repo's history. (No client leak found, so this is confirm-only.)
- **When email capture ships** (the planned per-event signup): validate server-side, rate-limit, never put the email in a URL/query, and use double-opt-in. New input = new attack surface.

## Pre-launch security checklist (priority order)
1. **[P0] Gate the Pro data** (auth on `/api/data`, or free/pro split) — before charging. *(High §)*
2. **[P0] Add the security headers** via `vercel.json`. *(Medium §)*
3. **[P0] Rate-limit `/api/data` + remove the uncached `.js` alias + drop CORS `*`.** *(High §)*
4. **[P1] Rotate the access pass; plan per-user auth for Pro.**
5. **[P1] Confirm Vercel env vars are server-only + Sensitive; rotate keys if ever exposed.**
6. **[P2] 301 the `.html` aliases; add `security.txt`.**
7. **[P2] Harden the future email-capture endpoint** when it lands.

**Bottom line:** you're not leaking keys and the repo/config isn't exposed — the build is clean. The real risk is that **your paid product's data is a free, unauthenticated, uncached, CORS-open API**, and the site ships **without standard security headers**. Close those two and rotate the pass, and pdufa.bio is genuinely hardened for launch.

*— Red Team Pass 11 (security audit; live via Chrome + Vercel).*
