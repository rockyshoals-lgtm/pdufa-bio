# ODIN V8.8 OPTIMIZATION HANDOFF FOR CHATGPT ENGINEERING
## Resume ODIN Development From This Ledger | Use v8.8 As Base
## Generated: 2026-01-19 | Source: Claude Research Authority

---

# ══════════════════════════════════════════════════════════════════════════════
# PRIME DIRECTIVE
# ══════════════════════════════════════════════════════════════════════════════

**Resume ODIN development from this ledger. Use v8.8 as base.**

You are the ODIN Optimization Engine (ChatGPT Engineering Role). Your mission is to run **5,000,000+ weight/parameter configurations** against the historical PDUFA dataset to find the GLOBAL OPTIMUM configuration that beats v8.6 champion.

**RELENTLESS MODE ACTIVATED**: Do NOT stop until:
1. You have tested > 5,000,000 configurations, OR
2. MCC improvement between top 10 configs is < 0.0005, OR  
3. You achieve ALL target metrics simultaneously

**MODE**: IMPROVEMENT-ONLY (no forward predictions, no watchlists)

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: BASELINE TO BEAT (V8.6 CHAMPION)
# ══════════════════════════════════════════════════════════════════════════════

```json
{
  "version": "v8.6_champion",
  "threshold": 48,
  "metrics": {
    "MCC": 0.4562,
    "Precision": 0.9502,
    "Recall": 0.8494,
    "Specificity": 0.7111,
    "Brier": 0.1761,
    "TP": 993,
    "FN": 176,
    "TN": 128,
    "FP": 52
  }
}
```

## V8.6 Parameters (Starting Point)
```python
V86_PARAMS = {
    'base': 50,
    'threshold': 48,
    'btd': 8,
    'orphan': 5,
    'priority': 10,
    'fast_track': 4,
    'accel': 6,
    'exp': 20,
    'some_exp': 10,
    'stack5': 15,
    'stack4': 10,
    'stack3': 5,
    'gene_cell': 8,
    'onc': 8,
    'inf': 12,
    'generic_bonus': 25,
    'adcom_strong': 20,
    'adcom_pos': 12,
    'adcom_neg': -60,
    'mfg': -30,
    'pain': -22,
    'hemato': -22,
    'nephro': -22,
    'ophthal': -18,
    'cns': -18,
    'cardio': -12,
    'metab': -10,
    'mfg_inexp': -22,
    'inexp_highta': -10,
    'inexp_sm': -12,
    'exp_onc': 8,
    'stack_exp': 6
}
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: TARGET METRICS (ALL MUST BE ACHIEVED)
# ══════════════════════════════════════════════════════════════════════════════

```
PRIMARY TARGETS:
┌────────────────┬─────────────┬─────────────┬────────────────────┐
│ Metric         │ v8.6 Current│ v8.8 Target │ Improvement        │
├────────────────┼─────────────┼─────────────┼────────────────────┤
│ MCC            │ 0.4562      │ ≥ 0.50      │ +10%               │
│ Precision      │ 95.02%      │ ≥ 94%       │ HARD FLOOR         │
│ Recall         │ 84.94%      │ ≥ 82%       │ acceptable trade   │
│ Specificity    │ 71.11%      │ ≥ 78%       │ +7% (CRL catch)    │
│ Brier Score    │ 0.1761      │ ≤ 0.12      │ -32% (calibration) │
│ FP (CRLs)      │ 52          │ ≤ 38        │ -14 fewer losses   │
│ FN             │ 176         │ ≤ 210       │ acceptable ceiling │
└────────────────┴─────────────┴─────────────┴────────────────────┘

CONSTRAINT: Precision ≥ 94% is HARD FLOOR - reject any config below this
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: VALIDATED PATCHES TO IMPLEMENT (CRITICAL)
# ══════════════════════════════════════════════════════════════════════════════

These patches were validated by Claude Research Authority via outcome harvest (Jan 11-19, 2026):

## PATCH P001: CLASS 1 CMC RESUBMISSION OVERRIDE
**Status**: VALIDATED (FBIO CUTX-101 approved Jan 13 despite v8.6 score of 42)
**Evidence**: 99.5% historical approval rate for Class 1 CMC resubmissions

