# pdufa.bio — Security RE-AUDIT · 2026-06-26

Verified the Pass-11 fixes live (Chrome). **Header hardening is solid — but the #1 finding (the open Pro-data API) is NOT fixed.**

## ✅ Fixed (verified)
- **Security headers — all added.** `/` now returns: **CSP (Report-Only)**, **X-Frame-Options: DENY**, **X-Content-Type-Options: nosniff**, **Referrer-Policy: strict-origin-when-cross-origin**, **Permissions-Policy** (present), plus HSTS. Clickjacking + MIME-sniffing + no-XSS-policy are resolved. Report-Only CSP is the correct rollout — watch the violation reports, then promote to enforcing `Content-Security-Policy`.
- **CORS narrowed.** `/api/data` `Access-Control-Allow-Origin` is now **`https://www.pdufa.bio`** (was `*`). Good — but see the caveat below.
- **`/.well-known/security.txt` — added** (200). Nice professional touch.

## 🔴 STILL OPEN — the core issue: `/api/data` is still a public, unauthenticated API
- **Tested no-credentials just now: `200`, full `35,742`-byte dataset.** Nothing changed — the entire "Pro" payload (live options, ATM IV, run-up, IV-crush, OI skew) is still served to anyone with **no auth**.
- **CORS scoping does NOT fix this.** `Access-Control-Allow-Origin` only restricts **browser** cross-origin JS. A server-side request (curl, Python, a scraper, a competitor's backend) **ignores CORS entirely** and still pulls the full dataset. So the data is exactly as exposed as before to any non-browser client. CORS was a good hygiene step, but it is **not** data protection.
- **`/api/data.js` alias is still live (`200`)** — the uncached, cache-bypassing route I flagged is not removed. Still a denial-of-wallet / scraping vector.
- **Why it still matters:** your `/pricing` page sells this exact data as the **$29 Pro** value. As of now, Pro's data is free and scriptable. This is the one to close before charging.

**To actually fix (pick one):**
1. **Gate the data server-side** — the `/api/data` function checks a signed session/JWT (or an API key for the institutional tier) and returns `401` without it. This is the real fix.
2. **Or split free vs pro** — a public `/api/data` with only calendar facts (date/drug/indication), and an authed `/api/pro-data` with the options/IV/run-up. Then CORS + auth on the pro one.
3. **Or decide the data is free on purpose** — then change the Pro value prop on `/pricing` to the *experience* (dashboard, alerts, watchlist digest), not "exclusive data," so you're not selling something that's openly downloadable. A deliberate choice, not an accident.
Plus: **remove the `/api/data.js` route** (canonical `/api/data` only) and **rate-limit** (Vercel Firewall / edge + KV, e.g. 60/min/IP) regardless of which option you pick.

## 🟡 Minor — still open
- **`/today.html` and `/app.html` still resolve (`200`)** — not 301'd to the clean paths. Low priority (they're `noindex`'d), but tidy them.
- **COOP** (`Cross-Origin-Opener-Policy`) not set — optional isolation hardening; nice-to-have, not required.
- **Access pass** — assumed rotated per your note (can't verify externally, and I won't test the old one). Reminder: it isn't data protection while the API is open.

## Verdict
Real progress on the perimeter — the headers were the easy, high-value win and they're done correctly, and CORS + security.txt are good hygiene. **But the central risk is unchanged: your paid product's data is a free, unauthenticated API**, and scoping CORS doesn't stop a server-side scraper. The single P0 remains: **gate `/api/data` (or split free/pro) and remove the `.js` alias + add rate-limiting** before the Pro launch. Everything else is genuinely hardened.

## Updated checklist
1. **[P0 — still open] Auth-gate `/api/data` (or free/pro split).** The only thing that protects Pro.
2. **[P0 — still open] Remove `/api/data.js`; add rate-limiting.**
3. **[done] Security headers · CORS scoped · security.txt.**
4. **[P2] 301 the `.html` aliases; optionally add COOP.**
5. **[confirm] Pass rotated; Vercel env vars server-only + Sensitive.**

*— Red Team Pass 12 (security re-audit; live via Chrome).*
