# pdufa.bio — one-click mine + build + deploy

**Goal:** convert pdufa.bio back to a FREE PUBLIC 2026 FDA PDUFA calendar, powered by OUR crawler + data, and refreshable with a single double-click.

## The one file to run
**`run_pdufa_bio.bat`** (in `9realms\`) does the whole thing:
1. **Full mine** — `catalyst_crawler.py --auto-universe --discover` (SEC EDGAR + ClinicalTrials.gov + FDA AdCom + openFDA + FMP), primary-sourced with provenance. ~2–4 hrs; leave the window open.
2. **Score + pages** — GUNGNIR readout scores, category calendars, SEO pages, dated archive.
3. **Merge into the calendar** — `build_slate_from_crawl.py` folds the fresh mine into the live data (`api/data.js` SLATE), **keeping every curated entry** (hand-written drug/indication, decided outcomes `OUT`, NCT tracking `REG`) and **adding newly-discovered PDUFAs**.
4. **Flip to free public calendar** — `apply_calendar_site_state.py`: homepage → the "2026 FDA PDUFA Calendar", password gate off, pricing stripped.
5. **Deploy** — `vercel deploy --prod` → pdufa.bio.

## One-time setup (required for the deploy step)
Add your Vercel token to `Odin Perfection\.env_master`:
```
VERCEL_TOKEN=your_token_here
```
(get it at https://vercel.com/account/tokens). Without it, steps 1–4 still run and stage everything; the deploy just skips with a note. `deploy_site.bat` re-publishes the current build without re-mining.

## What each new piece does
- **`pdufa_site_src\build_slate_from_crawl.py`** — the mine→calendar bridge (the piece that was missing). MERGE mode: keeps curated, adds new. Backs up `api/data.js` first. `--dry-run` to preview. *Verified on the June crawl: 37 curated + 33 new = 70 forward catalysts, all curation preserved (OTLK, CORT, CYTK, MLYS, NUVL, …).*
- **`pdufa_site_src\apply_calendar_site_state.py`** — restores `index.html` from `_home_pdufa_backup.html`, repoints `/` → the calendar, disables the `middleware.js` password gate (→ public), removes the `/pricing` route. Backs up `vercel.json` first. Idempotent. *Verified via dry-run.*
- **`run_pdufa_bio.bat`** — the master one-click (above).
- **`deploy_site.bat`** — fixed: was pointing at a deleted old-session path + a missing `_deploy_vercel.py`; now deploys `pdufa_site_src` via the Vercel CLI using `VERCEL_TOKEN`.

## Data flow (so it's auditable)
`catalyst_crawler.py` → `catalysts_out\catalysts_public.csv` (provenance-tagged, republishable rows only) → `build_slate_from_crawl.py` → `api/data.js` `SLATE` → the serverless `/api/data` enriches live (ORATS options + FMP price + CT.gov status) → the calendar renders. Free/pro is env-gated (`PRO_GATING_ENABLED`, unset = all free).

## Pricing (added 2026‑07‑09): free calendar + $10/mo Pro, 1 month free
- **Free (public):** the full PDUFA calendar — dates, drugs, indications, live prices, T‑minus.
- **Pro — 1 month free, then $10/mo billed annually ($120/yr):** options **expected‑move + IV** and **date‑slip alerts** (when the FDA/registry date moves). This is the existing `_freeView` gate in `api/data.js`.
- **What I changed:** the Stripe checkout now grants a **30‑day free trial** (`create-checkout-session.js` → `subscription_data.trial_period_days: 30`), and the site‑flip **keeps** the pricing page (no longer strips it).
- **Your one‑time Stripe setup (so Pro can charge):**
  1. In Stripe, create a **Product** "pdufa.bio Pro" with a **recurring yearly price of $120** (this is the "$10/mo billed annually"). Copy its **price ID** (`price_...`).
  2. On Vercel → the pdufa.bio project → **Settings → Environment Variables**, add:
     `STRIPE_SECRET_KEY=sk_live_...`, `STRIPE_PRO_PRICE_ID=price_...`, `PRO_SESSION_SECRET=<any long random string>`, and — to actually turn on the paywall for Pro features — `PRO_GATING_ENABLED=1`.
     (Leave `PRO_GATING_ENABLED` unset while you want everything free.)
  3. Point your Stripe **webhook** at `https://pdufa.bio/api/stripe-webhook`.
- Until you set those, the site runs **fully free** (Pro just isn't purchasable yet). The base calendar is free either way.
- The pricing page copy should read: **"Pro — 1 month free, then $120/year ($10/mo). Cancel anytime."** (tell me and I'll set that exact line in `pricing.html`).

## Crawler upgrade (2026‑07‑09): beat BPC on PDUFAs, fully original content
The recall gap vs BPC was **mega‑cap + combo PDUFAs** (GSK, PFE, GILD, LLY, NVS, and partner‑shared drugs) — names that don't file clean US 8‑Ks. Two durable fixes to `catalyst_crawler.py` (all primary‑sourced, nothing from BPC republished):
1. **Broader PDUFA phrasing** — the press/news scanner now also catches **BsUFA** (biosimilars), **GDUFA** (generics), **"regulatory decision / FDA decision expected/anticipated in Qx"**, and bare quarter/half dates. Verified: it now matches the mega‑cap/foreign phrasings it used to miss.
2. **BPC‑independent partner propagation** — co‑developer PDUFAs now propagate using **our own captured data** (any drug found under 2+ tickers), not just the BPC seed. This closes combo‑PDUFA gaps (e.g. MRK/BMY/ALPMY on one drug) as original content.
- **Still worth doing (highest‑leverage remaining):** add the missing mega‑caps to `bigpharma_pdufa_seed.csv` with a real IR/FDA `source_url` each — **GSK, PFE, GILD, LLY, NVS, GH** aren't seeded. I can verify + add those next (each independently sourced = original/republishable). After the first real crawl, send me `catalysts_out\qa_diff.json` and I'll confirm the recall gain and top up the seed.

## Notes / honest caveats
- The crawl is long (~2–4 hrs) and runs on your machine, not here. It's resumable — re-run if it dies.
- The calendar's decided-outcomes (`OUT`) + NCT map (`REG`) are curated; the bridge preserves them but doesn't auto-generate them — add new decided outcomes by hand as PDUFAs resolve.
- The GUNGNIR/category/SEO steps are carried over from the prior working pipeline; if any of their output needs re-wiring into the site, it'll show on the first real run (send me `catalysts_out\qa_diff.json` + any errors).
- Everything backs up before it writes (`api/data.js.bak_*`, `vercel.json.bak_*`, `middleware.js.disabled`), so the flip is reversible.
- Informational calendar / educational — not investment advice (carried in the site footer).
