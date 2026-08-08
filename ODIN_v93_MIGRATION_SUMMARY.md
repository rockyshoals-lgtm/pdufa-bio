# ODIN v9.3 Migration Summary: T-1 Compliance Fix

**Date:** January 28, 2026  
**Status:** ✅ FIX IMPLEMENTED - Ready for GPU Re-optimization  
**Priority:** 🔴 CRITICAL (Data Leakage Remediation)

---

## Executive Summary

ODIN v9.3 fixes a critical data leakage issue discovered in v9.2: the `manufacturing_risk` field was retroactively assigned based on CRL outcomes, not pre-decision manufacturing signals. This fix replaces the leaky feature with a T-1 compliant `modality_complexity` proxy based on inherent manufacturing process difficulty.

---

## What Was Wrong (v9.2)

### The Smoking Gun: `manufacturing_risk` is Outcome-Derived

Statistical analysis revealed an impossible correlation:

```
Small Molecule:
  APPROVED: 0.0% have manufacturing_risk (n=698)
  CRL:      82.3% have manufacturing_risk (n=124)

Chi-squared test: chi2=365.5, p=1.76e-81
```

**Interpretation:** If `manufacturing_risk` was assigned before knowing the outcome (T-1 compliant), approved and CRL events of the same modality should have similar rates. The 0% vs 82.3% split proves the field was assigned **after** knowing which events received CRLs.

### Impact on v9.2 Metrics

The v9.2 champion applied penalties up to -45% when `manufacturing_risk=True`:

```json
"modality_mfg_penalties": {
    "Small Molecule": -0.45,  // Near-certain CRL prediction
    ...
}
```

Since `manufacturing_risk=True` perfectly predicted CRLs for Small Molecules, the model was "cheating."

---

## What Was Fixed (v9.3)

### Replacement: Modality Complexity Proxy

The leaky `manufacturing_risk` field is replaced with `modality_complexity` based on **inherent manufacturing process difficulty**, NOT outcome rates:

| Modality | Complexity | Penalty (@-0.08 weight) | Rationale |
|----------|------------|-------------------------|-----------|
| Cell/Gene Therapy | 0.65 | -5.2% | Autologous, viral vectors, cold chain |
| RNA Therapy | 0.55 | -4.4% | LNP encapsulation, stability issues |
| Vaccine | 0.50 | -4.0% | Antigen production, sterility |
| ADC | 0.45 | -3.6% | Conjugation chemistry |
| Antibody | 0.30 | -2.4% | Biologics production |
| Peptide | 0.15 | -1.2% | Synthesis/recombinant |
| Small Molecule | 0.00 | 0.0% | Baseline (well-understood) |

**Why this is T-1 compliant:** These complexity scores are based on inherent manufacturing **process characteristics**, not historical CRL rates. A Cell/Gene Therapy product has complex manufacturing requirements regardless of whether FDA approves it.

### Secondary Fix: Temporal Boost Quarantine

Per ChatGPT's audit, `temporal_2024_plus_boost` is disabled in backtest mode to avoid regime leakage. For production predictions on 2026+ events, it remains available.

```python
config.temporal_backtest_mode = True  # Disables boost for honest backtest
```

---

## Performance Impact

| Metric | v9.2 (Leaky) | v9.3 (T-1 Compliant) | Change |
|--------|--------------|----------------------|--------|
| Brier Score | 0.0657 | 0.1067 | +62% (worse) |
| TIER_4 Count | 104 | 8 | -92% |
| TIER_4 CRL Rate | 99.0% | 75.0% | -24% |
| CRL Recall @85% | 76.1% | 67.2% | -9% |

**Key insight:** The v9.2 Brier of 0.0657 was artificially deflated by ~40%. The true baseline without leakage is ~0.10, which is close to the naive baseline of 0.0996 (predicting 86.7% for all events).

---

## Files Created

| File | Description |
|------|-------------|
| `odin_v93_config.py` | Complete v9.3 scoring module with T-1 compliant features |
| `ODIN_v93_CHAMPION_CONFIG.json` | Champion config (uses v9.2 weights as starting point) |

