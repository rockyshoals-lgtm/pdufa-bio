> 🧭 **FABLE — START HERE:** the master handoff for pdufa.bio **and** the Momentum Scanner is
> **`..\FABLE_HANDOFF\START_HERE.md`**. Read that first for current state, next actions, and rules.

# pdufa.bio → Momentum Tracker — BUILD NOTES (builder)

_Role split: a separate research-assistant Claude drops specs into `INBOX/`; this builder Claude actions them here. Last updated 2026-07-01._

## Goal
Retool pdufa.bio into a **momentum-tracking site** that looks like the uploaded example
(`index.html` — dark Tailwind, "hype-score" dashboard: High-Score Alerts rail + ranked
watchlist + detail modal), but **better and faster**. Keep basically the same formatting.

## Codebase recon (verified 2026-07-01)
- **Stack:** static HTML on **Vercel** (no framework; `package.json` only pulls `stripe`).
- **Data feed:** `/api/data.js` serverless function; `vercel.json` crons hit it **5×/day**
  (11/14/17/20/23 UTC). This is the live data source the dashboard should fetch.
- **Other API:** `create-checkout-session.js`, `stripe-webhook.js`, `verify-access.js` (Stripe
  pro-gating; anon calls get pro fields stripped — keep that intact).
- **Key files:** `index.html` (home), `app.html` (big app/dashboard, 447KB), `calendar.html`,
  `holding.html` (current coming-soon page), `historic.json` (691KB), `/pdufa/<event>/` SEO
  pages, `/condition/…`, `/coverage/`, `/learn/`, `/methodology/`.
- **Current state: DARK.** `vercel.json` redirects everything except api/holding/robots/sitemap/og
  to `/holding.html`. The real pages exist but are redirected away.

## Build approach (baseline — refine per INBOX specs)
1. **Static momentum dashboard** (single fast page) modeled on the example, fetching `/api/data`
   (fallback to local `site/data.json` for offline review). Client-side momentum scoring so the
   API can stay unchanged initially.
2. **Faster/better than the example:** async fetch + skeleton loader (no WebSocket reconnect
   spam), sortable/filterable/searchable watchlist, per-name sparkline, cap/event filters,
   localStorage filter persistence, responsive, SEO meta + JSON-LD, urgency ("days to catalyst").
