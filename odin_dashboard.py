#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN DASHBOARD v1.0                                                   ║
║  Real-time system health monitor (text-based)                          ║
║                                                                        ║
║  Reads:                                                                ║
║    - model_weights.json (current live model)                           ║
║    - audit_snapshot.json (last perpetual_loop output)                  ║
║    - audit_history.jsonl (audit_cycle trail)                           ║
║    - best_run_AUC_*.json (training runs)                               ║
║    - events.json / watchlist.json (pipeline status)                    ║
║                                                                        ║
║  Modes:                                                                ║
║    status  — One-shot system status (default)                          ║
║    watch   — Auto-refresh every 60 seconds (Ctrl+C to stop)           ║
║    history — Show last N audit actions                                 ║
║    best    — Show top 10 best runs                                     ║
║                                                                        ║
║  Run:  python odin_dashboard.py                                        ║
║        python odin_dashboard.py --mode watch                           ║
║  Deps: none (stdlib only)                                              ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import sys
import glob
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ═══════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════

ODIN_DATA = Path(os.environ.get("ODIN_DATA", Path.home() / "odin_data"))
PYTHON_DIR = Path(os.environ.get("ODIN_CODE", Path.home() / "Documents" / "Python"))

WEIGHTS_FILE = ODIN_DATA / "model_weights.json"
SNAPSHOT_FILE = ODIN_DATA / "audit_snapshot.json"
HISTORY_FILE = ODIN_DATA / "audit_history.jsonl"
EVENTS_FILE = ODIN_DATA / "events.json"
WATCHLIST_FILE = ODIN_DATA / "watchlist.json"
VERSIONS_FILE = ODIN_DATA / "versions.json"
LOOP_LOG = ODIN_DATA / "perpetual_loop.log"

BASELINE_AUC = 0.9085
BASELINE_BRIER = 0.114


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return default


def load_jsonl(path: Path, max_lines: int = 100) -> list:
    if not path.exists():
        return []
    lines = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return lines[-max_lines:]


def find_best_runs(top_n: int = 10) -> list:
    patterns = [
        str(ODIN_DATA / "best_run_AUC_*.json"),
        str(ODIN_DATA / "best_runs" / "best_run_AUC_*.json"),
    ]
    all_files = []
    for p in patterns:
        all_files.extend(glob.glob(p))

    runs = []
    for f in all_files:
        try:
            name = os.path.basename(f)
            parts = name.replace("best_run_AUC_", "").replace(".json", "")
            auc_str = parts.split("_")[0]
            auc = float(auc_str)
            mtime = os.path.getmtime(f)
            runs.append({
                "file": name,
                "auc": auc,
                "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                "path": f,
            })
        except (IndexError, ValueError):
            pass

    runs.sort(key=lambda x: x["auc"], reverse=True)
    return runs[:top_n]


def file_age_str(path: Path) -> str:
    if not path.exists():
        return "N/A"
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    delta = datetime.now() - mtime
    if delta.total_seconds() < 60:
        return f"{int(delta.total_seconds())}s ago"
    elif delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() / 60)}m ago"
    elif delta.total_seconds() < 86400:
        return f"{delta.total_seconds() / 3600:.1f}h ago"
    else:
        return f"{delta.days}d ago"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ═══════════════════════════════════════════════════════════════
#  DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def display_header():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║              ODIN PERPETUAL LOOP — DASHBOARD                   ║")
    print(f"║  {now}                                          ║")
    print("╚══════════════════════════════════════════════════════════════════╝")