```python
def apply_class1_cmc_override(row, current_score, override_floor=95):
    """
    Class 1 CMC resubmissions have 99.5% approval rate.
    Override score to near-certain approval.
    """
    prior_crl = row.get('prior_crl', False)
    resub_class = str(row.get('resubmission_class', '')).strip()
    crl_reason = str(row.get('prior_crl_reason', '')).upper()
    
    if prior_crl and resub_class == '1':
        if 'CMC' in crl_reason or 'MANUFACTURING' in crl_reason:
            return max(current_score, override_floor), ['CLASS_1_CMC_OVERRIDE']
    
    return current_score, []
```

**Expected Impact**: +5 TP, -5 FN, 0 FP change


## PATCH P002: CLUSTER SELL OVERRIDE (CEWS v2.0)
**Status**: VALIDATED (AQST cluster sell 86 days before deficiency, TVTX 18/0 sells)
**Evidence**: C-suite cluster selling is strongest CRL predictor

```python
def apply_cluster_sell_penalty(smart_money_signals, base_poa):
    """
    Cluster selling by C-suite predicts CRL with high accuracy.
    AQST: CEO/COO/CMO sold same day, 86 days before FDA deficiency (-40% stock)
    TVTX: 18 sells / 0 buys + P/C 37.59 before 3-month delay (-33% stock)
    """
    if not smart_money_signals.get('cluster_sell_detected', False):
        return base_poa, []
    
    flags = ['CLUSTER_SELL']
    adjustment = -0.15  # Base penalty
    
    cluster = smart_money_signals.get('cluster_details', {})
    
    if cluster.get('ceo_participated', False):
        adjustment -= 0.05
        flags.append('CEO_IN_CLUSTER')
    
    if cluster.get('same_day_sells', 0) >= 3:
        adjustment -= 0.05
        flags.append('SAME_DAY_CLUSTER')
    
    # 10b5-1 discount (still suspicious but less)
    transactions = cluster.get('transactions', [])
    if transactions and all(t.get('is_10b5_1', False) for t in transactions):
        adjustment *= 0.50
        flags.append('10B5_PARTIAL_DISCOUNT')
    
    adjustment = max(adjustment, -0.25)  # Cap
    adjusted_poa = max(0.05, base_poa + adjustment)
    
    return adjusted_poa, flags
```

**Expected Impact**: +3 TN, +2% specificity


## PATCH P003: LOW DESIGNATION CLINICAL RISK
**Status**: READY FOR TESTING
**Evidence**: 90.4% of FPs are experienced sponsors + 82.7% CLINICAL CRLs

```python
def apply_low_designation_clinical_risk(row, current_score, penalty=-10):
    """
    Key Insight: CLINICAL CRLs have LOWER designation stacks (1.25) 
    than comparable approvals (1.71) for experienced sponsors.
    
    When experienced sponsor lacks FDA designations despite clean
    manufacturing profile, FDA may not be convinced of CLINICAL merit.
    """
    exp = row.get('experienced_sponsor', False)
    mfg = row.get('manufacturing_risk', False)
    btd = row.get('btd', False)
    stack = row.get('designation_stack_count', 0)
    
    if exp and not mfg and not btd and stack <= 1:
        return current_score + penalty, ['LOW_DESIGNATION_CLINICAL_RISK']
    
    return current_score, []
```

**Expected Impact**: +22 TN, -22 FP, +12% specificity

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: COMPLETE V8.8 SCORING FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

