# pdufa.bio Rebuild — Builder Handoff Package

**Purpose:** everything a builder needs to retool **pdufa.bio** into a live, cloud-hosted,
cross-platform (Mac + anything) market dashboard with **two engines**:

1. **Momentum / Meme / UOA Radar** — whole-market micro/nano-cap momentum + unusual options activity.
2. **Biotech Catalyst Analyzer** — PDUFA catalysts scored by the ODIN engine.

This folder was assembled from a working session on the existing Momentum Scanner
(`9realms\Momentum Scanner\`) plus verified web/API research. It is a **spec + reference assets**,
not a finished app. Read the docs in order, then build against the existing site source at
`9realms\pdufa_site_src\`.

> **Informational and educational only — not investment advice.** Owned/operated by Odin Catalyst LLC.
> Every user-facing surface must carry this disclaimer.

---

## Read in this order

| # | File | What it covers |
|---|------|----------------|
| 1 | `BUILD_SPEC.md` | The master spec: goal, target architecture (Supabase single-source + Vercel Cron + static pages), update cadence, data-integrity model, secrets, acceptance criteria, and the **open decisions** still to be made. Start here. |
| 2 | `DATA_SOURCES.md` | Every external API: FMP, Unusual Whales, and social sentiment. Exact endpoints, auth, rate limits, response gotchas, and the **critical `avgVolume` bug + fix**. Includes the "does UW give social sentiment?" answer and a 2026 social-sentiment vendor comparison. |
| 3 | `MOMENTUM_ENGINE.md` | Full spec of the momentum/UOA scoring logic: universe, filters, 0–100 scoring, UOA score + bias, the 🚀 ROCKET rule, config knobs, and the output JSON schema. Port target. |
| 4 | `BIOTECH_ENGINE.md` | The biotech catalyst dashboard: the uploaded UI, the data shape it needs, and how to feed it live from ODIN instead of a WebSocket mock. |

## Reference assets (`/assets`)

| File | What it is |
|------|-----------|
| `momentum_meme_scanner_v1.py` | The working Python scanner — the **reference implementation** of the momentum/UOA algorithm. Port its logic; do not assume it is bug-free (see the `avgVolume` fix in `DATA_SOURCES.md`). |
| `momentum_scanner_README.md` | Original scanner README (run modes, config knobs). |
| `momentum_meme_dashboard.html` | Existing local dashboard (file-based, 60s auto-refresh). Design/logic reference for the momentum tab. |
| `sample_momentum_scan.json` | A **real populated** scan snapshot (2026-06-29). Canonical example of the momentum output payload the frontend consumes. |
| `biotech_catalyst_analyzer.html` | The uploaded "Anatomy of Alpha" biotech dashboard (WebSocket client). Design reference + data-shape source for the biotech tab. |

## Known state / gotchas (details in the docs)

- **The momentum scanner is currently returning 0 results** — not a quiet market. FMP's `/stable/quote`
  dropped the `avgVolume` field, so relative volume is always 0, which kills the "mover" filter and makes
  a 🚀 ROCKET mathematically impossible. **Fix = read `averageVolume` from `/stable/profile`.** This must
  ship in the rebuild. See `DATA_SOURCES.md` → "Critical fix."
- **Unusual Whales does not expose social sentiment via API** (only on their website). Social must come from
  other vendors. See `DATA_SOURCES.md` → "Social sentiment."
- **Data integrity = one writer.** The cloud job is the only thing that writes; every browser only reads.
  Never run the scanner on two machines at once.

---

## Added: Surge Radar — the "hop on early" momentum system

| # | File | What it covers |
|---|------|----------------|
| 5 | `SURGE_RADAR.md` | The live momentum scanner + the **surge-volume study** (does early-session volume predict a surge continuing up the same day?) + how it goes live on pdufa.bio (self-contained, any computer or phone) + **prospective logging** for an unbiased forward dataset. |

Reference assets added under `assets/`:

- `assets/surge-study/surge_study_phase1..4.py` — the 4-stage study: find ≥30% single-day jumps (small/micro US, 2 yrs) → 30-min intraday volume → continuation analysis + chart → forward framing from the 10:30 decision point. Plus `run_study_finish.py` (orchestrator).
- `assets/surge-study/` study **outputs** (`surge_events_2yr.csv`, `surge_intraday_features.csv`, `surge_study_report.md` + `surge_volume_vs_continuation.png`, `surge_forward_report.md`) — dropped in when the run completes.
- `assets/momentum_meme_scanner_v1.py` — **refreshed** with the avgVolume fix applied (the earlier copy predated the fix).

**Preliminary headline:** early-session volume vs same-day continuation is **inverse** — quiet gap-and-grind surges close near their highs (~96% make new highs after the first hour); 10×+ normal-volume blow-offs fade (only ~59%). "More volume = keeps ripping" is, if anything, backwards. Full numbers in `SURGE_RADAR.md` and the report files.

---

## Added: external research (audited)

- `RESEARCH_PROMPT.md` — the prompt fed to Gemini Deep Research + Perplexity Research to independently test our findings.
- `EXTERNAL_RESEARCH.md` — **audited** third-party findings. Every load-bearing citation was verified real before inclusion; practitioner blog claims are kept only as labeled hypotheses to backtest. Round 1 (Perplexity) done; Gemini round appends here.

Bottom line from Round 1: external evidence **corroborates** "big early moves exhaust" and adds two real risk features (LULD halts, pump-and-dump manipulation), but the specific **volume→continuation edge is not independently established** (one academic small-cap sample found volume uninformative) — treat it as a hypothesis to validate prospectively, leakage-free.

---

## Added: Morning-Runner strategy reality check

- `MORNING_STRATEGY_REALITY_CHECK.md` — tests the "catch it at 9:30, ride it, sell by noon" idea on 2 years of gap-up small-caps. Preliminary verdict: **the move is ~93% a pre-market event**, the intraday high usually lands by 10:00, and buying the open then exiting anywhere intraday lost money on average (only the unattainable "sell the exact top" wins). Pre-market entry adds a tiny (~+1% median) but largely unrealizable edge on thin books. Full 2-yr numbers + exit-timing chart land in `assets/surge-study/` when the run completes.
- Scripts: `assets/surge-study/surge_study_phase5_morning.py` (open-triggered morning path + exit-timing sim) and `surge_study_phase6_premarket.py` (pre-market edge test).

> **UPDATE (final, n=1,880):** the morning-runner runs are complete and `MORNING_STRATEGY_REALITY_CHECK.md` now carries final numbers. Verdict: the move is a pre-market event (median 100% of the run done before 9:30); buying the open loses on the typical (median) trade; confirmation entry doesn't rescue it (and the auto-report's rosy confirmation table is look-ahead bias); no subset clearly pays; the short-the-fade side has a positive median (~+2.5%, ~60% win covering fast) but a catastrophic squeeze tail + borrow/halt barriers. **Read medians, not means** — micro-cap tails make means (e.g. "+263% hold-to-close") meaningless. No demonstrated live long edge; treat the scanner as an alert, not a buy signal.
