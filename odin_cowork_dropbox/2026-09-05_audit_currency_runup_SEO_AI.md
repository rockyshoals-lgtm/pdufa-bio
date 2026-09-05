# Audit — 2026-09-05 · data currency, run-up sample, SEO / Bing / AI citations
**Live build `2026-09-05T14:44:18Z` · API `as_of` 2026-09-05 · both consoles read live**
*Facts and historical statistics only — not investment advice.*

---

# 1. ✅ CURRENCY — EVERYTHING IS CURRENT

| Check | Result |
|---|---|
| Live build | **2026-09-05T14:44Z** — today |
| API `as_of` | **2026-09-05** |
| `/calendar` | **"Updated September 5, 2026"** |
| `/runup-by-year` | **"Updated Sep 5, 2026 · 1,840 decisions"** |
| Past-goal day-precision PDUFAs with no decision | **0** |
| `Guided` readouts past their date | **0** |

Both safety nets are holding. Nothing is sitting past its date unresolved on either surface.

*`/methodology` still reads "Updated August 15, 2026" — I checked whether that's stale and **it isn't**. It quotes no sample size and no counts; the content genuinely hasn't changed. Re-stamping an unchanged page would be the defect, not the fix.*

---

# 2. ✅ THE RUN-UP SAMPLE IS CORRECT — AND THE DISCLOSURE IS THE BEST ON THE SITE

**Published: 1,840 PDUFA events, 2020-01-08 → 2026-08-28.** I reconciled every figure against `runup_study_stats.json`:

| Published | Source file | ✓ |
|---|---|---|
| 1,840 events | `n_events = 1840` | ✅ |
| 1,309 approvals | `n_approval = 1309` | ✅ |
| 71.1% approval rate | 1309 / 1840 = **71.14%** | ✅ |
| — | `n_crl = 531` → 1309 + 531 = **1,840** | ✅ internally closed |
| Median run-up T-120→T-1 **+2.1%** | `T-120_T-1_median_pct = 2.07` | ✅ |

**The end date is 2026-08-28 — MIMRYLO's approval day.** The event the watcher caught 33 days early is already folded into the study. That's the loop closing end to end.

## The coverage disclosure is exactly right

> *"**T-120 coverage.** 1,769 of 1,840 events (96.1%) have a full 120 sessions of prior trading history; the rest are companies that had not been listed long enough, and they are **excluded from the T-120 columns rather than measured**."*

Numerator, denominator, percentage, the *reason* for exclusion, and an explicit statement that they were dropped rather than imputed. **That is the denominator doctrine executed properly**, and it is the sentence I would point a sceptical reader at first.

The page also states its baseline once and holds it — *"All run-up figures use a single T-120 baseline… the same baseline quoted everywhere else on the site"* — and explains why it uses medians: *"A handful of 300% moves would make means meaningless here."* No competitor is being this careful.

*Minor: `/runup` resolves, `/runup/` returns 404. Every other hub takes the trailing slash. Worth normalising. (`/runup` itself is the password-locked internal Runup Explorer — correctly gated.)*

---

# 3. 🔴 THE CALENDAR IS MISSING FOUR APPROVALS INSIDE ITS OWN WINDOW

The calendar states:

> *"This page lists **75** FDA decision dates covering June 2026 to December 2026. **51** are still ahead, and **23** have been decided… **1** passed its target date without a published decision."*

**Its arithmetic is perfect** — 51 + 23 + 1 = 75, and I counted 51 `/pdufa/` links and 23 `/fda-decision/` links in the DOM. **This is not a broken counter. Four decided events are missing from the source set.**

| Ticker | Drug | Approved | On calendar? | Decision page |
|---|---|---|---|---|
| **MNKD** | FUROSCIX ReadyFlow | 2026-07-24 | ❌ **0 occurrences** | ✅ 200 |
| **REPL** | TUDRIQEV | 2026-08-06 | ❌ **0 occurrences** | ✅ 200 |
| **JAZZ** | Ziihera (zanidatamab) | 2026-08-25 | ⚠️ present, **no decision link** | ✅ 200 |
| **ZYME** | Ziihera (zanidatamab) | 2026-08-25 | ⚠️ present, **no decision link** | ✅ 200 |

