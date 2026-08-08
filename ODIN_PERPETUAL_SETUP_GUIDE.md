# ODIN PERPETUAL SYSTEM — SETUP & DEPLOYMENT GUIDE

## SYSTEM OVERVIEW

```
┌─────────────────────────┐       ┌─────────────────────────┐
│   perpetual_loop.py     │       │    audit_cycle.py        │
│   (30-min cycle)        │       │    (30-min monitor)      │
│                         │       │                          │
│  1. DISCOVER new PDUFAs │       │  1. Read snapshot        │
│  2. ENRICH w/ signals   │──────▶│  2. Compare vs baseline  │
│  3. SCORE predictions   │       │  3. Detect issues        │
│  4. APPEND to dataset   │       │  4. Auto-promote/alert   │
│  5. TRAIN model         │       │  5. Log to history       │
│  6. Write snapshot      │       │                          │
└─────────────────────────┘       └─────────────────────────┘
         │                                    │
         ▼                                    ▼
   audit_snapshot.json              audit_history.jsonl
   model_weights.json               sweep_queue.json
   events.json                      (promoted weights)
```

## FILES DEPLOYED

| File | Location | Purpose |
|------|----------|---------|
| `perpetual_loop.py` | `Documents\Python\` | Main engine: discover → enrich → score → train |
| `audit_cycle.py` | `Documents\Python\` | Health monitor: plateau, overfitting, promotions |
| `optimizer_config.json` | `Documents\Python\` | Hyperparameter search space & guard rails |
| `run_odin_system.bat` | `Documents\Python\` | Master launcher for both processes |

## PREREQUISITES

1. **Python 3.10+** on PATH
2. **Dependencies**: `pip install requests pandas numpy scikit-learn`
3. **Data directory**: `C:\Users\dcmoo\odin_data\` (created automatically)
4. **Dataset**: `ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv` in `Documents\Python\`
5. **Honing engine**: `run_perpetual_v2.py` in `Documents\Python\`

## QUICK START

### Step 1: Verify Data Directory
```cmd
dir C:\Users\dcmoo\odin_data\
```
Should contain: `events.json`, `model_weights.json`, and `best_run_AUC_*.json` files.

### Step 2: Generate Initial Snapshot
```cmd
cd C:\Users\dcmoo\Documents\Python
python perpetual_loop.py --mode snapshot > %USERPROFILE%\odin_data\audit_snapshot.json
```

### Step 3: Run First Audit Report
```cmd
python audit_cycle.py --mode report
```
This prints a human-readable health check. Verify no CRITICAL alerts.

### Step 4: Launch Full System
```cmd
run_odin_system.bat
```
This opens TWO terminal windows:
- **ODIN Perpetual Loop**: discovers/enriches/scores/trains every 30 min
- **ODIN Audit Cycle**: monitors health/promotes/alerts every 30 min

## LAUNCHER COMMANDS

| Command | What it does |
|---------|-------------|
| `run_odin_system.bat` | Start both processes (default) |
| `run_odin_system.bat loop` | Start perpetual loop only |
| `run_odin_system.bat audit` | Start audit cycle only |
| `run_odin_system.bat snapshot` | One-shot: generate snapshot + run report |
| `run_odin_system.bat sweep 20` | Generate 20 hyperparameter sweep configs |
| `run_odin_system.bat report` | Run audit report only (no snapshot) |
| `run_odin_system.bat status` | Check if processes are running |
| `run_odin_system.bat stop` | Kill both processes |

## AUDIT CYCLE MODES

```cmd
python audit_cycle.py --mode audit       # One-shot JSON output
python audit_cycle.py --mode auto        # Audit + auto-apply safe changes
python audit_cycle.py --mode sweep --trials 20  # Generate sweep configs
python audit_cycle.py --mode report      # Human-readable report
python audit_cycle.py --mode continuous --interval 1800  # Run every 30min
```

## ACTION PRIORITY CASCADE

The audit cycle determines an action each cycle:

| Priority | Action | Trigger | Auto-applied? |
|----------|--------|---------|---------------|
| 1 | **ALERT** | Overfitting >5%, AUC regression >0.5% | ❌ Manual |
| 2 | **PROMOTE** | Better weights with acceptable generalization | ✅ Auto |
| 3 | **RETRAIN** | Weights >48h old | ✅ Auto |
| 4 | **TUNE** | Plateau detected, mild overfitting | ❌ Manual |
| 5 | **EXPAND** | High-priority enrichment gaps | ❌ Manual |
| 6 | **HOLD** | All nominal | ✅ (no-op) |

## SAFETY CONSTRAINTS

- Never promotes if walk-forward gap > 0.03
- Never reduces L2 below 0.001
- ALERT/TUNE require human review (never auto-applied)
- Backs up current weights before promotion
- Append-only audit_history.jsonl (never deletes history)

## KEY THRESHOLDS

| Parameter | Value | Notes |
|-----------|-------|-------|
| Baseline AUC | 0.9085 | Champion model |
| Baseline Brier | 0.114 | Current calibration |
| Best observed AUC | 0.9201 | From best_runs |
| Promote delta | 0.001 | Must beat live by this |
| Max overfit gap | 0.03 | WARNING threshold |
| Critical overfit gap | 0.05 | ALERT threshold |
| Stale weights | 48 hours | Triggers RETRAIN |
| Plateau detection | 0.002 | AUC variance threshold |

## PLATEAU STRATEGY

When the model plateaus at different AUC bands:

| Band | Strategy | Actions |
|------|----------|---------|
| 0.905–0.915 | EXPAND_FEATURES | Add patent_cliff_years, competitor_count, fda_reviewer_division_rate |
| 0.915–0.925 | REGULARIZATION_SWEEP | L2 sweep [0.001, 0.005, 0.01, 0.05, 0.1] |
| 0.925+ | ENSEMBLE_OR_HALT | Switch to Brier calibration or ensemble methods |

## DATA FLOW

```
perpetual_loop.py WRITES:
  → odin_data/audit_snapshot.json    (model state)
  → odin_data/events.json            (all PDUFA events)
  → odin_data/model_weights.json     (live model)
  → odin_data/best_run_AUC_*.json    (training runs)
  → odin_data/perpetual_loop_log.jsonl