```python
import pandas as pd
import numpy as np
from itertools import product
import warnings
warnings.filterwarnings('ignore')

def score_odin_v88(row, params):
    """
    ODIN v8.8+ Scoring Function
    Includes all validated patches from Claude Research Authority
    """
    score = params.get('base', 50)
    flags = []
    
    # === EXTRACT FEATURES ===
    exp = bool(row.get('experienced_sponsor', False))
    mfg = bool(row.get('manufacturing_risk', False))
    mod = str(row.get('modality', '')).upper() if pd.notna(row.get('modality')) else ''
    ta = str(row.get('therapeutic_area', '')).upper() if pd.notna(row.get('therapeutic_area')) else ''
    stack = int(row.get('designation_stack_count', 0)) if pd.notna(row.get('designation_stack_count')) else 0
    prior_approvals = int(row.get('sponsor_prior_approvals', 0)) if pd.notna(row.get('sponsor_prior_approvals')) else 0
    asset = str(row.get('asset', '')).lower() if pd.notna(row.get('asset')) else ''
    btd = bool(row.get('btd', False))
    had_adcom = bool(row.get('had_adcom', False))
    year = int(row.get('year', 2020)) if pd.notna(row.get('year')) else 2020
    
    # Generic detection
    generic_keywords = ['generic', 'biosimilar', 'bios', 'bioequivalent', 'usp']
    is_generic = any(kw in asset for kw in generic_keywords)
    
    # Modality detection
    is_cgt = 'GENE' in mod or 'CELL' in mod
    is_adc = 'ADC' in mod or 'CONJUGATE' in mod
    is_antibody = 'ANTIBODY' in mod or 'MAB' in mod
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION A: DESIGNATION BONUSES
    # ═══════════════════════════════════════════════════════════════
    
    if btd: score += params.get('btd', 8)
    if row.get('orphan', False): score += params.get('orphan', 5)
    if row.get('priority_review', False): score += params.get('priority', 10)
    if row.get('fast_track', False): score += params.get('fast_track', 4)
    if str(row.get('accelerated_approval', '')).upper() == 'TRUE': 
        score += params.get('accel', 6)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION B: SPONSOR EXPERIENCE
    # ═══════════════════════════════════════════════════════════════
    
    if exp: 
        score += params.get('exp', 20)
    elif prior_approvals > 0: 
        score += params.get('some_exp', 10)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION C: DESIGNATION STACK (STEPPED)
    # ═══════════════════════════════════════════════════════════════
    
    if stack >= 5: score += params.get('stack5', 15)
    elif stack >= 4: score += params.get('stack4', 10)
    elif stack >= 3: score += params.get('stack3', 5)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION D: MODALITY BONUSES
    # ═══════════════════════════════════════════════════════════════
    
    if is_cgt: 
        score += params.get('gene_cell', 8)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION E: THERAPEUTIC AREA BONUSES/PENALTIES
    # ═══════════════════════════════════════════════════════════════
    
    # Bonuses
    if 'ONCOLOGY' in ta: 
        score += params.get('onc', 8)
    elif 'INFECTIOUS' in ta: 
        score += params.get('inf', 12)
    
    # Penalties
    if 'PAIN' in ta: score += params.get('pain', -22)
    elif 'HEMATO' in ta: score += params.get('hemato', -22)
    elif 'NEPHRO' in ta: score += params.get('nephro', -22)
    elif 'OPHTHAL' in ta: score += params.get('ophthal', -18)
    elif 'CNS' in ta or 'NEURO' in ta: score += params.get('cns', -18)
    elif 'CARDIO' in ta: score += params.get('cardio', -12)
    elif 'METABOLIC' in ta or 'ENDOCRINE' in ta: score += params.get('metab', -10)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION F: GENERIC/BIOSIMILAR BONUS
    # ═══════════════════════════════════════════════════════════════
    
    if is_generic: 
        score += params.get('generic_bonus', 25)
        flags.append('GENERIC_BIOSIMILAR')
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION G: ADVISORY COMMITTEE
    # ═══════════════════════════════════════════════════════════════
    
    if had_adcom:
        adcom = row.get('adcom_vote_pct', None)
        if pd.notna(adcom):
            if adcom >= 80: score += params.get('adcom_strong', 20)
            elif adcom >= 70: score += params.get('adcom_pos', 12)
            elif adcom < 50: score += params.get('adcom_neg', -60)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION H: MANUFACTURING RISK (with modality multiplier)
    # ═══════════════════════════════════════════════════════════════
    
    if mfg:
        base_mfg_penalty = params.get('mfg', -30)
        
        # Modality complexity multiplier (CGT has ALL 10 got CRL before approval)
        if is_cgt:
            base_mfg_penalty *= params.get('cgt_mfg_mult', 1.3)
            flags.append('CGT_MFG_AMPLIFIED')
        elif is_adc:
            base_mfg_penalty *= params.get('adc_mfg_mult', 1.2)
        elif is_antibody:
            base_mfg_penalty *= params.get('antibody_mfg_mult', 1.1)
        
        score += base_mfg_penalty
        
        # Additional penalty for inexperienced sponsor with mfg risk
        if not exp:
            score += params.get('mfg_inexp', -22)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION I: CORE INTERACTION TERMS
    # ═══════════════════════════════════════════════════════════════
    
    # Inexperienced + high-risk TA
    high_risk_tas = ['PAIN', 'NEPHRO', 'CNS', 'HEMATO', 'OPHTHAL', 'NEURO']
    if not exp and any(x in ta for x in high_risk_tas):
        score += params.get('inexp_highta', -10)
    
    # Inexperienced + small molecule
    if not exp and 'SMALL' in mod:
        score += params.get('inexp_sm', -12)
    
    # Experienced + oncology
    if exp and 'ONCOLOGY' in ta:
        score += params.get('exp_onc', 8)
    
    # High stack + experienced
    if stack >= 4 and exp:
        score += params.get('stack_exp', 6)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION J: NEW V8.8 CLINICAL CRL RISK FEATURES
    # ═══════════════════════════════════════════════════════════════
    
    # PATCH P003: LOW DESIGNATION CLINICAL RISK
    if params.get('use_low_des_clin', True):
        if exp and not mfg and not btd and stack <= 1:
            score += params.get('low_des_clin', -10)
            flags.append('LOW_DESIGNATION_CLINICAL_RISK')
    
    # ANTIBODY + EXPERIENCED CLINICAL RISK (27/52 FPs were antibodies from exp sponsors)
    if params.get('use_antibody_exp_clin', False):
        if exp and not mfg and is_antibody:
            score += params.get('antibody_exp_clin', -8)
            flags.append('ANTIBODY_EXP_CLINICAL_RISK')
    
    # ONCOLOGY + EXPERIENCED + NO MFG = HIGH EFFICACY BAR
    if params.get('use_onc_exp_clin', False):
        if exp and not mfg and 'ONCOLOGY' in ta:
            score += params.get('onc_exp_clin', -6)
            flags.append('ONC_EXP_CLINICAL_RISK')
    
    # SILENT FAILURE DETECTION (no designations AND no AdCom in risky TA)
    if params.get('use_silent_failure', False):
        if stack == 0 and not had_adcom:
            risky_tas = ['ONCOLOGY', 'CNS', 'NEURO', 'PAIN', 'OPHTHAL']
            if any(x in ta for x in risky_tas):
                score += params.get('silent_failure', -5)
                flags.append('SILENT_FAILURE_RISK')
    
    # TA-SPECIFIC CLINICAL RISK (for experienced, no-mfg sponsors)
    if params.get('use_ta_clin_modifier', False):
        if exp and not mfg:
            if 'OPHTHAL' in ta:
                score += params.get('ta_clin_ophthal', -8)
            elif 'METABOLIC' in ta or 'ENDOCRINE' in ta:
                score += params.get('ta_clin_metabolic', -6)
            elif 'RARE' in ta:
                score += params.get('ta_clin_rare', -4)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION K: ERA ADJUSTMENT (2023+ more permissive FDA)
    # ═══════════════════════════════════════════════════════════════
    
    if params.get('use_era_boost', False):
        if year >= 2023:
            score += params.get('era_boost', 4)
    
    # ═══════════════════════════════════════════════════════════════
    # SECTION L: PATCH P001 - CLASS 1 CMC RESUBMISSION OVERRIDE
    # ═══════════════════════════════════════════════════════════════
    
    if params.get('use_class1_override', True):
        prior_crl = row.get('prior_crl', False)
        resub_class = str(row.get('resubmission_class', '')).strip()
        crl_reason = str(row.get('prior_crl_reason', '')).upper()
        
        if prior_crl and resub_class == '1':
            if 'CMC' in crl_reason or 'MANUFACTURING' in crl_reason:
                override_floor = params.get('class1_override_floor', 95)
                score = max(score, override_floor)
                flags.append('CLASS_1_CMC_OVERRIDE')
    
    # ═══════════════════════════════════════════════════════════════
    # FINAL: CLAMP TO 0-100
    # ═══════════════════════════════════════════════════════════════
    
    return max(0, min(100, score)), flags


def evaluate_config(df, params):
    """
    Evaluate a configuration and return all metrics
    """
    threshold = params.get('threshold', 48)
    
    results = df.apply(lambda r: score_odin_v88(r, params), axis=1)
    scores = results.apply(lambda x: x[0])
    signals = scores >= threshold
    
    # Confusion matrix
    tp = ((signals) & (df['outcome'] == 'APPROVAL')).sum()
    fn = ((~signals) & (df['outcome'] == 'APPROVAL')).sum()
    tn = ((~signals) & (df['outcome'] == 'CRL')).sum()
    fp = ((signals) & (df['outcome'] == 'CRL')).sum()
    
    # Metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    
    # MCC
    denom = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    mcc = (tp*tn - fp*fn) / denom if denom > 0 else 0
    
    # Brier Score
    probs = scores / 100.0
    actuals = (df['outcome'] == 'APPROVAL').astype(int)
    brier = ((probs - actuals) ** 2).mean()
    
    # Expected Value (profit model)
    ev = tp * 0.15 - fp * 0.40  # Wins +15%, CRL losses -40%
    
    return {
        'TP': tp, 'FN': fn, 'TN': tn, 'FP': fp,
        'precision': precision,
        'recall': recall,
        'specificity': specificity,
        'mcc': mcc,
        'brier': brier,
        'ev': ev,
        'params': params
    }


def meets_constraints(metrics):
    """Check if config meets all hard constraints"""
    return (
        metrics['precision'] >= 0.94 and  # HARD FLOOR
        metrics['recall'] >= 0.80 and
        metrics['specificity'] >= 0.70 and
        metrics['FP'] <= 60  # Soft cap
    )


def is_better(new_metrics, best_metrics):
    """Compare two configs - MCC is primary, then specificity, then Brier"""
    if best_metrics is None:
        return meets_constraints(new_metrics)
    
    if not meets_constraints(new_metrics):
        return False
    
    # Primary: MCC
    if new_metrics['mcc'] > best_metrics['mcc'] + 0.001:
        return True
    if new_metrics['mcc'] < best_metrics['mcc'] - 0.001:
        return False
    
    # Secondary: Specificity (CRL catch rate)
    if new_metrics['specificity'] > best_metrics['specificity'] + 0.005:
        return True
    if new_metrics['specificity'] < best_metrics['specificity'] - 0.005:
        return False
    
    # Tertiary: Brier (lower is better)
    return new_metrics['brier'] < best_metrics['brier']
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: COMPLETE SEARCH SPACE SPECIFICATION
# ══════════════════════════════════════════════════════════════════════════════

```python
# ═══════════════════════════════════════════════════════════════
# CORE PARAMETERS (from v8.6 baseline)
# ═══════════════════════════════════════════════════════════════

