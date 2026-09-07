# Red team — Conference Catalyst Torque, its audit, and how it goes onto pdufa.bio
**2026-09-06 19:30 Pacific · every number below re-read from the named file on disk or the live site**
*Facts and build mechanics only — not investment advice.*

---

# VERDICT

**The torque page is an internal trading tool and cannot go on pdufa.bio in any recognisable form.** It is built from entry windows, exit windows, options timing, position sizes and a composite score — five things the site's manifesto bans by name. Its headline number (+4.88%, 58.5% win) is contradicted by the largest study on the disk, which puts the same cell at **−7.86% at a 38.9% win rate**.

**The audit note that came with it is correct on every figure I checked, and it reaches the right conclusion.** What goes to the site is the *facts layer* — the 42-conference calendar (already live), verified presenters (12 rows, gated), and the honest run-up finding as sentences — not the tool. That layer is also, as it happens, the version that AI answer boxes will quote.

**And one correction I owe from yesterday:** two of the six "wrong" figures I pinned on Gemini came from **our own stale `/research` index cards**. Details in §4.

---

# 1. WHAT I VERIFIED

| Claim in the audit note | Source I opened | Result |
|---|---|---|
| Overall 30-day median −0.03%, 49.8% up, n=1,425 | `_conference_runup_stats.json` → `overall.runup_30d` | ✅ exact |
| Nano −7.86% / 38.9% · micro −1.95% / 46.5% · small +2.75% / 52.7% · mid +3.45% / 55.2% · large −0.19% / 48.9% | `by_cap.*.runup_30d` | ✅ exact, all five |
| Post-event: event day −0.56% (44.3% up) · D+5 −1.59% (39.4%) · D+10 −1.93% (39.9%) | `overall.event_day / post_5d / post_10d` | ✅ exact |
| Two July studies exist and pre-date the page | `CONFERENCE_RUNUP_STUDY_FINAL_2017_2026.md`, `CONFERENCE_RUNUP_STUDY_2022_2026.md` on disk, Aug 3 mtime; page built Aug 4 | ✅ |
| Watchlist seeds INBX / MBX / TENX are in the HTML | `grep` on `conference_torque.html` | ✅ INBX ×2, MBX ×2, TENX ×3 |
| **The disputed +4.88% / 58.5% is NOT on the public site** | `/research`, `/conferences` — zero hits for 4.88, 58.5, 3.02, 66.7 | ✅ **good news — the wrong number never shipped publicly** |
| The public site already says the honest thing | `/research` FAQ: *"Do the studies predict outcomes? No. They measure what happened"*; `/conferences`: *"Facts, not advice"* | ✅ |

**The audit note is reliable. Build from it.**

---

# 2. RED TEAM OF THE TORQUE PAGE — why it can't cross to the site

Read the page's own vocabulary against the manifesto (*never approval probabilities · never buy/sell/position-sizing calls · never composite bullish/bearish scores · never unsourced data*):

| Page text | Manifesto clause it breaks |
|---|---|
| *"entry / exit windows … Equity D-30 : micro-cap entry … Options T-14 : ATM calls … Exit D-1 : the runup IS the trade — never hold through"* | position calls; "entry/exit/window" are on the banned-vocabulary list from the run-up ruling |
| *"torque = (100 − iv_rank)·0.35 + cap bonus + liquidity + tier weight"* → 0–100 | **a composite score**, by construction |
| *"Sizing: Equity ALPHA 5% / BETA 4% / GAMMA 2%, nano cap 3%. Options max 2% (SNIPER 1.5x → 3%)"* | position sizing |
| *"Am I too late? Cheap: IV %ile <30 … Tilt >1.3 = already priced — skip"* | a buy/skip signal |
| *"Boost +18% / +14% / +12% / +10%"* per conference tier | a probability-style multiplier from Conference Overlay v1.0 — the same source whose run-up figure is disputed |
| *"Nano/micro: D-30 → D-1, median +4.88% (58.5% win)"* | **unsourced** — no file on disk reproduces it; three files contradict it |
| Seeds *"INBX/TENX confirmed via PR; MBX EASD-thematic watch"* | **false provenance** — INBX and MBX appear nowhere in the mined file; TENX is tagged AHA, not ESC |
| `window.cowork.callMcpTool("mcp__unusual-whales__…")` | a browser-side vendor call that dies outside Cowork and exposes the integration |

**Every one of those is fine for a private 9 Realms tool David uses himself.** None can appear on a site whose entire moat is *"we don't do this."* The two clones that copied us this month would love a screenshot of pdufa.bio saying "Exit D-1: the runup IS the trade."

## Two things the audit note under-weights

