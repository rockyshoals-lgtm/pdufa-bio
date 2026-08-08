#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  9REALMS PERPETUAL UPDATE LOOP                                   ║
║                                                                  ║
║  Daily 6AM cron: benchmark → evolve → deploy (if beats v1071)   ║
║                                                                  ║
║  Crontab: 0 6 * * * cd /path/to/9realms && python               ║
║           mcp_core/9realms_update_loop.py                        ║
║                                                                  ║
║  Kill switches:                                                  ║
║    - V2.0 Tier4_Prec < v1071 → patches.json                     ║
║    - ALDX lift < 6pp → CEO module flagged                        ║
║    - Any candidate worse than v1071 → rejected                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import csv
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

REALMS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REALMS_ROOT / "mcp_core"))
sys.path.insert(0, str(REALMS_ROOT / "models"))

from benchmark_v1071 import (
    run_benchmark, daily_benchmark, load_v1071_weights,
    score_v1071, compute_auc, compute_brier, tier4_precision
)
from model_evolver import (
    generate_candidates, evaluate_candidate, save_champion
)
from aldx_stress_grid import make_aldx_signals, run_stress_grid


def log(msg: str, level: str = "INFO"):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)

    # Also append to alerts
    alerts_dir = REALMS_ROOT / "alerts"
    alerts_dir.mkdir(exist_ok=True)
    with open(alerts_dir / "slack_results.txt", "a") as f:
        f.write(line + "\n")


def check_kill_switches(v1071_metrics: dict, v2_metrics: dict,
                         aldx_v1071: float, aldx_v2: float) -> list:
    """Check all kill switches. Return list of triggered switches."""
    triggered = []

    # Kill switch 1: V2 Tier4 precision < v1071
    if v2_metrics["Tier4_Precision"] < v1071_metrics["Tier4_Precision"]:
        triggered.append({
            "switch": "TIER4_PRECISION_REGRESSION",
            "v1071": v1071_metrics["Tier4_Precision"],
            "v2": v2_metrics["Tier4_Precision"],
            "action": "PATCH — revert V2 module weights",
        })

    # Kill switch 2: ALDX lift < 6pp
    aldx_lift_pp = (aldx_v2 - aldx_v1071) * 100
    if aldx_lift_pp < 6.0:
        triggered.append({
            "switch": "ALDX_LIFT_INSUFFICIENT",
            "lift_pp": round(aldx_lift_pp, 1),
            "threshold": 6.0,
            "action": "FLAG — CEO module needs recalibration",
        })

    # Kill switch 3: AUC regression > 0.005
    if v2_metrics["AUC"] < v1071_metrics["AUC"] - 0.005:
        triggered.append({
            "switch": "AUC_REGRESSION",
            "v1071": v1071_metrics["AUC"],
            "v2": v2_metrics["AUC"],
            "action": "BLOCK — do not deploy",
        })

    return triggered


def run_evolution_cycle(n_candidates: int = 3):
    """Generate and evaluate candidate models."""
    from ULTIMATE_ODIN_V2 import W_ULTIMATE

    holdout_path = REALMS_ROOT / "data" / "daily_holdout.csv"
    if not holdout_path.exists():
        log("No daily_holdout.csv — running benchmark first", "WARN")
        daily_benchmark()

    if not holdout_path.exists():
        log("Still no holdout after benchmark — skipping evolution", "ERROR")
        return None

    seed = int(datetime.utcnow().strftime("%Y%m%d"))
    candidates = generate_candidates(dict(W_ULTIMATE), n_candidates, seed)

    best_candidate = None
    best_tier4 = 0

    for c in candidates:
        try:
            metrics = evaluate_candidate(c["weights"], str(holdout_path))
            c["metrics"] = metrics
            log(f"  {c['version']}: AUC={metrics['AUC']}, T4P={metrics['Tier4_Precision']:.1%}")

            if metrics["Tier4_Precision"] > best_tier4:
                best_tier4 = metrics["Tier4_Precision"]
                best_candidate = c
        except Exception as e:
            log(f"  {c['version']}: FAILED — {e}", "ERROR")

    return best_candidate


