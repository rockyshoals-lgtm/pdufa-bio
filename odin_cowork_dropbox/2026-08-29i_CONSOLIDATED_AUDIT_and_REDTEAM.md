# Consolidated audit + red team of the incoming agent drops
**2026-08-29 · site verified on a 6-min-old build · three agent documents red-teamed against source data**
*Facts and historical statistics only — not investment advice.*

---

# PART 1 — RED TEAM: the three incoming documents

I checked every claim I could verify against the actual files. **All three are good work.** Two are accurate on every checkable point. Below is what they got right, and the four things nobody flagged.

## 1.1 `2026-08-29h` — Stock Reaction Tracker audit → **VERIFIED ACCURATE**

Every checkable claim holds:

| Their claim | My check | Verdict |
|---|---|---|
| 14,296 bytes, ~101 days stale | 14,296 b, mtime **2026-05-21** | ✅ |
| Cards say 10 events, table has 9 | `tbody[0]` = **9 rows** | ✅ |
| "6 of 10" and "3 of 9" contradict the table | both strings present verbatim | ✅ |
| Brier baseline "0.0895" is really ODIN v14's holdout | `0.0895` present; it **is** v14's HO Brier | ✅ |
| Retraction line as quoted | verbatim match | ✅ |

**The finding they under-weighted is §5.3, and it's the most important thing in any of these documents.**

The page states:
> *"GUNGNIR v46 honest **0.6150** (claimed 0.8135 **retracted**). BIFROST v5.5 honest **0.7447** (claimed 0.9487 **retracted**)."*

The standing 9 Realms spec still carries **GUNGNIR v46 at AUC 0.8135** and **BIFROST v5.5 at LR AUC 0.9487** as champion figures. And the retracted BIFROST number (**0.7447**) is *well below* the **0.85–0.90** the standing Red Team note estimated as true generalisation.

**Two different sets of numbers for the same models are in active circulation, and the correction is larger than the audit that predicted it.** This needs an owner ruling before any model figure is quoted anywhere.

**Scope note for the builder — do not panic:** this artefact is **unpublished**, not in the artifact gallery, and has never reached pdufa.bio. **No public page carries these numbers.** The site publishes no model probabilities by design. This is an internal-spec conflict, not a site defect.

## 1.2 `2026-08-29g` — Readout + Conference handoff → **HIGH QUALITY, four gaps**

The precision-honesty framing is exactly our house discipline and the census reconciles **exactly**:

```
533 rows · confidence {SOFT 439, FIRM 6, GOLD 88} · precision {HALF 98, DAY 123, MONTH 222, QUARTER 90}
```

**The number the builder must internalise: only 94 of 533 rows (18%) are GOLD or FIRM — i.e. publishable as a hard date.** 439 are SOFT buckets. Their rendering rules are right and non-negotiable.

**Four things they did not flag:**

**🔴 (a) CAPR is in the gold file at a date that has already passed.**
```
date 2026-08-22 · precision DAY · confidence FIRM · source EDGAR/company-stated · event "readout guidance"
```
CAPR's PDUFA was **extended to 2026-11-22 on 2026-08-24**. The gold file still carries the old date at **FIRM/DAY** — the second-highest confidence tier — and **CAPR's actual 2026-11-22 PDUFA is absent entirely.** They flagged "BPC export is stale (2026-08-22)" in the abstract but never traced it to a consequence. This is the most-watched extended PDUFA on the board.

**🟠 (b) MIRM is paired with an Incyte compound.**
Both `INCY` and `MIRM` carry the identical drug string *"Zilurgisertib (INCB000928) - (PROGRESS)"* on 2026-09-26. `INCB000928` is an Incyte compound code; Mirum is a liver-disease company. This may be a real partnership I'm unaware of — **I am not asserting it's wrong** — but an INCB-coded asset on MIRM needs checking before it publishes.

**🟠 (c) A PDUFA whose provenance is a conference.**
`INO / INO-3107 / 2026-10-30 / event=PDUFA / source=BPC/conference:American Society of Clinical Oncology`. Either the event type or the source is wrong. A regulatory date sourced to a conference shouldn't reach GOLD.

