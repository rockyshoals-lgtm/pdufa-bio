# ODIN HINT Integration Migration Package
## Session: 2026-01-27 | Phase 3 Complete

**Purpose:** Continue HINT backtest analysis and signal integration from where we left off

---

# EXECUTIVE SUMMARY

## What Was Accomplished This Session

1. **HINT Integration Complete** - Deep learning model for clinical trial outcome prediction integrated into ODIN
2. **Comprehensive Backtest Executed** - 16 small molecule verified wins tested
3. **Ensemble Performance Validated** - 70/30 ODIN/HINT blend achieves 87.5% accuracy
4. **Critical Finding** - HINT has approval bias; ODIN's regulatory skepticism irreplaceable for CRL detection

---

# HINT BACKTEST RESULTS (PHASE 3 COMPLETE)

## Dataset
- **Total Cases Tested:** 16 small molecules from ODIN verified wins ledger
- **Excluded Modalities:** Cell therapies, mAbs, siRNA, gene therapies, oncolytic viruses, inorganic compounds, radiopharmaceuticals, biosimilars

## Performance Summary

### HINT Standalone
| Metric | Value |
|--------|-------|
| **Overall Accuracy** | 12/16 (75.0%) |
| **Approvals Correct** | 9/9 (100.0%) |
| **CRLs/Negatives Correct** | 3/7 (42.9%) |

### ODIN + HINT Ensemble (70/30)
| Metric | Value |
|--------|-------|
| **Overall Accuracy** | 14/16 (87.5%) |
| **Approvals Correct** | 8/9 (88.9%) |
| **CRLs/Negatives Correct** | 6/7 (85.7%) |

## Calibration Analysis

| Metric | HINT | ODIN | Interpretation |
|--------|------|------|----------------|
| Avg Score (Approved) | 79.0% | 82% | Similar optimism |
| Avg Score (CRL/Neg) | 66.3% | 45% | ODIN more skeptical |
| **Separation** | 12.7% | **38%** | ODIN superior CRL detection |

---

# 16 TEST CASES - DETAILED RESULTS

## Section A: UTC-Timestamped (4 small molecules)

| ID | Ticker | Drug | Indication | HINT Score | ODIN Score | Outcome | Result |
|----|--------|------|------------|------------|------------|---------|--------|
| TS-001 | MIST | Etripamil | PSVT | 85.3% BULL | 82% | APPROVED | ✓ Both |
| TS-002 | SNDX | Revumenib | AML | 66.1% NEUT | 87% | APPROVED | ✓ Both |
| TS-004 | VNDA | Tradipitant | Motion sickness | 75.9% BULL | 55% | APPROVED | ✓ Both |
| TS-006 | CORT | Relacorilant | Cushing's | 75.9% BULL | 58% | **CRL** | ⚠️ HINT miss |

## Section B: Additional Approvals (6 small molecules)

| ID | Ticker | Drug | Indication | HINT Score | ODIN Score | Outcome | Result |
|----|--------|------|------------|------------|------------|---------|--------|
| APP-001 | KURA | Ziftomenib | NPM1 AML | 66.1% NEUT | 75% | APPROVED | ✓ Both |
| APP-003 | AGIO | Mitapivat | Thalassemia | 84.0% BULL | 89% | APPROVED | ✓ Both |
| APP-004 | CYTK | Aficamten | oHCM | 97.5% BULL | 77% | APPROVED | ✓ Both |
| APP-005 | INVA | Zoliflodacin | Gonorrhea | 76.2% BULL | 85% | APPROVED | ✓ Both |
| APP-007 | NVS | Remibrutinib | CSU | 83.8% BULL | 95% | APPROVED | ✓ Both |
| APP-008 | GILD | Lenacapavir | HIV PrEP | 76.1% BULL | 95% | APPROVED | ✓ Both |

## Section D: CRL Predictions (3 small molecules)