All four decision pages exist and resolve. **The pages are right; the calendar doesn't point at them.**

**This matters more than the count suggests.** `/calendar` carries **47% of all site impressions** and 133 clicks — it is the highest-traffic page we have, and it currently under-reports our own coverage by four approvals.

**Two things I checked before calling this a defect**, because I have generated phantom calendar discrepancies before:

- **SPRO is NOT missing.** It renders as *"GSK / SPRO · 2026-06-17 · ✓ Approved · Tebipenem HBr"* — a co-development filed under GSK. My first ticker-level diff flagged it; the page is correct and my method was wrong.
- **CORT (2026-03-25) is correctly absent** — March falls outside the stated June–December window.

**And credit where it's due:** *"1 passed its target date without a published decision"* is a **new honest disclosure**. Most trackers would hide that row. Stating it is the right instinct.

---

# 4. 📈 BING — COMPOUNDING, AND SEPTEMBER IS THE STRONGEST STRETCH YET

**Window Jun 4 – Sep 3 (3 months):** **293 clicks · 9.7K impressions · 3.02% CTR**

Daily impressions are accelerating hard at the end of the window:

| Aug 29 | Aug 30 | Aug 31 | **Sep 1** | **Sep 2** | **Sep 3** |
|---:|---:|---:|---:|---:|---:|
| 91 | 188 | 408 | **566** | **577** | **698** |

Sep 3 is the highest single day on record.

## The CTR cliff, confirmed a third time

| Keyword | Impr | Clicks | CTR | Position |
|---|---:|---:|---:|---:|
| `fda pdufa calendar` | 13 | 5 | **38.46%** | 3.69 |
| `sabirnetug` | 15 | 5 | **33.33%** | 2.53 |
| `garetosmab pdufa` | 12 | 4 | **33.33%** | **2.00** |
| `pdufa calendar` | 22 | 6 | **27.27%** | 2.05 |
| `fda approvals today pdufa` | 30 | 4 | **13.33%** | 3.77 |
| `pfizer pfe pdufa dates fda approval decisions 2026 2027` | 82 | **0** | 0.00% | **3.23** |
| `camizestrant pdufa date` | 25 | **0** | 0.00% | 4.44 |
| `pdufa` | **838** | 4 | **0.48%** | 6.28 |

**Position 2.0–2.5 converts at 27–38%. Position 6.3 converts at 0.48% on 838 impressions.** The head term `pdufa` alone is leaking ~830 impressions a month.

**`/fda-decisions-today` is working.** `fda approvals today pdufa` → **13.33% CTR at position 3.77**. That page shipped Sept 1 and I said to check it Sept 8 — early read is positive.

**`garetosmab pdufa` at position 2.00 with 33% CTR** is the REGN drug we were 13 days stale on. Fixed, and now converting at the top of its class.

---

# 5. 🤖 AI CITATIONS — 3.3K, AND **BREADTH FINALLY BROKE**

| | Aug 12 | Aug 18 | Aug 26 | Aug 31 | **Sep 3** |
|---|---:|---:|---:|---:|---:|
| Citations | 115 | 413 | 1.6K | 2.4K | **3.3K** |
| Avg cited pages | 7 | 8 | 12 | 14 | **15** |
| **Grounding queries** | 1 | 5 | 16 | **18** | **19** |

**Grounding queries had been stuck at 18 for two weeks. It moved.** And the new entrants tell you exactly where the growth is:

| Grounding query | Citations | Citation share |
|---|---:|---:|
| `pdufa date` | 307 | 19.50% |
| `fda calendar 2026` | 183 | 27.44% |
| `camizestrant pdufa date` | 72 | **32.14%** |
| **`rusfertide pdufa date`** | **72** | **17.02%** |
| `upcoming clinical trial readouts rare disease specialty pharma 2025 2026` | 66 | **31.43%** |
| `zanidatamab pdufa date` | 8 | **100%** |
| `povetacicept` · `neladalkib` · `savara` · `tavapadon` pdufa date | 3–9 each | new |

**`rusfertide pdufa date` — 72 citations — did not exist before we caught that approval.** The watcher found MIMRYLO 33 days early, we published it, and it is now tied for our third-most-cited query. **That is the clearest evidence yet that speed on a single event converts directly into AI citation volume.**