3. **Momentum score (transparent):** blends approval odds (Hist LOA), price momentum, option-
   implied move + IV rank, and proximity to catalyst → 0–100 + a driver breakdown. NOT a
   probability of approval. (Research Claude may refine weights/inputs — I'll action.)
4. **Preserve** the SEO pages, Stripe gating, and the holding page until go-live.

## Deploy policy — HARD
- **No deploy without David's explicit "go."** Do not touch `vercel.json` redirects, do not
  `vercel deploy`, do not flip the holding page. Build + stage only.
- Any new API key / new serverless code / cron change is **owner-gated** — list it, don't ship it.

## Status
- [x] Handoff workspace + `INBOX/` created; codebase recon done.
- [x] `site/data.json` seeded (55 forward biotech catalysts w/ momentum fields).
- [ ] v1 dashboard (`site/index.html`) — building.
- [ ] Action research specs as they land in `INBOX/`.
- [ ] Owner review → deploy on go.

## Open questions for David
1. Deploy authority: confirm **build-and-hold** (my 
---

## 2026-07-03 — Builder integration review (LEADLAB engine) — STAGED, owner-gated
Reviewed + hardened Fable's staged engine against each spec's acceptance criteria. No deploy.

**Verified (real compile / real data):**
- `node --check` passes: api/surges.js, api/premarket.js, api/build-watchlist.js, lib/scoring.mjs (node v22).
- ESM import of lib/scoring.mjs resolves; scoring matches the grid — scoreOpen(12,7)=0.548 (55%, spec-01 criterion ✓); null-relvol → gap-only fallback ✓; EXHAUSTION_RISK + ROCKET flags fire ✓.
- **Spec 03 CRITICAL field verified LIVE:** UW `/screener/stocks` response returns **`avg30_volume`** (LAES 20.7M, WEN 30.5M, AI 8.0M) — assumed name is correct, build-watchlist.js works as-is. Bonus: screener also returns pre-computed `relative_volume` + `stock_volume`.
- vercel.json: `/premarket` route + pre-market warm crons + nightly build-watchlist cron (0 23 * * 1-5); `.bak_fable` backups present (surges.js / surges.html / vercel.json).

**Fixed (correctness):**
- surges.html footer + detail-modal still carried the OLD "2,980-event survivorship-biased study" copy — contradicted the new unbiased engine. Rewrote both to the LEADLAB unbiased-base-rate framing + added the "reached +25% intraday ≠ your entry P&L" caveat.
- Surfaced richer tier labels (PRIME/BUILDING/WATCH/NOISE via `tier_new`) in card/alert/modal badges; legacy color classes retained for compat.

**Minor notes (non-blocking):** a couple pre-market grid cells have n<12 and aren't null-guarded in scoring.mjs (conservative; consider an n-floor when the history is extended). A huge thin mover scores tier PRIME (p≈1.0 from the 40%+ gap row) while also flagging EXHAUSTION_RISK — acceptable, but a future tweak could cap tier on EXHAUSTION_RISK.

**Specs:** 01 ✓ verified · 02 ✓ code+compile verified (live pre-market smoke test pending the 4:00–9:30 ET window) · 03 ✓ field verified (needs UW_API_KEY + CRON_SECRET in Vercel + one seed run) · 04 ✓ copy+tier labels (deeper pre-market visual styling optional). 01–04 moved to INBOX/done/. **05 open** (P2 — extend Polygon history).

**Owner actions to go live (David):** set `UW_API_KEY` + `CRON_SECRET` in Vercel env → `vercel --prod` from pdufa_site_src → `GET /api/build-watchlist?key=<CRON_SECRET>` once to seed the ADV map → check `/api/premarket` (pre-market) and `/api/surges` (session).

**Extension roadmap (backtest-gated — NOT shipped):** (1) opening-velocity + pre-market rel-vol into make_grid (data in research/premarket_features.csv); (2) UW options-flow confluence booster — classify() already has a `uoaBull` hook + `UOA_BULL` informational flag, plumbing ready, gate UNVERIFIED until backtested; (3) extend base-rate history via research/pull_grouped.py (Polygon, resumable, 5/min) → rebuild grid drop-in; (4) halt/LULD + news-velocity triggers. Every new signal must be backtested for earliness + false-positive rate before shipping.

### 2026-07-03 — Extension backtest #1: opening velocity → NOT SHIPPED (failed the bar)
Backtested opening 1-min/5-min velocity (`r1_ret_pct`/`r5_ret_pct`) on the staged 641-event
`premarket_features.csv` (joined to `universe.csv` surge25 outcomes; base P=30.9%).
- Standalone it's weak/non-monotonic: 5-min velocity 0–2% → 15.8% (BELOW base); only ≥5% (48.8%),
  10–20% (72.7%), 20%+ (100%) are positive — i.e. only *strong* opening pops matter.
- **Fails vs current signals on both earliness AND precision:** open gap ≥10% (9:30)=61.7%,
  **pm 09:00 ≥10% (9:00, ~30m earlier)=74.8%**, opening-5min ≥5% (9:35)=60.9%.
- **No confluence lift:** gap≥10% AND 5min>0 = 59.5% vs gap≥10% AND 5min<0 (fading) = 63.2% — the
  fading group scored *higher*, so opening-velocity direction adds no separation over the gap.
- Only pocket of value: inside the noisy gap 5–10% zone, 5min≥5% → 21.1% vs 6–7% (but n=19, later).
**Decision:** do NOT add opening velocity to the scoring grid (violates "only ship what beats the
grid"). Pre-market rel-vol (the other half of extension #1) is already in the grid (91.8% confluence).
Candidate for future (more data): a low-gap-zone-only informational FAST_OPEN flag — not scored.

### Remaining extensions (still backtest-gated, not started)
- UW options-flow confluence booster: `classify()` has the `uoaBull` hook + `UOA_BULL` flag ready;
  needs an options-flow-vs-surge backtest (earliness + FP) before wiring live. NOT shipped.
- Extend base-rate history via `research/pull_grouped.py` (Polygon, needs `POLYGON_API_KEY`, 5/min,
  resumable) → rebuild `scoring_grid.json` (drop-in). Data task, no new backtest. Ongoing.
- Halt/LULD + news-velocity triggers: need a real feed + backtest. NOT started.