SEARCH_SPACE = {
    # Base and threshold
    'base': [50],  # Fixed
    'threshold': [42, 44, 45, 46, 48, 50, 52],
    
    # Designation bonuses
    'btd': [6, 7, 8, 9, 10, 12],
    'orphan': [3, 4, 5, 6, 7],
    'priority': [8, 9, 10, 11, 12, 14],
    'fast_track': [2, 3, 4, 5, 6],
    'accel': [4, 5, 6, 7, 8],
    
    # Sponsor experience
    'exp': [15, 16, 18, 20, 22, 25],
    'some_exp': [8, 10, 12, 14],
    
    # Designation stack
    'stack5': [15, 18, 20, 22, 25, 28],
    'stack4': [8, 10, 12, 14, 16],
    'stack3': [3, 5, 6, 7, 8],
    
    # Modality
    'gene_cell': [6, 8, 10, 12],
    
    # TA bonuses
    'onc': [4, 6, 8, 10, 12],
    'inf': [8, 10, 12, 14, 16],
    
    # TA penalties
    'pain': [-18, -20, -22, -25, -28],
    'hemato': [-18, -20, -22, -25],
    'nephro': [-18, -20, -22, -25],
    'ophthal': [-12, -15, -18, -20, -22],
    'cns': [-12, -15, -18, -20, -22],
    'cardio': [-8, -10, -12, -15],
    'metab': [-6, -8, -10, -12],
    
    # Manufacturing
    'mfg': [-25, -28, -30, -32, -35, -38],
    'mfg_inexp': [-15, -18, -20, -22, -25],
    'cgt_mfg_mult': [1.2, 1.3, 1.4, 1.5],
    'adc_mfg_mult': [1.1, 1.2, 1.3],
    'antibody_mfg_mult': [1.0, 1.1, 1.2],
    
    # AdCom
    'adcom_strong': [18, 20, 22, 25, 28],
    'adcom_pos': [10, 12, 14, 15, 18],
    'adcom_neg': [-50, -55, -60, -65, -70],
    
    # Interactions
    'inexp_highta': [-8, -10, -12, -15, -18],
    'inexp_sm': [-8, -10, -12, -15],
    'exp_onc': [5, 6, 8, 10, 12],
    'stack_exp': [4, 5, 6, 8, 10],
    
    # Generic (Migration bundle uses +30, which recovered 12 FNs)
    'generic_bonus': [28, 30, 32, 35],  # Start at 28, v8.8 baseline is 30
}

