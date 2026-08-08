#!/usr/bin/env python3
"""
ODIN Perpetual Honing Runner (companion to odin_honing_engine_v1249.py)

What it does:
  - Runs the honing engine in a loop
  - Version-tags outputs via --out_prefix (v####)
  - Updates the anchor for the next iteration ONLY if the run improved vs
    the baseline anchor (per the engine's metadata)

Usage examples:
  python odin_perpetual_honing_runner.py --engine odin_honing_engine_v1249.py --runs 50
  python odin_perpetual_honing_runner.py --start 1250 --runs 25 --anchor odin_anchor.json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

DEFAULT_ENGINE = "odin_honing_engine_v1249.py"
DEFAULT_ANCHOR = "odin_v1248_anchor.json"
DEFAULT_DATA   = "ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv"
DEFAULT_CONFIG = "odin_honing_config.json"
DEFAULT_LOG    = "perpetual_honing_log.txt"

def _read_meta(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj.get("honing_metadata", {}) or {}
    except Exception:
        return {}

def _improved(meta: dict, selection_metric: str) -> bool:
    """Return True if output improved vs the baseline anchor for this run."""
    selm = (selection_metric or meta.get("selection_metric") or "wf_brier").lower()
    eps = 1e-7

    base_val = meta.get("baseline_val_brier", None)
    base_wf  = meta.get("baseline_wf_brier", None)
    val_b    = meta.get("final_val_brier", None)
    wf_b     = meta.get("walk_forward_mean_brier", None)

    try:
        if selm == "val_brier" and base_val is not None and val_b is not None:
            return float(val_b) < float(base_val) - eps
        if selm == "wf_brier" and base_wf is not None and wf_b is not None:
            return float(wf_b) < float(base_wf) - eps

        # Default: blended (prefers WF) if possible, else val_brier
        if (base_wf is not None and wf_b is not None) and (base_val is not None and val_b is not None):
            base_blend = 0.65 * float(base_wf) + 0.35 * float(base_val)
            new_blend  = 0.65 * float(wf_b) + 0.35 * float(val_b)
            return new_blend < base_blend - eps

        if base_val is not None and val_b is not None:
            return float(val_b) < float(base_val) - eps
    except Exception:
        return False

    return False

def main():
    ap = argparse.ArgumentParser(description="Perpetual runner for ODIN honing engine")
    ap.add_argument("--engine", type=str, default=DEFAULT_ENGINE, help="Path to honing engine .py")
    ap.add_argument("--anchor", type=str, default=DEFAULT_ANCHOR, help="Anchor JSON path (updated only when improved)")
    ap.add_argument("--data", type=str, default=DEFAULT_DATA, help="Training CSV path")
    ap.add_argument("--config", type=str, default=DEFAULT_CONFIG, help="Config JSON path")
    ap.add_argument("--out_dir", type=str, default=".", help="Directory to write outputs")
    ap.add_argument("--start", type=int, default=1250, help="Starting version number (v####)")
    ap.add_argument("--runs", type=int, default=25, help="Number of perpetual iterations")
    ap.add_argument("--seed_base", type=int, default=None, help="Optional seed base; each run uses seed_base+run_idx")
    ap.add_argument("--log", type=str, default=DEFAULT_LOG, help="Append run summaries here")
    ap.add_argument("--selection_metric", type=str, default=None,
                    help="Override selection metric for this runner + engine via env var ODIN_SELECTION_METRIC")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    for i in range(args.runs):
        vnum = args.start + i
        prefix = f"v{vnum:04d}"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        seed = None
        if args.seed_base is not None:
            seed = int(args.seed_base) + i

        cmd = [
            sys.executable, args.engine,
            "--anchor", args.anchor,
            "--data", args.data,
            "--config", args.config,
            "--out_prefix", prefix,
        ]
        if seed is not None:
            cmd += ["--seed", str(seed)]

        env = os.environ.copy()
        if args.selection_metric:
            env["ODIN_SELECTION_METRIC"] = args.selection_metric

        print(f"\n[{ts}] Run {i+1}/{args.runs} → {prefix}")
        print("  " + " ".join(cmd))

        r = subprocess.run(cmd, cwd=args.out_dir, env=env)
        if r.returncode != 0:
            print(f"[ERROR] Engine returned code {r.returncode}. Stopping.")
            break

        best_path = os.path.join(args.out_dir, f"odin_{prefix}_best.json")
        if not os.path.exists(best_path):
            print(f"[ERROR] Missing expected best output: {best_path}. Stopping.")
            break

        meta = _read_meta(best_path)
        selm = meta.get("selection_metric", None) or (args.selection_metric or "wf_brier")
        improved = _improved(meta, selm)

        if improved:
            shutil.copy(best_path, args.anchor)
            anchor_note = "UPDATED"
            print(f"[Anchor] Updated → {args.anchor}")
        else:
            anchor_note = "KEPT"
            print(f"[Anchor] Not updated → {args.anchor} (no improvement)")

        line = (
            f"{ts} | {prefix} | kind={meta.get('type','selected')} | "
            f"val_brier={meta.get('final_val_brier',None)} | wf_brier={meta.get('walk_forward_mean_brier',None)} | "
            f"sel={selm} | anchor={anchor_note}"
        )

        with open(os.path.join(args.out_dir, args.log), "a", encoding="utf-8") as f:
            f.write(line + "\n")

        print(f"[Log] {line}")

        time.sleep(0.2)

if __name__ == "__main__":
    main()
