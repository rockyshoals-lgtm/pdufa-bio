# SEO Audit + Red Team — Conference Study & Site
**Date:** 2026-07-11 · Cache-busted live inspection · *Not investment advice.*

---

# PART A — RED TEAM: the published conference study

**URL:** `/research/conference-runup` (live, 200)

## ✅ What's right — genuinely excellent
This page is the best expression of the brand you've published. Specifically:
- **The core finding replicates my independent build.** Published median D-30→D-1 = **−0.23%**; my 1,401-event study = **−0.35%**. Same conclusion: *dispersion, not an edge.*
- **The three caveats are exactly right** — self-selection, single-anchor, small-n. The line *"we would rather tell you it is missing than quietly publish a number that pretends otherwise"* is the most on-brand sentence on the site.
- **No win rates, no scores, no sizing, no entry/exit.** Clean.
- **n printed next to every figure**, and an explicit instruction to discount n<20.
- Best line on the site: *"Anyone quoting you a single conference run-up number without a sample size and a quartile range is selling you something."*

## 🔴 The problem: it's built on 256 events. I gave you 1,401.

The page uses **256 presentations, 2022-06-29 → 2026-01-09**, sourced from "company catalyst disclosures." **It does not use the dataset I built** — `conf_study/conference_runup_FULL.csv`, **1,401 events, 2017–2026, 393 tickers, 48 fields**. You are publishing on **18% of the data you own.**

That gap isn't cosmetic — it changes the findings:

### 1. It misses the single most important insight: **2020 was a bubble**
| Year | n | median D-30 |
|---|---|---|
| 2017–19 | 132 | +2.4% to +3.2% |
| **2020** | **47** | **+17.27%** ← 5× any other year |
| 2021 | 71 | +2.19% |
| **2022–24** | **895** | **−3.3%, −2.9%, −1.7% (all negative)** |
| 2025–26 | 256 | +1.2%, +4.3% |

**This is the story.** It explains *why everyone believes in the conference run-up* — they learned it from a COVID-era bubble — and it shows the effect **inverted for three straight years afterwards.** It's the most quotable, most link-worthy finding you have, and the published page (starting in mid-2022) **cannot see it.**

### 2. It omits the nano tier — which is the worst performer
My data: **nano = −9.84% median (n=42)**, by far the worst cohort. The page shows only Micro/Small/Mid/Large. **The most retail-protective finding on the board is missing.**

### 3. Its numbers skew systematically positive because the sample is small and late
| Cut | Published (n) | My study (n) |
|---|---|---|
| Small-cap | **+7.90%** (66) | +3.28% (129) |
| ASH | **+8.74%** (47) | +3.13% (201) |
| AACR | **+8.01%** (13) | +2.83% (122) |
| SITC | +4.02% (13) | −2.27% (65) |

**AACR is published at n=13.** The page itself says treat n<20 as "indicative at best" — and then publishes four such rows anyway. **If you tell readers to discount a number, don't lead a table with it.** Either use the n=122 figure I have, or cut the row.

### 4. It's missing the post-event fade — the natural next question
My data (n=1,401): **event day −0.48% · D-1→D+5 −1.55% · D-1→D+10 −1.92%.**
Readers will immediately ask *"so what happens if I hold through?"* You have the answer and it's honest and unflattering. Publish it.

### 5. It asserts "dispersion is the story" but never quantifies the tails
The page's own thesis is unevidenced. Quantify it:
- Only **49.5%** of presenters were positive at all (worse than a coin flip)
- **15.6%** ran ≥25% · **6.3%** ran ≥50%
- **Mean +5.41% vs median −0.35%**, std dev 33.6%

### 6. Minor: reconsider "we never report a mean"
The page refuses to show a mean. But **the mean/median gap *is* the proof** that a small tail is doing all the work. Showing +5.41% mean vs −0.35% median and *explaining why the mean lies* is more transparent — and more persuasive — than hiding it.

### 7. Window convention differs from my build (document it)
The page uses D-30 = **21 trading days** (≈30 calendar days); my study used **30 trading days**. Both are defensible; they are **not comparable**. The page documents its convention (good) — just be aware the two datasets won't line up, and pick one convention going forward.

---

# PART B — SEO AUDIT: three regressions, and the flagship page is invisible

## 🔴 1. The sitemap has REGRESSED
| | Re-audit #5 (fixed) | **Now** |
|---|---|---|
| URLs | **330** | **170** ⬅ reverted |
| Host | **www.pdufa.bio** | **pdufa.bio** (non-www) ⬅ reverted |
| `/conferences` | ✅ present | ❌ **missing** |
| `/adcomm` | ✅ present | ❌ **missing** |

**Also missing from the sitemap:** `/screener`, `/developers`, and — critically — **`/research/conference-runup`**.

A deploy has overwritten the sitemap fix. **Your best new asset isn't in the sitemap.**

## 🔴 2. Canonical has REGRESSED
`/calendar` canonical is back to **`https://pdufa.bio/calendar` (non-www)** while every other page uses www. Same split-signal bug I flagged three audits ago, reverted again. Meanwhile `robots.txt` correctly points to the **www** sitemap — which itself emits **non-www** URLs. Three-way inconsistency.

## 🔴 3. The flagship research page has **zero structured data**
`/research/conference-runup` → **JSON-LD: []**. No `Dataset`, no `Article`, no `FAQPage`, no `BreadcrumbList`.

This is your **link-bait asset** — an original, decade-spanning study — and it is:
- not in the sitemap,
- carrying no schema,
- with a **231-character meta description** (truncates at ~155).

**Fix:** add `Dataset` + `Article` + `BreadcrumbList` + `FAQPage` schema, put it in the sitemap, trim the description, and request indexing. `Dataset` schema is what gets research surfaced in Google Dataset Search — free distribution nobody in this category uses.