def display_model_status():
    print()
    print("┌─ MODEL STATUS ──────────────────────────────────────────────────┐")

    weights = load_json(WEIGHTS_FILE)
    if not weights:
        print("│  ❌ model_weights.json not found or invalid                    │")
        print("└────────────────────────────────────────────────────────────────┘")
        return

    base_logit = weights.get("base_logit", 0)
    signals = weights.get("signals", {})
    sig_count = len(signals)

    # Try to get AUC from snapshot or versions
    snapshot = load_json(SNAPSHOT_FILE)
    current_auc = None
    current_brier = None
    if snapshot:
        current_auc = snapshot.get("model", {}).get("val_auc") or snapshot.get("current_auc")
        current_brier = snapshot.get("model", {}).get("val_brier") or snapshot.get("current_brier")

    # Best run
    best_runs = find_best_runs(1)
    best_auc = best_runs[0]["auc"] if best_runs else None

    auc_display = f"{current_auc:.4f}" if current_auc else "unknown"
    brier_display = f"{current_brier:.4f}" if current_brier else "unknown"
    best_display = f"{best_auc:.4f}" if best_auc else "none"

    # AUC health indicator
    if current_auc and current_auc > BASELINE_AUC:
        auc_icon = "🟢"
    elif current_auc and current_auc > BASELINE_AUC - 0.005:
        auc_icon = "🟡"
    elif current_auc:
        auc_icon = "🔴"
    else:
        auc_icon = "⚪"

    weights_age = file_age_str(WEIGHTS_FILE)

    print(f"│  Base Logit:     {base_logit:.4f}                                     │")
    print(f"│  Signal Weights: {sig_count}                                            │")
    print(f"│  Weights Age:    {weights_age:<20}                           │")
    print(f"│  {auc_icon} Live AUC:      {auc_display}  (baseline: {BASELINE_AUC})            │")
    print(f"│  Brier Score:    {brier_display}  (baseline: {BASELINE_BRIER})            │")
    print(f"│  Best Run AUC:   {best_display}                                     │")
    print("└────────────────────────────────────────────────────────────────┘")


def display_pipeline_status():
    print()
    print("┌─ PIPELINE STATUS ───────────────────────────────────────────────┐")

    # Events
    events = load_json(EVENTS_FILE)
    if isinstance(events, list):
        total_events = len(events)
        labeled = sum(1 for e in events if e.get("outcome") is not None)
        unlabeled = total_events - labeled
    elif isinstance(events, dict) and "events" in events:
        evts = events["events"]
        total_events = len(evts)
        labeled = sum(1 for e in evts if e.get("outcome") is not None)
        unlabeled = total_events - labeled
    else:
        total_events = 0
        labeled = 0
        unlabeled = 0

    # Watchlist
    watchlist = load_json(WATCHLIST_FILE, default={})
    if isinstance(watchlist, list):
        watch_count = len(watchlist)
    elif isinstance(watchlist, dict):
        watch_count = len(watchlist.get("events", watchlist.get("tickers", [])))
    else:
        watch_count = 0

    # Snapshot age
    snapshot_age = file_age_str(SNAPSHOT_FILE)
    loop_log_age = file_age_str(LOOP_LOG)

    print(f"│  Events Total:   {total_events}                                          │")
    print(f"│  Labeled:        {labeled}   |   Unlabeled: {unlabeled:<4}                    │")
    print(f"│  Watchlist:      {watch_count}                                              │")
    print(f"│  Last Snapshot:  {snapshot_age:<20}                           │")
    print(f"│  Last Loop Log:  {loop_log_age:<20}                           │")
    print("└────────────────────────────────────────────────────────────────┘")


def display_audit_status():
    print()
    print("┌─ AUDIT CYCLE STATUS ────────────────────────────────────────────┐")

    history = load_jsonl(HISTORY_FILE, max_lines=10)

    if not history:
        print("│  No audit history yet (run: python audit_cycle.py --mode auto) │")
        print("└────────────────────────────────────────────────────────────────┘")
        return

    last = history[-1]
    last_action = last.get("action", "unknown")
    last_severity = last.get("severity", "unknown")
    last_time = last.get("timestamp", "unknown")
    last_reason = last.get("reason", "")

    # Count actions in history
    action_counts = {}
    for entry in history:
        a = entry.get("action", "unknown")
        action_counts[a] = action_counts.get(a, 0) + 1

    total_audits = len(history)

    # Status icon
    icon_map = {
        "HOLD": "🟢", "PROMOTE": "🟢",
        "RETRAIN": "🟡", "TUNE": "🟡", "EXPAND": "🟡",
        "ALERT": "🔴",
    }
    icon = icon_map.get(last_action, "⚪")

    print(f"│  {icon} Last Action:   {last_action} ({last_severity})                        │")
    if last_reason:
        reason_trunc = last_reason[:52]
        print(f"│     Reason:      {reason_trunc:<52} │")
    print(f"│     Timestamp:   {str(last_time)[:30]:<30}                   │")
    print(f"│  Total Audits:   {total_audits}                                          │")
    print(f"│  Action History: {str(action_counts)[:50]:<50} │")
    print("└────────────────────────────────────────────────────────────────┘")


