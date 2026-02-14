# ODIN v10.68 Comprehensive Audit — Progress Checkpoint

**Last Updated:** 2026-02-14T16:00:00Z
**Session:** Comprehensive historical audit + Round 5 proposal
**Repo:** https://github.com/rockyshoals-lgtm/pdufa-bio
**Access Code:** 1U670NnGEhN6!Hv4Z7tJOd5Z%I9h

---

## COMPLETED WORK

### 1. Engine Validation (DONE ✅)
- Extracted full ODIN v10.68 engine from App.jsx
- 51 parameters across 7 signal categories
- Logistic regression: `logit = 1.3957 + Σ(signal_weights)`, `prob = sigmoid(logit)`
- Tier thresholds: T1 >85%, T2 70-85%, T3 60-70%, T4 <60%
- **Result:** Engine math is 100% correct — all 57 catalysts rescore to within 0.06% of stored values
- Regression test script: `rescore_v2.js` in repo root

### 2. Verified Wins Cross-Check (DONE ✅)
- Source: `ODIN_VERIFIED_WINS_MOMENTUM_ANALYSIS.md` (user uploaded)
- 16 total events (12 traded, 3 CRL avoids, 1 no data)
- Original prediction accuracy: 15/15 (100%) directional calls correct
- Cumulative return on 12 trades: +894%

### 3. Score Drift Analysis (DONE ✅)
- **CRITICAL REGRESSIONS FOUND:**
  - CAPR: originally 75% → now 40.8% (TIER_4) — would AVOID our biggest winner (+404%)
  - ASND: originally 58% → now 92.9% (TIER_1) — would BUY but was correctly avoided
  - AZN/Benralizumab: 92% → 65% (still directionally correct)
  - NVO/Semaglutide: 95% → 84.9% (still correct)
- 10 of 15 verified tickers MISSING from current DB (past events removed after resolution)
- Directional accuracy on 5 still in DB: 5/5 match but scores have drifted

### 4. RGNX CRL Research (DONE ✅)
- RGX-121 (clemidsogene lanparvovec) - gene therapy for MPS II
- CRL issued Feb 7, 2026
- FDA concerns: patient population definition, external control validity, CSF HS D2S6 surrogate endpoint skepticism
- Clinical hold in Jan 2026 (CNS tumor in sister program RGX-111)
- Pivotal trial: NCT03566043, n=48 (13 pivotal), single-arm, open-label
- ODIN correctly scored at 45% and avoided

### 5. IRON/Bitopertin CRL (DONE ✅)
- Already documented in verification/ directory
- CRL Feb 13, 2026
- Post-mortem drove Round 4 signal additions

---

## IN PROGRESS

### 6. Comprehensive Historical Event Pull (IN PROGRESS 🔄)

Building complete universe of ALL FDA PDUFA/catalyst events from Sept 1, 2025 through Feb 14, 2026.

#### Events Already Researched:

| # | Ticker | Drug | Event Type | Date | Outcome | ODIN Score (Original) | In Current DB? | Research Status |
|---|--------|------|-----------|------|---------|----------------------|----------------|-----------------|
| 1 | ARWR | Redemplo (plozasiran) | PDUFA | Nov 18, 2025 | APPROVED | 91% | NO | ✅ Done |
| 2 | SNDX | Revuforj (revumenib) | PDUFA | Oct 24, 2025 | APPROVED | 85% | NO | ✅ Done |
| 3 | CYTK | Myqorzo (aficamten) | PDUFA | Dec 19, 2025 | APPROVED | 92% | NO | ✅ Done |
| 4 | BHVN | Troriluzole/VYGLXIA | PDUFA | Nov 4, 2025 | CRL | 38% | NO | ✅ Done |
| 5 | MIST | Cardamyst (etripamil) | PDUFA | Dec 12, 2025 | APPROVED (post-CRL resubmit) | 72% | NO | ✅ Done |
| 6 | AGIO | Aqvesme (mitapivat) | PDUFA | Dec 23, 2025 | APPROVED | 82% | NO | ✅ Done |
| 7 | AMRX | Boncresa (denosumab-mobz) | PDUFA | Dec 22, 2025 | APPROVED (biosimilar) | 85% | NO | ✅ Done |
| 8 | TOVX | VCN-01 | Data Readout | ~Nov 2025 | POSITIVE | 72% | NO | ✅ Done |
| 9 | CAPR | Deramiocel (CAP-1002) | PDUFA | ~Nov 2025 | APPROVED | 75% (orig), 40.8% (current) | YES (regressed) | ✅ Done |
| 10 | KURA | Komzifti (ziftomenib) | PDUFA | ~Nov 2025 | APPROVED | 88% | NO | ✅ Done |
| 11 | ARCT/ARQT | Zoryve (roflumilast) | sNDA | ~Dec 2025 | APPROVED | 90% | NO | ✅ Done |
| 12 | NVO | Oral Wegovy (semaglutide) | sNDA | ~Dec 2025 | APPROVED | 95% (orig), 84.9% (current) | YES (drifted) | ⏳ Need details |
| 13 | AZN | Tezspire (tezepelumab) | sNDA/PDUFA | ~Q4 2025 | APPROVED | 92% (orig), 65% (current) | YES (drifted) | ⏳ Need details |
| 14 | RGNX | RGX-121 | PDUFA | Feb 7, 2026 | CRL | 45% | YES | ✅ Done |
| 15 | ASND | TransCon hGH | PDUFA | ~Q4 2025 | DELAYED | 58% (orig), 92.9% (current) | YES (regressed) | ✅ Done |
| 16 | IRON | Bitopertin | PDUFA | Feb 13, 2026 | CRL | 35.7% | YES | ✅ Done |