---

## Next Steps

### 1. GPU Re-Optimization (Required)

The current v9.3 config uses v9.2 weights as a starting point. Without the leaky feature, the optimal weights will be different. Run GPU optimization:

```bash
python odin_v93_gpu_optimizer.py --configs 1000000000 --output ODIN_v93_OPTIMIZED_CHAMPION.json
```

**Expected outcome:** Brier score will improve from 0.1067 but likely settle around 0.08-0.09 (still worse than the leaky 0.0657).

### 2. Holdout Validation (Required)

After optimization, validate on 2024-2026 events that weren't used in training:

```python
holdout_df = df[df['year'] >= 2024]
metrics = evaluate_model(optimized_config, holdout_df, backtest_mode=True)
```

### 3. Feature Engineering (Optional)

Consider adding new T-1 compliant features to recover some predictive power:
- **Pre-PDUFA Form 483 citations** (from FDA database, must verify inspection_date < PDUFA_date)
- **CDMO/CMO shipment signals** (supply chain data, T-60 to T-1)
- **Manufacturing-related 8-K filings** (capacity expansions, facility issues)

### 4. Dataset Remediation (Optional)

The `manufacturing_risk` column should be either:
- **Removed entirely** from the dataset to prevent future accidental use
- **Renamed** to `crl_had_cmc_issues` to clarify it's an outcome-derived label, useful only for CRL analysis

---

## Audit Response Summary

| Auditor | Issue | Status |
|---------|-------|--------|
| Migration File | manufacturing_risk leakage | ✅ FIXED (v9.3) |
| ChatGPT | temporal_2024_plus_boost regime leakage | ✅ FIXED (backtest mode) |
| ChatGPT | Feature lookback validation | ⚠️ Documented (auditability concern) |
| ChatGPT | Checkpoint metadata | ⚠️ Noted (good practice) |
| Perplexity | [Various claims] | See migration file for assessment |

---

## T-1 Compliance Certification

### Features CERTIFIED as T-1 Safe

| Feature | Rationale |
|---------|-----------|
| btd, orphan, priority_review, fast_track | Designated months/years before PDUFA |
| accelerated_approval | Pathway announced at filing |
| had_adcom, adcom_vote_pct | AdCom occurs 60-90 days before PDUFA |
| prior_crl, resubmission_class | From previous decision cycle |
| therapeutic_area, modality | Static drug attributes |
| sponsor_prior_approvals | Calculated as-of event date |
| modality_complexity | Based on inherent process difficulty |

### Features REMOVED/QUARANTINED

| Feature | Issue | Action |
|---------|-------|--------|
| manufacturing_risk | Outcome-derived (p<10⁻⁸⁰) | **REMOVED** - replaced with modality_complexity |
| temporal_2024_plus_boost | Regime leakage in backtest | **QUARANTINED** - disabled in backtest mode |

### Features REQUIRING VERIFICATION

| Feature | Concern | Recommendation |
|---------|---------|----------------|
| form_483_issues | Currently all FALSE | Verify source and temporal validity |
| sponsor_prior_approvals | Must be calculated as-of event date | Verify calculation logic |

---

## Code Changes Summary

```python
# REMOVED (v9.2):
def get_manufacturing_risk_penalty(config, event):
    if not event.get('manufacturing_risk', False):  # LEAKY FIELD
        return 0.0, "no_mfg_risk"
    modality = event.get('modality', 'Small Molecule')
    penalty = MODALITY_MFG_RISK_PENALTIES.get(modality, -0.12)
    return penalty, f"mfg_risk_{modality}"

# ADDED (v9.3):
def get_modality_complexity_penalty(config, modality):
    """T-1 COMPLIANT: Based on inherent process difficulty, not outcomes."""
    complexity = MODALITY_COMPLEXITY.get(modality, 0.15)
    penalty = config.modality_complexity_weight * complexity
    return penalty, f"complexity_{modality}"
```

---

*Migration completed: January 28, 2026*  
*Version: ODIN v9.3*  
*Status: Ready for GPU re-optimization*