| ID | Ticker | Drug | Indication | HINT Score | ODIN Score | Outcome | Result |
|----|--------|------|------------|------------|------------|---------|--------|
| CRL-002 | PTCT | Vatiquinone | Friedreich ataxia | 49.1% NEUT | 31% | CRL | ✓ Both |
| CRL-005 | ALDX | Reproxalap | Dry eye | 88.2% BULL | 10% TIER_4 | **CRL** | ⚠️ HINT miss |
| CRL-007 | MITO | Elamipretide | Mitochondrial myopathy | 37.7% BEAR | 20% | CRL | ✓ **HINT bearish!** |

## Section E: CEWS Signals (3 small molecules)

| ID | Ticker | Drug | Indication | HINT Score | ODIN Score | Outcome | Result |
|----|--------|------|------------|------------|------------|---------|--------|
| CEWS-001 | BHVN | Troriluzole | Cerebellar ataxia | 86.7% BULL | 40% | **CRL** | ⚠️ HINT miss |
| CEWS-004 | AQST | Epinephrine | Anaphylaxis | 50.7% NEUT | 65% | DEFICIENCY | ✓ Both |
| CEWS-005 | TVTX | Sparsentan | FSGS | 76.0% BULL | 88% | **DELAYED** | ⚠️ Both miss (CEWS saved) |

---

# CRITICAL FINDINGS

## 1. HINT Approval Bias
HINT trained on historical clinical trial data (~60-65% approval rates) learned to be optimistic. Gives bullish signals on almost everything. ODIN's 38% separation vs HINT's 12.7% demonstrates superior regulatory skepticism.

## 2. HINT Failures (4 cases)
| Case | HINT | ODIN | Outcome | Why HINT Failed |
|------|------|------|---------|-----------------|
| CORT Relacorilant | 75.9% BULL | 58% | CRL | ODIN skepticism correct |
| ALDX Reproxalap | 88.2% BULL | **10% TIER_4** | CRL | ODIN override critical |
| BHVN Troriluzole | 86.7% BULL | 40% | CRL | ODIN skepticism correct |
| TVTX Sparsentan | 76.0% BULL | 88% | DELAYED | Both missed, CEWS saved |

## 3. HINT Value-Add Cases
- **MITO Elamipretide:** HINT 37.7% BEAR → CRL ✓ (rare bearish signal validated)
- **PTCT Vatiquinone:** HINT 49.1% NEUT → CRL ✓ (neutral signal useful)
- **100% approval accuracy** confirms HINT useful for validation of bullish ODIN calls

---

# SIGNAL INTEGRATION MATRIX

## Decision Framework

| ODIN | HINT | CEWS | Action | Confidence |
|------|------|------|--------|------------|
| >85% | >75% | Clean | **STRONG BUY** | Very High |
| >85% | <45% | Clean | **CAUTION** | Review conflict |
| 60-85% | >75% | Clean | **BUY** | High |
| 60-85% | <45% | Clean | **HOLD** | Medium |
| <60% | Any | Clean | **AVOID** | High |
| Any | Any | RED FLAG | **AVOID** | Override |

## Key Rules
1. **Keep 70/30 ensemble** - Improved overall accuracy from 75% → 87.5%
2. **HINT = approval confirmation tool**, not CRL detector
3. **ODIN's regulatory skepticism irreplaceable** - ALDX at 10%, BHVN at 40% were correct CRL calls HINT completely missed
4. **CEWS override critical** - TVTX proves when both models fail, insider/options signals catch it
5. **HINT bearish signals rare but valuable** - When HINT <40%, pay attention (MITO example)

---

# FILE LOCATIONS & TECHNICAL DETAILS

