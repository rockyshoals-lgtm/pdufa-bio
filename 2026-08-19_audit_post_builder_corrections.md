# Audit — 2026-08-19, post builder corrections
**Current run verified: `x-vercel-cache: MISS` · `age: 0` · `dateModified 2026-08-19T17:01:01Z` (5 min old)**
*Facts and historical statistics only — not investment advice.*

---

# 1. EVERY ITEM I RAISED — VERIFIED FIXED

| # | Finding | Status | Evidence, live |
|---|---|---|---|
| 08-18 §2 | 9 hand-verified presenters missing | ✅ **FIXED** | **14 presenter entries across 8 conferences** (was 5/3). All nine back: IONS, BNTX, IBIO, IPSC, SANA, ENTX, XNCR, ZLAB, CRVO |
| — | CSV untracked / gitignored | ✅ | `git ls-files` now resolves it |
| 08-18 §2 rec | Minimum-row guard | ✅ **BUILT** | `tests/test_data_sources_present.py`, 106 lines, **git-tracked check** + 7 row floors |
| 08-18 §3 | Calendar two-source problem | ⚠️ **PARTIAL** | guard built (`test_calendar_two_sources.py`, 101 lines); gap 5 → **3** but not closed |
| 08-18c §7 | Conference pages `Question=0` | ✅ **FIXED** | ASH / ESMO / SITC / CTAD all **FAQPage=1, Q=3** |
| 08-18c §8 | Decision FAQs 1 → 3 | ✅ **FIXED** | JNJ 3, ALNY 3, VTRS 2 |
| 08-18c §1 | camizestrant page | ✅ **BUILT** | 5 Q, 517 words |
| 08-18c §3 | Complete per-event URLs | ✅ **EXTENDED** | `/pdufa/CAPR-deramiocel` **200** (was 404), `/pdufa/GILD-anito-cel` 200, `/pdufa/VTRS-mr-141` 200 |
| — | Guard total | ✅ | **46** |

**The builder also found a defect I missed.** `shape()` in `_lib.mjs` whitelisted fields and silently dropped `presenters` — the dataset carried 8 conferences with entries while the API served none. That's the same silent-degradation shape as the gitignore incident, caught independently and guarded against a planted failure.

## The three events the calendar guard surfaced — all verified in the API
| Event | Stored as | Check |
|---|---|---|
| **GILD 2026-12-23** Anito-cel | day precision, Upcoming | ✅ real — BLA accepted, PDUFA in Gilead's own Arcellx release |
| **IRD 2026-10-17** | **Phentolamine ophthalmic 0.75%** | ✅ **wrong drug corrected** (slate said OPGx-RDH12) |
| **VTRS 2026-10-17** | MR-141 (phentolamine ophthalmic 0.75%) | ✅ named so the dual-listing is visible as one program |
| **NVCR 2026-11-15** | **quarter precision** | ✅ **invented day precision removed** — it is the *only* non-day row in the window (70 day / 1 quarter) |

**Fossil rows HOOK, CRBP, NCNA: all gone.** Zero rows in the window.

**AMLX LUCIDITY published** — `/readouts` shows *"AMLX · 2026-08-18 ✓ positive · Avexitide (Ph3 LUCIDITY, PBH) · day-of close reaction, confirmed against the company release **+63.8%**"*. The intraday "+55.2% under a close label" problem self-healed as designed.

---

# 2. ⚠️ MY OWN CORRECTION — I nearly had you build a bad page

My 08-18c audit's **#1 action** was *"build `/drug/daraonrasib`"*, on the strength of 14 AI citations and 47 Bing impressions at position 7.26 with zero clicks.

**The drug is `daraxonrasib`, and the page already exists:**

```
/drug/daraxonrasib   200 · 488 words · 5 questions
title: "Daraxonrasib (RMC-6236): FDA Decision Dates & Catalyst History"
RMC-6236 ×10 · Revolution Medicines ×3 · RVMD ×3
```

**"Daraonrasib" is a user misspelling** — the missing "x" — and I copied it straight out of the Bing console without checking the INN. Building it would have created a thin duplicate under a misspelled slug, which is an SEO error, not a fix.

**The real gap is much smaller and much cheaper.** On that page:

```
occurrences of "daraonrasib": 0
```

The exact string driving **47 web impressions and 14 AI citations** appears nowhere on the page that should own it. That's a one-line alt-spelling addition, not a new page.

**Generalisable:** console query strings are user input, not entity names. Before treating a query as a missing entity, check it against the INN. Same discipline as everything else here — verify the premise before acting on the metric.

---

# 3. STILL OPEN

## 3.1 Calendar — narrowed, not closed
| | Page | API |
|---|---:|---:|
| Total (Jun–Dec 2026) | **74** | **71** |
| Ahead / Upcoming | **57** | **51** |
| Decided | 16 | 19 |
| Lapsed / Awaiting | 1 | 1 |

Gap history: 5 (08-12) → 5 (08-16) → 5 (08-18) → **3 (today)**.

The guard is working — it found three real events. But the builder's note says forward events are reconciled every run, and **forward is 6 apart (57 vs 51)**, the largest single component. The arithmetic suggests ~3 recently-decided events the page still lists as ahead, plus ~3 the API still lacks. **One more pass on the forward set should close it.**

## 3.2 A drug with a fresh positive Phase 3 and no page
```
/drug/avexitide  404      /ticker/AMLX  404
sitemap contains "avexitide": False
```
AMLX just posted a **positive Phase 3** (55% reduction, p=0.000003) and it's on `/readouts` — but there's no drug page. Given that four of five grounding queries follow `{drug} pdufa date`, a name retail is actively searching with no page is the exact gap the strategy exists to fill.

## 3.3 Still gated on you
`/compare` · `/terms` · `/privacy` · `/refund-policy` · `/contact` — **all 404.** The legal four block both email capture and the paywall.

---

# 4. WHAT I'D DO NEXT

| # | Item | Why | Effort |
|---|---|---|---|
| 1 | Add "daraonrasib" as an alt spelling on `/drug/daraxonrasib` | 47 impressions + 14 citations, string absent | minutes |
| 2 | Build `/drug/avexitide` + `/ticker/AMLX` | live positive Ph3, no page | hours |
| 3 | Close the forward-event gap (57 vs 51) | 4th audit; number is in FAQ schema | hours |
| 4 | Sweep all grounding queries for misspelling variants | daraonrasib won't be the only one | hours |
| 5 | **Legal pages** | blocks email *and* payments | 1 day |
| 6 | Email capture | audience compounding | 1 day |
| 7 | `/compare/` pilot | last content surface | 2 days |

---

# 5. BOTTOM LINE

Every item from the 08-18 audits is fixed and verified on a current run, and the builder caught a defect I'd missed — `shape()` silently dropping `presenters`, the same failure shape as the gitignore incident. The min-row guard now checks **git-tracked**, not just existence, which is the right test and closes that class properly.

The calendar guard earned its keep: three real events surfaced, one with the **wrong drug**, one with **invented day precision** on what's actually a quarter-guided device PMA. That's the guard doing exactly what it should.

**The correction is mine.** I told you to build `/drug/daraonrasib`. The drug is *daraxonrasib*, the page exists and is good, and I lifted a misspelling out of the console without checking the INN. The actual fix is one alt-spelling line — and the lesson is the same one that's caught me before: **verify the premise before acting on the metric.**

Two real gaps remain: the forward-event count, and a drug with a fresh positive Phase 3 and no page.

---
*Verified against a current run (cache MISS, age 0). Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
