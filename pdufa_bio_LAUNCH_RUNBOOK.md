# pdufa.bio — Launch Runbook (Vercel Pro + domain)

Status as of 2026-06-18. The site runs on Vercel project **pdufa-bio-staging** (team `team_HLoQLqGljk4BGwM2Recpsid5`), behind an AES password gate, `noindex`. These are the steps **only you can do** (payment / DNS / account), with the exact values.

## 1. Upgrade to Vercel Pro (~$20/mo per member) — REQUIRED before public launch
Why: Vercel **Hobby is non-commercial only** — a revenue/ad-supported pdufa.bio violates Hobby ToS. Pro also unlocks true sub-daily cron, 60-second function timeout (headroom for the ORATS+CT.gov fan-out in `/api/data`), and more bandwidth.

Steps:
1. vercel.com → your team → **Settings → Billing/Plans** → **Upgrade to Pro**.
2. Confirm the project `pdufa-bio-staging` is under the upgraded team.
3. (Optional) rename the project to `pdufa-bio` in **Settings → General**.

## 2. Custom domain pdufa.bio
1. Own the domain (registrar of choice). 
2. Vercel project → **Settings → Domains → Add** → `pdufa.bio` (and `www.pdufa.bio`).
3. Vercel shows DNS records to set at your registrar:
   - **Apex `pdufa.bio`** → `A` record to `76.76.21.21` (Vercel anycast), **or** switch the domain to Vercel nameservers if offered.
   - **`www`** → `CNAME` to `cname.vercel-dns.com`.
4. Wait for propagation; Vercel auto-issues the SSL cert.

## 3. Environment variables (Production)
Project → **Settings → Environment Variables** → ensure these exist for **Production**:
- `ORATS_API_KEY` = (your ORATS Delayed Data key)
- `FMP_API_KEY` = (your FMP key)
Redeploy after setting so `/api/data` returns live options/price.

## 4. Decide: keep the gate, or go public
- **Keep gated beta:** leave the AES wrapper + `noindex,nofollow`. The "Remember me on this device" toggle keeps the installed app auto-unlocking.
- **Go fully public:** serve `pdufa_today_dashboard.html` / `pdufa_app.html` directly (drop the AES wrapper for `today.html`/`app.html`), **remove `noindex`** in `vercel.json` headers + the `<meta name="robots">` so search engines index it. Keep the first-visit modal + footer legal (FDA non-affiliation, not-advice). Point `pdufa.bio/` → the dashboard and `pdufa.bio/app` → the app.

## 5. Cron (auto-refresh)
`vercel.json` already defines 5 daily crons (11/14/17/20/23 UTC). On **Pro** these run reliably; you can tighten to exact intra-day times if desired. On Hobby they may be throttled (each cron is just a cache "warmer" — freshness still holds via edge cache + client poll).

## 6. PWA / Android (already built)
- Manifest, icons (192/512 + maskable), and a service worker are deployed. On Android Chrome → open `/app.html` → **Install app**.
- When you move to the real domain, the PWA `start_url` is `/app.html`; if you change the app path, update `manifest.webmanifest` `start_url`/`scope` and the `<link rel="manifest">` in the app head, then redeploy.

## 7. Pre-public checklist
- [ ] Vercel Pro active (commercial-use compliant)
- [ ] `pdufa.bio` domain attached + SSL green
- [ ] `ORATS_API_KEY` + `FMP_API_KEY` set in Production
- [ ] Decide gate vs public; if public, remove `noindex` + AES wrapper
- [ ] Historic "experimental" banner stays until all ~195 CRLs are source-verified (currently 16 verified, 17 mislabel, 20 with source URLs; rest are price-only/unverified)
- [ ] First-visit modal + footer legal present on both surfaces (they are)

## Recurring cost summary
- Vercel Pro: ~$20/mo. ORATS Delayed Data: ~$99/mo. FMP + Unusual Whales: per your plans. Vercel Pro is the small line item; the data feeds are the real cost.