def main():
    """Main daily loop: benchmark → evolve → deploy."""
    log("=" * 60)
    log("9REALMS DAILY UPDATE LOOP STARTING")
    log("=" * 60)

    # ── Step 1: Run benchmark ──
    log("STEP 1: Running v1071 vs V2.0 benchmark...")
    try:
        metrics = daily_benchmark()
    except Exception as e:
        log(f"Benchmark FAILED: {e}", "ERROR")
        traceback.print_exc()
        return

    v1071_m = metrics["v1071"]
    v2_m = metrics["V2.0"]
    log(f"  v1071: AUC={v1071_m['AUC']}, T4P={v1071_m['Tier4_Precision']:.1%}")
    log(f"  V2.0:  AUC={v2_m['AUC']}, T4P={v2_m['Tier4_Precision']:.1%}")

    # ── Step 2: ALDX acid test ──
    log("STEP 2: Running ALDX stress grid...")
    try:
        from ULTIMATE_ODIN_V2 import UltimateOdinScorer, CeoTone, MarketRegime

        scorer = UltimateOdinScorer()
        # Baseline (no V2 modules)
        baseline_sig = make_aldx_signals(CeoTone.NEUTRAL, False, MarketRegime.NORMAL)
        baseline_result = scorer.score(baseline_sig)
        aldx_v1071 = baseline_result["probability"]

        # V2 (bullish + quiet review)
        v2_sig = make_aldx_signals(CeoTone.BULLISH, True, MarketRegime.NORMAL)
        v2_result = scorer.score(v2_sig)
        aldx_v2 = v2_result["probability"]

        log(f"  ALDX baseline: {aldx_v1071:.4f}")
        log(f"  ALDX V2 (bullish+quiet): {aldx_v2:.4f} (+{(aldx_v2-aldx_v1071)*100:.1f}pp)")
    except Exception as e:
        log(f"ALDX test FAILED: {e}", "ERROR")
        aldx_v1071, aldx_v2 = 0, 0

    # ── Step 3: Kill switches ──
    log("STEP 3: Checking kill switches...")
    kills = check_kill_switches(v1071_m, v2_m, aldx_v1071, aldx_v2)
    if kills:
        for k in kills:
            log(f"  ⚠ KILL SWITCH: {k['switch']} → {k['action']}", "WARN")

        # Save patches.json
        patches_path = REALMS_ROOT / "validation" / "patches.json"
        with open(patches_path, "w") as f:
            json.dump({"date": datetime.utcnow().isoformat(), "kills": kills}, f, indent=2)
        log(f"  Saved patches: {patches_path}")
    else:
        log("  All kill switches CLEAR ✓")

    # ── Step 4: Evolution cycle ──
    log("STEP 4: Running evolution cycle (3 candidates)...")
    try:
        best = run_evolution_cycle(n_candidates=3)
        if best and best.get("metrics"):
            bm = best["metrics"]
            log(f"  Best candidate: {best['version']} "
                f"(AUC={bm['AUC']}, T4P={bm['Tier4_Precision']:.1%})")

            # Only deploy if beats v1071 Tier4 precision
            if bm["Tier4_Precision"] > v1071_m["Tier4_Precision"]:
                version_tag = f"v2.{datetime.utcnow().strftime('%Y%m%d')}"
                save_champion(best, bm, version_tag)
                log(f"  NEW CHAMPION: {version_tag} → "
                    f"T4P {bm['Tier4_Precision']:.1%} > {v1071_m['Tier4_Precision']:.1%}", "ALERT")
            else:
                log(f"  No improvement over v1071 — candidate rejected")
        else:
            log("  No viable candidates produced")
    except Exception as e:
        log(f"Evolution FAILED: {e}", "ERROR")
        traceback.print_exc()

    # ── Summary ──
    log("=" * 60)
    log("9REALMS DAILY UPDATE COMPLETE")
    log(f"  v1071 AUC: {v1071_m['AUC']}")
    log(f"  V2.0  AUC: {v2_m['AUC']}")
    log(f"  Kill switches: {len(kills)} triggered")
    log("=" * 60)


if __name__ == "__main__":
    main()
