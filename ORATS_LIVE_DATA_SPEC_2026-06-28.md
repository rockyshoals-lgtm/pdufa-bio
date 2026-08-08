# pdufa.bio — Live ORATS Options Data · Design Spec

**Status: DRAFT for review — nothing deployed.**
**Date: 2026-06-28 · Owner/operator: Odin Catalyst LLC**

---

## 0. TL;DR

You already pull ORATS inside `/api/data` (expected move, ATM IV, call wall, OI).
"Going live" is **not** a new integration — it's turning the freshness dial: poll more
often, lower the CDN cache TTL, and do it **server-side only**. With 100,000 calls/month
and ~40 catalysts, a market-hours, tiered poll built on ORATS's multi-ticker **summary**
endpoint gets you **~1–3 minute fresh** data for a few thousand calls/month — comfortably
inside budget.

**The hard gate is ORATS redistribution licensing, not the engineering.** See §9 — confirm
that before any public display.

---

## 1. Goal & non-goals

**Goal:** near-real-time options context (IV, expected move, IV-crush, call wall, put/call
OI) on the **Pro** surface — sourced, timestamped, and within 100k ORATS calls/month.

**Non-goals:** tick-by-tick streaming; per-visitor ORATS calls; displaying ORATS data
without a redistribution license.

---

## 2. The one rule that governs everything

**Never call ORATS from the browser or per page-load.** A public page that fetched ORATS on
each visit would burn the month in an afternoon:

> 100,000 calls ÷ ~40 catalysts = **2,500 page-views** would exhaust the entire monthly budget.

ORATS must only be called by a **server-side cron**, which writes a cached snapshot the
website reads. "Live" = poll frequency + cache TTL, nothing more.

---

## 3. Current state (as built)

- `api/data.js` → `orats(tk, pdufa, KEY)` hits `GET https://api.orats.io/datav2/strikes?token=…&ticker=TK` — **one call per catalyst**.
- **Cron:** 5×/day (`vercel.json` crons at 11/14/17/20/23 UTC). **Cache:** `s-maxage=16000` (~4.4h).
- **Output `opt`:** `spot, exp, dte, atm_strike, em_pct, atm_iv_pct, call_wall, call_oi, put_oi, cp_oi` (Pro-gated; stripped for anon).
- **Current consumption:** ~5 × 40 = **~200 calls/day ≈ ~6k/month (~6% of budget).**
- **The only thing missing is freshness** — the 4.4h cache is why it looks stale, not the call budget.

---

## 4. Budget math (≈40 catalysts, 1 ORATS call each per refresh)

| Cadence | Calls/month | Verdict |
|---|---|---|
| Today (5×/day, all) | ~6,000 | Way under — but 4.4h stale |
| Every 5 min, **market-hours only** (~6.5h × 21d) | ~65,000 | ✅ comfortable, ≤5-min fresh |
| Every 3 min, market-hours | ~110,000 | ⚠️ just over — back off to 4 min |
| **Tiered** (near-term fast / far-term slow) | **~3–10k** | ✅ near-real-time where it matters |

ORATS rate limit is ~100 req/min → a 40-call refresh is fine; just don't fan out all tiers in the same second.

---

## 5. The optimization that makes it nearly free: summary endpoint + on-demand strikes

- **Per-ticker `strikes`** (current) = 40 calls/refresh. Gives call-wall + per-strike OI + exact expected move (ATM straddle).
- **Multi-ticker `summaries`** = **1–2 calls** for IV across *all* catalysts.
- **Hybrid:**
  - `summaries` (frequent, cheap) drives the **IV / expected-move / IV-crush strip** for every catalyst.
  - `strikes` is pulled **on demand** — only when a Pro user opens a specific catalyst — for the **call wall, per-strike OI, and exact expected move**.
- This collapses 40 calls → **~2 per refresh**, making 100k effectively unlimited for this use.

**Note on expected move:** `em_pct` today is computed from the ATM straddle (needs `strikes`).
From `summaries` you can approximate `em ≈ spot × IV × √(dte/365)`, or keep the *exact* em on
the slower strikes tier and label the fast-tier value "IV-implied (approx)."

> **CONFIRM with ORATS:** does your plan's `summaries` (or `cores`) endpoint accept
> comma-separated tickers and return `smvVol`/IV? If yes, the §6 architecture is the cheap path.