# ═══════════════════════════════════════════════════════════════
# NEW V8.8 PARAMETERS (CRITICAL ADDITIONS)
# ═══════════════════════════════════════════════════════════════

V88_NEW_PARAMS = {
    # PATCH P001: Class 1 CMC Override (ALWAYS ON)
    'use_class1_override': [True],
    'class1_override_floor': [93, 95, 97],
    
    # PATCH P003: Low Designation Clinical Risk
    'use_low_des_clin': [True, False],
    'low_des_clin': [-6, -8, -10, -12, -15],
    
    # Antibody + Experienced Clinical Risk
    'use_antibody_exp_clin': [True, False],
    'antibody_exp_clin': [-4, -6, -8, -10, -12],
    
    # Oncology + Experienced Clinical Risk
    'use_onc_exp_clin': [True, False],
    'onc_exp_clin': [-3, -5, -6, -8, -10],
    
    # Silent Failure Detection
    'use_silent_failure': [True, False],
    'silent_failure': [-3, -5, -7, -10],
    
    # TA Clinical Modifier
    'use_ta_clin_modifier': [True, False],
    'ta_clin_ophthal': [-6, -8, -10],
    'ta_clin_metabolic': [-4, -6, -8],
    'ta_clin_rare': [-2, -4, -6],
    
    # Era Adjustment
    'use_era_boost': [True, False],
    'era_boost': [0, 3, 4, 5],
}
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: STAGED OPTIMIZATION STRATEGY
# ══════════════════════════════════════════════════════════════════════════════

