# FDA Complete Response Letter (CRL) Corpus — openFDA

**Source:** openFDA "Complete Response Letters" transparency dataset
`https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip`
**Snapshot:** 2026-06-22 · **Records:** 439 (426 true COMPLETE RESPONSE letters + a few tentative/provisional/RTF)

## Files
- `CRL_corpus_openFDA_2026-06-22.json` — raw openFDA dump (full redacted letter **text** for every CRL).
- `CRL_index_openFDA.csv` — one row per CRL: application #, type (NDA/BLA), sponsor, letter date/year, division, `approval_status`, approximate deficiency flags, PDF file_name.

## Fields worth knowing
- `text` (in JSON) — the **full OCR'd letter**. This is the gold: real deficiency language, redacted.
- `approval_status` — **Approved** (309) vs **Unapproved** (130). NOTE: "Unapproved" = failed **OR** still-pending resubmission.
- `has_facility / has_cmc / has_efficacy / has_safety` (CSV) — keyword flags. Validated on known CMC-only cases (below). The single `primary_deficiency` column is **approximate** — letters are boilerplate-heavy, so treat the multi-label flags as "signal present," not a precise primary cause.

## ⚠️ CRITICAL: do NOT compute naive CRL→approval base rates from this dataset
It is **not a random sample.** Eventual-approval rate by CRL year is a step function:

| CRL year | n | eventually Approved |
|---|---|---|
| 2009–2023 | 295 | **~100%** |
| 2024 | 67 | 18% |
| 2025 | 59 | 0% |
| 2026 | 14 | 0% |

Two selection effects produce this:
1. **Historical bias** — FDA's first transparency batches published CRLs for products that were **subsequently approved**, so the pre-2024 set is ~100% approved *by construction*.
2. **Right-censoring** — 2024–2026 CRLs are mostly **pending resubmission** (6–18 mo to resolve), so they read as "Unapproved" simply because they haven't resolved yet.

So the "70% approved" headline and any per-deficiency rate from this file are **artifacts**, not base rates. For the real "does a CMC-only CRL resolve to approval?" question, rely on the **named precedents** (below) + published literature, not this dataset's raw rates.

## What it IS great for
- Reading the **actual deficiency language** of real CRLs (e.g., facility/483/cGMP wording vs efficacy-failure wording).
- **Precedent mining** — pull every CMC/facility-only CRL and see how it was worded and resolved.
- **Tracking the pending pipeline** — the 2024–2026 CMC CRLs (incl. Unicycive, apitegromab, tab-cel) are in here; re-pull the ZIP periodically to watch them flip Approved.

## Known-case validation (all present, correctly flagged facility/CMC)
| Drug | App # | Year | Status | Notes |
|---|---|---|---|---|
| cosibelimab (Checkpoint/UNLOXCYT) | BLA 761297 | 2023 | **Approved** | CMC-only (3rd-party CMO) → approved next cycle |
| tab-cel (Atara/Ebvallo) | BL 125745 | 2025 | Unapproved | CMC; cautionary — repeat mfg CRL |
| apitegromab (Scholar Rock) | BLA 761463 | 2025 | Unapproved | CMC-only (Catalent) → pending resubmission |
| oxylanthanum carbonate (Unicycive) | NDA 218607 | 2025 | Unapproved | CMC-only (3rd-party vendor) → PDUFA ~6/29/2026 |

All four contain the same tell: the deficiency is **"…provide satisfactory responses … to the FDA Form 483 … come into compliance with cGMP … may require re-inspection,"** with the *drug's* safety/efficacy not at issue. (The stock labeling sentence about "discontinuations due to adverse events" appears in nearly every letter and is **not** a safety deficiency — it tripped the first-pass classifier.)

## Refresh
Re-download the ZIP (same URL) to update; it's a living set the FDA appends to as new CRLs post.
