# ODIN v9.1 - Improvement #1 Results & Next Steps

## 🎯 Improvement #1: Indication Difficulty Adjustments

### Results (500K config test)

| Metric | Baseline | v9.1 Champion | Change |
|--------|----------|---------------|--------|
| Brier Score | 0.0996 | 0.08864 | **-11.0%** |
| TIER_1 approval | 94.7% | 95.6% | +0.9% |
| TIER_4 CRL rate | N/A | 85.7% | 🆕 |
| TIER_4 count | 0 | 28 | 🆕 |
| CRL recall @85% | 66.7% | 76.7% | **+10%** |

### Key Discovery
```
ta_adjustment_weight = 0.829
```
**Optimal use of indication difficulty is 83% of raw historical rates**, not 100%.

This makes sense: raw historical rates have noise, and the optimizer found the signal-to-noise sweet spot.

### Therapeutic Area Impact (after 83% scaling)

| TA | Scaled Adjustment | Risk Level |
|----|-------------------|------------|
| Pain Management | -23.7% | ⚠️ VERY HIGH |
| Hematology | -18.6% | ⚠️ HIGH |
| Nephrology | -14.7% | ⚠️ HIGH |
| Ophthalmology | -10.9% | ⚠️ HIGH |
| CNS/Neurology | -8.1% | ⚡ MOD |
| Oncology | +5.1% | ✅ LOW |
| Infectious Disease | +8.5% | ✅ LOW |
| Vaccines | +11.0% | ✅ LOW |

---

## 📁 Files for Billion-Scan

Run these on your RTX 4070 for the full billion-config optimization:

1. **`odin_v91_gpu_optimizer.py`** - GPU optimizer (modify `total_iterations` for 1B)
2. **`odin_v91_config.py`** - Config module with scoring logic
3. **`ODIN_v91_CHAMPION_CONFIG.json`** - Current best params (baseline for comparison)

### To run billion-scan locally:
```python
# In odin_v91_gpu_optimizer.py, change:
config = OptimizationConfig(
    batch_size=2_500_000,  # 2.5M per GPU batch
    total_iterations=1_000_000_000,  # 1 billion
)
```

Expected runtime on RTX 4070: ~15-20 minutes

---

## 🔄 Improvement Pipeline

### ✅ Completed
- [x] **#1: Indication Difficulty Adjustments** (+11% Brier improvement)

### 🔜 Next Up
- [ ] **#2: Molecular Complexity Features** (QED, Lipinski, MW from SMILES)
- [ ] **#3: HINT Bearish Alert** (flag HINT <40% as critical CRL risk)

### Workflow
1. Run billion-scan for #1 on RTX 4070
2. Return with champion params
3. Implement #2, test
4. Run billion-scan for #2
5. Stack improvements

---

## 📊 Expected Final Stack Performance

| Improvement | Brier Delta | Cumulative |
|-------------|-------------|------------|
| Baseline | - | 0.0996 |
| #1 TA Difficulty | -11% | 0.0886 |
| #2 Molecular (est.) | -3% | 0.0860 |
| #3 HINT Alert (est.) | -2% | 0.0843 |

Target: **<0.085 Brier** with stacked improvements.

---

## Quick Start for Billion-Scan

```bash
# On your RTX 4070 machine
cd /path/to/odin
python odin_v91_gpu_optimizer.py

# Or use the config directly
from odin_v91_config import OdinV91Config, score_event

config = OdinV91Config(ta_adjustment_weight=0.829)
result = score_event(config, your_event_dict)
```

Let me know when the billion-scan completes - we'll compare and then move to Improvement #2!