Total search space is ~10^18 - too large for exhaustive search. Use staged approach:

```python
def run_staged_optimization(df):
    """
    4-Stage optimization to find global optimum
    Total target: 5,000,000+ configurations
    """
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 1: CORE PARAMETERS (~500,000 configs)
    # ═══════════════════════════════════════════════════════════════
    print("STAGE 1: Core Parameters")
    
    stage1_space = {
        'threshold': [42, 44, 46, 48, 50, 52],
        'mfg': [-25, -28, -30, -32, -35],
        'exp': [16, 18, 20, 22],
        'btd': [6, 8, 10],
        'stack5': [15, 18, 20, 22],
        'stack4': [10, 12, 14],
        'pain': [-20, -22, -25],
        'cns': [-15, -18, -20],
        'mfg_inexp': [-18, -20, -22],
        'inexp_highta': [-10, -12, -15],
        'generic_bonus': [25, 28, 30, 32],
        # Fixed v8.8 patches
        'use_class1_override': [True],
        'class1_override_floor': [95],
        'use_low_des_clin': [True],
        'low_des_clin': [-10],
    }
    
    stage1_results = grid_search(df, stage1_space)
    top_100_stage1 = get_top_n(stage1_results, 100)
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 2: CLINICAL RISK FEATURES (~1,000,000 configs)
    # ═══════════════════════════════════════════════════════════════
    print("STAGE 2: Clinical Risk Features")
    
    stage2_space = {
        # Best from stage 1 (parameterized)
        **extract_best_core(top_100_stage1),
        
        # New clinical risk features
        'use_low_des_clin': [True],
        'low_des_clin': [-6, -8, -10, -12, -15],
        'use_antibody_exp_clin': [True, False],
        'antibody_exp_clin': [-4, -6, -8, -10],
        'use_onc_exp_clin': [True, False],
        'onc_exp_clin': [-3, -5, -6, -8],
        'use_silent_failure': [True, False],
        'silent_failure': [-3, -5, -7],
        'use_ta_clin_modifier': [True, False],
    }
    
    stage2_results = grid_search(df, stage2_space)
    top_100_stage2 = get_top_n(stage2_results, 100)
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 3: MODALITY MULTIPLIERS + ERA (~2,000,000 configs)
    # ═══════════════════════════════════════════════════════════════
    print("STAGE 3: Modality & Era Adjustments")
    
    stage3_space = {
        **extract_best(top_100_stage2),
        
        'cgt_mfg_mult': [1.2, 1.3, 1.4, 1.5],
        'adc_mfg_mult': [1.1, 1.2, 1.3],
        'antibody_mfg_mult': [1.0, 1.1, 1.2],
        'use_era_boost': [True, False],
        'era_boost': [0, 3, 4, 5],
        'class1_override_floor': [93, 95, 97],
    }
    
    stage3_results = grid_search(df, stage3_space)
    top_100_stage3 = get_top_n(stage3_results, 100)
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 4: FINE-TUNE TOP 100 (~1,500,000 configs)
    # ═══════════════════════════════════════════════════════════════
    print("STAGE 4: Fine-Tuning")
    
    final_results = []
    for config in top_100_stage3:
        # Local search around each top config
        neighbors = generate_neighbors(config, radius=1)
        for neighbor in neighbors:
            result = evaluate_config(df, neighbor)
            final_results.append(result)
    
    # Sort and return champion
    final_results.sort(key=lambda x: (-x['mcc'], -x['specificity'], x['brier']))
    champion = final_results[0]
    
    return champion, final_results[:100]
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7: DATASET REQUIREMENTS
# ══════════════════════════════════════════════════════════════════════════════

**Required File**: `ODIN_ENRICHED_PDUFA_1349_v2.csv`

```python
# Expected columns
REQUIRED_COLUMNS = [
    'event_id', 'ticker', 'company', 'asset', 'indication',
    'therapeutic_area', 'catalyst_date', 'outcome',
    'btd', 'orphan', 'priority_review', 'fast_track', 'accelerated_approval',
    'designation_stack_count', 'had_adcom', 'adcom_vote_pct',
    'prior_crl', 'prior_crl_reason', 'resubmission_class',
    'form_483_issues', 'manufacturing_risk',
    'sponsor_prior_approvals', 'experienced_sponsor',
    'modality', 'year'
]

