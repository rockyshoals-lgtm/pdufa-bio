# Audit + moat + non-link growth levers
**2026-08-29 19:40 UTC · site built 19:34 (6 min old) · consoles read live**
*Facts and historical statistics only — not investment advice.*

---

# PART 1 — AUDIT

## Shipped since this morning

| Commit | What | Verified |
|---|---|---|
| `173bb655e` | **NAV FREEZE until 2027-01-01, enforced by guard 51** | ✅ made a CI guard, not a note — exactly right |
| `e23f89fd3` | Homepage showed an approved drug as due today; **the decided-sweep had never actually run** | ✅ real defect, found by the builder |
| `4436370ec` | Run-up study advanced to **1,838 events** through Aug 27 | ✅ |
| `7154bf7b4` | GILD Bixlenvo published; **decision timing n=27** | ✅ |
| — | Guard count | **51** |

**Turning the nav freeze into guard 51 is the right instinct.** A directive in a document decays; a guard doesn't.

## 🟠 The cohort block shipped — but it's losing most of its value

I recommended rendering the cohort run-up data this morning. It's partially live, with three problems:

**(a) Coverage is inconsistent.**
```
/pdufa/REGN-garetosmab   → cohort block present
/pdufa/CAPR-deramiocel   → cohort: 0 · median: 0 · nothing rendered
```
But CAPR **has the data**: `cohort_n 274 · median 0% · p25 −3.99% · p75 +2.75%`. It's a rendering gap, not a data gap. **68 of 82 records carry it; far fewer pages show it.**

**(b) The rendering collapses the distribution into "±1% median".**
That destroys the most useful part. Compare:

| | p25 | median | p75 | Shape |
|---|---:|---:|---:|---|
| REGN | −0.93% | 0% | +1.03% | symmetric |
| **CAPR** | **−3.99%** | 0% | **+2.75%** | **downside-skewed** |

**"±1%" makes an asymmetric distribution look symmetric.** For a trader the skew *is* the signal. Render p25 and p75 explicitly.

**(c) It reads as a data-point, not an answer.** Current: *"Cohort decision-day move (history) ±1% median."* That is not a sentence an engine can lift. Make it one:

> **What stocks like this have done.** Across **274 comparable PDUFA events** (same market-cap tier), the median decision-day move was **0%**; half landed between **−3.99%** and **+2.75%**. This is history for similar events, not a forecast for this one.

## Not yet started (recommended this morning)
- `/pdufa-date-changes` — **404**
- Cash-cushion view — **404**

---

# PART 2 — CONSOLE STATUS (no new data)

Bing Webmaster Tools still reports through **Aug 26** — it lags 2–3 days, so these are the same figures as this morning and I'm not re-presenting them as movement:

- **195 clicks · 6.4K impressions · 3.04% CTR**
- **1,600 AI citations · 16 grounding queries · 289 on Aug 26**

Next meaningful read is ~Sept 1, which will be the first to include the 08-29 SEO batch.

---

# PART 3 — 🥇 THE BIGGEST NON-LINK LEVER: entity schema

You're handling links. **Here is the largest thing that isn't links, and it's a gap I hadn't checked until now.**

Schema `@type` coverage, sampled across nine page types:

```
DEPLOYED : FAQPage · Question · Answer · BreadcrumbList · ItemList ·
           ListItem · Event · Organization · WebSite · WebPage · SearchAction
ABSENT   : Drug · MedicalEntity · MedicalCondition · MedicalStudy ·
           MedicalTrial · Dataset · VideoObject · SpeakableSpecification
```

**We have 544 drug pages and zero `Drug` markup.**

This matters specifically for AI grounding. `FAQPage` says *"this page contains a Q&A."* `Drug` says *"this page **is** the entity camizestrant."* When an engine grounds *"camizestrant pdufa date"*, entity markup is how it decides which page **is** the authority rather than merely mentions the term.

**Ship, in order:**

| Schema | Where | Fields we already hold |
|---|---|---|
| **`Drug`** | 544 `/drug/*` | `nonProprietaryName`, `alternateName` (code names + misspellings), `manufacturer`, `activeIngredient` |
| **`MedicalCondition`** | 9 `/condition/*` | name, `associatedAnatomy`, drugs in review |
| **`MedicalStudy`** | pages with an NCT ID | `studyLocation`, `sponsor`, `phase`, `nctid` |
| **`Dataset`** | `/patent-cliff`, `/research/fda-decision-timing`, `/runup-by-year` | these are *literally* datasets and currently carry none |
| **`SpeakableSpecification`** | answer sentences | marks the exact sentence for voice/assistant read-out |

**`alternateName` is the systematic fix for the daraonrasib lesson.** Instead of hand-adding a misspelling paragraph per drug, declare every alias in schema: INN, code name (RMC-6236), brand name, common misspellings, ticker. One field, 544 pages, and it expands the query surface without a single new page.

---

# PART 4 — 🥈 VIDEO: free SERP real estate we're absent from

From the live Bing SERP for "pdufa calendar":

