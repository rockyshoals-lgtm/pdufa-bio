#!/usr/bin/env python3
"""
ODIN DAEMON v1.0 -- 2026-05-28
Continuous + scheduled autonomous improvement loop.

ARCHITECTURE
------------
Tier 1 (CONTINUOUS, market-hours): scanner refresh + auto-postmortem
Tier 2 (WEEKLY BATCH, Sunday 06:00): feature mining + weight optimization (GATED PROPOSALS)

All changes write to alerts/ for David's review. NOTHING auto-ships to production.

USAGE
-----
python odin_daemon.py                    # run continuously
python odin_daemon.py --once             # one cycle then exit (for testing)
python odin_daemon.py --tier1-only       # skip Sunday batch
python odin_daemon.py --tier2-only       # only run Sunday batch (testing)
python odin_daemon.py --dry-run          # no FMP calls, no file writes (smoke test)

INSTALL
-------
1. Place at C:\\Users\\dcmoo\\Documents\\Python\\9realms\\odin_daemon.py
2. Place support scripts at same location:
   - runner.py (scanner)
   - auto_postmortem_v1.py
   - feature_miner_v1.py
   - overlay_weight_optimizer_v1.py
3. Ensure FMP_API_KEY is in env (you did setx)
4. Run: python odin_daemon.py
5. To run in background (Windows):
   start /B python odin_daemon.py > daemon_stdout.log 2>&1

LOGS / ALERTS
-------------
Daemon writes to:
  daemon_logs/2026-05-28_daemon.log         (everything)
  alerts/2026-05-28_HIGH_PRIORITY.md        (tier flips, big moves, new catalysts)
  alerts/2026-05-28_PROPOSALS.md            (weekly feature/weight proposals -- needs your review)
"""

import os
import sys
import json
import time
import subprocess
import argparse
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================================
# CONFIG
# ============================================================================
HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "daemon_logs"
ALERT_DIR = HERE / "alerts"
PROPOSAL_DIR = HERE / "proposals"
for d in [LOG_DIR, ALERT_DIR, PROPOSAL_DIR]:
    d.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "tier1_cadence_minutes": 30,         # scanner refresh + postmortem cycle
    "tier1_market_open_et": "09:30",
    "tier1_market_close_et": "16:00",
    "tier1_postclose_run_et": "16:30",
    "tier2_run_day": "Sunday",
    "tier2_run_time_local": "06:00",
    "scanner_script": "runner.py",
    "postmortem_script": "auto_postmortem_v1.py",
    "feature_miner_script": "feature_miner_v1.py",
    "overlay_optimizer_script": "overlay_weight_optimizer_v1.py",
    "high_priority_alert_thresholds": {
        "tier_flip_pp": 5.0,              # ODIN score change >= 5pp
        "price_move_pct": 20.0,           # any tracked V-ID moves >= 20%
        "new_catalyst_score": 50.0        # new event in calendar scores >= 50
    },
    "throttle": {
        "max_fmp_calls_per_minute": 50,
        "min_seconds_between_cycles": 30,
    },
    "python_executable": sys.executable,
}

