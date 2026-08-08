# pdufa.bio — The Data Moat: What We Already Own
**Date:** 2026-07-11 · Inventory of a year of mining, filtered through the "facts, not edge claims" brand rule.
*Facts and historical statistics only. Not investment advice.*

---

## The rule I applied
Every asset below is sorted by one test: **can it be published as a historical FACT, or is it a SCORE/PREDICTION?**
- ✅ *Fact* = what happened, how often, how the stock traded → **publish, it's the moat**
- 🔒 *Score* = probability, tier, boost, win rate, sizing → **keep internal (ODIN/Gungnir/BIFROST)**

---

# 🥇 TIER 1 — Ship these. Nobody in the category has them.

## 1. **The CRL Tracker** — 439 Complete Response Letters, 2002 → 2026
`CRL_index_openFDA.csv` · mined from openFDA · **fully public data, but nobody has assembled it**

**The headline finding, and it's a bombshell:**

| Why the FDA actually rejects drugs | n | share |
|---|---|---|
| **CMC / Manufacturing** | **340** | **77%** |
| Safety | 33 | 8% |
| Efficacy | 32 | 7% |
| Other / unclear | 34 | 8% |

**Three-quarters of FDA rejections are manufacturing and quality problems — not "the drug didn't work."** 160 of 439 involve a facility issue. Retail investors almost universally read a CRL as *"the science failed"* and dump the stock. **That is factually wrong most of the time**, and we can prove it with 24 years of data.

Every field is there: `application_number, company, letter_date, division, primary_deficiency, cmc_only, has_facility, has_cmc, has_efficacy, has_safety`.

**What to build:**
- `/crl-tracker` — every FDA rejection since 2002, searchable by company/drug/year/reason
- A research page: **"Why the FDA actually rejects drugs (it's not what you think)"** → this is a *link magnet*. Endpoints/STAT/Fierce would cover it.
- A CRL badge on every event page: *"This drug received a CRL in 2023 — reason: CMC"*
- **SEO:** owns "CRL", "complete response letter", "[drug] CRL", "why was [drug] rejected" — all currently unowned.

**Nobody — not BioPharmaCatalyst, BiopharmaWatch, RTTNews, TheraRadar — has a CRL database.** This alone is a category-defining feature.

## 2. **The CRL → Approval Journey**
`CRL_CMC_cases.csv` — `ticker, drug, crl_date, num_crls, outcome, approval_date, tries_to_approve`

Answers the single most emotional question retail has after a rejection: **"Is it over?"**
Example in the data: **VRCA / YCANTH — 3 CRLs, approved on the 3rd+ try (2023-07-21).**

**Build:** on every CRL, show *"companies with a CMC-only CRL historically came back and got approved — here are the cases, and how long it took."* Pure fact. Enormously useful. Zero prediction.

## 3. **FDA Approval Rate by Therapeutic Area** — 2,210 PDUFA events, 2015 → 2026
`ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv` (1,498 approvals / 705 CRLs = **68% base rate**)

| Therapeutic area | Approved | n |
|---|---|---|
| **Oncology** | **53.6%** | **978** |
| Ophthalmology | 65.9% | 44 |
| Pain Management | 67.5% | 40 |
| Nephrology | 68.8% | 32 |
| CNS / Neurology | 76.4% | 140 |
| Cardiovascular | 79.4% | 63 |
| Metabolic / Endocrine | 80.0% | 35 |
| Rare Disease | 82.9% | 70 |
| Immunology | 88.2% | 93 |
| Infectious Disease | 89.7% | 175 |
| Dermatology | 90.6% | 32 |
| **Respiratory** | **96.8%** | 31 |

**Oncology — the most crowded, most hyped area in biotech — has by far the *worst* FDA approval rate (53.6%, n=978).** Respiratory approves at 96.8%. That's a genuinely counterintuitive, highly shareable, evergreen fact.

**Build:** expand `/fda-approval-rate` into a full interactive table + per-TA pages. **"FDA approval rate" is a high-volume evergreen query and a permanent backlink magnet.**

