# Validated Findings + Builder Fixes
**Date:** 2026-07-11 · Every publishable claim checked against peer-reviewed / official sources.
*Facts and historical statistics only. Not investment advice.*

> **Perplexity API is out of quota (401 — billing).** Validation was done via web search against primary literature (PLOS One event studies, Wong/Siah/Lo 2019, FDA PDUFA performance reports, FDA press releases). Sources listed at the end.

---

# 🔴 KILL THIS BEFORE IT SHIPS: the phase success-rate table

I recommended publishing trial success rates by phase. **Validation says do not.** It would have been publicly indefensible.

| Phase | **Our number** | **Wong, Siah & Lo (2019)** — the canonical benchmark | Verdict |
|---|---|---|---|
| Phase 1 | **33.3% positive** | **63.2%** | 🔴 **30pp too low** |
| Phase 2 | **50.3% positive** | **30.7%** | 🔴 **20pp too high** |
| **Phase 3** | **58.8% positive** | **58.1%** | ✅ **near-perfect match** |

**We invert the single most famous fact in drug development.** Wong et al. established that **Phase 2 is the valley of death (30.7%)** — the hardest phase. Our data says Phase 2 is *easy* (50.3%) and Phase 1 is *hard* (33.3%). Publishing that would get us corrected by anyone who has read the literature — which, in biotech, is everyone.

### Why it's broken (two reasons)
1. **We're measuring a different thing.** Wong measures **phase-transition probability** (did the drug advance?). We measure **"did an NLP labeller call this readout POSITIVE?"** Those are not the same metric and cannot be compared.
2. **Catastrophic missingness.** **7,207 of 11,104 readouts (65%) are `UNKNOWN` outcome.** Phase 1 is labelled for only **189 of 1,594 events (12%)**. We are computing a rate on a small, non-randomly-labelled subset.

### Why Phase 3 matches — and why that's actually reassuring
Phase 3 failures are **material and must be disclosed**, so the Phase 3 subset is well-labelled — and it lands within 0.7pp of the literature. **That's a genuine validation of our Phase 3 data.** The earlier phases are where the labelling collapses.

### 🛠️ Fix
- **Do not publish `% positive by phase`.**
- On `/clinical-trial-success-rates`, **cite Wong/Siah/Lo (2019) and BIO/Informa** for phase success rates — they're the standard, they're citable, and citing them *builds* credibility.
- Publish **our original data** where it's defensible: the **stock reaction** to readouts, which nobody else has.

---

# ✅ VALIDATED — ship these

## 1. "68% of readouts produce a flat move" — **corroborated by peer-reviewed literature**
Our data (n=1,752): FLAT **68.0%** · CRASH 7.6% · GREAT 3.1%.

**Independent support:** the PLOS One event study (*"The reaction of sponsor stock prices to clinical trial outcomes"*) finds median cumulative abnormal returns of just **+0.8% for positive events and −2.0% for negative** — i.e. **the median readout barely moves the stock.** Our "most readouts are duds" finding is exactly what the academic literature predicts.

✅ **Ship it.** It's original *at retail scale*, it's counterintuitive, and it now has peer-reviewed backing.

## 2. Cap-tier dispersion — **corroborated**
We find micro/small caps move far more than large. Literature: **early-stage biotechs showed 8.3%–11.0% higher abnormal returns than large pharma** on event day. ✅ Consistent.

## 3. FDA first-cycle approval rate — **validated**
Ours: **73.5%** first-cycle (n=1,888). FDA's own PDUFA performance reports: **75–81%** (FY2020: 81%).

✅ Close, and the small gap is explainable and honest: **our universe is publicly-traded biotech** (smaller sponsors, harder assets), FDA's includes all NDAs/BLAs including big-pharma supplements. **Say that on the page** — it turns a discrepancy into a credibility signal.

## 4. The CRL retraction — **confirmed**
FDA's press releases confirm the July-2025 release was explicitly *"associated with **since-approved applications**."* The 77%-CMC figure is a survivorship artifact. ✅ **Retraction stands. Do not publish it.**

## 5. "No systematic run-up" — **novel, and unchallenged**
Searching the event-study literature: research covers **announcement-day** returns extensively, but **pre-announcement run-up / drift for biotech catalysts is essentially unstudied.** No paper contradicts us.

⚪ **This is genuinely new ground.** Our finding — **no systematic run-up across three independent catalyst classes (PDUFA, conference, readout)** — is not just a marketing claim; it's an unfilled gap in the literature. Frame it that way.

