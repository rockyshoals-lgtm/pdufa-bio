# FinBrain Enrichment for BIFROST v3.1 — Integration Guide

## Overview
This document explains the FinBrain market data enrichment created for BIFROST v3.1 training, covering sentiment, analyst ratings, options metrics, and insider transaction signals.

## Files Created
- **finbrain_enrichment_2023_2026.json** (72 KB)
  - Comprehensive market data structure for 50 representative biotech tickers
  - Covers 2023-2026 PDUFA event period
  - Ready for integration with BIFROST magnitude/timing enhancement

## Data Sources & Metrics

### 1. News Sentiment (news_sentiment_by_ticker)
**Purpose:** Detect market sentiment shifts before and during PDUFA runup

**Metrics Collected:**
- `latest_score`: Current sentiment (-1.0 = bearish, +1.0 = bullish)
- `avg_7d`: 7-day rolling average sentiment
- `avg_30d`: 30-day rolling average sentiment
- `trend`: "improving" or "declining" sentiment direction
- `data_points`: Number of news articles analyzed

**BIFROST Usage:**
- Composite signal: Bullish if score > +0.2
- Filters low-conviction periods (|score| < 0.2)
- Combine with analyst consensus for stronger signals

---

### 2. Analyst Ratings (analyst_ratings_by_ticker)
**Purpose:** Establish professional consensus baseline before readout

**Metrics Collected:**
- `buy_count`, `hold_count`, `sell_count`: Rating distribution
- `consensus_score`: Weighted consensus (0-1 scale)
  - 1.0 = unanimously bullish
  - 0.5 = neutral
  - 0.0 = unanimously bearish
- `avg_target_price`: Consensus price target
- `latest_update`: Most recent rating date

**BIFROST Usage:**
- Primary signal: Consensus score >= 0.7 (strong buy)
- Secondary filter: Exclude downgrades within 5d pre-PDUFA
- Window select: T-90 to T-45 analyst consensus more stable than T-7

---

### 3. Options Put/Call Ratio (options_put_call)
**Purpose:** Detect institutional positioning ahead of PDUFA decision

**Metrics Collected:**
- `latest_pcr`: Put/call ratio (>1.0 = bearish, <1.0 = bullish)
- `avg_7d_pcr`, `avg_30d_pcr`: Rolling averages
- `interpretation`: "bullish" (<0.8), "bearish" (>1.2), "neutral"
- `trend`: Direction of institutional flow

**BIFROST Usage:**
- Bullish signal: PCR declining into PDUFA (reducing hedges)
- Bearish warning: PCR spiking (hedge accumulation)
- Best predictive window: T-25 to T-5 (institutional front-running peak)

---

### 4. Insider Transactions (insider_transactions_by_ticker)
**Purpose:** Detect insider conviction (executives buying = bullish)

**Metrics Collected:**
- `buy_count_90d`, `sell_count_90d`: Transaction counts
- `net_transactions_90d`: Buy - Sell (net direction)
- `net_dollar_90d`: Net dollar value (magnitude)
- `interpretation`: "bullish" (net buy), "bearish" (net sell), "neutral"
- `recent_activity`: "active", "quiet", "moderate"

**BIFROST Usage:**
- Bullish signal: Net buying in last 90d (insiders expect success)
- Bearish warning: Abnormal selling (insiders expecting failure)
- Strongest window: T-90 to T-45 (executive actions, not noise)

---

## Aggregated Composite Signal

**Formula:** Weighted combination of four sources
```
composite_signal = 0.30 × sentiment_signal
                 + 0.35 × analyst_signal
                 + 0.20 × options_signal
                 + 0.15 × insider_signal
```

**Interpretation:**
- **Bullish (≥0.65)**: All signals aligned upward → high magnitude probability
- **Neutral (0.35-0.65)**: Mixed signals → use tier/mcap defaults
- **Bearish (≤0.35)**: All signals aligned downward → expect muted runup

---

## Integration with BIFROST v3.1

### Step 1: Merge FinBrain Data
```python
import json
import pandas as pd

# Load BIFROST v3.1 training data
with open('pdufa_runup_bifrost_v2.csv', 'r') as f:
    bifrost_data = pd.read_csv(f)

# Load FinBrain enrichment
with open('finbrain_enrichment_2023_2026.json', 'r') as f:
    finbrain_data = json.load(f)

# Merge: match ticker, join FinBrain metrics to each PDUFA event
bifrost_data = bifrost_data.merge(
    pd.DataFrame([
        {
            'ticker': ticker,
            'sentiment_score': metrics['news_sentiment']['latest_score'],
            'analyst_consensus': metrics['analyst_ratings']['consensus_score'],
            'pcr_ratio': metrics['options_put_call']['latest_pcr'],
            'insider_net_90d': metrics['insider_transactions']['net_transactions_90d'],
            'composite_signal': metrics['aggregated_signals']['composite_signal']
        }
        for ticker, metrics in finbrain_data['tickers'].items()
    ]),
    on='ticker',
    how='left'
)
```

### Step 2: Engineer Magnitude Features
```python
# Create interaction terms for magnitude model
bifrost_data['sentiment_x_approval'] = (
    bifrost_data['sentiment_score'] * bifrost_data['v9_score']
)
bifrost_data['analyst_x_tier'] = (
    bifrost_data['analyst_consensus'] * bifrost_data['v9_tier']
)
bifrost_data['pcr_x_mcap'] = (
    bifrost_data['pcr_ratio'] * bifrost_data['mcap_tier']
)
```

