# Addendum to Pass 2 — Audit of the "auto-refresh ~5×/day" claim · 2026-06-19

**Question put to the red team:** How is the data refreshed, and is it server-side?

**Inspection limits:** `/api/data` returns an **empty body** to an unauthenticated external fetch (gated, like `/today` and `/app`). Chrome bridge is down, and curling for headers is out of scope, so I **could not read `/api/data`'s body or response headers directly.** This is reasoned from the client JS in `pdufa_bio_LAYOUT_AUDIT.md` (§4 web lines ~214–215, §5 app lines ~390–391) + the architecture. Items I can't see from outside are tagged **[VERIFY SERVER-SIDE]**.

---

## How it actually works (two layers, don't conflate them)

**Layer 1 — server-side data assembly (this is the "~5×/day").**
The prices/options can only be assembled server-side: the client never calls ORATS or FMP directly (it only fetches same-origin `/api/data`), and those vendors need API keys + would fail CORS from a browser. So a **server-side job pulls ORATS (options) + FMP (price), writes a snapshot, and `/api/data` serves it.** "~5×/day" is the cadence of *that job*. **Yes — the substantive refresh is server-side.**

**Layer 2 — client polling (this is NOT the 5×/day).**
Both the web dashboard and the app do, on load and then on a timer:
```js
fetch('/api/data', {cache:'no-store'})            // swaps DATA, updates the "LIVE · <refreshed_utc>" label
setInterval(refresh, 600000)                      // 600000 ms = every 10 minutes
```
So the browser re-pulls `/api/data` **~144×/day (every 10 min)** — it just re-reads whatever snapshot the server last wrote. The page also ships with an **embedded fallback snapshot** in the HTML (`DATA.as_of` was **2026-06-17** in the audited markup — i.e. ~2 days old) used for instant first paint / if the fetch fails.

**Net:** server regenerates ~5×/day; client re-reads every 10 min; "LIVE" is the client label, not the true data age.

---

## Findings / risks

**F1 — 🔴 `cache:'no-store'` does NOT protect against your CDN. (ties directly to the Pass-2 cache bug.)**
`{cache:'no-store'}` only bypasses the **browser** cache. It does **nothing** to a CDN/edge cache in front of the origin. We already proved the edge is serving **stale HTML** on `/` and `/calendar`. If `/api/data` is served through that same edge with any `s-maxage`, the edge can hand the client a **stale snapshot** and silently cap real freshness *below* 5×/day — while the UI still says "LIVE." **[VERIFY SERVER-SIDE]** that `/api/data` returns `Cache-Control: no-store` (or `private, no-cache, max-age=0`). Belt-and-suspenders: make the client cache-bust — `fetch('/api/data?t=' + Date.now(), {cache:'no-store'})`.

**F2 — 🟠 What is `refreshed_utc`, really? [VERIFY SERVER-SIDE]**
The "LIVE · <refreshed_utc>" label is only honest if `refreshed_utc` = the time the **ORATS/FMP pull completed** (true snapshot age). If it's set to `now()` when the response is served, the label is theater — it'll read "live" over data that's hours old. Confirm it reflects snapshot **generation** time, and surface it literally.

**F3 — 🟠 What triggers the job, and is it firing? [VERIFY SERVER-SIDE]**
"~5×/day" needs a real scheduler — Vercel Cron, a GitHub Action, an external scheduler. Confirm: (a) it exists and the schedule is genuinely ~5×/day, (b) it's actually firing (check the last N run logs), and (c) it is **not** "regenerate on deploy" or "on first request" — either of which would make data as stale as the last deploy / first hit. The embedded `as_of` being 2 days old in the audited shell is a yellow flag worth confirming against the live `refreshed_utc`.

**F4 — 🟡 "LIVE / live price" vs the underlying data latency.**
Per the engine notes, ORATS here is the **Delayed** feed (~15-min vendor delay), and a 5×/day sample means the options/price shown can be **hours** old between runs. Calling that "LIVE" overstates it for the exact audience (traders) who will check. Prefer precise: **"Snapshot · prices as of 14:05 ET · options ~15-min delayed · next refresh ~18:00."** (This is the W6 wording fix from Pass 1, now with the mechanism behind it.)

**F5 — 🟡 No stale-data guard.**
If `/api/data` fails or is edge-stale, the user silently sees the embedded fallback (2-day-old) snapshot with no warning. Add a guard: if `refreshed_utc` is older than ~12h (or the fetch fails), show "⚠ data may be stale — last updated <time>."

**F6 — 🟡 Cadence vs market hours.**
5×/day spread across 24h means some refreshes land overnight when nothing trades, and the gap *during* market hours may be wider than "5×/day" implies. If freshness during RTH matters, weight the schedule to market hours (e.g., 09:45 / 12:00 / 15:45 ET + an EOD + a pre-open) rather than evenly.

---

## What to verify server-side (the things I can't see from outside)
1. `/api/data` response headers → must be `no-store`/`no-cache` (F1).
2. `refreshed_utc` is the snapshot **generation** time, not request time (F2).
3. The scheduler exists, is ~5×/day, and the last runs actually fired (F3).
4. Live `refreshed_utc` is recent (not the 2-day-old `as_of` seen in the shell) (F3/F5).

## Bottom line
Architecture is sound and **the refresh is genuinely server-side** (it has to be). The exposure is **freshness vs. labeling**: `no-store` won't beat your edge cache (same root cause as the stale `/` and `/calendar`), "LIVE" oversells a ~5×/day, ~15-min-delayed snapshot, and there's no stale guard. Fix the cache headers on `/api/data`, make `refreshed_utc` honest, and reword "LIVE" → "Snapshot · last updated <time>." None of this touches the guardrails.

*— Red Team Pass 2 addendum (data freshness).*