## ✅ 4. What's good on the SEO side
- **New CRL pages shipped:** `/decisions/crl` (BreadcrumbList) and `/learn/what-is-a-crl` (**BreadcrumbList + FAQPage** ✅ — correctly schema'd).
- `/research/pdufa-stock-run-up-by-market-cap` — "763 FDA Decisions (2024–26)" is live.
- All content pages remain publicly crawlable post-paywall (no gating damage).
- og:image present across new pages.
- `/decisions/crl` meta description is only **76 chars** — too thin; expand toward 150.

## 5. Rankings — still outside the top 10 for the head term
**"PDUFA calendar"** → FDA Tracker, RTTNews, BPIQ, BiopharmaWatch, Assyro, CheckRare, BioPharmCatalyst, Dan Sfera. **pdufa.bio absent.**

**But the conference-run-up space is wide open.** Searching *"conference run-up study biotech ASCO ASH"* returns only **anecdotal editorial** ("stocks can double or triple into ASCO") — **there is no rigorous public study.** Your 1,401-event study would be the only authoritative source in existence. That's a genuine land-grab — **but only if it's indexable**, which today it isn't.

---

# PART C — Data the builder still isn't using

Everything below is built, validated, and sitting in the repo. **Point the builder here.**

| Asset | Path | Status |
|---|---|---|
| **Conference run-up — 1,401 events, 2017–2026, 48 fields** | `conf_study/conference_runup_FULL.csv` | ✅ built — **replaces the 256-event page** |
| Conference master universe (enriched) | `conf_study/MASTER_conference_events_ENRICHED.csv` | ✅ 1,427 events × 41 cols |
| **FINRA short interest panel, 2017–2026** | `conf_study/si_panel_2017_2026.csv.gz` | ✅ 3.63M rows, 47,243 tickers |
| SI at catalyst (T-1 compliant, **zero lookahead**) | `conf_study/si_at_catalyst_PDUFA.csv` (96.4% cov)<br>`conf_study/si_at_catalyst_CONFERENCE.csv` (93.8%) | ✅ built |
| **CRL comeback table (unbiased)** | from `ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv` | ✅ 73.5% → 42.9% → 26.9% |
| Approval rate by therapeutic area | same file, n=2,210 | ✅ Oncology 53.6% … Respiratory 96.8% |
| Device universe (510k + PMA) | `odin_catalyst_database.csv` | ⚠️ 29k events, **dates not parsed** |
| Trial design depth | `ctgov_t1_dataset.csv` | ⚠️ 18,524 trials × 117 cols, unused |

---

# PART D — Red team: the standing risks

| # | Risk | Status |
|---|---|---|
| 1 | **Published study uses 18% of available data**, skews positive, omits nano/2020/fade | 🔴 **fix now** |
| 2 | Sitemap + canonical regressions (reverted twice) | 🔴 **add a CI guard so they can't revert again** |
| 3 | Flagship research page: no schema, not in sitemap | 🔴 |
| 4 | **No `/account`, `/login`** — paying customers can't get their API key | 🔴 *(from paywall audit)* |
| 5 | **Credits checkout 503s** — `STRIPE_PRICE_CREDITS_25K` unset | 🔴 *(from paywall audit)* |
| 6 | API locks fields the public HTML gives away (indication, NCT, cohort, runway) | 🟠 leaky + inconsistent |
| 7 | `prior_crl` label leak still in the model feature set | 🟠 drop it |
| 8 | BIFROST SI features still lookahead-biased | 🟠 rebuild from `si_panel` |
| 9 | Conference Overlay v1.0 numbers (+4.88% nano/micro) **refuted** — nano is actually −9.84% | 🟠 retire everywhere |
| 10 | DrugBank zip (licensed, unused) still in repo | 🟡 delete |

## Add this CI guard — the canonical/sitemap fix has now been reverted twice
```python
# tests/test_seo_invariants.py — must block deploy
import requests, xml.etree.ElementTree as ET, sys
BASE='https://www.pdufa.bio'
errs=[]
sm=requests.get(f'{BASE}/sitemap.xml').text
locs=[e.text for e in ET.fromstring(sm).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
if any('//pdufa.bio' in l for l in locs): errs.append('FATAL: sitemap emits non-www URLs')
MUST=['/conferences','/adcomm','/screener','/developers','/research/conference-runup']
for p in MUST:
    if not any(l.endswith(p) for l in locs): errs.append(f'FATAL: {p} missing from sitemap')
for p in ['/','/calendar','/pdufa-calendar','/conferences']:
    html=requests.get(BASE+p).text
    if 'rel="canonical" href="https://www.pdufa.bio' not in html:
        errs.append(f'FATAL: {p} canonical is not www')
if errs: print('\n'.join(errs)); sys.exit(1)
print(f'OK — sitemap {len(locs)} urls, all www, all key pages present.')
```

---

# Priority
1. **Republish the conference study on the 1,401-event dataset** — add 2017–21 (the 2020 bubble), the nano tier, the post-event fade, and the tail quantification. Cut the n=13 rows.
2. **Restore sitemap (www, all pages) + canonical**, and ship the CI guard so it can't revert a third time.
3. **Add `Dataset` + `Article` schema** to the research page and request indexing — the conference-run-up SERP is *empty of rigorous sources*. It's yours to take.
4. Then the paywall blockers (`/account`, credits Stripe IDs).

**Bottom line:** the study's *honesty* is excellent and the writing is the best on the site. The *data behind it* is 18% of what you own, and the numbers it publishes are the ones most likely to be revised. Fix the dataset before this gets links — because once it's cited, correcting it is far more expensive.

---
*Facts and historical statistics only. Not investment advice.*
