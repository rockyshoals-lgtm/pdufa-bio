# SURGE RADAR — momentum scanner + surge-volume study + live pdufa.bio integration

_Informational and educational only — not investment advice. Odin Catalyst LLC._

This is the "hop on early and ride the momentum" system. Three parts:

1. **Live scanner** — `assets/momentum_meme_scanner_v1.py` (avgVolume-fixed). Whole-market micro/nano movers + UOA, scored, with 🚀 ROCKET flags. See `MOMENTUM_ENGINE.md`.
2. **Surge-volume study** — offline research (`assets/surge-study/`) that answers: *does early-session volume predict a surge continuing up the same day?* It tunes the live "keep-riding vs fade" signal.
3. **Prospective logging** — the live scanner records first-hour movers + outcomes daily, building an **unbiased forward dataset** over time (the honest version of the study).

---

## The study (assets/surge-study/)

Four stages, all on our own APIs (no yfinance, no bulk-endpoint abuse):

| Stage | Script | What it does |
|---|---|---|
| 1 | `surge_study_phase1.py` | Scan ~3,257 small/micro US names (FMP company-screener), 2 yrs of daily bars → every **≥30% single-day** jump. ~3,122 events. |
| 2 | `surge_study_phase2.py` | For each surge day, pull 30-min intraday bars; compute early-session volume vs the stock's normal 20-day ADV, plus intraday continuation labels. |
| 3 | `surge_study_phase3.py` | Analysis + chart + report: continuation rate by early-volume bin. |
| 4 | `surge_study_phase4.py` | **Forward** framing: from the ~10:30 decision point, did the observed first-hour move+volume continue to the close? |

**Outputs** (dropped into `assets/surge-study/` when the run completes): `surge_events_2yr.csv`,
`surge_intraday_features.csv`, `surge_study_report.md` + `surge_volume_vs_continuation.png`,
`surge_forward_features.csv` + `surge_forward_report.md`.

### Headline finding (preliminary — final numbers in the report files)
The relationship between **first-hour volume (÷ normal ADV)** and **same-day continuation** is **inverse and monotonic** — the opposite of "more volume = more upside":

| 1st-hour volume ÷ ADV | closed near day-high (0–1) | made new high after 1st hr |
|---|---|---|
| <0.5× | 0.77 | 96% |
| 1–2× | 0.77 | 88% |
| 2–5× | 0.73 | 81% |
| 5–10× | 0.66 | 73% |
| 10×+ | 0.53 | 59% |

Read: **quiet gap-and-grind** surges (low relative volume) close near their highs; **climactic blow-offs**
(10×+ normal volume) front-load and fade. For "ride it up," moderate/low relative volume with steady
higher-highs is the healthier tape; a massive first-hour volume spike is more often exhaustion.

### Caveats (must survive into any UI copy)
- **Selection/outcome bias:** events are chosen because they *closed* ≥30% up, so Phases 1–3 describe the
  intraday *shape* of big up-days, not a clean at-the-open predictor. Phase 4 measures forward continuation
  from 10:30 but still on this winner-heavy set.
- **The clean version is prospective:** the live scanner must log first-hour movers + their outcomes going
  forward — no look-ahead, no survivorship. That accumulating dataset is the real edge.
- **Survivorship:** universe is currently-active names; delisted pump-and-dumps are missing → real
  continuation is likely lower.
- **No guarantee.** Base rates, not promises. Micro-cap spreads can erase any edge; check tradeable liquidity.

---

## Making it live on pdufa.bio — self-contained, any device

Same single-writer architecture as `BUILD_SPEC.md` (Supabase = one source of truth; Vercel Cron writes;
browsers only read). Nothing to install — open a URL on another computer or your phone.

- **`/radar` page** on pdufa.bio (plain HTML, matches the existing site) that polls Supabase every ~30–60s and shows: live ROCKETs, top momentum, top UOA — plus a **continuation cue** per name derived from the study (e.g. "grind" vs "blow-off risk" based on first-hour volume ÷ ADV).
- **Scan jobs** (Vercel Cron / serverless): fast-lane ~60s, full enrichment ~3 min, market-hours only. Write snapshots to the `radar_snapshots` table (`engine='momentum'`).
- **Prospective log table** (`surge_watch`): each market morning, log every name up ≥ (threshold)% with its first-hour volume ÷ ADV; end-of-day, write the outcome (did it continue to the close?). Over weeks this becomes the unbiased forward dataset — and it can retrain the continuation cue.
- **Secrets** stay server-side (Vercel/Supabase env). Browser gets only the Supabase anon key (read-only via RLS). Never ship FMP/UW keys to the client.
- **Disclaimer** on every view.

### Auto-start at market open
The live scanner already supports `--market-hours` loop mode. In the cloud build, that's just the Vercel
Cron schedule (no PC needed). If you also want the local `momentum_meme_scanner_v1.py` to auto-run on the
Windows box at 9:30 ET, that's a Windows Task Scheduler entry — see the scanner's README. (Cloud is the
cross-device path; the local run is optional/redundant.)

## Build order for the builder
1. Ship the momentum `/radar` (BUILD_SPEC architecture) with the avgVolume-fixed scanner logic.
2. Add the `surge_watch` prospective log + the continuation cue (start with the study's preliminary rule: treat 10×+ first-hour volume as blow-off/fade risk, moderate volume + higher-highs as healthy).
3. Let the forward dataset accumulate; retrain the cue from real, unbiased outcomes.

---

## FINAL results (pipeline complete — supersedes the preliminary table above)

Sample: **2,980** ≥30% single-day surges, with intraday 30-min bars + point-in-time 20-day ADV.

**Same-day continuation by first-hour volume ÷ ADV (Phase 3):**

| 1st-hr vol ÷ ADV | n | % held 1h gain | % new high after 1h | close-in-range |
|---|---|---|---|---|
| <0.5× | 1072 | 95.8 | 95.1 | 0.77 |
| 0.5–1× | 325 | 93.8 | 93.5 | 0.76 |
| 1–2× | 369 | 87.5 | 87.8 | 0.74 |
| 2–5× | 360 | 81.7 | 80.6 | 0.72 |
| 5–10× | 210 | 75.2 | 75.2 | 0.66 |
| 10×+ | 644 | 62.7 | 56.4 | 0.50 |

Correlation(first-hr vol ÷ ADV, close-in-range) = **−0.115** — more early volume → *less* continuation.

**Forward from the ~10:30 decision point (Phase 4):**
- By first-hour volume: **<1× ADV → 95% continued (+29% avg forward)**; 10×+ → 62% (+12%).
- By first-hour move: <10% → 86%, 10–25% → 89%, 25–50% → 68%, **50%+ → 39%** (big early moves exhaust).

**Takeaway for the live "keep-riding" cue:** the healthy ride-it-up tape is a **moderate** early move on
**moderate/low relative volume** making steady higher-highs. A first hour already +50% and/or 10×+ normal
volume is more often a blow-off that fades. Caveats stand (selection on ≥30% close = winner-heavy;
survivorship) — treat as directional and let prospective logging build the clean forward dataset.