audit_cycle.py READS:
  ← odin_data/audit_snapshot.json
  ← odin_data/model_weights.json
  ← odin_data/events.json, watchlist.json
  ← odin_data/best_run_AUC_*.json

audit_cycle.py WRITES:
  → odin_data/audit_history.jsonl    (append-only log)
  → odin_data/sweep_queue.json       (hyperparameter configs)
  → odin_data/model_weights.json     (promoted weights)
```

## TROUBLESHOOTING

**"No snapshot found"**
Run `python perpetual_loop.py --mode snapshot > %USERPROFILE%\odin_data\audit_snapshot.json`

**"ModuleNotFoundError: requests"**
Run `pip install requests pandas numpy scikit-learn`

**Audit says ALERT but everything looks fine**
Check `audit_history.jsonl` for the specific finding. Common false positives:
- Stale weights after weekend (just run a training cycle)
- Overfitting gap from a bad training run (promote older stable weights)

**GPU underutilized (0.14%)**
The logistic regression model is tiny. To use GPU:
- Run parallel sweeps (10+ configs simultaneously)
- Enable gradient boosting via optimizer_config.json
- Run bootstrap confidence intervals (1000 iterations)

## DAILY WORKFLOW

1. **Morning check**: `run_odin_system.bat status`
2. **If stopped**: `run_odin_system.bat` (restarts both)
3. **Quick health**: `run_odin_system.bat snapshot`
4. **If ALERT**: Check audit_history.jsonl, investigate manually
5. **Weekly**: `run_odin_system.bat sweep 50` for expanded hyperparameter search

## GPU UTILIZATION

Current: 17.6MB / 12,288MB (0.14%) — massive headroom.

Recommended upgrades in optimizer_config.json:
- Parallel sweeps (10+ simultaneous)
- LightGBM-GPU as model candidate
- Bootstrap resampling (1000 iterations for CI)
- Feature interaction expansion (3-way terms)
