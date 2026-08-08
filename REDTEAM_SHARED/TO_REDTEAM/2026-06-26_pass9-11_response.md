# Builder response to Red Team Pass 9 (strategy/design) + 10a (PR) + 10b (tokens) + 11 (security) · 2026-06-26

## ✅ SHIPPED THIS PASS — security hardening (live + verified on the apex)
From the **security audit (Pass 11)**, the builder-actionable P0/P2 items are done and verified via live header inspection:
- **Security headers added globally** (`vercel.json` `/(.*)`): `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()`, and **`Content-Security-Policy-Report-Only`** (started in Report-Only so nothing breaks; the site rendered clean under it). All five verified present on the live response.
- **Killed the uncached `/api/data.js` scraping alias** — it now 301s to the canonical, edge-cached `/api/data` (verified the alias canonicalizes). This closes the denial-of-wallet / cache-bypass vector.
- **Scoped CORS** — `data.js` now sends `Access-Control-Allow-Origin: https://www.pdufa.bio` + `Vary: Origin` (no more `*`), so other sites can't read the feed cross-origin in a browser. (`node --check` passes.)
- **Added `/.well-known/security.txt`** (responsible-disclosure contact).

Plus the **Pass-10a builder task**: `/research/pdufa-stock-run-up-by-market-cap` now carries **`Dataset` JSON-LD** (creator, `temporalCoverage` 2024–2026, CC-BY-4.0 license, n=694) + a visible **"Cite this dataset"** block with a suggested citation and a data-request email — so every journalist cite is a clean, rich, attributable link.

## 🔴 OWNER / ARCHITECTURE — the two security items that aren't a quick edit
1. **[P0 before charging] Gate the Pro data on `/api/data`.** The feed still returns the full dataset (options/IV/run-up) to anyone — the audit's #1 risk. Real fix = **free/pro payload split + per-user auth**: serve calendar facts to everyone, gate the Pro fields behind a signed session checked in the function. That auth layer **is** the Stripe integration (`verify-access.js`), which isn't live yet — so this must land **with** the Stripe go-live, before you charge. (Mitigated for now: CORS scoped + uncached alias killed reduce casual scraping.)
2. **[P0] Rate-limit `/api/data`** — needs a **Vercel Firewall** rule (dashboard: ~60/min/IP) or KV-backed edge middleware. Owner/dashboard action; I can wire KV middleware if you'd rather do it in code.

## 🟠 OWNER — quick but yours to decide
- **Rotate the access pass.** It's a shared static string that's been pasted in chats/briefs. Pick a new one and I'll re-encrypt `/app` + `/today` with it in minutes. (Lower urgency than it sounds — the pass never protected the data; the API gating above is the real fix. The long-term answer is per-user auth for Pro.)
- **Confirm Vercel env vars** (ORATS/FMP keys) are **server-only + marked Sensitive**, and rotate them if they were ever in the old deleted repo's history. (No client leak was found — confirm-only.)

## 🟢 BIGGER PROJECTS (recommended, not one-pass fixes)
- **Pass 10b — the light-clinical-teal redesign.** This is a genuine **multi-day redesign** (light-first public site + dark `[data-theme="pro"]` app, Inter font, retire the gold for teal `#0E7C86`, sentence-case, tabular numerals, bordered rows, AA fixes) across ~500 pages **plus** the encrypted app. The tokens are excellent and drop-in; I'd recommend doing it as a dedicated build (I can pilot it on one surface — the homepage or a condition page — so you can see it before committing the whole site).
- **Pass 9 / 10a — PR + index cleanup (mostly done or owner).** The index-cleanup and internal-linking items from Pass 9's sprint are already shipped (redirects, on-site hub links, condition de-mistag, story blocks). What remains is **owner outreach** — the `/research` asset is now citation-ready, so the pitch kit (STAT/Feuerstein, Endpoints, BioPharma Dive, Fierce, Seeking Alpha) can go out, and **GSC Removals** on the lingering old-ODIN URLs.
- **Promote CSP Report-Only → enforcing** after a few days of watching for violations (then it actually contains XSS rather than just reporting).

**Bottom line:** the site is now hardened on the two things the audit said ship before launch that are in builder scope — **standard security headers + the open-cache/CORS scraping vectors** — and the link-bait asset is citation-ready. The remaining security work (**Pro-data auth gating + rate-limit**) is the architecture that goes live **with Stripe**, and the **teal redesign** is the next big build whenever you want to start it.
