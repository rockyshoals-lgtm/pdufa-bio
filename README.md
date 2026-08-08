# ODIN v38.a — Billion-Iteration Improvement Bundle

This bundle is a **local brute-force / GPU-friendly search runner** designed to:
- Start from your latest **top configs** (`ODIN_TOP_CONFIGS_V5.json`)
- Run massive **random+local refinement** searches (billions of iterations feasible locally)
- Enforce **hard precision floor** (default: 0.94)
- Optimize for **FP aversion + calibration** (FP ↓, Brier ↓, MCC ↑)

## What’s inside
- `run_billion_search.py` — main search runner (CPU numpy; optional GPU via CuPy if installed)
- `odin_score.py` — scoring + metrics (vectorized)
- `config_space.py` — param bounds + local perturbation logic seeded from your top configs
- `io_utils.py` — dataset loading + column mapping + run hashing + output logging
- `requirements.txt`
- `examples/` — example commands and output schema

## Expected datasets
Point `--data` to one of your authoritative T-1 safe datasets, e.g.
- `ODIN_ENRICHED_PDUFA_1349_v2.csv`

If your column names differ, edit `COLUMN_MAP` in `io_utils.py`.

## Quick start
```bash
python run_billion_search.py \
  --data /path/to/ODIN_ENRICHED_PDUFA_1349_v2.csv \
  --top-configs /path/to/ODIN_TOP_CONFIGS_V5.json \
  --outdir ./outputs/v38a_run1 \
  --iters 50000000 \
  --batch 250000 \
  --min-precision 0.94
```

## Notes (important)
- This bundle **does not scrape** anything and is **T-1 compliant** as long as your input CSV is.
- The scorer is a **parameterized signal-based model** aligned to your provided config fields.
- If you have a more exact scoring equation already, swap it into `odin_score.py::score_probs()`
  (everything else stays the same).

Generated: 2026-01-23T17:17:36.676115


## Windows CMD note: avoid the `More?` prompt
If you accidentally paste Python traceback caret-lines like `^^^^^^^^^^` into CMD, CMD treats `^` as a line-continuation
escape and will show `More?` and then try to execute traceback lines as commands.

If you see `More?`:
- press **Ctrl+C** to cancel
- then re-run your `python run_billion_search.py ...` command


## Patch 3
- Fixed an indentation bug in `run_billion_search.py` introduced by Patch 2 (unindented `top_cfgs = ...` line).
