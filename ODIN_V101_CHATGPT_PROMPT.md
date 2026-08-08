# ChatGPT Implementation Prompt — ODIN v10.1

**Copy this entire prompt to ChatGPT to begin implementation.**

---

## TASK

Implement ODIN v10.1 FDA PDUFA prediction model in Python. This is an upgrade from v9.1 with validated weight adjustments.

## KEY CHANGES FROM v9.1

```
BTD weight:      0.06 → 0.12  (96.3% approval validated, p<0.0001)
Orphan weight:   0.04 → 0.10  (92.8% approval validated)
Ophthalmology:  -0.13 → -0.25 (30.4% CRL rate - highest)
Pain Mgmt:      -0.29 → -0.30 (29.5% CRL rate)
NEW S21:         N/A → +0.03  (Specialist Fund Composite)
NEW S17-S20:     N/A → ±0.02  (LunarCrush Social Signals)
```

## SCORING FORMULA

```python
prob = 0.827  # base rate

# S1-S5: Designations (additive)
prob += 0.12 if btd else 0
prob += 0.10 if orphan else 0
prob += 0.085 if priority_review else 0
prob += 0.03 if fast_track else 0
prob += 0.05 if accelerated_approval else 0

# S6-S8: AdCom
if had_adcom and adcom_vote_pct:
    if adcom_vote_pct >= 0.65: prob += 0.08
    elif adcom_vote_pct >= 0.50: prob -= 0.06
    else: prob -= 0.19

# S9-S11: Prior CRL
if prior_crl:
    prob -= 0.085
    if resubmission_class == 1: prob += 0.157
    elif resubmission_class == 2: prob -= 0.05

# S12-S13: Sponsor
if sponsor_prior_approvals >= 5: prob += 0.05
elif sponsor_prior_approvals == 0: prob -= 0.07

# S14-S15: Manufacturing
if manufacturing_risk: prob -= 0.12
if form_483_issues: prob -= 0.07

# S16: Therapeutic Area (multiply by 0.83)
ta_adj = TA_ADJUSTMENTS.get(therapeutic_area, 0) * 0.83
prob += ta_adj

# S21: Specialist Composite (if 2+ signals)
specialist_count = sum([btd, orphan, ta in ['Rare Disease','Oncology'], stack>=3])
if specialist_count >= 2: prob += 0.03

# Clamp
prob = max(0.01, min(0.99, prob))

# Tier
if prob >= 0.858: tier = 'TIER_1'
elif prob >= 0.734: tier = 'TIER_2'
elif prob >= 0.578: tier = 'TIER_3'
else: tier = 'TIER_4'  # 85.7% CRL rate!
```

## THERAPEUTIC AREA ADJUSTMENTS

```python
TA_ADJUSTMENTS = {
    "Pain Management": -0.30,
    "Ophthalmology": -0.25,
    "Nephrology": -0.22,
    "Hematology": -0.18,
    "CNS/Neurology": -0.10,
    "Cardiovascular": -0.08,
    "Metabolic/Endocrine": -0.07,
    "Other": -0.06,
    "Rare Disease": -0.04,
    "Immunology": +0.02,
    "Dermatology": +0.03,
    "Oncology": +0.06,
    "GI/Hepatology": +0.07,
    "Respiratory": +0.09,
    "Infectious Disease": +0.10,
    "Vaccines": +0.13,
    "Women's Health": +0.13,
}
```

## VALIDATION TARGETS

| Metric | Target |
|--------|--------|
| Brier Score | ≤ 0.085 |
| TIER_1 Approval | ≥ 95% |
| TIER_4 CRL Rate | ≥ 80% |

## DELIVERABLES

1. `odin_v101.py` — Main scoring module with `score_pdufa_event()` function
2. `odin_v101_config.json` — Exportable config
3. Unit tests for edge cases
4. Batch scoring function for DataFrame input

## TEST CASES

```python
# Test 1: BTD + Oncology should be TIER_1 (>90% prob)
event1 = {'btd': True, 'orphan': True, 'therapeutic_area': 'Oncology', 
          'sponsor_prior_approvals': 10, 'designation_stack_count': 3}
# Expected: TIER_1, prob > 0.95

# Test 2: Pain Management no designations should be TIER_3/4
event2 = {'btd': False, 'orphan': False, 'therapeutic_area': 'Pain Management',
          'sponsor_prior_approvals': 2, 'designation_stack_count': 0}
# Expected: TIER_3 or TIER_4, prob < 0.65
```

## FILES PROVIDED

- `ODIN_V101_CHATGPT_ENGINEERING_SPEC.md` — Full specification
- `ODIN_V101_CONFIG.json` — JSON config to import
- `ODIN_ENRICHED_PDUFA_v4_2_AUDITED.csv` — 1,934 event dataset

Begin implementation. Ask clarifying questions if needed.
