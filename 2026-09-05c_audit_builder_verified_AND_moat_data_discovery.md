# Audit — 2026-09-05 (evening) · builder batch verified · what a year of aggregation is actually worth
**Live build `2026-09-05T20:45:23Z` · every approval below verified against a primary source · every dataset below opened and measured**
*Facts and historical statistics only — not investment advice.*

---

# PART I — THE BUILDER BATCH

## 1. ✅ The drug-page watcher ran once and found FOUR approvals we'd missed

I asked for a drug-page watcher because camizestrant slipped through. **On its first run it found camizestrant and three more.** I verified every one against a primary source, not the commit message:

| Brand | INN | Ticker | Approved | Site says | Verified against | ✓ |
|---|---|---|---|---|---|---|
| **Etcamah** | camizestrant | AZN | 2026-09-04 | Sep 4, 2026, accelerated, w/ CDK4/6i, Guardant360 CDx | 3× fda.gov | ✅ |
| **Rasonque** | daraxonrasib | RVMD | 2026-08-26 | Aug 26, 2026 | **openFDA NDA220910, ORIG-1 AP 20260826** | ✅ exact |
| **Lisraya** | brepocitinib | ROIV | 2026-08-27 | Aug 27, 2026 | Roivant release 2026-08-27 (dermatomyositis) | ✅ |
| **Zanvastro** | zilganersen | IONS | 2026-09-03 | Sep 3, 2026 | Ionis release + STAT 2026-09-03 (Alexander disease) | ✅ |

**Two of these are grounding queries we already rank on.** `daraxonrasib pdufa date` (and its misspelling, 64 Bing impressions) and `zilganersen pdufa date` (9 citations) — both had pages saying "no public date" while the drugs were approved. All four now carry the brand in `alternateName`; camizestrant's reads `["ETCAMAH","AZ-14066724","AZD-9833",…]`.

**The watcher's rejections are as good as its catches.** `_drug_watch_ack.json` shows it declined three supplement approvals with reasons:
> *"Efficacy supplement (SUPPL-41) on marketed tirzepatide; our page tracks the LLY Oct 2027 readout, not this."*

That's the Mounjaro MACE label expansion — a real FDA action that is *not* the catalyst our page tracks. Declining it with a written reason is exactly the discipline that keeps the archive honest.

## 2. ✅ The rest of the 09-05b batch

| Item | Status |
|---|---|
| `watch_drug_approvals.py` + `watch_readouts.py` + `tests/test_drug_pages_state_approvals.py` | ✅ **61 guards** (was 59) |
| `/fda-this-month` — *"What the FDA Decides in September 2026: PDUFA Dates in Plain Language"* | ✅ live; carries *"The FDA publishes no forward calendar of these dates."* |
| Calendar explainer sentences | ✅ partial — "does not publish" present; no 10-month / 6-month / 3-month review-clock sentences yet |
| Table `<caption>` elements | ❌ **0** on `/calendar` |
| **Calendar decision links for MNKD, REPL, JAZZ, ZYME** | ❌ **still absent** — counter moved 23 → 25 decided, but none of the four is linked |

The calendar item is now two audits old and sits on the page carrying 47% of impressions.

---

# PART II — WHAT THE YEAR OF AGGREGATION IS WORTH

## 3. Google Drive: a mirror, not a second store

I searched Drive for everything catalyst-, FDA-, PDUFA-, runner- and nest-related. The results are the local repo's own files (`pdufa_calendar.json`, `_fda_brand_names.json`, `nest_avgvol.json`, service logs) plus thousands of hash-named git objects synced up. **Drive holds nothing the hard drive doesn't.** Nothing to mine there.

## 4. The hard drive: 96 GB, of which ~5 GB is data and ~80 GB is one runaway log

```
Momentum Scanner/_DATA/_runall_test.err     79.3 GB   ← a log. Delete it.
Momentum Scanner/_DATA/  (real data)        ~5.5 GB   Jul–Sep 2026 intraday: tape, first_hour, ticks, runners, board_timeline
Odin Perfection/                             3.7 GB   ← the multi-year aggregation
```

