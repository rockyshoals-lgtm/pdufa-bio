# ODIN PDUFA Scoring System — Complete Implementation

## System Overview

ODIN is an FDA PDUFA approval probability scoring system for biotech catalyst trading. It combines:

1. **POA Scorer** — Probability of Approval using v10.66 canonical logistic regression weights
2. **S24 Revenue Impact** — Peak sales estimation and revenue tier classification  
3. **Runup Module** — Alpha Score, window selection, position sizing, exit protocol
4. **Regime Detection** — Biotech market regime (BULL/NORMAL/BEAR/CRISIS)

## File Manifest

### Core Scoring Engine
| File | Purpose |
|------|---------|
| `odin_v1066_expanded_best.json` | Canonical POA weights (33 params) — **IMMUTABLE** |
| `odin_orchestrator.py` | POA scorer + full pipeline combiner |
| `odin_runup_module.py` | Alpha score, window selection, position sizing, exit protocol |
| `odin_regime.py` | Biotech market regime detection (XBI-based) |
| `odin_live_scorer.py` | **Main entry point** — "Score TICKER" end-to-end pipeline |

### Data Files
| File | Contents |
|------|----------|
| `pdufa_full_v2.csv` | 1,865 events (2020-2025), 58 columns, 10 return windows |
| `price_cache.json` | 356 tickers + SPY daily prices (T-80 to T+10) |
| `ODIN_MODEL_READY_v1066_T1_2015on_2200.csv` | Full 2,197-event training dataset |
| `ODIN_MODEL_READY_v1066_T1_2015on_2200_WITH_MCAP.csv` | Same + market cap enrichment |
| `ticker_market_caps.json` | Current market caps for 1,735 tickers |
| `backtest_scored_full.csv` | All 1,719 events scored with POA + alpha + runup |

### Utilities
| File | Purpose |
|------|---------|
| `odin_backtest_validation.py` | Phase 3 backtest validation (10 tests) |
| `odin5.py` | Original v10.66 GPU training engine |
| `odin5_upgraded.py` | Upgraded CLI with backtest modes |
| `rebuild_price_data.py` | Rebuilds price_cache.json from Yahoo Finance |
| `fetch_market_caps.py` | Market cap enrichment script |

## Quick Start

### Score a single catalyst
```bash
python odin_live_scorer.py IRON \
  --catalyst-date 2026-02-15 \
  --ta "Rare Disease" \
  --indication "Erythropoietic protoporphyria (EPP)" \
  --asset "bitopertin" \
  --btd --orphan --priority-review \
  --regime AUTO
```

### From Python
```python
from odin_live_scorer import score_live

result = score_live(
    ticker="IRON",
    catalyst_date="2026-02-15",
    event_data={
        'therapeutic_area': 'Rare Disease',
        'indication': 'Erythropoietic protoporphyria (EPP)',
        'btd': True, 'orphan': True, 'priority_review': True,
        'sponsor_prior_approvals': 0,
    },
    regime='AUTO',
)
```

### In Claude conversation with MCPs
```python
# After calling FinBrain MCPs, pass results to scorer:
from odin_live_scorer import score_live, build_mcp_finbrain

fb_data = build_mcp_finbrain(
    insider_raw=insider_result['series'],
    options_raw=options_result['series'],
    sentiment_raw=sentiment_result['series'],
)

result = score_live("IRON", "2026-02-15", mcp_finbrain=fb_data)
```

## Output Format (Spec §10.2)

```json
{
  "ticker": "IRON",
  "catalyst_date": "2026-02-15",
  "odin_score": 0.7539,
  "odin_tier": "TIER_2",
  "revenue_analysis": {
    "peak_sales_estimate": 243100000,
    "market_cap": 2774070528,
    "revenue_impact_ratio": 0.088,
    "revenue_tier": "R4",
    "estimation_method": "COMPARABLE_DRUG",
    "comparable": "EPP"
  },
  "alpha_score": {
    "total": 61.5,
    "tier": "ALPHA_2",
    "components": {
      "iv_slope": 0.5,
      "smart_money": 0.5,
      "ta_quality": 1.0,
      "designation": 1.0,
      "revenue": 0.2,
      "technical": 0.6
    }
  },
  "window": { "entry": "T-25", "exit": "T-5", "name": "DEFAULT" },
  "expected_return": { "low": 0.018, "high": 0.048 },
  "position": { "base": 10000, "final": 7560, "multiplier": 0.756 },
  "exit_protocol": { "exit_day": "T-5", "runner_pct": 0.0 },
  "regime": { "current": "BULL" },
  "confidence": "MEDIUM"
}
```

## Backtest Validation Results (Phase 3)

### Key Findings (1,719 events, 2020-2025)

| Test | Result | Detail |
|------|--------|--------|
| Alpha monotonicity | ✅ | ALPHA_2 (+2.79%) > ALPHA_3 (+1.56%) |
| Specialist lift | ✅ | Specialist +2.53% vs Non-spec +1.74% |
| Dead money confirmed | ✅ | T-25→T-7 (+1.97%) >> T-7→T-1 (+0.58%) |
| Position weighting | ✅ | PW +2.60% vs EW +2.20% |
| Test set positive | ✅ | 2024-25 mean +2.96% |
| TA quality correlation | ✅ | r = 0.836 (TA runup scores predict returns) |

### Nano-Cap (<$10) Highlights
- Specialist nano: +9.54% mean, 66.7% win rate, Sharpe 0.317
- ALPHA_2 nano: +7.19% mean, 57.3% win rate
- Rare Disease nano: +17.44% mean (N=10, small but monster)
- Pain Management: -5.67% mean → confirmed DEAD ZONE

### Time-Split Stability (Nano T-25→T-7)
- Train 2020-22: +7.17% mean ✅
- Val 2023: +5.80% mean ✅  
- Test 2024-25: +6.08% mean ✅

## Tier Definitions

### ODIN Tier (Approval Probability)
| Tier | Probability | Exit Day | Position % |
|------|------------|----------|-----------|
| TIER_1 | ≥86% | T-5 | 100% |
| TIER_2 | 73-85% | T-5 | 75% |
| TIER_3 | 58-72% | T-7 | 50% |
| TIER_4 | <58% | **NO ENTRY** | 0% |

### Alpha Tier (Runup Magnitude)
| Tier | Score | Multiplier |
|------|-------|-----------|
| ALPHA_1 | ≥75 | 1.5x |
| ALPHA_2 | 55-74 | 1.2x |
| ALPHA_3 | 35-54 | 0.8x |
| ALPHA_4 | <35 | 0.5x |

### Revenue Tier
| Tier | Ratio | Description |
|------|-------|------------|
| R1 | ≥2.0 | Transformational (1.5x) |
| R2 | 0.5-2.0 | Significant (1.2x) |
| R3 | 0.1-0.5 | Modest (1.0x) |
| R4 | <0.1 | Negligible (0.7x) |

## Non-Negotiable Rules

1. **v10.66 DYNAMIC is immutable** — never modify odin_v1066_expanded_best.json
2. **TIER_4 = NO TRADE** — no exceptions regardless of revenue or alpha
3. **Exit by T-7 (Tier 3) or T-5 (Tier 1-2)** — T-7→T-1 is dead money
4. **No entry after T-15** — late entries capture <58% of move
5. **Weekend PDUFA → exit Thursday/Friday**
6. **Honest evaluation** — 3-way time split (train/val/test), no peeking

## Dependencies

```
pip install numpy pandas yfinance
```

Optional (for GPU training): `cupy`