CONFIG_PATH = HERE / "odin_daemon_config.json"
def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                user_cfg = json.load(f)
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(user_cfg)
            return cfg
        except Exception as e:
            log(f"WARNING: Could not load config, using defaults: {e}")
    # Write defaults
    with open(CONFIG_PATH, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG

# ============================================================================
# LOGGING
# ============================================================================
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {level} {msg}"
    print(line, flush=True)
    log_path = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_daemon.log"
    try:
        with open(log_path, 'a') as f:
            f.write(line + "\n")
    except Exception:
        pass

def alert(msg, level="HIGH_PRIORITY"):
    """Write a high-visibility alert to alerts/ dir for David's review."""
    ts = datetime.now().strftime("%H:%M:%S")
    alert_path = ALERT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_{level}.md"
    try:
        existing = alert_path.read_text() if alert_path.exists() else f"# Daemon Alerts -- {datetime.now().strftime('%Y-%m-%d')} ({level})\n\n"
    except Exception:
        existing = f"# Daemon Alerts -- {datetime.now().strftime('%Y-%m-%d')} ({level})\n\n"
    with open(alert_path, 'w') as f:
        f.write(existing + f"\n### {ts}\n{msg}\n")
    log(f"ALERT_{level}: {msg[:80]}", level=level)

# ============================================================================
# MARKET HOURS HELPER (ET-aware)
# ============================================================================
def is_market_hours(now=None):
    """Approximate ET market hours check. Doesn't handle DST perfectly; close enough for v1."""
    now = now or datetime.now()
    # Skip weekends
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    # Local time -> ET. User on Windows; assume PT or similar. For v1, just check 06:30-13:00 local
    # which corresponds to 09:30-16:00 ET if user is on PT. Adjust if needed via config.
    # Better: just allow any time, let the underlying APIs return what they return.
    # Cleaner: assume daemon runs locally and ET = local + 3hr (PT) or local + 0 (ET).
    # For v1, just check the LOCAL hour bracket -- works as long as user runs from one timezone.
    hour = now.hour
    if 6 <= hour <= 17:  # generous window covers ET regardless of where user is
        return True
    return False

def is_sunday_batch_time(now=None):
    now = now or datetime.now()
    # Sunday + 06:00-07:00 local
    return now.weekday() == 6 and 6 <= now.hour < 7

# ============================================================================
# SUBPROCESS RUNNER
# ============================================================================
def run_script(script_name, args=None, timeout=300):
    """Run a Python script as subprocess, capture output."""
    cfg = load_config()
    script_path = HERE / script_name
    if not script_path.exists():
        log(f"Script not found: {script_path}", level="ERROR")
        return {"returncode": -1, "stdout": "", "stderr": f"Script not found: {script_path}"}
    cmd = [cfg["python_executable"], str(script_path)] + (args or [])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(HERE))
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],   # truncate massive output
            "stderr": result.stderr[-1000:],
        }
    except subprocess.TimeoutExpired:
        log(f"Script timeout: {script_name}", level="ERROR")
        return {"returncode": -2, "stdout": "", "stderr": "TIMEOUT"}
    except Exception as e:
        log(f"Script error: {script_name}: {e}", level="ERROR")
        return {"returncode": -3, "stdout": "", "stderr": str(e)}

# ============================================================================
# TIER 1 -- CONTINUOUS DURING MARKET HOURS
# ============================================================================
def tier1_cycle(cfg, dry_run=False):
    """Run scanner refresh + auto-postmortem cycle."""
    log("=== Tier 1 cycle START ===")
    cycle_start = time.time()
    results = {}

    # 1. Scanner refresh
    log("Running scanner refresh...")
    if not dry_run:
        scanner_result = run_script(cfg["scanner_script"])
        results["scanner"] = scanner_result
        if scanner_result["returncode"] != 0:
            log(f"Scanner failed: {scanner_result['stderr'][:200]}", level="ERROR")
        else:
            log(f"Scanner OK")
            # Check output for NEW high-score events
            if "NEW events flagged:" in scanner_result["stdout"]:
                try:
                    line = next(l for l in scanner_result["stdout"].split("\n") if "NEW events flagged:" in l)
                    n_new = int(line.split(":")[1].strip())
                    if n_new > 0:
                        alert(f"Scanner detected {n_new} NEW catalyst events. Review phase_readout_new_events_*.csv.", level="HIGH_PRIORITY")
                except Exception:
                    pass

    # 2. Auto-postmortem (if today is a market day and we're at/past close)
    now = datetime.now()
    if is_market_hours(now) or (now.hour >= 16 and now.weekday() < 5):
        log("Running auto-postmortem check...")
        if not dry_run:
            pm_result = run_script(cfg["postmortem_script"])
            results["postmortem"] = pm_result
            if pm_result["returncode"] != 0:
                log(f"Postmortem failed: {pm_result['stderr'][:200]}", level="ERROR")
            else:
                log("Postmortem OK")
                # Check output for FIRED catalysts
                if "FIRED:" in pm_result["stdout"]:
                    for line in pm_result["stdout"].split("\n"):
                        if line.strip().startswith("FIRED:"):
                            alert(f"Catalyst FIRED: {line.strip()[7:]}", level="HIGH_PRIORITY")

    elapsed = time.time() - cycle_start
    log(f"=== Tier 1 cycle END ({elapsed:.1f}s) ===")
    return results