**🟡 (d) The stale-BPC exposure is quantified nowhere.**
Source census: `EDGAR/guidance 188 · CTgov/MED 114 · CTgov/LOW 105 · BPC/conference 49 · BPC/PDUFA-bucketed 32 · BPC/PDUFA 30 · EDGAR/conference 9 · EDGAR/company-stated 6`.
**111 rows — 21% of the file — come from the 2026-08-22 BPC export.** That's the blast radius of the staleness they mention in passing.

*Credit where due: `BPC/PDUFA-bucketed` (32 rows) shows they downgraded precision on vendor rows rather than inheriting a false day. That is the right instinct.*

## 1.3 `BUILDER_NOTE_conference_torque` → **ACCURATE AND USEFULLY SELF-CRITICAL**

Row counts verified exactly: mined **174**, verified **10**, history **754**.

Their best catch is their own: the page's three seeded watchlist tickers (INBX, MBX, TENX) are **not** what the source comment claims — INBX and MBX appear zero times in the mined data, and TENX is mined for **AHA**, not ESC. That's the kind of self-audit that earns trust.

**One correction and one credit:**

**The VERIFIED file grew from the 9 rows I created on 08-12 to 10** — `CYTK/ESC` was appended. My first instinct was that this breaks the file's guarantee. **It doesn't:** the row carries `reviewer = cowork 2026-08-22` and a note reading *"Lead from BPC cross-check, CONFIRMED against Cytokinetics…"*. **The discipline held — a different agent checked it and signed it.** Keep the per-row reviewer field; it's what makes appending safe.

**Their NewAmsterdam observation confirms my 08-12 finding still stands.** They note a mined row citing **ESC 2025**. That's the historical false-positive class I found when the corpus was 102 rows; at 174 rows it persists. The miner's edition gate protects *new* rows — **the legacy corpus was never re-swept.**

## 1.4 The pattern across all three

**Three artefacts, one systemic failure: hand-built HTML that cannot refresh itself.**

| Artefact | Failure |
|---|---|
| `stock_reaction_tracker.html` | every number hand-typed; 101 days stale; forward table overtaken by events |
| `conference_torque.html` | 14 conferences hardcoded while `conferences.json` holds **41 verified**; the two drift and nothing reconciles them |
| BPC export | static vendor file, 7 days stale, 21% of the gold set |

**Both HTML pages also hardcode a Cowork connector UUID** (`window.cowork.callMcpTool("mcp__50fc209a-…__quote")`). Same fragility, twice. Any port to pdufa.bio must replace those with server-side endpoints — **never ship browser-side vendor calls on the public site.**

---

# PART 2 — MY OWN AUDIT (carried forward from `2026-08-29f`)

## Shipped and verified
- **NAV FREEZE is now guard 51** — a directive that can't decay. Correct call.
- Builder self-caught: homepage showed an approved drug as due today; the decided-sweep had never run.
- Run-up study at **1,838 events**; decision timing **n=27**; **51 guards**.

## 🟠 The cohort block is live but leaking most of its value
- **Coverage inconsistent:** `/pdufa/REGN-garetosmab` renders it; `/pdufa/CAPR-deramiocel` renders nothing **despite holding the data** (`cohort_n 274 · median 0% · p25 −3.99% · p75 +2.75%`). Rendering gap, not data gap.
- **It collapses the distribution to "±1% median".** REGN is symmetric (−0.93/+1.03); **CAPR is downside-skewed (−3.99/+2.75)**. For a trader the skew *is* the signal, and it's being rounded away.
- **It isn't a liftable sentence.** Make it one, with p25/p75 and the n.

## 🥇 The biggest non-link lever: entity schema
**544 drug pages, zero `Drug` markup.** Deployed: FAQPage, Question, Answer, BreadcrumbList, ItemList, Event, Organization, WebSite, SearchAction. **Absent: `Drug`, `MedicalCondition`, `MedicalStudy`, `Dataset`, `VideoObject`, `SpeakableSpecification`.**

`FAQPage` says *"this page contains a Q&A."* `Drug` says *"this page **is** camizestrant."* That's the difference between being quoted and being the source. **`alternateName` is the systematic fix for the daraonrasib problem** — declare INN, code name, brand, ticker and misspellings once per drug instead of hand-writing paragraphs.