## 4. **The Conference Run-up Study** — 1,427 events, 2017 → 2026 *(built this session)*
`conf_study/MASTER_conference_events_ENRICHED.csv` — 393 tickers, 41 metadata fields.
Finding so far: **there is no systematic conference run-up** (median ≈ 0, p=0.92 vs baseline) — the returns live entirely in a fat right tail. *Needs the local FMP price run to finish.*

## 5. **The PDUFA Run-up Study** — 1,683 events *(already live — the current moat)*

---

# 🥈 TIER 2 — Strong, needs a bit of work

| # | Asset | What it is | The feature |
|---|---|---|---|
| 6 | **Device calendar** | `odin_catalyst_database.csv`: **14,974 510(k) + 14,232 PMA**, 6,989 companies | You already have `/devices`. Nobody has a real **device catalyst calendar** — medtech investors are completely unserved. ⚠️ *Dates aren't parsed for device rows — fix first.* |
| 7 | **Short interest at the catalyst** | `si_event_features.csv` — 3,889 events, 2020–2026: days-to-cover, short/ADV, SI trend | *"How crowded is the short going into this PDUFA?"* — a **fact**, hugely wanted by retail, and shown by nobody. Safe: it's a market observation, not a prediction. |
| 8 | **Trial-design depth** | `ctgov_t1_dataset.csv` — **18,524 trials × 117 columns** (randomized, blinded, N, arms, endpoints, sites, countries) | Put real trial design on every readout page: *"Phase 3, randomized, double-blind, n=450, 12 countries, hard endpoint."* Competitors show a drug name and a date. |
| 9 | **AdComm vote history** | 50 events w/ AdComm, 62 with vote % | *"The panel voted 9-2 in favour — and the FDA agreed."* Thin but unique. Grow it. |
| 10 | **Drug modality (ChEMBL)** | modality, mechanism, target class, first-in-class for ~1,250 drugs | Adds real science to every event: *"ADC, HER2, first-in-class."* |

---

# 🔒 TIER 3 — Keep internal. Publishing these kills the brand.
ODIN/Gungnir/BIFROST scores, tiers and probabilities · Conference Overlay boosts · Smart Money & UOA overlays · win rates · options torque / IV playbooks · position sizing · ALPHA/BETA/GAMMA labels.

These are your alpha. They are also **exactly** what `/why-no-approval-probability` promises you'll never show. Publishing them would make pdufa.bio just another BiopharmaWatch PoA black box — and destroy the one thing that differentiates it.

---

# ⚠️ Data-quality flag — fix before publishing anything
In the ODIN archive, `prior_crl = True` → **0.0% approved (n=125)**. That is almost certainly a **labelling artifact** (the flag appears to mark the CRL event itself, not the resubmission), and it directly contradicts `CRL_CMC_cases.csv`, which shows companies *do* come back and get approved (VRCA on the 3rd try). **Do not publish any "resubmission approval rate" until this is reconciled.** Accuracy is the brand.

---

# The strategic point

Competitors sell **a list of dates**. That's a commodity — BioPharmaCatalyst gives it away free.

What you have that literally none of them do:
1. **24 years of CRLs, categorised by why** → and the finding that *77% of rejections are manufacturing, not science*
2. **A decade of approval base rates by therapeutic area** → *oncology is the hardest, at 53.6%*
3. **Run-up history for PDUFAs, readouts and conferences** → *what the stock actually did*
4. **The CRL→approval journey** → *what happens after a rejection*

That is a **research franchise**, not a calendar. It's all public-source fact (defensible), it's all on-brand ("facts, not odds"), it's un-copyable without a year of mining, and every one of these is a **link magnet + a rankable evergreen page** — which is precisely the off-page authority problem currently keeping you off page 1.

**Lead with the CRL finding.** *"Three-quarters of FDA rejections are manufacturing problems, not failed science"* is a headline that gets picked up, earns links, and reframes how every retail investor reads a CRL. No competitor can answer it.

---
*Facts and historical statistics only — no trade recommendations, no approval probabilities. Not investment advice.*