**(a) The "conference signal" (90.2% positive readouts vs 76.7% base) is a *different dataset* from the run-up study, and it carries a selection effect the note names but doesn't quantify.** The 90.2% comes from the Gungnir readout set (1,752 events) where "positive" is a readout outcome label; the run-up study is 1,425 *presentations* with price paths. Companies present at conferences when they have data worth presenting. A 90.2% positive rate among self-selected presenters is a fact about *who presents*, not about *what presenting does*. If it goes on the site it must say so in the same sentence: *"Companies choose to present; the higher positive rate partly reflects that choice."*

**(b) The note's Finding 3 slides into strategy.** *"a lottery with roughly a 1-in-5 win, a 1-in-10 severe loss … may still be a legitimate positive-expectancy bet with correct sizing"* — correct internally, and exactly the sentence that must never reach the site. The publishable form is the distribution alone: *"Among nano, micro and small-cap presenters (n=306), 19.6% rose 25% or more in the 30 days before and 9.5% fell 25% or more."* No "bet," no "expectancy," no "sizing."

---

# 3. WHAT THE AUDIT NOTE GOT RIGHT THAT I WANT ON RECORD

- **Anchor problem (Finding 5.1).** Both studies anchor on conference *start date*, not abstract-title release. The true catalyst may be weeks earlier, which means D-30 may measure the wrong interval. I raised the same dual-anchor point in the August study spec; it's still the single most important methodological fix and it could move the result in either direction. **Until it's done, no sentence about "the 30 days before" should imply causation.**
- **2020 is a bubble artefact** (+17.27% median, n=47, 5× any other year). Anything calibrated on 2020–21 inherits it. The +4.88% likely does.
- **Post-event decay is the best-evidenced fact in the whole stack** — −1.59% median by D+5, 39.4% up, n=1,425, agreed by two independent computations. That *is* publishable, as a measurement.
- **Presenter verification is 12 of 174 (6.9%).** At least one mined row matches last year's presentation (ESC 2025). Unverified rows must never render as confirmed presenters.

---

# 4. A CORRECTION I OWE — from the Gemini red-team

Yesterday I listed *"mean price path"* and *"1,754 events"* among Gemini's errors. **Both phrases are on our own `/research` index page, today:**

> *"PDUFA run-up by year (2020-present) — **Mean price path** into FDA decisions, T-120→T+5, by year: **1,754 events**"*

while `/runup-by-year` itself says *"Medians throughout"* and *"1,845."* The same index card says the conference study is *"256 presentations, 2022-2026"* while the FAQ three lines below says *"1,425 presentations."*

**Gemini quoted our stale cards accurately.** Its specific percentages (−5.1, −3.8, 14.3, 13.3) still appear nowhere on the site and remain unverified from this evidence — but the framing I called wrong was ours. **Two stale `/research` cards are a live defect** and go in the ORDER below.

---

# 5. IMPLEMENTATION — three layers, hard boundary between them

## Layer 1 — PUBLISH on pdufa.bio (facts only; this is also the AI-citation play)

Conference pages already earn impressions and convert at zero — `/conference/SABCS` 14 impressions, `/conference/AES` 14, `/conference/CTAD` 11, all 0 clicks at positions 6.7–7.9 (Sept 3 read). They have dates and no sentences. This is the sentence supply:

| Where | The sentence (from data on disk, n stated) |
|---|---|
| Every `/conference/{code}` page, one block | *"Across 1,425 presentations at major medical meetings from 2017 to 2026, the median presenting company's stock moved **−0.03%** in the 30 trading days before the meeting (49.8% rose) and **−1.59%** in the 5 days after (39.4% rose). Small caps: +2.75% before (n=298); nano caps: −7.86% (n=108). The middle half of all presenters ranged from −12% to +20%. This measures what happened; it is not a forecast for any company below."* |
| `/conferences` hub lede | *"The FDA does not run these meetings and there is no reliable pre-conference run-up: the median presenter is flat going in and down afterward. Every date below comes from the organiser; every presenter below links the SEC filing that named the meeting."* |
| Per-presenter row | only `HUMAN_VERIFIED` rows render as presenters; the filing link and the matched sentence sit behind a "source" link. Mined-unverified rows: **not rendered**, or rendered under a separate heading *"Filings that mention this meeting (unreviewed)"* with the sentence visible — never as "presenting" |
| `/research` conference card → a real study page `/research/conference-runups` | the by-cap table, the post-event table, the quartiles, n at every cell, the anchor caveat verbatim (*"anchored on the meeting start date, not on the abstract release; the true catalyst may be earlier"*), CC BY 4.0 CSV, `Dataset` schema |
| The "signal" — **only if** stated with the selection caveat | *"Of N readouts presented at a major meeting 2022–2026, N (90.2%) were positive, against N of N (76.7%) not presented. Companies choose what to present; part of that gap is the choice."* Counts, n, caveat in the same sentence. |

