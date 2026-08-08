
# ODIN Signal Discovery Harness (v38)

This folder contains a **T-1-safe**, audit-friendly harness for ODIN's *signal discovery* workflow:

- **Signal Registry**: a single place to define candidate signals (metadata + function).
- **Marginal tests**: Baseline vs Baseline + single signal.
- **Leave-one-out ablation**: on a chosen multi-signal bundle.
- **FP-averse evaluation**: selects a decision threshold that meets **Precision ≥ 0.94** and then minimizes **FP count**.

## Quickstart

### Linux/macOS/WSL (bash)

```bash
python run_v38a_signal_discovery.py \
  --dataset /mnt/data/ODIN_ENRICHED_PDUFA_1349_v2.csv \
  --baseline-config /mnt/data/ODIN_v88_UNIFIED_CONFIG.json \
  --outdir /mnt/data/odin_runs/v38.a \
  --version v38.a
```

### Windows (Command Prompt)

Important: the `\` line-continuation shown above is **bash-specific**. In `cmd.exe`, use `^` for line continuation, or just put everything on one line.

```bat
cd C:\Users\dcmoo\Documents\Python\ODIN_signal_harness_v38

python run_v38a_signal_discovery.py ^
  --dataset "C:\path\to\ODIN_ENRICHED_PDUFA_1349_v2.csv" ^
  --baseline-config "C:\path\to\ODIN_v88_UNIFIED_CONFIG.json" ^
  --outdir "C:\path\to\odin_runs\v38.b" ^
  --version v38.b
```

### Windows (PowerShell)

In PowerShell, use the backtick `` ` `` for line continuation:

```powershell
cd C:\Users\dcmoo\Documents\Python\ODIN_signal_harness_v38

python .\run_v38a_signal_discovery.py `
  --dataset "C:\path\to\ODIN_ENRICHED_PDUFA_1349_v2.csv" `
  --baseline-config "C:\path\to\ODIN_v88_UNIFIED_CONFIG.json" `
  --outdir "C:\path\to\odin_runs\v38.b" `
  --version v38.b
```

Note: paths like `/mnt/data/...` are from the ChatGPT sandbox / Linux examples. On Windows, always use your local `C:\...` paths (or run under WSL and keep the Linux paths).



### Windows wrapper scripts (recommended)

To avoid both common Windows pitfalls (line continuation + local package import), this bundle includes:

- `run_v38a_signal_discovery.cmd` (Command Prompt wrapper)
- `run_v38a_signal_discovery.ps1` (PowerShell wrapper)

These wrappers automatically set `PYTHONPATH` to the harness folder and forward all arguments to Python.

**cmd.exe example (one line):**

```bat
cd C:\Users\dcmoo\Documents\Python\ODIN_signal_harness_v38
run_v38a_signal_discovery.cmd --dataset "C:\path\to\ODIN_ENRICHED_PDUFA_1349_v2.csv" --baseline-config "C:\path\to\ODIN_v88_UNIFIED_CONFIG.json" --outdir "C:\path\to\odin_runs\v38.b" --version v38.b --ram-mode dynamic --ram-frac-available 0.35 --ram-reserve-gb 4 --ram-recompute-every-s 1.0
```

### Optional: dynamic RAM-aware signal caching

Signal discovery can re-compute the same signal outputs many times (especially
in leave-one-out ablations). You can enable an in-memory cache that is bounded
by a **RAM budget**.

The budget can be:
- `off` (default): no caching (original behavior)
- `fixed`: cache budget is a fixed number of GB
- `dynamic`: cache budget scales with *current available RAM* (and shrinks under
  high memory pressure)

Example (dynamic):

```bash
python run_v38a_signal_discovery.py \
  --dataset /mnt/data/ODIN_ENRICHED_PDUFA_1349_v2.csv \
  --baseline-config /mnt/data/ODIN_v88_UNIFIED_CONFIG.json \
  --outdir /mnt/data/odin_runs/v38.a \
  --version v38.a \
  --ram-mode dynamic \
  --ram-frac-available 0.35 \
  --ram-reserve-gb 4
```

Outputs:
- `marginal_tests.csv`
- `run_manifest.json` (includes immutable `run_hash`)
- (optional) `ablations.csv`

## Built-in signals (initial)

Backtestable now (from the core dataset):
- `rolling_t1_reference_base_rate` (base prior override)
- `adcom_vote_curve` (continuous vote% curve adjustment)
- `trap_v2_stack4_inexp_non_orphan`
- `form_483_flag`

Stubbed (requires enrichment columns):
- `publication_velocity` (PubMed recent vs lifetime)

Add more signals by registering them in `build_registry()`.

## Design constraints

- **Improvement-only**: this harness only evaluates historical rows; it does not make forward predictions.
- **T-1 compliance**: rolling base rates are computed using only *prior* events (strictly before the row's `catalyst_date`).
- **UNKNOWN stays UNKNOWN**: missing values are treated as neutral (no imputation to True/False).
## Troubleshooting

### `ModuleNotFoundError: No module named 'odin_signal_harness'`

That means Python can't see the local package folder. Fix by ensuring you did **not** copy the runner script by itself.

Expected structure:

- `ODIN_signal_harness_v38/`
  - `run_v38a_signal_discovery.py`
  - `odin_signal_harness/`
    - `__init__.py`
    - `registry.py`
    - ...

Then run the script from inside `ODIN_signal_harness_v38/` (recommended).


## Windows quality-of-life wrappers

This bundle includes two wrappers that eliminate common Windows issues (cwd + imports):

- `run_v38a_signal_discovery.cmd` (Command Prompt)
- `run_v38a_signal_discovery.ps1` (PowerShell)

From inside `ODIN_signal_harness_v38`, you can run:

```bat
run_v38a_signal_discovery.cmd --dataset "C:\path\to\ODIN_ENRICHED_PDUFA_1349_v2.csv" --baseline-config "C:\path\to\ODIN_v88_UNIFIED_CONFIG.json" --outdir "C:\path\to\odin_runs\v38.b" --version v38.b
```