**The Momentum Scanner data is two months old, not a year** — July 13 to September 5, 2026. It is intraday (tick, first-hour, runner boards) and belongs to a different product. The year-plus history is in **`Odin Perfection/`**, and it is considerably more valuable than I expected.

## 5. Five datasets nobody else has — measured against the 1,840-event run-up universe

| Dataset | What it is | Coverage | Match to PDUFA events |
|---|---|---|---|
| **`orats_strikes_cache/`** | 2,714 full options-chain snapshots — strike-level IV, volume, OI, bid/ask | **355 tickers · 2019-12 → 2026-05** | **1,273 events (71%)** have a chain within 30 days before |
| **`_god_tier_13f_cache.json`** | Quarterly 13F holdings of the 10 specialist biotech funds — units, Δunits, first-buy date | **1,279 tickers · 45 quarters · 2015-Q1 → 2026-Q1 · 18,375 records** | **878 events (49%)** |
| **`conf_study/si_panel_2017_2026.csv.gz`** | Bi-monthly short interest panel — qty, ADV, days-to-cover | **25,842 tickers · 194 settlement dates · 2017-12 → 2026-03** | full-market |
| **`fmp_mcap_cache_6yr.json`** | Daily market cap | 280 tickers · 6 yr | **1,549 events (86%)** |
| **`sec_form4_cache.json`** | Form 4 filing index (date, accession) | 242 tickers | **1,488 events (83%)** |
| `conf_study/sec_shares_outstanding.json` | Shares outstanding history | 317 tickers | dilution facts |
| `daily/readouts_*.csv` | 36 daily snapshots Jul 14 → Aug 27 | — | a readout changelog by construction |

**Two of these settle open red-team findings.** The April audit flagged *"Short Interest Lookahead: a single April 2026 snapshot applied retroactively to 1,704 events."* **There is a full 2017–2026 SI panel on the disk.** The BIFROST SI features can be rebuilt honestly. Likewise the *"HO > WF anomaly"* monitoring gets a real market-cap history instead of a snapshot.

## 6. Proof of concept — I computed the one that matters

**"What did the options market price, and what happened?"** is the single most-asked pre-catalyst question by a retail reader, and **no free source publishes it.** I computed it from the disk, not from a description:

**Method:** for each PDUFA event, take the chain snapshot closest to 14 days before; nearest expiry *after* the event; at-the-money straddle (call mid + put mid) ÷ stock price = the move the market priced. Compare to the close-to-close move across the decision.

**Result on 389 events, 2024-01 onward (49% of that window computable):**

| | |
|---|---|
| Median priced move | **±7.1%** |
| Median actual move | **2.1%** |
| Actual exceeded priced | **30 of 389 — 8%** |

Individually quotable rows:

| Ticker | PDUFA | Priced (T-14) | Actual | ATM IV |
|---|---|---:|---:|---:|
| OMER | 2025-12-24 | ±49.6% | **+79.5%** | 212% |
| OTLK | 2025-12-31 | ±91.8% | **−64.7%** | 402% |
| CORT | 2025-12-31 | ±32.0% | **−45.6%** | 141% |
| AGIO | 2025-12-23 | ±16.2% | +16.9% | 55% |
| VNDA | 2025-12-30 | ±21.2% | +22.5% | 88% |
| AMRX | 2025-12-22 | ±25.6% | +2.1% | 202% |

**Two caveats that must ship with it, or it shouldn't ship:**

1. **The straddle two weeks out prices two weeks of ordinary movement plus the event.** It is *"the move the options market priced from T-14 through the first expiry after the decision,"* not *"the event-implied move."* Say the first thing. Never the second.
2. **The 8% figure describes history and invites a strategy reading.** Publish it the way the run-up curve is published — as a measurement with its distribution, never with a verb. *"Sell volatility"* must not appear anywhere near it, and the disclaimer stack applies in full.

## 7. What each dataset becomes on the site — as facts, under the doctrine

Every one of these is **public data** (options prices, 13F filings, FINRA short interest, SEC Form 4, SEC shares outstanding). None of it is a prediction. Each becomes one dated sentence on an event page:

