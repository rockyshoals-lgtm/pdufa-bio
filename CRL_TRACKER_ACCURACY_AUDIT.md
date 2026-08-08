# CRL Tracker — Accuracy Audit + Expanded Asset Sweep
**Date:** 2026-07-11 · **Verdict: my "77%" recommendation was wrong. Do not publish it.**
*Facts and historical statistics only. Not investment advice.*

---

# 🔴 PART 1 — I have to retract the headline I gave you

Yesterday I told you to lead with: *"77% of FDA rejections are manufacturing problems, not failed science."*

**That claim is not supportable.** I stress-tested it and it fails. Here's exactly why.

## The corpus is structurally biased — and the data proves it internally

| `approval_status` in your 439 CRLs | n |
|---|---|
| **Approved** (drug later won approval) | **309 (70%)** |
| Unapproved | 130 (30%) |

**Seventy percent of the CRL corpus is for drugs that eventually got approved anyway.**

Now split the deficiency mix by that status — the bias is unmistakable:

| Primary deficiency | Among **Approved** | Among **Unapproved** |
|---|---|---|
| CMC / Manufacturing | **257 (83%)** | 83 (64%) |
| Efficacy | 16 (5%) | **16 (12%)** ← *2.4× more common* |
| Safety | 28 (9%) | 5 (4%) |
| Other / unclear | 8 (3%) | **26 (20%)** ← *6× more common* |

CMC-dominance is **exactly what you'd expect from a sample of drugs that were later approved** — because manufacturing problems are *fixable* and efficacy failures are *fatal*. We measured the survivors and concluded rejection is survivable. That's circular.

## Confirmed against the primary source
The FDA's own press releases confirm the release program is non-random:
- **July 2025:** FDA published 200+ CRLs — explicitly *"associated with **since-approved applications**."*
- **September 2025:** released 89 more, for *pending or withdrawn* applications.
- Only **going forward** will CRLs be released in real time.

So the public corpus was *seeded* with success stories. Your year-distribution shows the same fingerprint: **2024–26 alone = 142 of 439 (32%)**, while 2002–2012 has 1–4 letters per year — essentially nothing.

## Coverage is also partial
FDA issues roughly 40–60 NDA/BLA CRLs a year. Across 2002–2026 the true population is likely **~1,000–1,400**. You have **439** — roughly a third, non-randomly selected. **"24 years of CRLs" overstates it.** It's *"every CRL the FDA has chosen to publish."*

## Also: not quite first-of-its-kind
Syner-G has published *"291 FDA Complete Response Letters Decoded"* — a CMC-strategy analysis of the same openFDA corpus. **Their angle is pharma manufacturing consulting.** A **ticker-linked, investor-facing CRL tracker with comeback rates** is still genuinely novel — but drop any "first ever" claim. Accuracy is the brand; overclaiming here would be the exact hypocrisy we're trying to avoid.

---

# ✅ PART 2 — What the CRL data *can* honestly support (and it's better)

Stop asking *"why does the FDA reject drugs?"* (unanswerable with this sample). Ask **"what happens after a CRL?"** — which is what investors actually want, and which this data *can* answer.

## Comeback rate by deficiency type — among published CRLs

| Primary deficiency | Eventually approved | n |
|---|---|---|
| **Safety** | **84.8%** | 33 |
| **CMC / Manufacturing** | **75.6%** | 340 |
| **Efficacy** | **50.0%** | 32 |
| **Other / unclear** | **23.5%** | 34 |

**The honest, useful headline:**
> **"A manufacturing CRL is usually survivable. An efficacy CRL is a coin flip."**

**Mandatory caveats to print on the page:**
1. These are **published** CRLs only — a set the FDA seeded with since-approved applications, so **absolute rates are inflated**. The *relative ordering* is the signal, not the levels.
2. Coverage is ~⅓ of all CRLs, weighted to 2024–26.
3. Say all of this **on the page.** Publishing the bias *is* the differentiator — no competitor would.

**Still ship the CRL Tracker.** It's real, it's unique in an investor context, and it reframes how retail reads a rejection. Just frame it as *what happened next*, not *why they reject*.

## ⚠️ Also fix before publishing
The `prior_crl = True → 0.0% approved (n=125)` artifact in the ODIN archive is still unresolved and **contradicts this table** (which shows 50–85% comeback rates). One of the two is wrong. Reconcile before either ships.

---

# 📦 PART 3 — New assets found in the wider folders

I swept every subfolder and Google Drive (Drive is a synced mirror — no new data, though you already have an `.ics` generator and `catalyst_crawler.py`).

## 🥇 The real find: **FINRA short interest, 2017 → 2026**
`si_raw/` — **196 bi-monthly files, 2017-12-29 → 2026-03-31**, full FINRA schema (`currentShortPositionQuantity, averageDailyVolumeQuantity, daysToCoverQuantity, changePercent, settlementDate`) for **all US stocks.**

This is a genuine, rare asset, and it does two things:

1. **It fixes a real flaw your own red team flagged.** The audit noted BIFROST applied *a single April-2026 SI snapshot retroactively to 1,704 historical events* — lookahead bias. **You had the historical data all along.** Rebuilding SI features from `si_raw/` makes every SI-based model honest.
2. **It's a publishable pdufa.bio feature:** *"Short interest going into this PDUFA: 18% of float, 6.2 days to cover"* — a **fact**, not a prediction. Retail badly wants it. No competitor shows historical SI at the catalyst.

## Other assets
| Asset | What it is | Note |
|---|---|---|
| `orats_phase3_cache/` | **14,703** ORATS options/IV files | Implied-move context. On-brand only as a *market fact*, not an edge claim. |
| `catalysts_out/catalysts_public.csv` | 1,123 × 50 cols, has `date_precision` | The production catalyst pipeline — good. |
| `smart_money_cache/` (305), `phase_readout_cache/` (134) | 13F / news caches | Institutional ownership is public fact; the *scoring* is not. |
| `seo_pages/`, `pdufa_site_src/` (1,045) | Site source + SEO templates | — |

## 🚨 Two legal flags — check these before anything ships
1. **`catalysts_out/bpc_internal.csv` (643 rows).** The name reads as **BioPharmaCatalyst-derived**. If any of it was scraped from a competitor, using it on a commercial competing site is a **ToS/legal risk** — and it directly contradicts pdufa.bio's *"100% original content"* claim. **Verify provenance; purge if scraped.**
2. **`drugbank_all_full_database.xml.zip` (182 MB).** DrugBank is **licensed data** — free for academic use, **commercial use requires a paid licence.** Do not ship DrugBank-derived fields on a paid product without one. Use ChEMBL (open) instead.

---

# Bottom line
- **Kill the "77% of rejections are manufacturing" headline.** It's a survivorship artifact and it would not survive scrutiny from anyone who checked — which, for an accuracy-first brand, is the worst possible way to get famous.
- **Ship the CRL Tracker anyway**, reframed as *"what happens after a CRL"*, with the comeback table and the bias disclosed on the page. That's honest, unique, and more useful.
- **The sleeper asset is `si_raw/`** — 9 years of FINRA short interest. It repairs a known modelling flaw *and* gives pdufa.bio a factual feature nobody else has.
- **Two legal flags** (`bpc_internal.csv`, DrugBank) need clearing.

I got the CRL headline wrong. Better to catch it here than in a Hacker News comment thread.

---
*Facts and historical statistics only — no trade recommendations, no approval probabilities. Not investment advice.*