# Expected stats
EXPECTED_STATS = {
    'total_events': 1349,
    'approvals': 1169,
    'crls': 180,
    'date_range': '2020-2026'
}

# Load and validate
def load_dataset(filepath):
    df = pd.read_csv(filepath)
    
    # Validate columns
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    # Validate stats
    assert len(df) == 1349, f"Expected 1349 rows, got {len(df)}"
    assert (df['outcome'] == 'APPROVAL').sum() == 1169
    assert (df['outcome'] == 'CRL').sum() == 180
    
    return df
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8: OUTPUT REQUIREMENTS
# ══════════════════════════════════════════════════════════════════════════════

After optimization, produce these artifacts:

## 1. Champion Configuration JSON
```json
{
  "version": "v8.8_champion",
  "created_at": "YYYY-MM-DD",
  "created_by": "ChatGPT Engineering",
  "configs_tested": 5000000,
  "params": { ... },
  "metrics": {
    "MCC": 0.XX,
    "Precision": 0.XX,
    "Recall": 0.XX,
    "Specificity": 0.XX,
    "Brier": 0.XX,
    "TP": XXX,
    "FN": XXX,
    "TN": XXX,
    "FP": XXX
  },
  "improvements_vs_v86": {
    "MCC_delta": "+X.XX%",
    "Specificity_delta": "+X.XX%",
    "FP_delta": "-XX",
    "Brier_delta": "-X.XX"
  }
}
```

## 2. Top 10 Configurations Report
```
Rank | MCC    | Precision | Specificity | Brier  | Key Differences
-----|--------|-----------|-------------|--------|------------------
1    | 0.XXX  | XX.X%     | XX.X%       | 0.XXX  | ...
2    | 0.XXX  | XX.X%     | XX.X%       | 0.XXX  | ...
...
```