**Why this is the citation play:** Google's AI Overview and Bing's answer box lift definitional sentences with numbers. *"There is no reliable pre-conference run-up: median −0.03% over 1,425 presentations"* is exactly that shape, it is original, and no competitor will say it because it undercuts the thing they sell.

## Layer 2 — INTERNAL ONLY (9 Realms / Cowork; never on the public domain)

The torque page stays where it is, **after** the fixes the builder note lists: slate driven from `conferences.json` (42, not 14); seeds replaced with `HUMAN_VERIFIED` rows or emptied; Playbook numbers replaced with the 1,425-event figures or removed; cap-tier bonus re-derived (it currently rewards the two worst cells); Unusual Whales call kept — it's fine inside Cowork.

**Hard boundary:** nothing from `conference_torque.html` — no window dates, no torque score, no tier boost, no IV-cheapness rule, no sizing — is imported by any `pdufa_site_src/` build step. **Guard:** `test_no_strategy_vocabulary.py` — fail the build if any public page contains "entry window", "exit window", "torque", "position size", "ALPHA/BETA/GAMMA" as tiers, "the runup is the trade", "never hold through", "am I too late". Prove 0 → planted 1 → healed 0.

## Layer 3 — NEVER, anywhere public

The +4.88% / 58.5% figure (unsourced, contradicted) · the 0–100 torque score · tier "boosts" · the IV-cheapness "skip" rule · sizing · any sentence with a verb telling a reader what to do.

---

# 6. ORDER FOR THE BUILDER

| # | Item | Acceptance (I run live) |
|---|---|---|
| **1** | **Fix the two stale `/research` cards**: "Mean price path … 1,754" → "Median price path … 1,845"; "256 presentations" → "1,425 presentations". Then a guard: every n on `/research` equals the n on the page it links | `/research` contains "Median", "1,845", "1,425"; contains neither "Mean price path" nor "1,754" nor "256 presentations" |
| **2** | **Conference run-up block** on every `/conference/*` page and the `/conferences` lede, wording as in Layer 1, numbers read from `_conference_runup_stats.json` at build time (never hand-typed) | `/conference/ESMO` contains "1,425", "−0.03%", "−1.59%", "not a forecast"; no strategy vocabulary |
| **3** | **`/research/conference-runups` study page** with by-cap and post-event tables, quartiles, n per cell, the anchor caveat verbatim, CSV + `Dataset` schema | 200; contains the anchor sentence; CSV link resolves; `@type: Dataset` present |
| **4** | **Presenter gating**: only `HUMAN_VERIFIED` rows render as presenters; mined rows go under "Filings that mention this meeting (unreviewed)" with the matched sentence, or not at all. Retire the ESC-2025 false positive | `/conference/ESC` shows ≤2 presenters (the verified count) and no NewAmsterdam row as a presenter |
| **5** | **Guard `test_no_strategy_vocabulary.py`** across `pdufa_site_src/` | proven 0 → 1 → 0; list of banned tokens in the file header |
| 6 | Torque page internal fixes (slate from `conferences.json`, seeds, playbook numbers) — **not a site item**; do it when the 9 Realms tooling is next touched | not audited on the site |
| 7 | **Dual-anchor rebuild** (abstract-release date) — research item, gates any causal wording ever | a second `_conference_runup_stats_abstract_anchor.json` with the same schema; the study page shows both anchors side by side |
| 8 | `conferences.json` hygiene: bump `_verified_on`, re-sort, normalise AACR-PANC city to "San Diego, CA" | `tests/test_no_fabricated_conferences.py` extended to sort order + stamp bump |

---

# BOTTOM LINE

**The torque page is a good private tool with a wrong headline number and false seed provenance; the audit note that found both is accurate to the decimal.** Nothing in the page's operating layer — windows, torque, boosts, sizing — can appear on pdufa.bio, because the site's entire position is that it doesn't do those things, and the two clones that copied us this month would frame the screenshot.

**What does cross is the finding underneath it:** across 1,425 presentations the median presenter is flat before the meeting and down after. That is original, sourced, publishable as counts with n, and shaped exactly like the sentences AI answer boxes lift. Put it on every conference page — the ones earning impressions at 0% CTR today — and on a proper study page with the anchor caveat and a CSV.

**And I owe a correction:** the "mean price path" and "1,754" I attributed to Gemini yesterday are on our own `/research` index right now, stale by two builds. Gemini quoted us accurately. Fixing those two cards is item 1.

---
*Numbers verified against `_conference_runup_stats.json` and the live site 2026-09-06. Not investment advice.*