## 6. Conference abnormal returns — **no academic study exists**
Confirmed: only anecdotal trade-press coverage ("stocks can double into ASCO"). No event study. ⚪ Our conference study is the only rigorous source — **but keep the wording to "we could find no published study," not "first ever."**

---

# 📋 BUILDER — action list

### 🔴 P0 — accuracy (do before any publishing)
1. **Remove the phase success-rate table** from any planned page. Cite Wong/Siah/Lo (2019) + BIO/Informa instead.
2. **Fix `gungnir_readout_analysis.ret_1d` / `ret_5d` scaling.** They are not decimal fractions — treating them as such yields impossible values (p25 = −521%). Confirm units before publishing any readout-move number. *(The `tier` classification is sound and safe to use.)*
3. **Drop the `prior_crl` boolean** — label leak (True → 0 approvals, 123 CRLs). Use `prior_crl_count`; cap at 4 (28 events show implausible counts up to 26 — counting at company level).
4. **Do not publish the openFDA "77% CMC" stat.** Use the unbiased comeback table instead (73.5% → 42.9% → 26.9%).

### 🔴 P1 — the moat is leaking
5. **Add a `ConferencePresentation` catalyst type to `catalyst_crawler.py`.** The live pipeline has *no* conference type — that's why ASCO26 has 6 events and EHA26/ADA26 have zero. Source from company PRs/8-Ks (crawler already reads EDGAR + FMP press) and conference agendas. **Without this the conference dataset decays permanently.**
6. **Backfill ASCO26 / EHA26 / ADA26 / ASCO-GU26** presenters.

### 🟠 P2 — publish what's validated
7. **Republish `/research/conference-runup` from `conf_study/conference_runup_FULL_v2.csv`** (1,425 events, 2017–2026) — not the current 256. Add: the 2020 bubble (+17.3%), nano tier (−9.84%), post-event fade, tail quantification. Cut the n=13 rows.
8. **Ship "68% of readouts do nothing"** — cite the PLOS One event study as independent corroboration. Strongest fact we own.
9. **Ship the readout run-up study** (`conf_study/readout_runup_events.csv`, n=1,751) — completes the trilogy and fills a genuine gap in the literature.
10. On `/fda-approval-rate`, note our 73.5% vs FDA's 75–81% and **explain the difference** (public biotech universe vs all NDAs/BLAs).

### 🟠 P3 — SEO regressions (from the last audit, still open)
11. Restore sitemap (**www**, 330 URLs, include `/conferences`, `/adcomm`, `/screener`, `/developers`, `/research/conference-runup`) + fix `/calendar` canonical to www. **Ship the CI guard** — this has now reverted twice.
12. Add `Dataset` + `Article` schema to the research pages (currently **zero JSON-LD** on `/research/conference-runup`).

### 🔴 P4 — paywall blockers (from the paywall audit)
13. Ship `/account` + auth + API-key delivery — **customers can currently pay and get nothing.**
14. Configure `STRIPE_PRICE_CREDITS_25K/_100K/_300K` + build `/pricing/credits` — the credits path **503s**.
15. Unlock API fields already visible on public pages (`indication`, `nct_id`, `days_to_decision`).

---

# The strategic read
Validation **strengthened** the two findings that matter and **killed one that would have embarrassed us**:

- **Killed:** phase success rates (contradicts the canonical literature — we'd have been corrected in public).
- **Strengthened:** "68% of readouts do nothing" now has peer-reviewed backing.
- **Confirmed novel:** the run-up work occupies a genuine gap — the literature studies *announcement-day* returns, not *pre-announcement drift*. Three independent catalyst classes, same answer, and nobody has published it.

That's the franchise. Publish the run-up trilogy and the readout-move distribution; cite other people's numbers for phase success rates. **Being the site that cites the literature correctly — and refuses to publish its own weak numbers — is the brand.**

---
## Sources
- Wong CH, Siah KW, Lo AW (2019), *Estimation of clinical trial success rates and related parameters*, **Biostatistics** 20(2):273–286 — Phase 1 63.2%, Phase 2 30.7%, Phase 3 58.1%.
- *The reaction of sponsor stock prices to clinical trial outcomes: An event study analysis*, **PLOS One** — median CAR +0.8% (positive) / −2.0% (negative).
- *Stock Market Returns and Clinical Trial Results of Investigational Compounds*, **PLOS One** — early biotech +8.3–11.0% higher abnormal returns vs large pharma.
- FDA, *PDUFA Performance Reports* / *Independent Evaluation of FDA's First-Cycle Review Performance* — first-cycle approval 75–81%.
- FDA press releases (Jul & Sep 2025) on Complete Response Letter publication — confirms the released CRL set is weighted to since-approved applications.

*Not investment advice.*
