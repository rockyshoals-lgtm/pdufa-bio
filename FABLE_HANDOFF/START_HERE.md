# FABLE — START HERE (Momentum-Stock Radar)
**Last updated: 2026-07-03 · Owner: David / Odin Catalyst LLC**

Your job, Fable, is one thing: **momentum stocks.** Catch small/micro-cap stocks that are
surging, rate how likely they are to keep running, and — the prime directive — **find better
ways to spot them SOONER.** Earlier, faster detection is the whole game.

There are two linked pieces to continue:
**(A) pdufa.bio — a live momentum-surge site**, and **(B) the Momentum Scanner** (the research +
engine that feeds it). Stay scoped to the folders listed below.

> **Read order:** this file → the deeper docs it points to. Current as of 2026-07-03.

---

## PRIME DIRECTIVE — find momentum sooner
The current engine reacts to surges that are *already* moving. The biggest wins come from
catching them **earlier in the move.** Your standing mandate is to research and build better
**leading** detection. Concrete directions (pick, prototype, backtest, measure "how many minutes
earlier does this fire?" + false-positive rate):

- **Pre-market / extended-hours movers.** FMP has **no pre-market feed** on the current plan
  (quotes freeze at the prior close until 9:30), so the board is blind before the open. A feed
  with real pre-market/real-time data (e.g. Polygon, Alpaca/IEX, or similar) is the single biggest
  unlock. Evaluate + wire one.
- **Velocity / acceleration, not just % move.** Rate-of-change of price *and* volume in the first
  minutes flags a runner before the absolute % gets big.
- **Volume before price.** An abnormal relative-volume ramp usually precedes the price spike —
  surface it as its own early trigger (needs an ADV source; FMP's quote lacks `avgVolume`).
- **Options / UOA before price.** Unusual call sweeps or an options-volume spike often fire ahead
  of the move — the scanner already scores this; push it earlier and lighter-weight.
- **Halts / LULD (limit-up/limit-down).** Trading halts are often the earliest tell of a parabolic
  move. Detect resumptions fast.
- **News / filing / social velocity.** 8-K/offering triggers, PR hits, and the *acceleration* of
  social mentions (StockTwits/Reddit) as leading confluence — secondary signals, never proof.
- **Confluence, fired ASAP.** The 🚀 ROCKET (abnormal volume **and** unusual options together) is
  the highest-quality signal — the goal is to raise it as early in the move as the data allows.
- **Gap scanner at 9:30.** The morning-runner study shows the intraday high lands by ~10:00 **62%**
  of the time — so catching the gap-up *at the open* beats reacting after it's run.

Every new signal should be **backtested on real data** for earliness + hit rate before it ships.

---

## PROJECT A — pdufa.bio momentum-surge site
**Source of truth (deploy from here):** `9realms\pdufa_site_src\`
**Live:** https://www.pdufa.bio  · **Host:** Vercel (static HTML + serverless ESM functions)
The site runs as a **momentum-surge radar** — a live board of surging small/micro-caps with an
odds rating and an educational on-watch flag.

### What's built & how it works
- **`api/surges.js`** — server-side surge engine. Pulls FMP live movers (`biggest-gainers` ∪
  `most-actives` → `batch-quote`), filters to small/micro (≤ $3B, move ≥ 8%), and **rates
  continuation odds** from the surge-study base rates. FMP key read from `process.env.FMP_API_KEY`
  — **never reaches the browser.** Edge-cached ~20s.
  - **Market-hours gating:** computes **only during 9:30–16:00 ET (OPEN).** Pre-market returns an
    "opens at 9:30" message and shows no data (FMP is blind pre-open — see the prime directive).
- **`api/log.js`** — daily auto-logger + call scorecard. Logs every **≥25% gainer** to Vercel KV /
  Upstash (`surge_log`), then does **T+1 scoring** (FMP intraday lags same-day): reconstructs
  open→10:30→noon to measure how often HIGH-ODDS morning setups continued. Cron `30 20 * * 1-5`.
- **`api/scorecard.js`** — read-only; returns the rolling scorecard the page shows.
- **`surges.html`** — the radar UI (dark). Fetches only `/api/surges`, renders the rated board + an
  educational **⚡ HIGH-ODDS "on-watch"** flag + a live scorecard line. Framing: **9:30am–noon ET,
  "ride the morning wave, exit by midday."** Auto-refresh ~20s (slower when not OPEN).
- **`middleware.js`** — private password gate (Vercel Edge Middleware). HTTP Basic Auth vs
  `SITE_PASSWORD` env; Vercel Cron allowed through via `CRON_SECRET`; **fail-open** (missing var /
  error → site stays up, ungated — deliberate). Needs `@vercel/edge` (in package.json).
- **`vercel.json`** — `/` and `/surges` serve `surges.html`; crons warm `/api/data`, `/api/surges`,
  `/api/log`.  **`package.json`** deps: `stripe`, `@vercel/kv`, `@vercel/edge`.

### Deploy (David's machine only — do NOT deploy from here)
```
cd 9realms\pdufa_site_src
vercel --prod
```
Keys already in Vercel env: `FMP_API_KEY` + Upstash (`KV_REST_API_URL/TOKEN` or
`UPSTASH_REDIS_REST_URL/TOKEN`). For the password gate David sets **`SITE_PASSWORD`** and
**`CRON_SECRET`** (both required) then redeploys.

### Open / pending
1. **Password gate go-live:** David sets `SITE_PASSWORD` + `CRON_SECRET` → redeploy → test login.
2. **Scorecard fill-in:** confirm `/api/log` populates the hit-rate a day after each session (T+1).
3. **Re-fit base rates to the 9:30–noon window:** swap the `CONT_BY_RELVOL` / `CONT_BY_MOVE` tables
   in `api/surges.js` for the re-fit when it's ready (see Project B), then redeploy.
4. **Relative-volume signal:** FMP quote lacks `avgVolume` → `relvol` can be null (move-based
   fallback). Wire an ADV source.
5. **Earlier detection:** everything in the Prime Directive — pre-market feed is #1.

---

## PROJECT B — Momentum Scanner (research + engine)
**Folder:** `9realms\Momentum Scanner\` · overview: `README.md` · kickoff: `MOMENTUM_CLAUDE_KICKOFF_PROMPT.md`

### The engine
- **`momentum_meme_scanner_v1.py`** — whole-market micro/nano scanner (FMP movers ∪ Unusual Whales
  flow firehose), filters to ≤ $300M, scores momentum 0–100 + a separate UOA 0–100, flags
  **🚀 ROCKET** (≥5× rel-vol AND unusual options firing together). Env keys **`FMP_API_KEY`,
  `UW_API_KEY`** (social keys optional). Writes `momentum_scan_latest.{json,js}` + timestamped snapshots.
- **`momentum_meme_dashboard.html`** — live dashboard (loads `momentum_scan_latest.js`, 60s refresh).
- **`run_momentum_scheduled.ps1` / `run_momentum_radar.bat`** — scheduled/loop runners (market hours).
  Scans are firing on schedule (see the `momentum_scan_2026-*_*.json` snapshots + `scheduled_run_*.log`).

### The research (base rates that feed the site)
- **`surge_study_report.md`** (+ `surge_study_phase1-6.py`): 2,980 surge days (small/micro, ~2yr).
  **Finding:** moderate early volume continues best — **<0.5× ADV first-hour → ~96% closed up;
  10×+ → ~68%** (blow-off tops fade). Drives the surges.js rating.
- **`morning_report.md`**: gap-up morning-runner + exit timing — **the intraday high lands by ~10:00
  62% of the time**; most fixed-time exits lose (survivorship caveat). Basis for the 9:30–noon framing.
- **`premarket_report.md`, `morning_slices_report.md`, `surge_forward_report.md`** — pre-market /
  9:30–noon slices (the re-fit for the site's rating tables, in progress).

### Open / pending
1. **Finish the 9:30–noon re-fit** → hand the new `CONT_BY_*` tables to the site (Project A #3).
2. Keep the scheduled scans + the Upstash 25%+ auto-log running — that's the **forward, unbiased
   learning dataset** (the historical study is survivorship-biased; the live log fixes that over time).
3. Attack the **Prime Directive** (earlier detection) — prototype + backtest new leading signals.

---

## HARD RULES (do not violate)
- **Real data only.** No fabrication/simulation. Red-team everything. If a datapoint can't be
  verified, say so and exclude it.
- **Educational only — NOT investment advice.** Never recommend buy/sell/hold. Frame everything as
  historical base rates + "you decide." Keep the ⚡ HIGH-ODDS flag educational.
- **API keys are env-vars only** — never hardcode into committed/deployed files. Never open or echo
  the Vercel token or any secret.
- **No deploy without David's explicit "go."** Build + stage only. Deploys run from David's machine.
- **Stay in your lane:** work only in `pdufa_site_src\`, `Momentum Scanner\`, `pdufa_bio_build\`,
  and this `FABLE_HANDOFF\` folder.

## Role split
A **research-assistant Claude** drops build specs into `9realms\pdufa_bio_build\INBOX\`; the
**builder (you, Fable)** actions them in `pdufa_site_src\` / `Momentum Scanner\`. Build-and-hold —
wait for David's "go" to deploy.

## Immediate next actions (in order)
1. Confirm the site is live + gated (David sets `SITE_PASSWORD`+`CRON_SECRET`, redeploys) and the
   scorecard is filling in (T+1).
2. **Prime directive:** scope + prototype an **earlier-detection** upgrade — start with a real
   pre-market/real-time mover feed, then velocity + volume-before-price triggers. Backtest earliness.
3. When the 9:30–noon re-fit lands, swap the rating tables in `api/surges.js` and stage for redeploy.
4. Keep the scanner's scheduled scans + the 25%+ auto-log running; watch the forward dataset grow.
5. Action any specs in `pdufa_bio_build\INBOX\`.
