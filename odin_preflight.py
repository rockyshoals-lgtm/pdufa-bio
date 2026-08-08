#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN PREFLIGHT CHECK v1.0                                             ║
║  Validates entire system before launch                                 ║
║                                                                        ║
║  Checks:                                                               ║
║    1. Python version & dependencies                                    ║
║    2. CUDA / GPU availability                                          ║
║    3. Directory structure & permissions                                 ║
║    4. Required files (dataset, weights, configs)                       ║
║    5. File integrity (row counts, JSON validity)                       ║
║    6. API connectivity (ClinicalTrials.gov)                            ║
║    7. Disk space                                                       ║
║                                                                        ║
║  Run:  python odin_preflight.py                                        ║
║  Deps: none (stdlib only, tests for optional deps)                     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import sys
import shutil
import subprocess
import importlib
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════

ODIN_DATA = Path(os.environ.get("ODIN_DATA", Path.home() / "odin_data"))
PYTHON_DIR = Path(os.environ.get("ODIN_CODE", Path.home() / "Documents" / "Python"))

REQUIRED_FILES = {
    "perpetual_loop.py":    PYTHON_DIR / "perpetual_loop.py",
    "audit_cycle.py":       PYTHON_DIR / "audit_cycle.py",
    "run_perpetual_v2.py":  PYTHON_DIR / "run_perpetual_v2.py",
    "optimizer_config.json": PYTHON_DIR / "optimizer_config.json",
    "dataset (1933 CSV)":   PYTHON_DIR / "ODIN_ENRICHED_PDUFA_1933_v4_T1_COMPLIANT.csv",
}

REQUIRED_DATA_FILES = {
    "model_weights.json":   ODIN_DATA / "model_weights.json",
    "events.json":          ODIN_DATA / "events.json",
}

OPTIONAL_DATA_FILES = {
    "watchlist.json":       ODIN_DATA / "watchlist.json",
    "best_runs/":           ODIN_DATA / "best_runs",
}

REQUIRED_PACKAGES = ["requests"]
OPTIONAL_PACKAGES = ["pandas", "numpy", "torch", "sklearn"]

# ═══════════════════════════════════════════════════════════════
#  CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════

class PreflightResult:
    def __init__(self):
        self.checks = []
        self.errors = 0
        self.warnings = 0

    def ok(self, label, detail=""):
        self.checks.append(("OK", label, detail))

    def warn(self, label, detail=""):
        self.warnings += 1
        self.checks.append(("WARN", label, detail))

    def fail(self, label, detail=""):
        self.errors += 1
        self.checks.append(("FAIL", label, detail))

    def print_report(self):
        print()
        print("=" * 72)
        print("  ODIN PREFLIGHT CHECK")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 72)

        for status, label, detail in self.checks:
            icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(status, "?")
            line = f"  {icon} {label}"
            if detail:
                line += f" — {detail}"
            print(line)

        print("-" * 72)
        if self.errors == 0 and self.warnings == 0:
            print("  🟢 ALL CHECKS PASSED — Ready to launch!")
        elif self.errors == 0:
            print(f"  🟡 PASSED with {self.warnings} warning(s)")
        else:
            print(f"  🔴 {self.errors} FAILURE(s), {self.warnings} warning(s) — FIX BEFORE LAUNCH")
        print("=" * 72)
        print()

        return self.errors == 0


def check_python_version(r: PreflightResult):
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major == 3 and v.minor >= 10:
        r.ok("Python version", ver_str)
    elif v.major == 3 and v.minor >= 8:
        r.warn("Python version", f"{ver_str} (3.10+ recommended)")
    else:
        r.fail("Python version", f"{ver_str} (need 3.8+)")


def check_packages(r: PreflightResult):
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            r.ok(f"Package: {pkg}")
        except ImportError:
            r.fail(f"Package: {pkg}", f"pip install {pkg}")

    for pkg in OPTIONAL_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "?")
            r.ok(f"Package: {pkg}", f"v{version}")
        except ImportError:
            r.warn(f"Package: {pkg}", "not installed (optional)")