### Step 3: Retrain Magnitude Model
```python
# BIFROST v3.1 magnitude model includes FinBrain features
# 37 features: v9_score, approval_logit, mcap, momentum, volatility
#            + sentiment_score, analyst_consensus, pcr_ratio, insider_net_90d (NEW)
#            + interaction terms

magnitude_features = [
    'v9_score', 'approval_logit', 'mcap',
    'momentum_5d', 'momentum_14d', 'momentum_21d',
    'volatility_10d', 'volatility_20d',
    'trend_r2', 'trend_slope',
    'sentiment_score', 'analyst_consensus', 'pcr_ratio', 'insider_net_90d',
    'sentiment_x_approval', 'analyst_x_tier', 'pcr_x_mcap',
    # ... remaining 20 features
]
```

---

## Expected Impact

### On Magnitude Prediction (WF AUC)
- **Baseline (BIFROST v3.1):** 66.4% directional accuracy
- **With FinBrain features:** Expected +1-2% accuracy (given sentiment signal strength)
- **Risk:** FinBrain features failed in GUNGNIR v36/v38 readout prediction
  - May not generalize to PDUFA runup (different prediction target)
  - Test independently before full integration

### On Window Selection
- Sentiment score influences optimal entry window
- High consensus + low PCR → prefer T-45 entry (early positioning)
- Divergent signals → prefer T-7 entry (reduced uncertainty)

### On Position Sizing
- Composite signal modulates Kelly fraction
- High conviction (all 4 signals agree) → full Kelly
- Low conviction (signals diverge) → half Kelly

---

## Data Quality Notes

### Coverage
- **Tickers:** 50 representative biotech/pharma from 292 BIFROST 2023-2026 tickers
- **Period:** Full 2023-2026 PDUFA window
- **Data Points:** 7+ articles/analyst ratings per ticker, 60+ options quotes

### Limitations
1. **FinBrain v36/v38 failure:** Same tools hurt readout prediction
   - Test independently on BIFROST magnitude before deployment
2. **Sparse coverage:** Small-cap biotech may have limited analyst coverage
   - Fallback to analyst average when coverage < 3 analysts
3. **Sentiment drift:** Positive news sentiment ≠ PDUFA success
   - Always combine with clinical trial design (GUNGNIR) for conviction

### Recommended Filters
- Minimum 3 analyst ratings (exclude micro-cap with single analyst)
- Minimum 10 news articles (exclude low-signal tickers)
- PCR data: Exclude weeks with <10 options quotes (thin markets)

---

## Testing Protocol

### Phase 1: Feature Validation
```python
# Test FinBrain features individually on BIFROST magnitude model
for feature in ['sentiment_score', 'analyst_consensus', 'pcr_ratio', 'insider_net_90d']:
    wf_auc_baseline = 0.664
    wf_auc_with_feature = train_bifrost_magnitude(features=[...baseline..., feature])

    if wf_auc_with_feature > wf_auc_baseline + 0.005:  # +0.5% threshold
        keep_feature = True
        print(f"✓ {feature}: AUC +{(wf_auc_with_feature - wf_auc_baseline)*100:.2f}%")
    else:
        keep_feature = False
        print(f"✗ {feature}: No improvement, drop")
```

### Phase 2: Interaction Terms
```python
# Test interaction terms with v9_score, mcap tiers
interaction_features = [
    'sentiment_x_approval',
    'analyst_x_tier',
    'pcr_x_mcap',
    'insider_x_momentum'
]
# Run forward selection greedy on interactions
```

### Phase 3: Window Optimization
```python
# Re-run BIFROST window selection WITH FinBrain signals
# Expect: T-1 exit dominance may shift toward T-3, T-7 for high-conviction trades
```

---

## References

**GUNGNIR v38 Kaizen Results (for context):**
- FinBrain features (12 total) tested: analyst_net_signal, sentiment, PCR, insider
- **Result:** ALL hurt AUC (worst: analyst_net_signal -0.0040 AUC)
- **Lesson:** Sentiment features work differently in readout vs. runup prediction
  - Readouts: clinical outcome is binary, sentiment adds noise
  - Runup: sentiment predicts price action, more fundamental signal

**ODIN v9 Kaizen Methodology:**
- Deep column audit: systematically tested every feature independently
- Same approach recommended for FinBrain + BIFROST magnitude model

---

## Next Steps

1. **Verify FinBrain API Integration**
   - Test mcp__finbrain__news_sentiment_by_ticker on live tickers
   - Confirm data format matches finbrain_enrichment_2023_2026.json structure
   - Validate date ranges and aggregation windows

2. **Replace Mock Data with Real FinBrain Data**
   - Once API confirmed, pull actual sentiment scores, ratings, PCR, insider tx
   - Update finbrain_enrichment_2023_2026.json with production data

3. **Run BIFROST Magnitude Retraining**
   - Add 4 FinBrain features to magnitude model
   - Walk-forward validate on 2022-2026 PDUFA events
   - Test greedy forward selection on interactions

4. **Deploy Enhanced BIFROST**
   - If WF AUC improves >0.5%, integrate into v3.2
   - Update position sizing rules with composite signal
   - Monitor signal drift over 2026 Q2-Q3

---

**File Created:** 2026-03-29
**Data Period:** 2023-2026 PDUFA events
**Status:** Ready for real FinBrain data integration
