
================================================================================
    ODIN DATASET v4.2 AUDITED - COMPREHENSIVE AUDIT REPORT
================================================================================
Generated: 2026-02-02
Dataset: ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv

================================================================================
EXECUTIVE SUMMARY
================================================================================

Total Records:    1,934 events
Approval Rate:    82.8% (1,601 approvals)  
CRL Rate:         17.2% (333 CRLs)
Date Range:       2002-2026
Primary Sources:  rule_based_v1 (1,093), FDA_NME_COMPILATION (404), 
                  web_verified_v2 (176), FDA_CRL_Database (151)

OVERALL GRADE: ⚠️  NEEDS REMEDIATION

The dataset contains significant data quality issues that MUST be addressed
before production use. See CRITICAL ISSUES below.

================================================================================
🚨 CRITICAL ISSUES (MUST FIX)
================================================================================

1. MANUFACTURING_RISK DATA LEAKAGE
   -----------------------------------------------------------------
   Status: CRITICAL - T-1 COMPLIANCE VIOLATION
   
   Finding: manufacturing_risk=True has 61.9% CRL rate vs 5.9% baseline
            Predictive lift: 10.5x (impossible for legitimate T-1 feature)
   
   Root Cause: 27% of manufacturing_risk flags (106/391) come from 
               FDA_CRL_Database where the flag is derived from post-decision
               CRL reason text (e.g., "Manufacturing/CMC").
   
   Impact: Inflates model performance artificially; will not generalize
           to prospective predictions.
   
   REQUIRED FIX:
   - Remove manufacturing_risk column OR
   - Re-derive using only T-1 compliant sources (Form 483, EMA CMC flags)
   - Document derivation methodology

2. PRIOR_CRL FIELD MISUSE
   -----------------------------------------------------------------
   Status: CRITICAL - LOGICAL ERROR
   
   Finding: All 151 records with prior_crl=True have outcome=CRL (100%)
            Expected: Class I resubmissions have ~90%+ approval rate
   
   Root Cause: Field set to True for records from FDA_CRL_Database.
               These ARE the CRL events, not resubmissions of prior CRLs.
   
   Impact: prior_crl cannot be used as a predictive feature in current form.
   
   REQUIRED FIX:
   - Rename field to "is_crl_database_record" OR
   - Match CRL records to their subsequent resubmission outcomes
   - Correct resubmission_class logic accordingly

3. FIRST_CYCLE FIELD CORRUPTION
   -----------------------------------------------------------------
   Status: CRITICAL - LOGICAL IMPOSSIBILITY
   
   Finding: first_cycle=True for ALL 1,934 records (100%)
            BUT prior_crl=True for 151 records
            
   Impact: Resubmissions cannot logically be first_cycle=True
   
   REQUIRED FIX:
   - Set first_cycle=False where prior_crl=True OR
   - Remove first_cycle column entirely

4. CONFLICTING OUTCOME DUPLICATES
   -----------------------------------------------------------------
   Status: CRITICAL - DATA CORRUPTION
   
   Finding: 3 event_ids have BOTH CRL and APPROVAL outcomes:
   - SAGE|Zuranolone (SAGE-217)|PDUFA|2023-08-04
   - BIIB|Zuranolone (SAGE-217)|PDUFA|2023-08-04  
   - RYTM|IMCIVREE (setmelanotide)|PDUFA|2022-06-16
   
   REQUIRED FIX:
   - Research actual outcomes and remove incorrect records
   - Note: Zuranolone was APPROVED for PPD, CRL for MDD (different indications)
   - Split into separate event_ids if multiple indications

================================================================================
⚠️  HIGH PRIORITY ISSUES
================================================================================

5. ERA BIAS
   -----------------------------------------------------------------
   Status: HIGH - WILL BIAS MODEL
   
   Finding: CRL rates vary dramatically by era:
   - 2015-2019: 35.9% CRL rate (n=343)
   - 2020-2022: 15.0% CRL rate (n=585)
   - 2023+:     11.8% CRL rate (n=794)
   - Pre-2015:  13.2% CRL rate (n=212)
   
   Root Cause: 2015-2019 period heavily influenced by FDA_CRL_Database
               which only contains CRL events.
   
   RECOMMENDED FIX:
   - Apply era weighting during training
   - Consider excluding 2015-2019 or downweighting
   - Document era-specific baseline rates

6. RNA THERAPY MODALITY BIAS
   -----------------------------------------------------------------
   Status: HIGH - MISLEADING SIGNAL
   
   Finding: RNA Therapy shows 55.6% CRL rate (50/90)
            BUT 94% of CRLs (47/50) come from FDA_CRL_Database
   
   Impact: True RNA Therapy CRL rate is likely ~7-10% (per web-sourced data)
   
   RECOMMENDED FIX:
   - Calculate modality-specific rates using only balanced sources
   - Flag modality rates as potentially biased for CRL-database modalities

7. DUPLICATE EVENT_IDS
   -----------------------------------------------------------------
   Status: MEDIUM - DATA HYGIENE
   
   Finding: 8 event_ids appear multiple times (16 total records)
   
   Categories:
   - Same outcome duplicates (5): Likely co-development partners
   - Conflicting outcome duplicates (3): See Critical Issue #4
   
   RECOMMENDED FIX:
   - Deduplicate same-outcome records (keep one per event_id)
   - Resolve conflicting outcomes per Critical Issue #4