# ============================================================================
# TIER 2 -- WEEKLY SUNDAY BATCH
# ============================================================================
def tier2_batch(cfg, dry_run=False):
    """Run feature mining + overlay weight optimization. Outputs PROPOSALS only."""
    log("=== Tier 2 weekly batch START ===")
    batch_start = time.time()
    results = {}

    # 1. Feature mining (ODIN/GUNGNIR/BIFROST)
    log("Running feature mining...")
    if not dry_run:
        fm_result = run_script(cfg["feature_miner_script"], timeout=1800)  # 30 min budget
        results["feature_miner"] = fm_result
        if fm_result["returncode"] == 0 and "PROPOSAL:" in fm_result["stdout"]:
            alert(f"Feature mining produced proposals. Review proposals/ dir.", level="PROPOSALS")

    # 2. Overlay weight optimization
    log("Running overlay weight optimization...")
    if not dry_run:
        ow_result = run_script(cfg["overlay_optimizer_script"], timeout=1800)
        results["overlay_optimizer"] = ow_result
        if ow_result["returncode"] == 0 and "PROPOSAL:" in ow_result["stdout"]:
            alert(f"Overlay weight optimization produced proposals. Review proposals/ dir.", level="PROPOSALS")

    elapsed = time.time() - batch_start
    log(f"=== Tier 2 weekly batch END ({elapsed:.1f}s) ===")
    return results

# ============================================================================
# MAIN LOOP
# ============================================================================
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--once', action='store_true', help='Run one cycle then exit')
    p.add_argument('--tier1-only', action='store_true', help='Skip weekly batch')
    p.add_argument('--tier2-only', action='store_true', help='Only run weekly batch (testing)')
    p.add_argument('--dry-run', action='store_true', help='No subprocess calls, no file writes')
    args = p.parse_args()

    cfg = load_config()
    log(f"ODIN DAEMON v1.0 starting. Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    log(f"Tier 1 cadence: {cfg['tier1_cadence_minutes']}min. Tier 2: weekly Sunday.")
    log(f"Logs: {LOG_DIR}")
    log(f"Alerts: {ALERT_DIR}")

    if args.tier2_only:
        tier2_batch(cfg, dry_run=args.dry_run)
        return

    if args.once:
        tier1_cycle(cfg, dry_run=args.dry_run)
        if not args.tier1_only and is_sunday_batch_time():
            tier2_batch(cfg, dry_run=args.dry_run)
        return

    # Continuous loop
    last_tier2_run = None
    last_tier1_run = None
    cycle_sec = cfg["tier1_cadence_minutes"] * 60
    min_gap = cfg["throttle"]["min_seconds_between_cycles"]

    while True:
        try:
            now = datetime.now()
            today = now.date()

            # Tier 2: weekly batch (Sunday morning)
            if not args.tier1_only and is_sunday_batch_time(now):
                if last_tier2_run != today:
                    log("Sunday batch window detected -- running Tier 2")
                    tier2_batch(cfg, dry_run=args.dry_run)
                    last_tier2_run = today

            # Tier 1: continuous during market hours
            if is_market_hours(now) or (now.hour == 16 and 25 <= now.minute <= 35):
                if last_tier1_run is None or (now - last_tier1_run).total_seconds() >= cycle_sec - 5:
                    tier1_cycle(cfg, dry_run=args.dry_run)
                    last_tier1_run = now
                    time.sleep(max(min_gap, 1))
                else:
                    # Wait until next cycle
                    wait_sec = cycle_sec - (now - last_tier1_run).total_seconds()
                    time.sleep(min(60, max(wait_sec, 5)))
            else:
                # Outside market hours, idle check every 5 minutes
                log(f"Outside market hours, idling. Next check in 5 min. (Weekday={now.weekday()}, hour={now.hour})")
                time.sleep(300)

        except KeyboardInterrupt:
            log("Daemon stopped by user.")
            break
        except Exception as e:
            log(f"Unhandled exception in daemon loop: {e}\n{traceback.format_exc()}", level="ERROR")
            time.sleep(60)

if __name__ == "__main__":
    main()
