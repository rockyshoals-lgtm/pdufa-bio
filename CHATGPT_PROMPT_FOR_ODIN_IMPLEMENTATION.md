# ChatGPT Prompt for ODIN v8.12 Implementation

---

## COPY EVERYTHING BELOW THIS LINE AND PASTE INTO CHATGPT

---

You are implementing critical remediation for ODIN (Outcome Determination Intelligence Network), a biotech PDUFA prediction model. A multi-AI audit has confirmed a severe T-1 compliance violation that must be fixed before production deployment.

## CRITICAL BACKGROUND

**What happened:** The `manufacturing_risk` feature in ODIN v8.11 appears to have an 11.5x predictive lift for identifying CRLs. However, forensic analysis proved this feature is **derived from post-decision CRL notes** (checking if "CMC" appears in the CRL reason), NOT from legitimate pre-PDUFA inspection data.

**Why it matters:** This is data leakage. The model "knows" the outcome before making predictions. In production, this feature will be worthless because we won't have CRL notes before the FDA decision.

**Evidence of leakage:**
- 136 of 180 CRLs have `manufacturing_risk=True` (perfectly matches CMC-attributed CRLs)
- 149 approvals also flagged True (false positives from biosimilars with complex manufacturing)
- The `form_483_issues` column (which should contain real inspection data) is completely EMPTY
- The enrichment source is "rule_based_v1" which used outcome labels to derive the flag

## YOUR TASK

Implement the remediation plan in the attached `ODIN_CHATGPT_IMPLEMENTATION_PACKAGE.md` document. This includes:

### Phase 1: Immediate Config Patch (TODAY)
1. Disable the leaked `manufacturing_risk` feature by setting weights to 0.0
2. Add audit trail documentation to the config

### Phase 2: FDA API Integration (Week 1)
1. Set up FDA Data Dashboard API client (requires registration)
2. Implement T-1 compliant inspection data retrieval
3. Build the `ODINManufacturingRiskCalculator` class

### Phase 3: New Signal Implementation (Week 2)
1. Implement `s21_form_483_oai` - OAI inspection flag
2. Implement `s22_cmc_citations` - CMC citation density
3. Implement `s23_inspection_trend` - inspection track record

### Phase 4: Dataset Enrichment (Week 2-3)
1. Backfill inspection data for all 1,349 PDUFA events
2. Validate T-1 compliance (all inspection dates < PDUFA dates)
3. Run validation against known test cases

### Phase 5: Re-optimization (Week 3-4)
1. Re-run Optuna with new legitimate features
2. Validate performance drop is within acceptable range
3. Document new baseline metrics

## EXPECTED PERFORMANCE AFTER FIX

| Metric | v8.11 (Leaked) | v8.12 (Clean) | Acceptable? |
|--------|----------------|---------------|-------------|
| F1 Score | 0.93 | ~0.85 | ✓ Yes |
| Precision | 0.96 | ~0.94 | ✓ Yes |
| Recall | 0.90 | ~0.78 | ✓ Yes |
| Specificity | 75.6% | ~30% | ⚠️ Expected major drop |

**The v8.12 performance represents REAL predictive signal.** The v8.11 numbers were artificially inflated by data leakage.

## KEY CONSTRAINTS

1. **T-1 Compliance is NON-NEGOTIABLE**: Every feature must use only data available BEFORE the PDUFA decision date
2. **FDA API Registration Required**: The Data Dashboard API requires credentials from FDA - apply at https://datadashboard.fda.gov/oii/api/index.htm
3. **Audit Trail**: Document all changes with timestamps and rationale
4. **Preserve Existing Signals**: Only modify the manufacturing_risk signal; leave all other signals intact

## DELIVERABLES

Please produce:

1. **Updated config file** (`ODIN_v812_CONFIG.json`) with disabled leaked feature and new signal definitions

2. **Python implementation** of:
   - `FDADataDashboardClient` class
   - `ODINManufacturingRiskCalculator` class  
   - `enrich_pdufa_dataset()` function

3. **Enriched dataset** with new columns:
   - `form_483_oai_flag`
   - `oai_count_pre_pdufa`
   - `cmc_citation_count`
   - `mfg_risk_score`
   - `mfg_risk_level`
   - `s21_form_483_oai`
   - `s22_cmc_citations`
   - `s23_inspection_trend`

4. **Validation report** confirming:
   - T-1 compliance for all new features
   - Test case results for known CMC CRLs
   - False positive reduction for biosimilar approvals

## ATTACHED DOCUMENT

The complete implementation package is attached as `ODIN_CHATGPT_IMPLEMENTATION_PACKAGE.md`. This contains:
- Full Python code for FDA API clients
- API endpoint documentation
- Field definitions
- Test cases
- Registration instructions

Please begin by reviewing the document and confirming you understand the task. Then proceed with Phase 1 (config patch) first.

---

## END OF CHATGPT PROMPT

---

# Instructions for David:

1. **Copy everything between the "COPY" lines above**
2. **Attach the `ODIN_CHATGPT_IMPLEMENTATION_PACKAGE.md` file** when pasting the prompt
3. **If ChatGPT needs the current dataset**, also attach `ODIN_ENRICHED_PDUFA_1349_v2.csv`
4. **For FDA API registration**, ChatGPT will need you to manually:
   - Register at https://datadashboard.fda.gov/oii/api/index.htm
   - Provide the credentials when received (typically 1-3 business days)

## Alternative: If FDA API Credentials Take Too Long

ChatGPT can implement a fallback strategy using:
1. OpenFDA enforcement API (no registration, immediate access)
2. SEC EDGAR for disclosed 483s in company filings
3. FDA Inspection Observations Excel downloads (manual download required)

Ask ChatGPT: "Implement the fallback strategy while we wait for FDA API credentials"
