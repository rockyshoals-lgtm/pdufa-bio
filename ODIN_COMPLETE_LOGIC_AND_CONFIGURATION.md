# ODIN COMPLETE LOGIC & CONFIGURATION REFERENCE
## Outcome Determination Intelligence Network (ODIN)
### Version: v9.0 (Consolidated from v7, v8.8, v8.11 branches)
### Last Updated: 2026-01-26
### Author: ODIN Research Authority

---

# TABLE OF CONTENTS
1. [System Overview](#1-system-overview)
2. [Core Scoring Formula](#2-core-scoring-formula)
3. [Champion Configuration (v9.0)](#3-champion-configuration)
4. [Complete Signal Catalog (47 Signals)](#4-complete-signal-catalog)
5. [Feature Engineering](#5-feature-engineering)
6. [T-1 Compliance Rules](#6-t-1-compliance-rules)
7. [Override Patches (P001-P007)](#7-override-patches)
8. [Optimization Configuration](#8-optimization-configuration)
9. [Dataset Specification](#9-dataset-specification)
10. [Validation Metrics](#10-validation-metrics)

---

# 1. SYSTEM OVERVIEW

## Purpose
ODIN predicts FDA PDUFA (Prescription Drug User Fee Act) outcomes for biotech investments:
- **APPROVAL**: Drug receives FDA marketing authorization
- **CRL (Complete Response Letter)**: FDA requires additional information/studies

## Baseline Statistics
- **Dataset**: 1,349-1,925 PDUFA events (2009-2026)
- **Base Approval Rate**: ~86.2%
- **CRL Rate**: ~13.8%

## Model Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    ODIN SCORING PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT FEATURES (T-1 Compliant)                                 │
│  ├── Designations (BTD, Orphan, Priority, Fast Track, Accel)   │
│  ├── Therapeutic Area                                           │
│  ├── Modality (Small Molecule, Biologic, Gene Therapy, etc.)   │
│  ├── Manufacturing Risk Signals                                 │
│  ├── Sponsor Experience                                         │
│  ├── AdCom Vote (if occurred)                                   │
│  ├── Prior CRL History                                          │
│  ├── Social Sentiment (LunarCrush S17-S20)                     │
│  ├── Options Flow (FinBrain S24-S27)                           │
│  └── CMC/Inspection (S21-S23)                                  │
│                                                                 │
│  SCORING ENGINE                                                 │
│  ├── Base Probability (p_base)                                 │
│  ├── Signal Adjustments (weighted sum)                         │
│  ├── Override Patches (P001-P007)                              │
│  └── Probability Clamping [0.05, 0.995]                        │
│                                                                 │
│  OUTPUT                                                         │
│  ├── Probability of Approval [0, 1]                            │
│  ├── Binary Prediction (prob > threshold)                      │
│  └── Tier Classification (1-5)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# 2. CORE SCORING FORMULA

## Primary Equation
```python
prob = p_base 
     + Σ(designation_weights × designation_flags)
     + therapeutic_area_adjustment
     + modality_adjustment  
     + manufacturing_adjustment
     + sponsor_experience_adjustment
     + adcom_adjustment
     + prior_crl_adjustment
     + social_sentiment_adjustment
     + options_flow_adjustment
     + cmc_inspection_adjustment

# Apply overrides (P001-P007)
prob = apply_overrides(prob, event_data)

# Clamp to valid probability range
prob = max(0.05, min(0.995, prob))

# Binary prediction
prediction = "APPROVAL" if prob > threshold else "CRL"
```

## Vectorized GPU Implementation
```python
def batch_score_vectorized(data, params, xp=np):
    """
    Vectorized batch scoring - GPU accelerated via CuPy.
    
    Args:
        data: (n_events, N_FEATURES) array
        params: (n_configs, N_PARAMS) array
        xp: cupy or numpy module
    
    Returns:
        probs: (n_configs, n_events) probabilities
        preds: (n_configs, n_events) binary predictions
    """
    n_events = data.shape[0]
    n_configs = params.shape[0]
    
    # Initialize with base probability
    probs = params[:, 0, None] * xp.ones((1, n_events), dtype=xp.float32)
    
    # Add weighted signals
    for signal_idx, param_idx in SIGNAL_TO_PARAM_MAP.items():
        probs += params[:, param_idx, None] * data[None, :, signal_idx]
    
    # Clamp probabilities
    probs = xp.clip(probs, 0.05, 0.995)
    
    # Binary predictions
    preds = (probs > params[:, 1, None]).astype(xp.int32)
    
    return probs, preds
```

---

# 3. CHAMPION CONFIGURATION (v9.0)

## Core Parameters
```json
{
  "p_base": 0.770,
  "p_threshold": 0.770,
  "version": "v9.0",
  "dataset_rows": 1349,
  "optimization_method": "GPU_RANDOM_SEARCH",
  "configs_tested": "1B+"
}
```

## Designation Weights
| Parameter | Weight | Interpretation |
|-----------|--------|----------------|
| w_btd | -0.049 | BTD slightly negative (may indicate difficult path) |
| w_orphan | -0.020 | Orphan neutral |
| w_priority | -0.021 | Priority Review neutral |
| w_fast | +0.038 | Fast Track slightly positive |
| w_accel | +0.063 | Accelerated Approval positive |
| w_exp | **+0.131** | **Experienced sponsor = +13.1pp** |
| w_stack | -0.002 | Stack count neutral |

## Manufacturing/CMC Signals
| Parameter | Weight | Interpretation |
|-----------|--------|----------------|
| w_form483 | **-0.240** | **Form 483 issues = -24pp** |
| w_form483_oai | **-0.334** | **OAI findings = -33.4pp** |
| w_s22_cmc | -0.163 | CMC citations = -16.3pp |
| w_s23_trend | +0.001 | Inspection trend neutral |
| w_prior_cmc_crl | -0.069 | Prior CMC CRL = -6.9pp |
| w_cmc_hiring | -0.063 | CMC hiring signal = -6.3pp |

## Therapeutic Area Adjustments
| Area | Weight | Approval Rate |
|------|--------|---------------|
| Pain Management | **-0.180** | 58.1% |
| CNS/Psychiatry | -0.099 | 75.3% |
| Nephrology | -0.177 | 69.0% |
| Hematology | -0.224 | 64.3% |
| Ophthalmology | -0.133 | 73.5% |
| Cardiovascular | -0.150 | ~72% |
| **Oncology** | **+0.149** | 92.5% |
| **Infectious Disease** | +0.103 | 97.0% |
| **Vaccines** | +0.133 | 100.0% |
| Rare Disease | +0.040 | ~90% |

## Social Sentiment Signals (S17-S20)
| Signal | Weight | Interpretation |
|--------|--------|----------------|
| w_s17_sentiment | **+0.090** | Bullish sentiment (>75%) = +9pp |
| w_s18_engagement | **+0.118** | Engagement spike = +11.8pp |
| w_s19_silence | **-0.183** | Social silence = -18.3pp ⚠️ |
| w_s20_divergence | -0.038 | Smart money divergence = -3.8pp |

## AdCom & Interaction Signals
| Parameter | Weight | Interpretation |
|-----------|--------|----------------|
| w_adcom | **+0.289** | AdCom vote strongly positive |
| adj_cns_amp | -0.042 | CNS + AdCom negative interaction |
| w_des_trap | -0.001 | Designation trap neutral |

---

# 4. COMPLETE SIGNAL CATALOG (47 SIGNALS)

## Category 1: Core Designations (S01-S07)
| ID | Signal | Column | Range | Source |
|----|--------|--------|-------|--------|
| S01 | Breakthrough Therapy (BTD) | btd | 0/1 | Dataset |
| S02 | Orphan Drug | orphan | 0/1 | Dataset |
| S03 | Priority Review | priority_review | 0/1 | Dataset |
| S04 | Fast Track | fast_track | 0/1 | Dataset |
| S05 | Accelerated Approval | accelerated_approval | 0/1 | Dataset |
| S06 | Designation Stack Count | designation_stack_count | 0-5 | Derived |
| S07 | Experienced Sponsor | experienced_sponsor | 0/1 | Dataset (≥3 prior approvals) |

## Category 2: Therapeutic Area (S08-S14)
| ID | Signal | Values | Weight Range |
|----|--------|--------|--------------|
| S08 | Oncology | is_onco | +0.05 to +0.22 |
| S09 | Infectious Disease | is_inf | +0.04 to +0.15 |
| S10 | CNS/Neurology | is_cns | -0.15 to +0.05 |
| S11 | Pain Management | is_pain | -0.35 to -0.15 |
| S12 | Rare/Orphan Disease | is_rare | +0.00 to +0.20 |
| S13 | Cardiovascular | is_cardio | -0.25 to +0.05 |
| S14 | Ophthalmology | is_ophthal | -0.20 to +0.05 |

## Category 3: AdCom & Interactions (S15-S16)
| ID | Signal | Formula | Weight Range |
|----|--------|---------|--------------|
| S15 | AdCom Vote Score | (adcom_vote_pct - 50) / 50 × had_adcom | +0.10 to +0.35 |
| S16 | CNS + AdCom Amplifier | is_cns × had_adcom | -0.20 to 0.00 |

## Category 4: Social Sentiment (S17-S20) - LunarCrush
| ID | Signal | Trigger | Weight | Source |
|----|--------|---------|--------|--------|
| S17 | Social Sentiment | sentiment_score > 75% | +0.03 to +0.12 | LunarCrush |
| S17 | Social Sentiment | sentiment_score < 40% | -0.08 to -0.02 | LunarCrush |
| S18 | Engagement Spike | engagements > 2x avg + bullish | +0.02 to +0.12 | LunarCrush |
| S18 | Engagement Spike | engagements > 3x avg + bearish | -0.05 to -0.02 | LunarCrush |
| S19 | Social Silence | mentions < 50% avg | -0.20 to -0.05 | LunarCrush |
| S20 | Smart Money Divergence | Galaxy Score < 35 + sentiment < 50 | -0.15 to -0.02 | LunarCrush |

### S17-S20 Calculation Code
```python
def compute_social_signals(row):
    """Compute ODIN social signals from LunarCrush data"""
    signals = {}
    
    # S17: Sentiment Score
    if row['sentiment_score'] is not None:
        if row['sentiment_score'] >= 75:
            signals['s17'] = +0.03  # Bullish boost
        elif row['sentiment_score'] <= 40:
            signals['s17'] = -0.08  # Bearish penalty
        else:
            signals['s17'] = 0.0
    
    # S18: Engagement Spike
    spike = False
    if row['engagements_24h'] and row['engagements_daily_avg']:
        ratio = row['engagements_24h'] / row['engagements_daily_avg']
        if ratio > 2.0:
            spike = True
            if row['sentiment_score'] > 70:
                signals['s18'] = +0.02  # Good news leaked
            elif row['sentiment_score'] < 50:
                signals['s18'] = -0.05  # Bad news leaked
            else:
                signals['s18'] = 0.0
    if not spike:
        signals['s18'] = 0.0
    
    # S19: Social Silence
    if row['mentions_24h'] and row['mentions_daily_avg']:
        if row['mentions_24h'] < row['mentions_daily_avg'] * 0.5:
            signals['s19'] = -0.03  # Silence warning
        else:
            signals['s19'] = 0.0
    
    # S20: Smart Money Divergence
    if row['galaxy_score'] and row['galaxy_score'] < 35:
        if row['sentiment_score'] and row['sentiment_score'] < 50:
            signals['s20'] = -0.02  # Smart money exiting
        else:
            signals['s20'] = 0.0
    else:
        signals['s20'] = 0.0
    
    # Total
    signals['social_total'] = sum(signals.values())
    
    # Classification
    if signals['social_total'] < -0.05:
        signals['classification'] = 'BEARISH'
    elif signals['social_total'] > 0.03:
        signals['classification'] = 'BULLISH'
    else:
        signals['classification'] = 'NEUTRAL'
    
    return signals
```

## Category 5: CMC/Manufacturing/Inspection (S21-S23)
| ID | Signal | Trigger | Weight | Source |
|----|--------|---------|--------|--------|
| S21 | Form 483 OAI | Official Action Indicated | -0.40 to -0.20 | FDA OIIWEB |
| S22 | CMC Citations | Manufacturing deficiencies | -0.30 to -0.10 | FDA Warning Letters |
| S23 | Inspection Trend | Worsening pattern | -0.25 to -0.05 | FDA Inspection DB |

## Category 6: Options Flow (S24-S27) - FinBrain
| ID | Signal | Trigger | Weight | Source |
|----|--------|---------|--------|--------|
| S24 | Put/Call Spike | PCR > 1.5 (30-day) | -0.20 to -0.05 | FinBrain |
| S25 | Unusual Volume | > 3x avg options volume | -0.10 to +0.10 | FinBrain |
| S26 | IV Percentile | IV Rank > 90th | -0.15 to +0.05 | FinBrain |
| S27 | Options Divergence | Puts vs analyst ratings | -0.20 to -0.05 | FinBrain |

## Category 7: Market Microstructure (S28-S31)
| ID | Signal | Trigger | Weight | Source |
|----|--------|---------|--------|--------|
| S28 | Short Interest | SI > 20% | -0.15 to -0.05 | FinBrain |
| S29 | Institutional Flow | Net buying/selling | -0.10 to +0.10 | FinBrain |
| S30 | Analyst Sentiment | Consensus rating | -0.05 to +0.10 | FinBrain |
| S31 | Price Momentum | vs 52-week range | -0.05 to +0.05 | Market Data |

## Category 8: Pattern Signals (P001-P007)
| ID | Signal | Trigger | Effect | Source |
|----|--------|---------|--------|--------|
| P001 | Class 1 CMC Resubmission | resubmission_class == 1 | PENALTY (was override) | Dataset |
| P002 | Cluster Sell | ≥3 insiders sell in 30 days | -0.25 max | FinBrain |
| P003 | Designation Trap | stack ≥ 4 + inexperienced | -0.10 | Dataset |
| P004 | Trial Design TRAP | Single pivotal + non-orphan | Override to 0.55 | ClinicalTrials |
| P005 | EU ≠ US Approval | EU approved, US pending | -0.05 | ChEMBL |
| P006 | Publication Volume | < 10 publications | -0.08 to -0.10 | PubMed |
| P007 | Trial Velocity | > 10 years from Phase 1 | -0.06 to -0.10 | ClinicalTrials |

## Category 9: Forensic Signals (S32-S36)
| ID | Signal | Trigger | Weight | Source |
|----|--------|---------|--------|--------|
| S32 | The VOID (Hiring) | Zero commercial job posts T-6 to T-3 | -0.50 to -0.20 | Indeed |
| S33 | Hiring Slope | Negative ramp in hiring | -0.15 to 0.00 | Indeed |
| S34 | hERG Risk | IC50 < 1μM | -0.20 to -0.05 | ChEMBL |
| S35 | LogP Risk | LogP > 5 | -0.10 to -0.03 | ChEMBL |
| S36 | Timeline Delay | Multiple PDUFA delays | -0.15 to -0.05 | FDA/SEC |

---

# 5. FEATURE ENGINEERING

## Column Index Mapping
```python
COL_IDX = {
    # Core features
    'btd': 0,
    'orphan': 1,
    'priority': 2,
    'fast_track': 3,
    'accel': 4,
    'stack_count': 5,
    'experienced': 6,
    'mfg_risk': 7,
    'form_483': 8,
    'modality': 9,
    
    # Therapeutic area (one-hot)
    'is_onco': 10,
    'is_inf': 11,
    'is_cns': 12,
    'is_pain': 13,
    'is_rare': 14,
    'is_cardio': 15,
    'is_ophthal': 16,
    'is_nephro': 17,
    'is_heme': 18,
    
    # AdCom
    'had_adcom': 19,
    'vote_scaled': 20,  # (vote - 50) / 50
    
    # Prior CRL
    'prior_crl': 21,
    'prior_crl_cmc': 22,
    'first_cycle': 23,
    'resubmission_class': 24,
    
    # Social (S17-S20)
    's17_sentiment': 25,
    's18_engage': 26,
    's19_silence': 27,
    's20_diverge': 28,
    'social_total': 29,
    
    # CMC/Inspection (S21-S23)
    's21_oai': 30,
    's22_cmc': 31,
    's23_trend': 32,
    
    # Options (S24-S27)
    's24_pcr': 33,
    's25_uvol': 34,
    's26_iv': 35,
    's27_optdiv': 36,
    
    # Market (S28-S31)
    's28_short': 37,
    's29_inst': 38,
    's30_analyst': 39,
    's31_price': 40,
    
    # Derived
    'des_trap': 41,
    'quality_score': 42,
    'risk_cluster': 43,
}
```

## Parameter Index Mapping
```python
PARAM_IDX = {
    # Core (0-14)
    'p_base': 0,
    'p_threshold': 1,
    'w_social': 2,
    'w_btd': 3,
    'w_orphan': 4,
    'w_priority': 5,
    'w_fast': 6,
    'w_accel': 7,
    'w_exp': 8,
    'w_stack': 9,
    'w_mfg_pen': 10,
    'w_mfg_amp': 11,
    'i_mfg_inexp': 12,
    'w_adcom': 13,
    'w_des_trap': 14,
    
    # TA adjustments (15-23)
    'adj_onco': 15,
    'adj_inf': 16,
    'adj_cns': 17,
    'adj_cns_amp': 18,
    'adj_rare': 19,
    'adj_pain': 20,
    'adj_cardio': 21,
    'adj_nephro': 22,
    'adj_ophthal': 23,
    
    # MCP patterns (24-36)
    'w_p002_cluster': 24,
    'w_p003_des_trap_ext': 25,
    'w_p1_insider': 26,
    'w_p2_pcr': 27,
    'w_p3_pubvol': 28,
    'w_p4_velocity': 29,
    'w_p5_divergence': 30,
    'w_p6_eu_not_us': 31,
    'w_p7_post_sell': 32,
    'w_s1_trial_design': 33,
    'w_s4_genetic': 34,
    'w_s5_proctor': 35,
    'w_resub_class1': 36,
    
    # Forensic (37-47)
    'w_void_6mo': 37,
    'w_void_9mo': 38,
    'w_void_12mo': 39,
    'w_hiring_slope': 40,
    'w_herg': 41,
    'w_logp': 42,
    'w_timeline_delay': 43,
    'w_single_trial': 44,
    'w_us_site': 45,
    'w_pub_velocity': 46,
    'w_mod_penalty': 47,
}
```

---

# 6. T-1 COMPLIANCE RULES

## Definition
**T-1 Compliance**: All features must use ONLY information available BEFORE the FDA decision date (PDUFA). No post-decision information can be used.

## Safe Features ✅
| Feature | Reason |
|---------|--------|
| BTD, Orphan, Priority, Fast Track | Granted by FDA before submission |
| Therapeutic Area | Known at NDA filing |
| Modality | Known at NDA filing |
| Sponsor Experience | Historical record (frozen at T-1) |
| Prior CRL History | From previous submission cycles |
| AdCom Vote (with date check) | AdCom occurs before PDUFA |
| Resubmission Class | Known at resubmission |
| Form 483 Issues (with date check) | Inspection occurs before PDUFA |

## Unsafe Features ❌
| Feature | Reason | Fix |
|---------|--------|-----|
| `crl_notes` | Contains post-decision CRL reasons | NEVER use as feature |
| `outcome` | The label we're predicting | Target only |
| Post-decision press releases | Contaminated with outcome | Exclude |

## Conditional Features ⚠️
| Feature | Condition | Validation |
|---------|-----------|------------|
| `manufacturing_risk` | Must be derived from pre-PDUFA data | Verify source |
| `form_483_issues` | 483 date < PDUFA date | Date check required |
| `adcom_vote_pct` | AdCom date < PDUFA date | Date check required |

## Validation Code
```python
def validate_t1_compliance(df):
    """Check dataset for T-1 compliance issues"""
    issues = []
    
    # Check for crl_notes in features (CRITICAL)
    if 'crl_notes' in df.columns and df['crl_notes'].notna().any():
        issues.append("CRITICAL: crl_notes contains data - MUST NOT use as feature")
    
    # Validate AdCom dates
    adcom_rows = df[df['adcom_vote_pct'].notna()]
    if 'adcom_date' in df.columns and 'catalyst_date' in df.columns:
        invalid = adcom_rows[pd.to_datetime(adcom_rows['adcom_date']) >= 
                            pd.to_datetime(adcom_rows['catalyst_date'])]
        if len(invalid) > 0:
            issues.append(f"AdCom date >= PDUFA date for {len(invalid)} rows")
    
    # Validate Form 483 dates (if available)
    if 'form_483_date' in df.columns and 'catalyst_date' in df.columns:
        invalid = df[pd.to_datetime(df['form_483_date']) >= 
                     pd.to_datetime(df['catalyst_date'])]
        if len(invalid) > 0:
            issues.append(f"Form 483 date >= PDUFA date for {len(invalid)} rows")
    
    return issues
```

---

# 7. OVERRIDE PATCHES (P001-P007)

## P001: Class 1 CMC Resubmission (CORRECTED)
**Previous (WRONG)**: Hard override to 0.995 probability
**Current (CORRECT)**: Weighted penalty signal

```python
# WRONG - Do not use
if resubmission_class == 1 and prior_crl_reason == 'CMC':
    return 0.995  # NO! This bypasses the model

# CORRECT - Use as weighted feature
w_resub_class1 = config['w_resub_class1']  # Optimized weight
prob += w_resub_class1 * (resubmission_class == 1) * prior_crl_cmc
```

**Rationale**: Historical Class 1 CMC resubmissions have ~95% approval rate, but the 99.5% claim was unverifiable and created overconfidence.

## P002: Cluster Sell Override
```python
def apply_p002(prob, insider_data):
    """
    P002: Multiple insider sells in 30-day window
    Validated cases: AQST, TVTX
    """
    sells_30d = count_insider_sells(insider_data, window=30)
    if sells_30d >= 3:
        penalty = min(0.25, sells_30d * 0.05)
        prob -= penalty
    return prob
```

## P003: Designation Trap
```python
def apply_p003(prob, event):
    """
    P003: High designation count + inexperienced sponsor = elevated risk
    Pattern: FDA grants designations to encourage development, but 
    inexperienced sponsors often fail on execution
    """
    stack = event['designation_stack_count']
    experienced = event['experienced_sponsor']
    
    if stack >= 4 and not experienced:
        prob -= 0.10  # Trap penalty
    
    return prob
```

## P004: Trial Design TRAP Override
```python
def apply_p004(prob, event):
    """
    P004: Single pivotal trial + non-orphan = high risk
    FDA skeptical of single-trial evidence for large populations
    """
    pivotal_count = event['pivotal_trial_count']
    is_orphan = event['orphan']
    
    if pivotal_count == 1 and not is_orphan:
        prob = min(prob, 0.55)  # Cap probability
    
    return prob
```

## P005-P007: Secondary Patterns
```python
# P005: EU approval but US pending
if event['eu_approved'] and not event['us_approved']:
    prob -= 0.05  # Slight penalty for discordance

# P006: Low publication volume
if event['pubmed_count'] < 10:
    prob -= 0.08  # Research concerns

# P007: Long trial timeline
years_in_development = (event['nda_date'] - event['phase1_start']).days / 365
if years_in_development > 10:
    prob -= 0.06  # Velocity concerns
```

---

# 8. OPTIMIZATION CONFIGURATION

## Search Bounds
```python
@dataclass
class SignalBounds:
    """Parameter search bounds for GPU optimization"""
    
    # Core parameters
    p_base: Tuple[float, float] = (0.60, 0.90)
    p_threshold: Tuple[float, float] = (0.50, 0.90)
    w_social: Tuple[float, float] = (-2.0, 10.0)  # EXPANDED from [0, 5]
    
    # Designations
    w_btd: Tuple[float, float] = (0.00, 0.12)
    w_orphan: Tuple[float, float] = (-0.05, 0.08)
    w_priority: Tuple[float, float] = (0.00, 0.10)
    w_fast: Tuple[float, float] = (0.00, 0.05)
    w_accel: Tuple[float, float] = (0.00, 0.10)
    w_exp: Tuple[float, float] = (-0.02, 0.15)
    w_stack: Tuple[float, float] = (-0.03, 0.03)
    
    # Manufacturing
    w_mfg_pen: Tuple[float, float] = (-0.15, 0.00)
    w_mfg_amp: Tuple[float, float] = (0.5, 2.5)
    i_mfg_inexp: Tuple[float, float] = (0.5, 2.0)
    
    # AdCom
    w_adcom: Tuple[float, float] = (0.10, 0.50)
    w_des_trap: Tuple[float, float] = (-0.20, 0.00)
    
    # Therapeutic areas
    adj_onco: Tuple[float, float] = (0.00, 0.35)
    adj_inf: Tuple[float, float] = (0.00, 0.25)
    adj_cns: Tuple[float, float] = (-0.15, 0.15)
    adj_pain: Tuple[float, float] = (-0.40, 0.00)
    adj_rare: Tuple[float, float] = (0.00, 0.20)
    
    # Social (S17-S20)
    w_s17_sentiment: Tuple[float, float] = (-0.10, 0.15)
    w_s18_engage: Tuple[float, float] = (-0.05, 0.15)
    w_s19_silence: Tuple[float, float] = (-0.25, 0.00)
    w_s20_diverge: Tuple[float, float] = (-0.15, 0.00)
    
    # Forensic (The VOID)
    w_void_6mo: Tuple[float, float] = (-0.50, 0.00)
```

## Objective Function
```python
def compute_objective(metrics, weights):
    """
    Multi-objective optimization function
    
    Balances:
    - Brier score (calibration)
    - F1 score (precision-recall balance)
    - Specificity (CRL detection - critical for trading)
    - Precision (avoid false approvals)
    """
    obj = (
        weights['brier'] * (1.0 - metrics['brier']) +  # Minimize Brier
        weights['f1'] * metrics['f1'] +
        weights['specificity'] * metrics['specificity'] +
        weights['precision'] * metrics['precision']
    )
    return obj

# Default weights
OBJECTIVE_WEIGHTS = {
    'brier': -0.30,       # Negative = minimize
    'f1': 0.25,
    'specificity': 0.35,  # Heavy weight on CRL detection
    'precision': 0.10
}
```

## Hardware Configuration
```python
@dataclass
class GPUConfig:
    """RTX 4070 configuration"""
    device: str = "cuda:0"
    vram_gb: float = 12.0
    cuda_cores: int = 5888
    streaming_multiprocessors: int = 46
    
    # Optimal batch sizes (empirically determined)
    batch_size: int = 2_000_000  # 2M configs per batch
    max_configs_in_memory: int = 5_000_000
    
    # Performance
    expected_throughput: str = "50-150M configs/second"
```

## Optimization Run Configuration
```python
@dataclass
class OptimizationConfig:
    """Full optimization run settings"""
    
    # Search space
    n_configs_global: int = 500_000_000   # 500M global random search
    n_configs_local: int = 250_000_000    # 250M local refinement
    n_configs_final: int = 100_000_000    # 100M final polish
    
    # Constraints
    min_precision: float = 0.85  # Floor for precision
    min_recall: float = 0.80     # Floor for recall
    
    # Output
    save_top_n: int = 100        # Save top 100 configs
    checkpoint_interval: int = 10_000_000  # Every 10M configs
    
    # Reproducibility
    random_seed: int = 42
```

---

# 9. DATASET SPECIFICATION

## Primary Dataset
**File**: `ODIN_ENRICHED_PDUFA_1349_v2.csv`
**Rows**: 1,349 PDUFA events
**Columns**: 32
**Time Range**: 2009-2026

## Column Definitions
| Column | Type | Description |
|--------|------|-------------|
| event_id | str | Unique event identifier |
| ticker | str | Stock ticker symbol |
| company | str | Company name |
| asset | str | Drug name |
| indication | str | Target indication |
| therapeutic_area | str | TA category |
| catalyst_date | date | PDUFA target date |
| catalyst_type | str | "PDUFA" |
| data_cutoff_date | date | T-1 date |
| outcome | str | APPROVED/CRL |
| btd | bool | Breakthrough designation |
| orphan | bool | Orphan designation |
| priority_review | bool | Priority review |
| fast_track | bool | Fast track designation |
| accelerated_approval | str | Accelerated approval |
| designation_stack_count | int | Total designations |
| had_adcom | bool | AdCom held |
| adcom_vote_pct | float | % favorable vote |
| adcom_date | date | AdCom date |
| prior_crl | bool | Had prior CRL |
| prior_crl_reason | str | Reason for prior CRL |
| resubmission_class | float | Class 1/2 |
| first_cycle | bool | First review cycle |
| form_483_issues | bool | Form 483 problems |
| manufacturing_risk | bool | CMC risk flag |
| sponsor_prior_approvals | int | Prior FDA approvals |
| experienced_sponsor | bool | ≥3 prior approvals |
| modality | str | Drug type |
| year | int | PDUFA year |
| enrichment_source | str | Data source |
| enrichment_confidence | str | Confidence level |
| crl_notes | str | CRL reason (DO NOT USE) |

## Outcome Distribution
| Outcome | Count | Rate |
|---------|-------|------|
| APPROVED | ~1,169 | 86.7% |
| CRL | ~180 | 13.3% |

## Therapeutic Area Distribution
| Area | Count | Approval Rate |
|------|-------|---------------|
| Oncology | ~350 | 92.5% |
| CNS/Neurology | ~180 | 75.3% |
| Infectious Disease | ~150 | 97.0% |
| Rare Disease | ~200 | 90.0% |
| Pain Management | ~60 | 58.1% |
| Cardiovascular | ~100 | 72.0% |

---

# 10. VALIDATION METRICS

## Performance Benchmarks (v9.0)
| Metric | Value | Target |
|--------|-------|--------|
| Precision | 89.4% | ≥85% |
| Recall | 86.0% | ≥80% |
| F1 Score | 0.877 | ≥0.85 |
| Specificity | 41.2% | ≥50% (improvement area) |
| Brier Score | 0.120 | ≤0.10 |
| MCC | 0.251 | ≥0.30 |

## Confusion Matrix
```
                    Predicted
                 APPROVAL    CRL
Actual  APPROVAL   1,411     230   (TP/FN)
        CRL          167     117   (FP/TN)
```

## Key Insights
1. **Strength**: High precision (89.4%) - When we predict approval, we're usually right
2. **Weakness**: Low specificity (41.2%) - We miss 59% of CRLs
3. **Priority**: Improve CRL detection without sacrificing precision

## Tier Classification
| Tier | Probability Range | Recommendation |
|------|-------------------|----------------|
| TIER 1 | ≥92% | HIGHEST CONVICTION - Long calls |
| TIER 2 | 85-91% | HIGH CONVICTION - Call spreads |
| TIER 3 | 75-84% | MODERATE - Smaller position |
| TIER 4 | 60-74% | ELEVATED RISK - Consider puts |
| TIER 5 | <60% | HIGH RISK - Avoid/Short |

---

# APPENDIX A: API INTEGRATIONS

## LunarCrush (Social Sentiment)
```python
# MCP Tool: LunarCrush:Topic
topic_data = LunarCrush.Topic(topic="$TICKER")
# Returns: sentiment_score, galaxy_score, alt_rank, engagements, mentions, creators
```

## FinBrain (Options/Insider)
```python
# Options put/call ratio
pcr_data = FinBrain.options_put_call(market="S&P 500", ticker="TICKER")

# Insider transactions
insider_data = FinBrain.insider_transactions_by_ticker(market="S&P 500", ticker="TICKER")

# Senate/House trades
senate_data = FinBrain.senate_trades_by_ticker(market="S&P 500", ticker="TICKER")
```

## PubMed (Publication Volume)
```python
# Search for drug publications
results = PubMed.search_articles(query=f"{drug_name} clinical trial")
pub_count = results['total_count']
```

## ClinicalTrials.gov (Trial Data)
```python
# Get trial details
trials = ClinicalTrials.search_trials(intervention=drug_name, phase=['PHASE3'])
```

## ChEMBL (Molecular Properties)
```python
# Get ADMET properties
admet = ChEMBL.get_admet(molecule_chembl_id=chembl_id)
# Returns: logP, hERG binding, etc.
```

---

# APPENDIX B: FILE LOCATIONS

## Project Files
```
/mnt/project/
├── ODIN_ENRICHED_PDUFA_1349_v2.csv    # Main dataset
├── lunarcrush_cache.json               # Social sentiment cache
└── LUNARCRUSH_ENRICHMENT_PROGRESS.md   # Enrichment tracking
```

## Output Files
```
/mnt/user-data/outputs/
├── ODIN_CHAMPION_CONFIG_V9.json        # Best configuration
├── ODIN_TOP_100_CONFIGS.json           # Top 100 configs
├── ODIN_2026_PREDICTIONS.csv           # Current predictions
└── ODIN_BACKTEST_RESULTS.csv           # Validation results
```

## Code Files
```
/home/claude/
├── ODIN_GOD_MODE_V9_GPU.py             # Main optimization script
├── odin_lunarcrush_enrichment.py       # Social signal extraction
├── odin_finbrain_enrichment.py         # Options/insider extraction
└── ODIN_LEAKAGE_AUDIT_REPORT.md        # T-1 compliance audit
```

---

*Document generated: 2026-01-26*
*Version: v9.0 Consolidated*
*Status: PRODUCTION READY (pending specificity improvements)*