**10 of 19 grounding queries are now `{drug} pdufa date`.** The entity strategy is the growth engine, and it is compounding without a single backlink.

*Two notes on Bing's own labels, which are theirs and not ours: it files `pdufa date` under "Holidays & Observances" and the daraonrasib misspelling under "Hunting, Firearms & Ammunition." Classifier noise. More usefully, it files `rusfertide pdufa date` under **"ETFs & Retail Investing Products"** — that is Bing telling us who it thinks our audience is.*

---

# 6. GOOGLE — IMPRESSIONS UP, CLICKS FLAT, CTR DOWN

**Window Jun 4 – Sep 3:** 53 clicks · **2.98K impressions** (was 2.74K) · **1.8% CTR** (was 2.0%) · position **19.6** (was 20.7) · **157 queries**

**Entity queries still convert at or near 100%:** `pdufa.bio` 3/3 · `monalizumab` 1/1 · `giredestrant` 1/1 · `nct04229979` 1/1 · `miplyffa` 1/1 · `rezatapopt` 1/2 · `deramiocel pdufa` 1/3.

**Head terms convert at zero:** `pdufa dates` **0 clicks / 63 impressions** · `pdufa date` **0 / 51**.

The pattern is unchanged and unambiguous: **we are gaining impressions at positions that cannot convert.** Position improved a full point and CTR still fell, because the new impressions arrived below the fold. Google is an authority problem, and links are the lever — which you're handling.

---

# 7. WHAT I'D DO NEXT

| # | Action | Why |
|---|---|---|
| **1** | **Add MNKD, REPL, JAZZ, ZYME to the calendar's decided set** | four approvals missing from our highest-traffic page; the decision pages already exist |
| **2** | **Guard: every `Decided` PDUFA in the calendar window must render a `/fda-decision/` link** | same shape as guard 59 — assert the render, not the data |
| 3 | **Watcher `brand_name` → `alternateName`** | 10 of 19 grounding queries are drug entities; brands (MIMRYLO, PASATRU) are still absent and are the next entity tier |
| 4 | **Company-scoped PDUFA pages** | `pfizer pfe pdufa dates…` = 82 impressions, **position 3.23, zero clicks**. There's demand for `/company/{name}` that we don't serve |
| 5 | Normalise `/runup/` → `/runup` | trailing-slash inconsistency |
| 6 | Fix `/readouts` TYRA row (Aug 2026 + −8% on a 2027 event) and populate `outcome` on TENX/MPLT | carried from 09-04; still open |

---

# BOTTOM LINE

**Everything is current and the run-up sample is right.** Live build is four hours old, every dated surface reads September 5, and **1,840 events reconciles exactly** to `runup_study_stats.json` — 1,309 approvals plus 531 CRLs, 71.1%, through 2026-08-28. The T-120 coverage sentence — *"1,769 of 1,840 (96.1%)… excluded from the T-120 columns rather than measured"* — is the best disclosure on the site.

**One real defect: the calendar is missing four approvals inside its own June–December window.** MNKD and REPL appear zero times; JAZZ and ZYME appear without decision links. All four decision pages exist and return 200 — **the pages are right, the calendar doesn't point at them** — on the page carrying 47% of our impressions. *(SPRO looked missing and isn't; it's filed under GSK as a co-development. I checked before writing it up.)*

**The channel numbers are the strongest yet.** Bing at **293 clicks / 9.7K impressions**, with Sept 3 the best single day on record. AI citations at **3.3K**, and **grounding queries finally broke 18 → 19** after two flat weeks.

**And the loop is now provable.** The watcher caught MIMRYLO 33 days early on August 28. `rusfertide pdufa date` did not exist as a grounding query before that. It now returns **72 citations at 17% share**, and the event is folded into the 1,840-event study. **Catching one approval early, quickly, generated a citation stream — no backlinks involved.** That is the moat working exactly as designed, and it argues for pointing the same speed at the readout calendar next.

---
*Verified against the 2026-09-05T14:44:18Z build. Bing and Google consoles read live 2026-09-05. Not investment advice.*