8. ENRICHMENT_CONFIDENCE CASING
   -----------------------------------------------------------------
   Status: LOW - DATA HYGIENE
   
   Finding: Mixed casing: "Medium" (1,238) vs "MEDIUM" (151)
                          "High" (111) vs "HIGH" (434)
   
   RECOMMENDED FIX:
   - Normalize to uppercase: df['enrichment_confidence'].str.upper()

================================================================================
FIELD-BY-FIELD T-1 COMPLIANCE AUDIT
================================================================================

| Field                    | T-1 Safe | Notes                                |
|--------------------------|----------|--------------------------------------|
| btd                      | ✅ YES   | Designated before PDUFA              |
| orphan                   | ✅ YES   | Designated before PDUFA              |
| priority_review          | ✅ YES   | Assigned with PDUFA date             |
| fast_track               | ✅ YES   | Designated before PDUFA              |
| accelerated_approval     | ✅ YES   | Pathway known before decision        |
| designation_stack_count  | ✅ YES   | Derived from T-1 safe designations   |
| had_adcom                | ✅ YES   | AdCom occurs before PDUFA            |
| adcom_vote_pct           | ✅ YES   | Votes recorded before decision       |
| prior_crl                | ⚠️ MISUSE| Field semantics are wrong            |
| resubmission_class       | ⚠️ MISUSE| Only valid if prior_crl fixed        |
| first_cycle              | 🔴 CORRUPT| 100% True is impossible              |
| form_483_issues          | ✅ YES   | Inspections occur before decision    |
| manufacturing_risk       | 🔴 LEAKAGE| Derived from post-decision CRL text  |
| sponsor_prior_approvals  | ✅ YES   | Historical count before event        |
| experienced_sponsor      | ✅ YES   | Derived from prior_approvals         |
| therapeutic_area         | ✅ YES   | Known at filing                      |
| modality                 | ✅ YES   | Known at filing                      |

================================================================================
SIGNAL VALIDATION SUMMARY
================================================================================

| Signal                  | CRL w/   | CRL w/o  | Lift  | Status        |
|-------------------------|----------|----------|-------|---------------|
| BTD                     | 3.7%     | 19.9%    | 5.4x  | ✅ VALID      |
| Orphan                  | 7.2%     | 20.8%    | 2.9x  | ✅ VALID      |
| Priority Review         | 7.0%     | 25.4%    | 3.6x  | ✅ VALID      |
| Fast Track              | 7.0%     | 22.2%    | 3.2x  | ✅ VALID      |
| Experienced Sponsor     | 4.7%     | 19.0%    | 4.0x  | ✅ VALID      |
| Manufacturing Risk      | 61.9%    | 5.9%     | 10.5x | 🔴 LEAKAGE    |
| Had AdCom               | 0.0%     | 17.7%    | ∞     | ⚠️ SMALL N=49 |
| Prior CRL               | 100%     | 10.2%    | 9.8x  | 🔴 CORRUPT    |

================================================================================
RECOMMENDATIONS
================================================================================

IMMEDIATE (Before any model training):
1. Remove or rebuild manufacturing_risk column
2. Remove first_cycle column (or fix logic)
3. Remove or rename prior_crl column
4. Remove 3 conflicting duplicate records
5. Deduplicate 5 same-outcome duplicates

SHORT-TERM (Data enrichment):
1. Match CRL records to subsequent resubmission outcomes
2. Apply era weights for 2015-2019 oversampling
3. Normalize enrichment_confidence casing

DOCUMENTATION:
1. Document source of each record type
2. Flag modality/TA rates as potentially biased
3. Create T-1 compliance certification for each field

================================================================================
RECORDS TO REMOVE (16 total)
================================================================================

Same-outcome duplicates (5 records - keep 1 each):
- IONS|WAINUA (eplontersen)|PDUFA|2023-12-22 (2 records)
- AZN|WAINUA (eplontersen)|PDUFA|2023-12-22 (2 records)
- LLY|RETEVMO (Selpercatinib)|PDUFA|2022-09-21 (2 records)
- ABBV|RINVOQ (Upadacitinib)|PDUFA|2022-01-14 (2 records)
- TGTX|UKONIQ (umbralisib)|PDUFA|2021-02-05 (2 records)

Conflicting duplicates (6 records - research required):
- SAGE|Zuranolone (SAGE-217)|PDUFA|2023-08-04 (CRL + APPROVAL)
- BIIB|Zuranolone (SAGE-217)|PDUFA|2023-08-04 (CRL + APPROVAL)
- RYTM|IMCIVREE (setmelanotide)|PDUFA|2022-06-16 (CRL + APPROVAL)

================================================================================
COMPARISON TO PREVIOUS DATASET (1,349 records)
================================================================================

| Metric              | v4.2 (1,934) | Previous (1,349) | Delta   |
|---------------------|--------------|------------------|---------|
| Total Records       | 1,934        | 1,349            | +585    |
| Approval Rate       | 82.8%        | 86.7%            | -3.9%   |
| CRL Rate            | 17.2%        | 13.3%            | +3.9%   |
| CRL Database Recs   | 151          | ~0               | +151    |
| Pre-2020 Records    | 424          | ~300             | +124    |

The lower approval rate in v4.2 is driven by:
1. Addition of 151 FDA_CRL_Database records (all CRLs)
2. Expansion of 2015-2019 era with higher CRL rates

================================================================================
END OF AUDIT REPORT
================================================================================