def check_gpu(r: PreflightResult):
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
            r.ok("CUDA GPU", f"{name} ({mem:.1f} GB)")
        else:
            r.warn("CUDA GPU", "not available — CPU training only (slower)")
    except ImportError:
        r.warn("CUDA GPU", "torch not installed — cannot check")


def check_directories(r: PreflightResult):
    for label, path in [("odin_data", ODIN_DATA), ("Python code", PYTHON_DIR)]:
        if path.exists() and path.is_dir():
            r.ok(f"Directory: {label}", str(path))
        else:
            r.fail(f"Directory: {label}", f"MISSING: {path}")

    # Ensure best_runs exists
    best_runs = ODIN_DATA / "best_runs"
    if not best_runs.exists():
        try:
            best_runs.mkdir(parents=True, exist_ok=True)
            r.ok("Directory: best_runs", "created")
        except Exception as e:
            r.fail("Directory: best_runs", f"cannot create: {e}")
    else:
        r.ok("Directory: best_runs", str(best_runs))


def check_required_files(r: PreflightResult):
    for label, path in REQUIRED_FILES.items():
        if path.exists():
            size_kb = path.stat().st_size / 1024
            r.ok(f"File: {label}", f"{size_kb:.0f} KB")
        else:
            r.fail(f"File: {label}", f"MISSING: {path}")

    for label, path in REQUIRED_DATA_FILES.items():
        if path.exists():
            size_kb = path.stat().st_size / 1024
            r.ok(f"Data: {label}", f"{size_kb:.0f} KB")
        else:
            r.fail(f"Data: {label}", f"MISSING: {path}")

    for label, path in OPTIONAL_DATA_FILES.items():
        if path.exists():
            r.ok(f"Optional: {label}")
        else:
            r.warn(f"Optional: {label}", "not found (will be created)")


def check_dataset_integrity(r: PreflightResult):
    csv_path = REQUIRED_FILES.get("dataset (1933 CSV)")
    if not csv_path or not csv_path.exists():
        return  # Already flagged in file check

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            header = f.readline()
            row_count = sum(1 for _ in f)  # Exclude header

        if row_count >= 1900:
            r.ok("Dataset rows", f"{row_count} events (expected ~1933)")
        elif row_count >= 1800:
            r.warn("Dataset rows", f"{row_count} events (expected ~1933)")
        else:
            r.fail("Dataset rows", f"Only {row_count} events (expected ~1933)")

        # Check key columns
        cols = [c.strip().lower() for c in header.split(",")]
        required_cols = ["ticker", "pdufa_date", "outcome", "btd", "orphan"]
        for col in required_cols:
            if col in cols:
                r.ok(f"Column: {col}")
            else:
                r.warn(f"Column: {col}", "not found in CSV header")

    except Exception as e:
        r.fail("Dataset integrity", str(e))


def check_weights_integrity(r: PreflightResult):
    wpath = REQUIRED_DATA_FILES.get("model_weights.json")
    if not wpath or not wpath.exists():
        return

    try:
        with open(wpath, "r") as f:
            w = json.load(f)

        if "base_logit" in w:
            r.ok("Weights: base_logit", f"{w['base_logit']:.4f}")
        else:
            r.fail("Weights: base_logit", "missing from model_weights.json")

        if "signals" in w:
            sig_count = len(w["signals"])
            r.ok("Weights: signals", f"{sig_count} signal weights loaded")
        else:
            r.warn("Weights: signals", "no signals dict in weights")

    except json.JSONDecodeError as e:
        r.fail("Weights: JSON", f"invalid JSON: {e}")
    except Exception as e:
        r.fail("Weights: read", str(e))


