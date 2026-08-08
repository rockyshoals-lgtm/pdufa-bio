# ODIN v9.4 GPU Optimizer - Billion-Parameter Search

## Overview

This GPU-accelerated optimizer searches through billions of parameter configurations to find the optimal ODIN v9.4 model. It's designed for your RTX 4070 (12GB VRAM) and includes comprehensive improvement logging.

## Key Features

### v9.4 Improvements (from Perplexity Analysis)
| Feature | Description |
|---------|-------------|
| **CRL Count Multiplier** | 2 CRLs = 1.4x, 3 CRLs = 1.8x, 4+ = 2.2x penalty |
| **Modality-Indication Interactions** | 10 interaction penalties (Gene+Rare Disease, etc.) |
| **Class 2 Resubmission Fix** | Changed from penalty to +0.04 boost |
| **Indication Overrides** | 21 specific indication adjustments (RCKT calibrated) |
| **Enhanced Modality** | Direct penalties for Gene/Cell/RNA therapy |

### Performance Features
| Feature | Benefit |
|---------|---------|
| **Dynamic VRAM Auto-tuning** | Automatically scales batch size to your GPU |
| **Streaming Metrics** | No full C×N matrices (memory efficient) |
| **OOM Backoff** | Automatic recovery from GPU memory errors |
| **Checkpoint/Resume** | Resume interrupted runs |
| **Improvement Logger** | Logs every config that beats previous best |
| **Top-100 Tracking** | Maintains diversity in top configs |

## Parameters (25 total)

```
Designation weights:     btd_weight, orphan_weight, priority_review_weight,
                        fast_track_weight, accelerated_approval_weight

AdCom adjustments:       adcom_high_boost, adcom_mid_penalty, adcom_low_penalty

CRL/Resubmission:        prior_crl_base_penalty, crl_count_multiplier_2,
                        crl_count_multiplier_3, crl_count_multiplier_4plus,
                        class1_resubmission_boost, class2_resubmission_boost

Sponsor:                 experienced_sponsor_boost, inexperienced_sponsor_penalty

Modality:                gene_therapy_penalty, cell_therapy_penalty, rna_therapy_penalty

Interactions:            modality_indication_weight, ta_adjustment_weight,
                        indication_override_weight

Tier Thresholds:         tier1_threshold, tier2_threshold, tier3_threshold
```

## Usage

### Quick Test (1M configs, ~30 seconds)
```bash
python odin_v94_gpu_optimizer.py --quick --csv ODIN_ENRICHED_PDUFA_1349_v2.csv
```

### Standard Optimization (100M configs, ~10-15 min)
```bash
python odin_v94_gpu_optimizer.py --configs 100000000 --csv ODIN_ENRICHED_PDUFA_1349_v2.csv
```

### Billion Config Search (~2 hours)
```bash
python odin_v94_gpu_optimizer.py --billion --csv ODIN_ENRICHED_PDUFA_1349_v2.csv
```

### Resume from Checkpoint
```bash
python odin_v94_gpu_optimizer.py --resume odin_output/odin_v94_checkpoint.npz --csv ODIN_ENRICHED_PDUFA_1349_v2.csv
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--configs` | 100M | Total configurations to test |
| `--batch-size` | 2.5M | Max batch size (auto-tuned) |
| `--event-chunk-size` | 128 | Event chunk for streaming (auto-tuned) |
| `--min-tier4-count` | 15 | Minimum TIER_4 events required |
| `--min-tier4-crl-rate` | 0.50 | Minimum CRL rate in TIER_4 |
| `--min-crl-recall` | 0.55 | Minimum CRL recall @85% |
| `--progress-every` | 10M | Log progress every N configs |
| `--csv` | env or default | Path to PDUFA dataset |
| `--output-dir` | odin_output | Output directory |
| `--resume` | None | Checkpoint file to resume from |
| `--quick` | False | Quick mode (1M, relaxed constraints) |
| `--billion` | False | Billion config mode |

## Output Files

| File | Description |
|------|-------------|
| `ODIN_v94_CHAMPION_CONFIG.json` | Best configuration found |
| `odin_v94_improvements.log` | Every improvement recorded |
| `progress.log` | Progress metrics over time |
| `odin_v94_checkpoint.npz` | Resumable checkpoint |
| `odin_v94_top100_configs.json` | Top 100 configs for diversity |

## Improvement Log Format

```csv
timestamp,improvement_num,brier_score,improvement_pct,tier4_count,tier4_crl_rate,crl_recall,params_json
2026-01-29T...,1,0.095000,5.0200,18,0.5556,0.5833,"{"btd_weight":0.065,...}"
2026-01-29T...,2,0.093500,1.5789,20,0.6000,0.6000,"{"btd_weight":0.058,...}"
```

This log captures the "code breaking" journey - every time you find a better config, it's recorded with full details.

## Constraints (Relaxed from v9.3)

Based on Perplexity analysis, constraints are relaxed to improve feasibility:

| Constraint | v9.3 | v9.4 | Rationale |
|------------|------|------|-----------|
| Min TIER_4 count | 20 | 15 | More configs pass |
| Min TIER_4 CRL rate | 70% | 50% | Achievable with new signals |
| Min CRL recall | 60% | 55% | Better balance |

## Expected Performance

Based on v9.1 champion (Brier 0.08864):
- **Target**: Beat 0.08864 with v9.4 signals
- **Quick mode**: Find feasible configs in ~30 seconds
- **Full optimization**: Expect 100-500 improvements over 100M configs
- **Throughput**: 50-150M configs/sec on RTX 4070

## File Locations

On Windows (WSL), set environment variables:
```bash
export ODIN_CSV_PATH="/mnt/c/Users/.../ODIN_ENRICHED_PDUFA_1349_v2.csv"
export ODIN_OUTPUT_DIR="/mnt/c/Users/.../odin_output"
```

Or pass directly:
```bash
python odin_v94_gpu_optimizer.py --csv "C:\path\to\data.csv" --output-dir "C:\path\to\output"
```

## Troubleshooting

### "CuPy not available"
Install CuPy for your CUDA version:
```bash
pip install cupy-cuda12x  # For CUDA 12.x
```

### GPU OOM
The optimizer will automatically reduce batch size. If it keeps happening:
```bash
python odin_v94_gpu_optimizer.py --batch-size 500000 --event-chunk-size 64
```

### Low feasibility rate
Relax constraints:
```bash
python odin_v94_gpu_optimizer.py --min-tier4-crl-rate 0.35 --min-crl-recall 0.45
```

## Integration with v9.4 Config

After finding a champion, validate with the v9.4 scoring module:
```python
from odin_v94_config import OdinV94Config, score_event_v94
import json

with open('odin_output/ODIN_v94_CHAMPION_CONFIG.json') as f:
    champion = json.load(f)

# Test on RCKT
rckt_result = score_rckt_test(champion['champion_params'])
print(f"RCKT probability: {rckt_result['probability']*100:.1f}%")
```