> **Videos of PDUFA Calendar**
> *"September 2026 PDUFA Dates: 5 FDA Decisions Biotech Investors Should Watch"* — **RTTNews, YouTube, 1 view, 12 hours ago**

**RTTNews holds a video carousel slot on the head-term SERP with a video that has one view and is twelve hours old.** The barrier is effectively zero, and the carousel sits above most organic results.

**We already have the script.** A monthly *"September 2026 PDUFA Dates"* video is our own calendar read aloud over the dates. Auto-generatable: our data → slide frames → TTS → upload. Add `VideoObject` schema and embed on `/calendar/2026/september`.

**This is not a links play, it's an inventory play** — a second SERP surface on the exact query we're fighting FDA Tracker for.

---

# PART 5 — 🥉 MORE MOAT, RANKED

**1. Date-change tracker** *(proven feasible, not built)* — 90 git snapshots make every PDUFA date change recoverable. Uncopyable without having watched daily for months. Also the alerts engine.

**2. Cash cushion at the catalyst** *(data exists, 47% coverage, not built)* — BTAI faces its decision with ~1.1 months of cash behind it.

**3. "When did the run-up peak?"** — you hold **1,838 events with T-120→T+5 daily series**. The retail question *"when should I have been in?"* has no sourced public answer. Published as pure history with n — *"across 1,838 events the median run-up peaked at T−X"* — it is factual, uncopyable, and directly citable. **Highest-value unpublished thing you own.**

**4. Catalyst congestion** — the calendar already computes "6 decisions in the week of Aug 17". A standing *"busiest FDA weeks"* view is a sector-volatility signal nobody publishes.

**5. AdComm concordance** — still only **2 events** in the API. Revisit at ~30.

---

# PART 6 — NON-LINK LEVERS FOR IMPRESSIONS AND CLICKS

| Lever | Status | Note |
|---|---|---|
| **Sitelinks** | in progress | nav frozen + guard 51; needs months of stability |
| **PAA capture** | not done | Google asks *"Does FDA approve before the PDUFA date?"* — we have the only sourced answer (n=27) |
| **FAQ rich results** | deployed | already earning |
| **`Drug`/`Dataset` rich results** | **absent** | Part 3 |
| **Video carousel** | **absent** | Part 4 |
| **Freshness stamp** | deployed | "4 hours ago" matches novapharmanews on the SERP |
| **`alternateName` alias coverage** | **absent** | expands query surface with no new pages |
| **IndexNow** | automated | working |
| **API + `llms.txt`** | deployed | AI crawlers can consume directly — worth listing the new datasets in `llms.txt` |

---

# PART 7 — DO THIS, IN ORDER

| # | Item | Cost | Why |
|---|---|---|---|
| 1 | Fix the cohort block: **every** event page, **p25/p75 explicit**, written as a sentence | hours | data already computed; currently loses the skew |
| 2 | **`Drug` schema + `alternateName` aliases** on 544 pages | 1 day | biggest non-link citation lever |
| 3 | `Dataset` schema on patent-cliff, decision-timing, run-up | hours | they are datasets and say nothing |
| 4 | PAA capture — answer the four questions verbatim | hours | cheapest Google page-one entry |
| 5 | `/pdufa-date-changes` from git + `date_history[]` forward | 2 days | uncopyable; feeds alerts |
| 6 | "When the run-up peaks" from the 1,838-event series | 1 day | best unpublished asset |
| 7 | Monthly PDUFA video + `VideoObject` | 1 day setup | free SERP surface |
| 8 | `MedicalCondition` on the 9 condition pages | hours | Google's #2 impression driver |
| 9 | Cash-cushion view, coverage stated | 1 day | BTAI headline |

---

# BOTTOM LINE

**The nav freeze became guard 51 — a directive that can't decay.** And the builder caught a real one on their own: the homepage was showing an approved drug as due today because the decided-sweep had never actually run.

**The cohort block shipped but is leaking most of its value.** It's missing from pages that have the data, and it collapses an asymmetric distribution into "±1%". CAPR's real shape is −3.99% / +2.75% — the skew is the signal, and it's being rounded away.

**The biggest non-link lever is one I hadn't checked until today: we have 544 drug pages and zero `Drug` schema.** `FAQPage` tells an engine there's a Q&A on the page; `Drug` tells it the page *is* the entity. That's the difference between being quoted and being the source. And `alternateName` solves the daraonrasib problem systematically — declare every alias, code name and misspelling in schema instead of hand-writing paragraphs.

**The cheapest surface you're not on is video.** RTTNews holds a Bing carousel slot on your head term with a one-view video posted twelve hours earlier. You already have the script; it's your own calendar.

**And the best thing you own is still unpublished:** 1,838 events of T-120→T+5 daily price series. *"When does the run-up actually peak?"* is the question every catalyst trader has, it has no sourced public answer, and you're the only one who can give it with an n attached.

---
*Consoles read live 2026-08-29; Bing data lags to Aug 26. Not investment advice.*