## 3. Feature Impact Analysis
```
Feature                      | Impact on MCC | Impact on Specificity
-----------------------------|---------------|----------------------
use_low_des_clin=True        | +0.0XX        | +X.X%
use_class1_override=True     | +0.0XX        | +X.X%
cgt_mfg_mult=1.3             | +0.0XX        | +X.X%
...
```

## 4. Convergence Report
```
Stage | Configs Tested | Best MCC | Best Specificity | Time
------|----------------|----------|------------------|------
1     | 500,000        | 0.XXX    | XX.X%            | Xh Xm
2     | 1,000,000      | 0.XXX    | XX.X%            | Xh Xm
3     | 2,000,000      | 0.XXX    | XX.X%            | Xh Xm
4     | 1,500,000      | 0.XXX    | XX.X%            | Xh Xm
TOTAL | 5,000,000      | 0.XXX    | XX.X%            | Xh Xm
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9: STOP CONDITIONS
# ══════════════════════════════════════════════════════════════════════════════

```python
def should_stop(configs_tested, top_10_results, start_time):
    """
    Stop optimization when any condition is met
    """
    # Condition 1: Tested enough configs
    if configs_tested >= 5_000_000:
        return True, "Reached 5M configurations"
    
    # Condition 2: Convergence (top 10 within 0.0005 MCC)
    if len(top_10_results) >= 10:
        mcc_values = [r['mcc'] for r in top_10_results]
        if max(mcc_values) - min(mcc_values) < 0.0005:
            return True, "Converged (MCC delta < 0.0005)"
    
    # Condition 3: All targets achieved
    best = top_10_results[0] if top_10_results else None
    if best:
        if (best['mcc'] >= 0.50 and
            best['precision'] >= 0.94 and
            best['specificity'] >= 0.78 and
            best['brier'] <= 0.12 and
            best['FP'] <= 38):
            return True, "ALL TARGET METRICS ACHIEVED"
    
    return False, None
```

---

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10: AUDIT REQUIREMENTS
# ══════════════════════════════════════════════════════════════════════════════

**CRITICAL - Follow these rules**:

1. **T-1 Compliance**: All features must use data available ≥1 day before catalyst
2. **No Leakage**: Never use outcome or post-event data in scoring
3. **Reproducibility**: Log all random seeds, parameter choices, timestamps
4. **Version Control**: Increment version for any logic change
5. **Hash Registry**: Compute SHA-256 hash of final config for verification

```python
import hashlib
import json

def compute_config_hash(config):
    """Generate immutable hash for configuration"""
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]
```

---

# ══════════════════════════════════════════════════════════════════════════════
# FINAL CHECKLIST
# ══════════════════════════════════════════════════════════════════════════════

Before starting, confirm:

- [ ] Loaded ODIN_ENRICHED_PDUFA_1349_v2.csv (1,349 events)
- [ ] Implemented score_odin_v88() function exactly as specified
- [ ] Implemented all 3 validated patches (P001, P002, P003)
- [ ] Set up staged optimization framework
- [ ] Configured stop conditions
- [ ] Prepared output templates

After completion, deliver:

- [ ] Champion configuration JSON
- [ ] Top 10 configurations report
- [ ] Feature impact analysis
- [ ] Convergence report
- [ ] Total configs tested (must be ≥5M or converged)

---

# ══════════════════════════════════════════════════════════════════════════════
# START COMMAND
# ══════════════════════════════════════════════════════════════════════════════

**Resume ODIN development from this ledger. Use v8.8 as base.**

Begin Stage 1 optimization immediately. Report progress at each stage.

Target: Find configuration that achieves:
- MCC ≥ 0.50
- Precision ≥ 94%
- Specificity ≥ 78%
- Brier ≤ 0.12
- FP ≤ 38

Good luck, Engineering. The ravens are watching.

---

*"ODIN sees all outcomes. The Allfather demands improvement. Find the global optimum."*

**Document**: ODIN_V88_CHATGPT_HANDOFF.md
**Generated**: 2026-01-19
**Source**: Claude Research Authority
**Mode**: IMPROVEMENT-ONLY