def check_best_runs(r: PreflightResult):
    import glob
    pattern_root = str(ODIN_DATA / "best_run_AUC_*.json")
    pattern_sub = str(ODIN_DATA / "best_runs" / "best_run_AUC_*.json")

    runs = glob.glob(pattern_root) + glob.glob(pattern_sub)

    if len(runs) == 0:
        r.warn("Best runs", "no best_run_AUC_*.json files found")
        return

    # Find best AUC
    best_auc = 0.0
    best_file = ""
    for f in runs:
        try:
            name = os.path.basename(f)
            auc_str = name.split("AUC_")[1].split("_")[0]
            auc = float(auc_str)
            if auc > best_auc:
                best_auc = auc
                best_file = name
        except (IndexError, ValueError):
            pass

    r.ok("Best runs", f"{len(runs)} files, best AUC={best_auc:.4f} ({best_file})")

    if best_auc > 0.92:
        r.ok("Best AUC", f"{best_auc:.4f} — above 0.92 target")
    elif best_auc > 0.91:
        r.ok("Best AUC", f"{best_auc:.4f} — above baseline 0.9085")
    elif best_auc > 0.9085:
        r.warn("Best AUC", f"{best_auc:.4f} — marginal improvement over baseline")
    else:
        r.warn("Best AUC", f"{best_auc:.4f} — at or below baseline 0.9085")


def check_events_json(r: PreflightResult):
    epath = REQUIRED_DATA_FILES.get("events.json")
    if not epath or not epath.exists():
        return

    try:
        with open(epath, "r") as f:
            data = json.load(f)

        if isinstance(data, list):
            r.ok("events.json", f"{len(data)} events")
        elif isinstance(data, dict) and "events" in data:
            r.ok("events.json", f"{len(data['events'])} events (nested)")
        else:
            r.warn("events.json", f"unexpected structure: {type(data)}")

    except json.JSONDecodeError as e:
        r.fail("events.json", f"invalid JSON: {e}")


def check_disk_space(r: PreflightResult):
    try:
        usage = shutil.disk_usage(str(ODIN_DATA))
        free_gb = usage.free / (1024 ** 3)
        if free_gb > 10:
            r.ok("Disk space", f"{free_gb:.1f} GB free")
        elif free_gb > 2:
            r.warn("Disk space", f"{free_gb:.1f} GB free (low)")
        else:
            r.fail("Disk space", f"{free_gb:.1f} GB free (critical)")
    except Exception as e:
        r.warn("Disk space", f"cannot check: {e}")


def check_api_connectivity(r: PreflightResult):
    try:
        import requests
        resp = requests.get(
            "https://clinicaltrials.gov/api/v2/studies?pageSize=1",
            timeout=10,
        )
        if resp.status_code == 200:
            r.ok("ClinicalTrials.gov API", "reachable")
        else:
            r.warn("ClinicalTrials.gov API", f"HTTP {resp.status_code}")
    except ImportError:
        r.warn("ClinicalTrials.gov API", "requests not installed, skipped")
    except Exception as e:
        r.warn("ClinicalTrials.gov API", f"unreachable: {e}")


def check_optimizer_config(r: PreflightResult):
    cfg_path = PYTHON_DIR / "optimizer_config.json"
    if not cfg_path.exists():
        return

    try:
        with open(cfg_path, "r") as f:
            cfg = json.load(f)

        if "training_params" in cfg:
            r.ok("optimizer_config.json", "training_params present")
        else:
            r.warn("optimizer_config.json", "missing training_params section")

        if "guard_rails" in cfg:
            rails = cfg["guard_rails"]
            max_gap = rails.get("max_overfitting_gap", None)
            if max_gap is not None:
                r.ok("Guard rails", f"max_overfitting_gap={max_gap}")
            else:
                r.warn("Guard rails", "max_overfitting_gap not set")
        else:
            r.warn("optimizer_config.json", "missing guard_rails section")

    except json.JSONDecodeError as e:
        r.fail("optimizer_config.json", f"invalid JSON: {e}")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def run_preflight() -> bool:
    r = PreflightResult()

    check_python_version(r)
    check_packages(r)
    check_gpu(r)
    check_directories(r)
    check_required_files(r)
    check_dataset_integrity(r)
    check_weights_integrity(r)
    check_best_runs(r)
    check_events_json(r)
    check_optimizer_config(r)
    check_disk_space(r)
    check_api_connectivity(r)

    return r.print_report()


if __name__ == "__main__":
    passed = run_preflight()
    sys.exit(0 if passed else 1)
