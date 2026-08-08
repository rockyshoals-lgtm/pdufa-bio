# ODIN PDUFA Dataset Enrichment Report v4

**Generated:** 2026-01-29 02:51:08
**Status:** COMPLETE

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Events | 1906 |
| Approvals | 1573 |
| CRLs | 333 |
| Overall CRL Rate | 17.5% |
| Year Coverage | 2002 - 2026 |
| Unique Companies | 617 |

---

## Dataset Composition

### By Era
| Period | Events | Approvals | CRLs | CRL Rate |
|--------|--------|-----------|------|----------|
| Pre-2020 | 555 | 404 | 151 | 27.2% |
| 2020-2026 | 1351 | 1169 | 182 | 13.5% |

### By Source
| Source | Events | Description |
|--------|--------|-------------|
| rule_based_v1 | 1093 | Unknown |
| FDA_NME_COMPILATION | 404 | FDA NME approval compilation |
| web_verified_v2 | 176 | Unknown |
| FDA_CRL_Database | 151 | Unknown |
| web_search_batch1 | 70 | Unknown |
| web_search_batch2 | 10 | Unknown |
| FDA_CRL_DB_2025 | 1 | Unknown |
| FDA_CRL_DB_2026 | 1 | Unknown |

---

## Therapeutic Area Analysis (2020+ Unbiased)

| Therapeutic Area | Events | CRLs | CRL Rate | Risk Tier |
|------------------|--------|------|----------|-----------|
| Pain Management | 31 | 13 | 41.9% | HIGH |
| Hematology | 14 | 5 | 35.7% | HIGH |
| Nephrology | 29 | 9 | 31.0% | HIGH |
| Ophthalmology | 34 | 9 | 26.5% | HIGH |
| CNS/Neurology | 96 | 23 | 24.0% | MODERATE |
| Cardiovascular | 42 | 9 | 21.4% | MODERATE |
| Metabolic/Endocrine | 30 | 6 | 20.0% | MODERATE |
| Rare Disease | 68 | 12 | 17.6% | MODERATE |
| Other | 315 | 48 | 15.2% | MODERATE |
| Immunology | 85 | 10 | 11.8% | LOW |
| Dermatology | 19 | 2 | 10.5% | LOW |
| Oncology | 401 | 30 | 7.5% | LOW |
| GI/Hepatology | 15 | 1 | 6.7% | LOW |
| Respiratory | 23 | 1 | 4.3% | LOW |
| Infectious Disease | 132 | 4 | 3.0% | LOW |
| Vaccines | 10 | 0 | 0.0% | LOW |
| Women's Health | 7 | 0 | 0.0% | LOW |

---

## Year-by-Year Breakdown

| Year | Approvals | CRLs | Total | CRL Rate |
|------|-----------|------|-------|----------|
| 2002 | 0 | 1 | 1 | 100.0% |
| 2004 | 0 | 1 | 1 | 100.0% |
| 2007 | 0 | 1 | 1 | 100.0% |
| 2008 | 0 | 1 | 1 | 100.0% |
| 2009 | 26 | 1 | 27 | 3.7% |
| 2010 | 21 | 2 | 23 | 8.7% |
| 2011 | 30 | 2 | 32 | 6.2% |
| 2012 | 39 | 1 | 40 | 2.5% |
| 2013 | 27 | 10 | 37 | 27.0% |
| 2014 | 41 | 8 | 49 | 16.3% |
| 2015 | 45 | 9 | 54 | 16.7% |
| 2016 | 22 | 19 | 41 | 46.3% |
| 2017 | 46 | 25 | 71 | 35.2% |
| 2018 | 59 | 33 | 92 | 35.9% |
| 2019 | 48 | 37 | 85 | 43.5% |
| 2020 | 160 | 30 | 190 | 15.8% |
| 2021 | 188 | 31 | 219 | 14.2% |
| 2022 | 149 | 27 | 176 | 15.3% |
| 2023 | 217 | 41 | 258 | 15.9% |
| 2024 | 249 | 27 | 276 | 9.8% |
| 2025 | 204 | 24 | 228 | 10.5% |
| 2026 | 2 | 2 | 4 | 50.0% |

---

## Designation Stack Analysis (2020+ Unbiased)

| Designation | Events w/ | Approval Rate | Description |
|-------------|-----------|---------------|-------------|
| BTD | 244 | 94.7% | Expedited pathway |
| Orphan | 332 | 88.6% | Expedited pathway |
| Priority Review | 619 | 90.1% | Expedited pathway |
| Fast Track | 485 | 90.7% | Expedited pathway |

---

## Data Quality Notes

1. **Pre-2020 Data Sources:**
   - CRLs: FDA CRL Transparency Database (400 records, 2002-2025)
   - Approvals: FDA NME Compilation (404 records, 2009-2019)

2. **Potential Biases:**
   - Pre-2020 CRLs may be incomplete for early years
   - BTD designation only available from 2012+
   - Some designations N/A for historical events

3. **T-1 Compliance:**
   - All features use pre-decision information
   - data_cutoff_date set to catalyst_date - 1 day
   - No post-decision CRL reasons used for features

4. **Recommended Usage:**
   - Primary training: 2020-2026 data (1,351 events, balanced)
   - Supplementary: 2009-2019 data (555 events, higher CRL rate)
   - CRL rate calculation: Use 2020+ only (13.5%)

---

## Files Generated

| File | Description |
|------|-------------|
| ODIN_ENRICHED_PDUFA_v4.csv | Final enriched dataset (1,906 events) |
| fda_crl_enrichment.csv | Raw FDA CRL data (400 records) |
| fda_pre2020_approvals.csv | Raw FDA NME approvals (404 records) |
| pre_2020_approvals_odin.csv | ODIN-formatted pre-2020 approvals |
| pre_2020_crls_enrichment.csv | ODIN-formatted pre-2020 CRLs |

---

## Enrichment Impact

- **Dataset size:** +557 events (+41% from original 1,349)
- **Historical coverage:** Extended from 2020-2026 to 2002-2026
- **CRL examples:** +153 additional CRL cases for training
- **Approval examples:** +404 additional approval cases