#### Events Still To Find:
- Need to search for ALL other PDUFA dates in Sept-Feb 2026 window that ODIN didn't cover
- FDA approval calendar, BioPharma Catalyst, FDA website
- Must identify blind spots (events we didn't score at all)

---

## PENDING WORK

### 7. Score Every Historical Event Through v10.68
- Reconstruct signal profiles for all 10 missing tickers
- Run through current engine
- Compare to original predictions

### 8. Calculate Directional Accuracy
- Across ALL events (not just verified wins)
- Identify false positives (scored high, got CRL)
- Identify false negatives (scored low, got approved)

### 9. Post-Mortem Every Miss
- What signals fired incorrectly?
- What signals were missing?
- Root cause for CAPR regression (form_483 signal?)
- Root cause for ASND regression (which new signals inflated it?)

### 10. Propose Round 5 Signal Changes
- Fix CAPR/ASND regression
- Add special situation flags (CRL recovery, data read, platform)
- Consider binary BUY/AVOID classification vs percentage
- Shift default entry from T-25 to T-30
- Add transformational approval flag for post-binary hold

### 11. Commit Everything to Repo
- Verified wins documentation (canonical)
- Comprehensive audit results
- Round 5 proposals
- Updated regression test

---

## KEY FILES

| File | Location | Purpose |
|------|----------|---------|
| App.jsx | src/App.jsx | Main source of truth — all catalysts + engine |
| rescore_v2.js | repo root | Regression test script |
| IRON CRL | verification/IRON-bitopertin-CRL-2026-02-13.json | IRON outcome record |
| IRON Post-Mortem | verification/IRON-bitopertin-POSTMORTEM-2026-02-13.json | IRON analysis |
| Verified Wins | uploads/ODIN_VERIFIED_WINS_MOMENTUM_ANALYSIS.md | User's verified wins file |
| This File | ODIN_AUDIT_PROGRESS.md | Progress checkpoint |

---

## ODIN v10.68 ENGINE REFERENCE

### Base Logit: 1.3957

### Signal Weights (all 51):
```
REGULATORY DESIGNATIONS:
  BTD: +0.1676, orphan: +0.1469, fast_track: +0.0888
  priority_review: +0.1053, RMAT: +0.15, accelerated_approval: +0.12

SPONSOR & APPLICATION:
  experienced_sponsor: +0.9387, inexperienced_sponsor: -1.2875
  prior_approval: +0.3, prior_CRL: -3.3533
  resubmission_post_CRL: +1.5, advisory_committee_favorable: +0.8212
  advisory_committee_unfavorable: -1.5069

THERAPEUTIC AREA RISK:
  ta_low_risk: +0.1531, ta_moderate_risk: -0.0532, ta_high_risk: -0.2555
  ta_very_high_risk: -0.5

CMC/MANUFACTURING:
  form_483: -1.3552, import_alert: -0.8
  manufacturing_warning: -0.5, cGMP_violation: -0.6

ENDPOINT QUALITY:
  primary_endpoint_met: +0.45, primary_endpoint_missed: -1.8
  surrogate_only: -0.45, biomarker_primary: -0.3
  PRO_endpoint: -0.15, composite_endpoint: -0.1

COMPETITIVE LANDSCAPE:
  first_in_class: +0.45, unmet_need: +0.55
  crowded_market: -0.2, designation_stack: +0.35

ADVANCED/INTERACTION SIGNALS:
  novice_high_risk_ta: -0.4071
  experienced_low_risk: +0.2
  interaction_inexperienced_mfg: -0.5
  interaction_prior_crl_mfg: -0.7
  accelerated_approval_non_onc: -0.30
  surrogate_clinical_disconnect: -0.35
  designation_surrogate_penalty: -0.25
  small_pivotal_n: -0.20
  single_arm_pivotal: -0.15
  cber_advanced_therapy: -0.12
  repurposed_failed_compound: -0.20
  early_action_risk: -0.15
  serial_crl_penalty: -0.50
  novel_manufacturing_platform: -0.18
  efficacy_magnitude_weak: -0.25
  post_hoc_subgroup_primary: -0.30
  safety_signal_liver: -0.35
  safety_signal_cardiac: -0.40
  competitor_crl_same_class: -0.15
```

### Tier Thresholds:
- TIER_1: prob > 0.85
- TIER_2: prob >= 0.70
- TIER_3: prob >= 0.60
- TIER_4: prob < 0.60