| Dataset | The sentence (example from the disk) |
|---|---|
| ORATS | *"Two weeks before the decision, at-the-money options priced a move of ±49.6% through December 26. The stock closed +79.5%."* (OMER) |
| 13F | *"As of the March 31, 2026 filings, 5 of the 10 largest biotech specialist funds held Revolution Medicines — Baker Bros. 9,555,357 shares (+100,000 in the quarter), Avoro 2,344,444 (+174,444), Perceptive 258,600 (new position)."* (RVMD, approved Aug 26) |
| SI panel | *"Short interest was X% of float at the last settlement before the decision, down/up N points over 60 days."* |
| Form 4 | *"Insiders filed N Form 4s in the 90 days before the decision — N purchases, N sales."* |
| Shares outstanding | *"Shares outstanding rose 7.2% between March 2025 and April 2026."* (AAPG, from the file) |
| Market cap | *"Market cap at the decision: $9.5B. Twelve months earlier: $X."* |

**Why this is the moat and not a feature:** novapharmanews copied our freshness stamp in weeks; dansfera copied our per-drug page. **None of them has 2,714 historical options chains, 45 quarters of specialist-fund 13Fs, or a 2017–2026 short-interest panel.** The sentence is copyable. The number inside it is not — and every one of these sentences is the kind an AI answer lifts verbatim.

**Where it goes:** a **"Positioning before the decision"** block on each `/fda-decision/` page (historical, ~1,270 events) and each `/pdufa/` event page (current, where a chain exists). Plus one research page each — *"What the options market priced vs what happened, 2020–2026"* and *"Specialist-fund holdings into FDA decisions, 2015–2026"* — in the same shape as `/runup-by-year`, with n and coverage stated.

---

# 8. ORDER

| # | Action | Class |
|---|---|---|
| **1** | **Calendar: link MNKD, REPL, JAZZ, ZYME** | two audits old, 47% of impressions |
| **2** | **Delete `_runall_test.err` (79 GB)** and put a size guard on the log dir | housekeeping, but 82% of the disk |
| **3** | **Build the implied-vs-actual dataset through the production pipeline** (my 389-event PoC is indicative only) → `/fda-decision/` block + research page, with both caveats in §6 | the biggest single moat asset on the disk |
| 4 | **13F "specialist funds held" block** on event and drug pages — Q1-2026 filings are current; Q2 filings land mid-August and should already be pullable | 878 events, 49% |
| 5 | **Rebuild BIFROST SI features from the 2017–2026 panel** | closes an April red-team finding |
| 6 | Form 4 counts + shares-outstanding delta per event | dilution and insider facts, 83% coverage |
| 7 | Table captions + review-clock sentences on `/calendar` | Bing answer box, carried |
| 8 | `/pdufa-date-changes` from `daily/readouts_*.csv` (36 snapshots already exist) | BPIQ's shape, already on disk |

---

# BOTTOM LINE

**The watcher I asked for found four approvals on its first run, and every one checks out against a primary source** — daraxonrasib to the exact openFDA date. Two of them were drugs we were already being cited on with "no public date" pages. It also correctly refused three label expansions with written reasons. That is the fail-safe working on both edges.

**Drive is a mirror; the disk is the asset.** Four-fifths of the 96 GB is one runaway log. The rest of `Odin Perfection/` is the year of aggregation, and it holds **five datasets no competitor has**: 2,714 options chains back to 2019, 45 quarters of specialist-fund 13Fs back to 2015, a full 2017–2026 short-interest panel, six years of market cap, and a Form 4 index — matching **49–86% of the 1,840 PDUFA events already on the site.**

**I computed the most valuable one to prove it's real.** Across 389 decisions since 2024, at-the-money options two weeks out priced a median ±7.1% move; the median actual move was 2.1%; the move exceeded what was priced in 8% of cases. **No free site publishes that, and it comes with two caveats that must travel with it** — it prices two weeks plus the event, and it describes history without a verb.

Freshness got cloned in weeks. **Nobody clones eleven years of 13Fs.** Render them as sentences.

---
*Approvals verified against openFDA / fda.gov / sponsor releases 2026-09-05. Datasets opened and measured on disk 2026-09-05. Implied-move PoC is indicative and must be recomputed through the production pipeline before anything publishes. Not investment advice.*