def display_best_runs(top_n: int = 10):
    print()
    print("┌─ TOP TRAINING RUNS ─────────────────────────────────────────────┐")

    runs = find_best_runs(top_n)
    if not runs:
        print("│  No best_run_AUC_*.json files found                            │")
        print("└────────────────────────────────────────────────────────────────┘")
        return

    print(f"│  {'#':<3} {'AUC':<10} {'Modified':<18} {'File':<30} │")
    print(f"│  {'─'*3} {'─'*10} {'─'*18} {'─'*30} │")

    for i, run in enumerate(runs, 1):
        auc_str = f"{run['auc']:.4f}"
        delta = run["auc"] - BASELINE_AUC
        delta_str = f"(+{delta:.4f})" if delta > 0 else f"({delta:.4f})"
        icon = "🏆" if i == 1 else "  "
        fname = run["file"][:28]
        print(f"│{icon}{i:<2} {auc_str:<10} {run['modified']:<18} {fname:<30} │")

    print("└────────────────────────────────────────────────────────────────┘")


def display_process_status():
    """Check if perpetual_loop and audit_cycle are running (Windows)."""
    print()
    print("┌─ PROCESS STATUS ────────────────────────────────────────────────┐")

    if os.name == "nt":
        import subprocess
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5
            )
            py_count = result.stdout.count("python.exe") - 1  # Subtract header
            if py_count < 0:
                py_count = 0
            print(f"│  Python processes running: {py_count}                                 │")
        except Exception:
            print("│  Cannot check process status                                  │")
    else:
        print("│  Process check not implemented for this OS                     │")

    print("└────────────────────────────────────────────────────────────────┘")


# ═══════════════════════════════════════════════════════════════
#  MAIN MODES
# ═══════════════════════════════════════════════════════════════

def mode_status():
    display_header()
    display_model_status()
    display_pipeline_status()
    display_audit_status()
    display_process_status()
    print()


def mode_watch(interval: int = 60):
    print("ODIN Dashboard — auto-refresh mode (Ctrl+C to stop)")
    try:
        while True:
            clear_screen()
            mode_status()
            print(f"  ⏳ Refreshing in {interval}s... (Ctrl+C to stop)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Dashboard stopped.")


def mode_history(n: int = 20):
    display_header()
    print()
    print(f"┌─ AUDIT HISTORY (last {n}) ────────────────────────────────────────┐")

    history = load_jsonl(HISTORY_FILE, max_lines=n)
    if not history:
        print("│  No audit history found.                                       │")
        print("└────────────────────────────────────────────────────────────────┘")
        return

    for entry in reversed(history):
        ts = str(entry.get("timestamp", "?"))[:19]
        action = entry.get("action", "?")
        severity = entry.get("severity", "?")
        reason = entry.get("reason", "")[:40]
        icon = {"HOLD": "🟢", "PROMOTE": "⬆️", "RETRAIN": "🔄", "TUNE": "🔧",
                "EXPAND": "📊", "ALERT": "🚨"}.get(action, "❓")
        print(f"│  {icon} {ts}  {action:<10} {severity:<8} {reason:<40} │")

    print("└────────────────────────────────────────────────────────────────┘")
    print()


def mode_best():
    display_header()
    display_best_runs(20)
    print()


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ODIN Dashboard")
    parser.add_argument("--mode", choices=["status", "watch", "history", "best"],
                        default="status", help="Dashboard mode")
    parser.add_argument("--interval", type=int, default=60, help="Watch refresh interval (seconds)")
    parser.add_argument("-n", type=int, default=20, help="Number of history entries")

    args = parser.parse_args()

    if args.mode == "status":
        mode_status()
    elif args.mode == "watch":
        mode_watch(args.interval)
    elif args.mode == "history":
        mode_history(args.n)
    elif args.mode == "best":
        mode_best()
