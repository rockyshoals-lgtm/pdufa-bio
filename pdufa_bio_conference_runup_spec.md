# Conference Run-up on pdufa.bio — What to Ship, What to Never Ship
**Date:** 2026-07-10 · Source reviewed: `Conference_Catalyst_Calendar_H2_2026_v2.xlsx`, `conference_trades_apr_may_2026.json`, `conference_scoring_results_apr2026.json`
**Verdict: YES to conference run-up *history*. NO to the conference *overlay/scoring*.**

---

## Why this matters
Right now `/conferences` is just a date list — same as BioBucks, TheraRadar, BiopharmaWatch. **Adding run-up history makes it the only conference calendar in existence that shows how presenters actually traded into the event.** That's an instant best-in-class differentiator, built from data you already own, and it's the exact same data species you already publish for PDUFAs.

But the existing conference dataset is a **trading playbook**, not a neutral study. Most of it cannot go on the public site.

---

## 🟢 SHIP — on-brand, extends the moat

This is the direct analogue of the existing PDUFA run-up study (historical price action, no forecast):

- **Conference run-up history by cap tier** — median % move from D-30 (and D-5) into D-1, with **n**, date range, and distribution (p25/median/p75). *Present as history, never as a recommendation.*
- **Sparkline on every conference presenter row** — identical treatment to PDUFA/readout rows. Visual consistency, instant "tape" feel.
- **A `/research/conference-runup` study page** mirroring `/runup-by-year`: how presenting stocks have historically traded into ASCO/ASH/ESMO/AACR etc., split by cap tier and presentation type.
- **Per-conference detail pages** (`/conference/{slug}`, e.g. `/conference/esmo-2026`) with date, location, TA, presenter list, and each presenter's run-up sparkline. ← *also a big SEO win; currently only a flat `/conferences` list exists.*
- **Factual presentation metadata:** oral / late-breaking / poster / number of presentations. Facts, not weights.
- **API:** expose `runup` + `cohort_move_*` on `type=Conference` events as **Pro depth fields** (per the API spec).

### Two methodology upgrades that would make it genuinely best-in-class
1. **Dual anchor.** Conference run-ups have a wrinkle PDUFAs don't: the **abstract/title drop** (ASH ~early Nov, ESMO LBA titles ~mid-Oct — your own Legend sheet notes this) is *itself* a price event, weeks before the conference. Measure run-up from **both** the abstract-drop date and the conference start date. No competitor does this, and it's the honest way to model it.
2. **Disclose n and vintage on every number.** The sheet's headline figures (median +4.88% nano/micro D-30→D-1; +3.02% small D-5→D-1) carry **no sample size** in the source. Accuracy is the brand — do not publish a single number without n, date range, and method.

---

## 🔴 DO NOT SHIP — keep internal to 9realms / ODIN / Gungnir

Everything below is in the current conference files and would **directly contradict the site's core promise** (`/why-no-approval-probability`, and the footer's *"no trade recommendations and no individual-drug approval probabilities"*):

| Item in the data | Why it can't go public |
|---|---|
| **"Presenters 90.2% positive vs 76.7% baseline"** | This is a **probability of a positive outcome**. It is precisely the approval-odds claim the brand is built on refusing. Also **selection-biased** — your own note says the mechanism is *"abstract acceptance = implicit peer review + company self-selection."* Companies choose to present good data. It's not a clean causal signal, and publishing it as a probability is both off-brand and statistically shaky. |
| **Boost multipliers** (ELITE +18%, AACR +20%, oral +8%…) | That's a scoring engine. "No scoring" is the positioning. |
| **Win rates** (58.5%, 66.7%) | Trade framing. Report *median historical move*, never "win rate." |
| **Options torque / IV expansion / "buy ATM calls spanning the event"** | **Explicit trade recommendations.** Serious compliance exposure for a site that says "not investment advice." |
| **Position sizing** (ALPHA 5% / BETA 4% / nano capped 3%; "max 2% per options position") | Portfolio advice. Absolutely not. |
| **"Cardinal rule: THE RUNUP IS THE TRADE"** | Recommendation language. |
| **ALPHA/BETA/GAMMA/DELTA tiers; `score`, `prob`, `tier` fields** in `conference_trades_apr_may_2026.json` | Scoring output. Strip entirely before any public use. |

**The bright line:** *publish what the stock **did**; never publish what a trader **should do** or how likely an outcome **is**.* Median historical run-up = fact. Win rate, boost, score, probability, entry/exit, sizing = edge claim.

---

## Data work required
- **Rebuild the conference run-up numbers as a clean study**, not a playbook: event list → presenter tickers → price series → run-up windows (dual anchor) → median/quartiles **with n**, by cap tier and presentation type.
- **Strip all scoring fields** (`score`, `tier`, `prob`) from anything that feeds the public site or API.
- **Refresh the presenter list** — `conference_trades_apr_may_2026.json` is Apr/May 2026 (stale and scored). `Conference_Catalyst_Calendar_H2_2026_v2.xlsx` (Jul 4) is current and is the better base — but note its "Confidence" caveat: presenter lists only firm up ~2–3 weeks pre-conference. Ship a **confidence/estimated flag** on presenter rows, same as the readouts staleness flags.
- **Methodology page** for conference run-up, mirroring the existing `/methodology` — state the anchors, the windows, the n, and the self-selection caveat explicitly. *Publishing the caveat is itself a trust differentiator.*

---

## Net
Ship the **history**, kill the **playbook**. You get: the only conference calendar with run-up data, a new research page + per-conference SEO pages, a new Pro depth field for the API — and you protect the one thing that actually differentiates pdufa.bio from BiopharmaWatch's black-box PoA scores: **it doesn't tell you the odds, it tells you the facts.**

---
*Informational and educational only — not investment advice.*