## HINT Integration
- **Integration Script:** `C:\Users\dcmoo\Documents\Python\odin_hint_integration.py`
- **Backtest Script:** `C:\Users\dcmoo\Documents\Python\hint_backtest_all_wins.py`
- **Pre-trained Weights:** `C:\Users\dcmoo\Documents\Python\hint_models\save_model\`
- **BioBERT Encoder:** `dmis-lab/biobert-base-cased-v1.1`

## ODIN Core Files
- **Dataset:** `ODIN_ENRICHED_PDUFA_1349_v2.csv` (1,349 PDUFA events)
- **Verified Wins Ledger:** `ODIN_COMPLETE_VERIFIED_WINS_LEDGER_2026-01-19.md`
- **LunarCrush Cache:** `lunarcrush_cache.json` (14/294 tickers = 4.8%)

## Model Requirements
```
torch>=2.0.0
transformers>=4.30.0
rdkit-pypi  # For SMILES processing
pubchempy   # For drug name → SMILES conversion
```

---

# NEXT STEPS (PENDING)

## Priority 1: Signal Integration
- [ ] Codify signal integration matrix into production scoring
- [ ] Create HINT score column in ODIN dataset for small molecules
- [ ] Implement HINT <40% alert system

## Priority 2: Extended Validation
- [ ] Batch process full 1,349-row ODIN dataset (small molecules only)
- [ ] Calculate HINT scores for all historical events
- [ ] Backtest ensemble on full dataset

## Priority 3: Model Improvements
- [ ] Investigate HINT retraining on FDA-specific outcomes vs clinical trial data
- [ ] Consider HINT fine-tuning on regulatory rejection patterns
- [ ] Implement CEWS override logic in production system

## Priority 4: LunarCrush Enrichment
- Continue enriching remaining 280 tickers
- Priority: LLY, AZN, AMGN, JNJ, PFE, BIIB, NVO, VRTX, GSK, NVS
- Imminent PDUFAs: APTO (Feb), INDV (Feb), GLSI (Mar), TLX (Mar)

---

# WINS LEDGER SUMMARY

**Total Verified Wins:** 28+

| Section | Count | Description |
|---------|-------|-------------|
| A (UTC-Timestamped 10/5/25+) | 8 | Primary validation set |
| B (Additional Approvals) | 8 | Extended approval wins |
| C (Pre-10/5/25) | 2 | Historical wins |
| D (CRL Predictions) | 10 | CRL detection wins |
| E (CEWS Signals) | 5 | Early warning system wins |

**Small Molecule Eligible for HINT:** 16 unique cases (18 counting section overlaps)

---

# RESUME INSTRUCTIONS

To continue this work in a new chat:

```
Continue ODIN HINT integration and backtest analysis.

Current state:
- Phase 3 COMPLETE: 16 small molecule backtest finished
- HINT standalone: 75% accuracy (100% on approvals, 43% on CRLs)
- 70/30 Ensemble: 87.5% accuracy
- Key finding: HINT has approval bias, ODIN skepticism critical for CRL detection

Next priorities:
1. Implement signal integration matrix in production
2. Batch process full ODIN dataset with HINT scores
3. Continue LunarCrush enrichment (280 tickers remaining)

Files needed:
- ODIN_HINT_MIGRATION_PACKAGE_2026-01-27.md (this document)
- ODIN_ENRICHED_PDUFA_1349_v2.csv
- lunarcrush_cache.json
- hint_backtest_all_wins.py
```

---

# APPENDIX: MODALITY FILTERING

## HINT-Eligible (Small Molecules)
- Traditional small molecule drugs
- Peptides (like elamipretide)
- Novel mechanism inhibitors/agonists

## NOT HINT-Eligible
| Modality | Examples | Reason |
|----------|----------|--------|
| Cell Therapy | CAPR Deramiocel | Different trial structure |
| mAb | OMER Narsoplimab, CSL Garadacimab | Biologic, not small molecule |
| siRNA | ARWR Plozasiran | Nucleic acid therapeutic |
| Gene Therapy | PGEN Papzimeos, RGNX RGX-121 | Viral vector delivery |
| Oncolytic Virus | TOVX VCN-01, REPL RP1 | Viral therapeutic |
| Inorganic | FBIO CUTX-101, UNCY Oxylanthanum | Not organic drug |
| Radiopharmaceutical | TLX TLX101 | Radioactive compound |
| Biosimilar | OTLK ONS-5010 | Biologic copy |

---

*Generated: 2026-01-27*
*Session: HINT Phase 3 Backtest Complete*
*Next Session: Signal Integration & Dataset Enrichment*