---

## 6. Proposed architecture (the exact changes)

### 6a. Tier each catalyst by days-to-event
- `NEAR` = ≤ 21 days to PDUFA (where IV actually moves) · `FAR` = > 21 days.
- ~8 NEAR / ~32 FAR at any time.

### 6b. Split the function — move ORATS off the read path
This is the key shift. Today ORATS is called **on the read path** (`/api/data` calls it on
cache-miss) — risky if traffic spikes cause many misses.

- **`/api/data`** → becomes a pure **READ** endpoint: returns the cached snapshot, **zero ORATS calls.**
- **`/api/refresh`** → new **cron-only** (not public) endpoint: fetches ORATS (summaries + any due strikes), writes the snapshot to a store.

### 6c. Store the snapshot
- **Vercel KV** (Redis) or **Edge Config** holds `{ ticker: opt, _as_of }` — ~40 small keys, written by `/api/refresh`, read by `/api/data`.
- Decouples the website entirely from the ORATS budget (reads never touch ORATS).

### 6d. Crons (market hours ≈ 13:30–20:00 UTC, weekdays)
```
*/2  13-20 * * 1-5   → /api/refresh?tier=near    (every 2 min)
*/30 13-20 * * 1-5   → /api/refresh?tier=far     (every 30 min)
0    11    * * 1-5   → /api/refresh?tier=all      (pre-market warm so the open snapshot is ready)
```
- Vercel **Pro** supports minute-level cron; **Hobby caps at 1/day** — confirm the plan.

### 6e. Cache TTL
- `/api/data` `s-maxage`: **16000 → 180–300** (3–5 min) + `stale-while-revalidate`.
- Keep the existing `refreshed_utc`; add a per-field `opt_as_of` so the UI can show "as of HH:MM ET."

### 6f. Budget guardrail
- A monthly counter incremented in `/api/refresh`; at 80% alert, at 90% auto-throttle the FAR tier.
- Weekday + market-hours gate already halves the naive cost; optionally skip US market holidays.

---

## 7. What it looks like on the site (Pro surface)

- Per-catalyst **live strip**: expected move %, ATM IV, IV-vs-cohort, call wall, put/call OI — refreshed every few minutes during market hours, stamped **"as of 10:42 ET."**
- **IV-crush flag** (already fires at IV ≥ 120%) and the **T-120 IV-expansion curve** refresh live.
- Honest label, matching the `/coverage` brand: **"~3–5 minute snapshot, not a live tick."**

---

## 8. Licensing — DO THIS FIRST (the real gate)

- Displaying ORATS-derived values on a **public** site (even Pro-paywalled) is **redistribution**.
- Many market-data contracts permit **internal use** but require a separate **redistribution / display license** to show data to your users.
- **Confirm your ORATS plan permits external display/redistribution — in writing — before shipping it publicly.** This is the one thing that can sink the feature.
- Check whether ORATS requires an attribution credit (e.g., "Options data by ORATS").

---

## 9. Rollout plan

1. **Confirm ORATS redistribution license + `summaries` multi-ticker support.** (Blocking.)
2. Build `/api/refresh` + the KV/Edge-Config store behind a flag; `/api/data` still reads the old inline path.
3. Switch `/api/data` to read the store; lower `s-maxage` to 300.
4. Set the crons; watch the monthly budget counter for a week (should land a few k).
5. Roll the live strip onto the Pro dashboard with the "as of" stamp.

**Rollback:** revert `/api/data` to the inline ORATS path + `s-maxage=16000`, remove the new crons. (Single-file revert; the store is additive.)

---

## 10. Open questions for David

- ORATS plan: **live** or 15-min **delayed**? Does the contract allow **redistribution/display**?
- Does `summaries`/`cores` accept **multiple tickers** and return IV?
- **Vercel plan** (Hobby vs Pro) — sets the minimum cron interval.
- **Vercel KV vs Edge Config** preference for the snapshot store?
- Do you want exact expected move on every tier (more `strikes` calls) or IV-approx on the fast tier?

---

*Informational/engineering spec only — not investment advice. Nothing in this document is deployed; it is a proposal for review. Owner/operator: Odin Catalyst LLC.*