## 🥈 Video — free SERP real estate
Bing's SERP for "pdufa calendar" carries a video carousel where **RTTNews holds a slot with a one-view video posted twelve hours earlier.** We're absent. The script is our own calendar.

## Not started
`/pdufa-date-changes` (404) · cash-cushion view (404).

---

# PART 3 — CONSOLIDATED ACTION LIST

## 🔴 Accuracy — before anything ships
| # | Action | Source |
|---|---|---|
| 1 | **Do not ingest the gold file until CAPR is corrected.** 2026-08-22 must become the 2026-11-22 PDUFA. | §1.2(a) |
| 2 | Resolve **MIRM/zilurgisertib** and **INO PDUFA-sourced-to-a-conference** before either publishes | §1.2(b,c) |
| 3 | Re-sweep the **174-row mined corpus** through the edition gate — legacy rows predate it | §1.3 |
| 4 | **Owner ruling on GUNGNIR v46 and BIFROST v5.5.** Two sets of numbers are in circulation. *No site impact — internal spec only.* | §1.1 |

## 🟠 The data drop — rules of engagement
| # | Action |
|---|---|
| 5 | Ingest `readout_gold_dates.csv` **only at GOLD/FIRM** — that's **94 of 533 rows**. SOFT renders as its bucket, never as a day. |
| 6 | Honour `precision` absolutely: MONTH → "September 2026", QUARTER → "Q4 2026", HALF → "2H 2026". **Never synthesise a day.** |
| 7 | Surface the **8 conflict rows**; never silently resolve |
| 8 | Union our EDGAR presenters with BPC, dedup on ticker+conference — ours has 5 BPC lacks (EIKN, ZLAB, MOLN, CRVO, CADL) |
| 9 | Spot-check the reported stale SMMT 2026-07 readout item; SMMT's PDUFA is **2026-11-14** |

## 🟢 Growth — highest return first
| # | Action | Why |
|---|---|---|
| 10 | Fix the cohort block: every page, **p25/p75 explicit**, written as a sentence | data already computed, skew being lost |
| 11 | **`Drug` schema + `alternateName`** across 544 pages | biggest non-link citation lever |
| 12 | `Dataset` schema on patent-cliff, decision-timing, run-up | they *are* datasets and say nothing |
| 13 | PAA capture — Google asks *"Does FDA approve before the PDUFA date?"*; we hold the only sourced answer (n=27) | cheapest page-one entry |
| 14 | **A dedicated ESMO 2026 page** — 2026-10-23 is a **14+ name cluster**, the densest catalyst day in 90 days | their idea, and it's a good one |
| 15 | `/pdufa-date-changes` from 90 git snapshots + `date_history[]` forward | uncopyable; feeds alerts |
| 16 | "When does the run-up peak?" from the 1,838-event series | best unpublished asset you own |
| 17 | Monthly PDUFA video + `VideoObject` | free SERP surface |

## ⛔ Standing
**NAV FROZEN until 2027-01-01** — enforced by guard 51. Every edit resets the sitelink clock.

---

# BOTTOM LINE

**All three incoming documents are good, and two are accurate on every point I could check.** The tracker audit correctly found a 10-vs-9 contradiction and a mislabelled Brier baseline; the torque note caught its own seeded-watchlist defect, which is the hardest kind of finding to make.

**The four things nobody flagged are all in the readout handoff, and one of them blocks ingestion:** CAPR sits in the gold file at **2026-08-22**, a date that passed a week ago, marked **FIRM/DAY**, while its real 2026-11-22 PDUFA is missing entirely. The stale BPC export they mention in passing accounts for **21% of the file**.

**The systemic pattern is worth naming:** three artefacts, all hand-built HTML that can't refresh, two of them hardcoding the same fragile connector UUID. The estate keeps producing point-in-time snapshots that drift. Anything ported to pdufa.bio has to be driven from the living dataset — which is exactly what `conferences.json` and the daily rebuild already are.

**And the model-number conflict needs your ruling.** GUNGNIR v46 and BIFROST v5.5 each have two published figures, and the retracted ones are materially worse than the standing Red Team estimate. No site page carries them, so nothing is publicly wrong today — but it should be settled before any number leaves the estate.

---
*All claims above re-verified against the source files and the live site, 2026-08-29. Not investment advice.*
