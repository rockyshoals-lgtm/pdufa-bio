#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  GUNGNIR PERPETUAL RUNNER v1.0                                         ║
║  Persistent service for continuous honing on Phase readout data         ║
║                                                                        ║
║  Usage:                                                                ║
║    python gungnir_runner.py                         Interactive mode    ║
║    python gungnir_runner.py --auto                  Daemon mode         ║
║    python gungnir_runner.py --hone                  One-shot honing     ║
║    python gungnir_runner.py --backtest              Run backtests       ║
║    python gungnir_runner.py --status                Quick status        ║
║    python gungnir_runner.py --report                Full report         ║
║    python gungnir_runner.py --weights               Dump all weights    ║
║    python gungnir_runner.py --score "Phase 3..."    Score catalyst text ║
║    python gungnir_runner.py --best                  Show best config    ║
║                                                                        ║
║  Data dir: ~/gungnir_data/ (cross-platform)                            ║
║  Companion to ODIN Runner (PDUFA events)                               ║
║  Built for pdufa.bio — Feb 2026                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from gungnir_honing_engine import (
    GungnirHoningScorer,
    CalibrationEngine,
    GradientRecalibrator,
    Backtester,
    load_phase_events,
    precompute_features,
    extract_features,
    save_weights,
    load_weights,
    sigmoid,
    FEATURE_NAMES,
    INITIAL_WEIGHTS,
    RISK_RULES,
    __version__ as ENGINE_VERSION,
)

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════════════
#  DATA DIRECTORY
# ═══════════════════════════════════════════════════════════════

def get_data_dir() -> str:
    d = str(Path.home() / "gungnir_data")
    os.makedirs(d, exist_ok=True)
    return d


# ═══════════════════════════════════════════════════════════════
#  HONING LOG — Every cycle logged
# ═══════════════════════════════════════════════════════════════

class HoningLog:
    """Persistent log of all honing cycles."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.cycles = []
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                self.cycles = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.cycles, f, indent=2, default=str)

    def log_cycle(self, metrics: dict, recal_report: dict, drift_alerts: list):
        self.cycles.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "recalibration": recal_report,
            "drift_alerts": drift_alerts,
        })
        self.save()

    def recent(self, n=5) -> list:
        return self.cycles[-n:]


# ═══════════════════════════════════════════════════════════════
#  BEST CONFIG TRACKER — Saves the best model ever seen
# ═══════════════════════════════════════════════════════════════

class BestConfigTracker:
    """
    Tracks the best model configuration across all honing cycles.
    Persists to disk so the best is never lost.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.best = None
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.best = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.best, f, indent=2, default=str)

    def check_and_update(self, weights: dict, metrics: dict,
                         recal_report: dict, version_tag: str) -> bool:
        """
        Compare current model against best ever.
        Returns True if this is a new best.

        Primary metric: AUC (discrimination)
        Tiebreaker: Brier (calibration)
        """
        auc = metrics.get("auc", 0)
        brier = metrics.get("brier", 1)
        t1_n = metrics.get("tiers", {}).get("TIER_1", {}).get("n", 0)
        t1_pos = metrics.get("tiers", {}).get("TIER_1", {}).get("actual_positive_rate", 0)
        t4_n = metrics.get("tiers", {}).get("TIER_4", {}).get("n", 0)
        t4_pos = metrics.get("tiers", {}).get("TIER_4", {}).get("actual_positive_rate", 1)

        is_new_best = False
        if self.best is None:
            is_new_best = True
        else:
            best_auc = self.best.get("auc", 0)
            best_brier = self.best.get("brier", 1)
            # Primary: higher AUC wins
            if auc > best_auc + 0.001:
                is_new_best = True
            # Tiebreaker: lower Brier wins
            elif abs(auc - best_auc) <= 0.001 and brier < best_brier - 0.001:
                is_new_best = True

        if is_new_best:
            self.best = {
                "version": version_tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "auc": round(auc, 6),
                "brier": round(brier, 6),
                "accuracy": metrics.get("accuracy", 0),
                "n": metrics.get("n", 0),
                "base_rate": metrics.get("base_rate", 0),
                "tier_1_n": t1_n,
                "tier_1_positive_rate": round(t1_pos, 4),
                "tier_4_n": t4_n,
                "tier_4_positive_rate": round(t4_pos, 4),
                "weights": deepcopy(weights),
                "recalibration_summary": {
                    "epochs": recal_report.get("epochs", 0),
                    "features_changed": recal_report.get("features_changed", 0),
                },
            }
            self.save()

        return is_new_best

    def print_best(self):
        if not self.best:
            print("  No best config recorded yet.")
            return
        b = self.best
        print(f"\n  ╔══════════════════════════════════════════════════╗")
        print(f"  ║  GUNGNIR BEST CONFIG EVER                       ║")
        print(f"  ╚══════════════════════════════════════════════════╝")
        print(f"  Version:  {b['version']}")
        print(f"  Saved:    {b['timestamp'][:19]}Z")
        print(f"  AUC:      {b['auc']:.4f}")
        print(f"  Brier:    {b['brier']:.4f}")
        print(f"  Accuracy: {b['accuracy']:.4f}")
        print(f"  Events:   {b['n']}")
        print(f"  TIER_1:   n={b['tier_1_n']}  actual_pos={b['tier_1_positive_rate']:.1%}")
        print(f"  TIER_4:   n={b['tier_4_n']}  actual_pos={b['tier_4_positive_rate']:.1%}")
        print(f"  Epochs:   {b['recalibration_summary']['epochs']}")
        print(f"  Features: {b['recalibration_summary']['features_changed']} changed")

        # Top 10 weights
        w = b["weights"]["features"]
        sorted_feats = sorted(w.items(), key=lambda x: abs(x[1]), reverse=True)
        print(f"\n  Top 10 feature weights:")
        for fname, wt in sorted_feats[:10]:
            arrow = "↑" if wt > 0 else "↓"
            print(f"    {arrow} {fname:>30s}: {wt:+.4f}")


# ═══════════════════════════════════════════════════════════════
#  MODEL VERSION STORE
# ═══════════════════════════════════════════════════════════════

class ModelVersionStore:
    """Track model versions over time."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.versions = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.versions = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.versions, f, indent=2, default=str)

    def record_version(self, version_tag: str, weight_hash: str,
                       metrics: dict, note: str = ""):
        self.versions.append({
            "version": version_tag,
            "hash": weight_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "note": note,
        })
        self.save()

    def latest(self) -> dict:
        return self.versions[-1] if self.versions else {}

    def count(self) -> int:
        return len(self.versions)


# ═══════════════════════════════════════════════════════════════
#  DRIFT DETECTOR
# ═══════════════════════════════════════════════════════════════

class DriftDetector:
    """Detect model drift from recent events."""

    @staticmethod
    def detect(scorer: GungnirHoningScorer, events: list,
               recent_n: int = 50) -> list:
        resolved = [e for e in events if e.get("outcome") in ("POSITIVE", "NEGATIVE")]
        if len(resolved) < recent_n + 20:
            return []

        alerts = []
        recent = resolved[-recent_n:]
        historical = resolved[:-recent_n]

        # Base rate shift
        r_rate = sum(1 for e in recent if e["outcome"] == "POSITIVE") / len(recent)
        h_rate = sum(1 for e in historical if e["outcome"] == "POSITIVE") / len(historical)
        if abs(r_rate - h_rate) > 0.08:
            alerts.append({
                "type": "BASE_RATE_SHIFT",
                "recent_rate": round(r_rate, 3),
                "historical_rate": round(h_rate, 3),
                "delta": round(r_rate - h_rate, 3),
            })

        # Brier degradation
        r_preds = [scorer.score(e)["probability"] for e in recent]
        r_acts = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in recent]
        r_brier = sum((p - a) ** 2 for p, a in zip(r_preds, r_acts)) / len(recent)

        h_preds = [scorer.score(e)["probability"] for e in historical]
        h_acts = [1.0 if e["outcome"] == "POSITIVE" else 0.0 for e in historical]
        h_brier = sum((p - a) ** 2 for p, a in zip(h_preds, h_acts)) / len(historical)

        if r_brier > h_brier * 1.25:
            alerts.append({
                "type": "RECENCY_DRIFT",
                "recent_brier": round(r_brier, 4),
                "historical_brier": round(h_brier, 4),
            })

        return alerts


# ═══════════════════════════════════════════════════════════════
#  PREDICTION LEDGER
# ═══════════════════════════════════════════════════════════════

class PredictionLedger:
    """Persistent storage of predictions and outcomes."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.records = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.records = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.records, f, indent=2, default=str)

    def record_prediction(self, event_id: str, score_result: dict, event: dict):
        self.records[event_id] = {
            "event_id": event_id,
            "ticker": event.get("ticker", ""),
            "asset": event.get("asset", ""),
            "stage": event.get("stage", ""),
            "indication": event.get("indication", ""),
            "probability": score_result["probability"],
            "ml_score": score_result["ml_score"],
            "tier": score_result["tier"],
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "outcome": None,
            "resolved_at": None,
        }
        self.save()

    def record_outcome(self, event_id: str, outcome: str):
        if event_id in self.records:
            self.records[event_id]["outcome"] = outcome
            self.records[event_id]["resolved_at"] = datetime.now(timezone.utc).isoformat()
            self.save()

    def get_resolved(self) -> list:
        return [r for r in self.records.values() if r.get("outcome")]

    def get_unresolved(self) -> list:
        return [r for r in self.records.values() if not r.get("outcome")]

    def count(self) -> dict:
        total = len(self.records)
        resolved = len(self.get_resolved())
        return {"total": total, "resolved": resolved, "unresolved": total - resolved}


# ═══════════════════════════════════════════════════════════════
#  GUNGNIR RUNNER — Main orchestrator
# ═══════════════════════════════════════════════════════════════

class GungnirRunner:
    """
    Persistent Gungnir service:
    - Loads Phase readout datasets
    - Calibrates model via gradient descent
    - Tracks best config across all cycles
    - Auto-honing daemon mode
    - Interactive CLI
    """

    def __init__(self, data_dir: str = None,
                 phase_csv: str = None, hist_csv: str = None):
        self.data_dir = data_dir or get_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)

        # File paths
        self.weights_path = os.path.join(self.data_dir, "model_weights.json")
        self.best_config_path = os.path.join(self.data_dir, "best_config.json")
        self.versions_path = os.path.join(self.data_dir, "versions.json")
        self.honing_path = os.path.join(self.data_dir, "honing_log.json")
        self.ledger_path = os.path.join(self.data_dir, "ledger.json")

        # Components
        self.scorer = GungnirHoningScorer()
        self.best_tracker = BestConfigTracker(self.best_config_path)
        self.versions = ModelVersionStore(self.versions_path)
        self.honing_log = HoningLog(self.honing_path)
        self.ledger = PredictionLedger(self.ledger_path)

        # Events
        self.events = []
        self.resolved_events = []

        # Auto-honing state
        self._auto_thread = None
        self._stop_flag = threading.Event()
        self._cycle_count = 0

        # Try to load saved weights
        if os.path.exists(self.weights_path):
            saved = load_weights(self.weights_path)
            self.scorer.weights = saved
            print(f"  Loaded saved weights from {self.weights_path}")

        # Load data
        print("  Loading Phase readout data...")
        self.events = load_phase_events(phase_csv, hist_csv)
        self.events = precompute_features(self.events)
        self._split_events()

    def _split_events(self):
        self.resolved_events = [
            e for e in self.events
            if e.get("outcome") in ("POSITIVE", "NEGATIVE")
        ]

    def weight_hash(self) -> str:
        """Short hash of current weights for version tracking."""
        w_str = json.dumps(self.scorer.weights, sort_keys=True)
        return hashlib.sha256(w_str.encode()).hexdigest()[:12]

    def save_current_weights(self):
        save_weights(self.scorer.weights, self.weights_path)

    # ───────────────────────────────────────────────
    #  HONING CYCLE — Core loop
    # ───────────────────────────────────────────────

    def run_honing_cycle(self, force=False) -> dict:
        """
        One honing cycle:
        1. Compute current metrics
        2. Check for drift
        3. Recalibrate if needed
        4. Compare against best config → save if new best
        5. Log everything
        """
        if len(self.resolved_events) < 20:
            return {"status": "INSUFFICIENT_DATA", "n": len(self.resolved_events)}

        self._cycle_count += 1

        # Current metrics
        preds = [self.scorer.score(e)["probability"] for e in self.resolved_events]
        actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0
                   for e in self.resolved_events]
        metrics = CalibrationEngine.compute_metrics(preds, actuals)

        # Drift detection
        drift_alerts = DriftDetector.detect(self.scorer, self.resolved_events)

        # Recalibrate
        should_recal = force or metrics["brier"] > 0.18 or len(drift_alerts) > 0
        recal_report = {"status": "NOT_NEEDED"}

        if should_recal:
            recal = GradientRecalibrator(lr=0.003, l2=0.005, max_epochs=3000)
            recal_report = recal.recalibrate(self.scorer, self.resolved_events)

            # Re-score with new weights
            preds = [self.scorer.score(e)["probability"] for e in self.resolved_events]
            metrics = CalibrationEngine.compute_metrics(preds, actuals)

            self.save_current_weights()

            # Version
            h = self.weight_hash()
            v = f"1.0.{self.versions.count() + 1}"
            self.versions.record_version(v, h, {
                "brier": metrics["brier"],
                "auc": metrics["auc"],
                "accuracy": metrics["accuracy"],
                "n": metrics["n"],
            }, note="auto-honing" if not force else "forced")

            # Check if new best
            is_best = self.best_tracker.check_and_update(
                self.scorer.weights, metrics, recal_report, v
            )
            recal_report["is_new_best"] = is_best

        # Log cycle
        self.honing_log.log_cycle(metrics, recal_report, drift_alerts)

        return {
            "cycle": self._cycle_count,
            "metrics": metrics,
            "drift_alerts": drift_alerts,
            "recalibration": recal_report,
        }

    def initial_calibration(self):
        """First calibration on loaded data."""
        if len(self.resolved_events) < 20:
            print("  Not enough resolved events for calibration.")
            return

        print(f"\n  Running initial calibration on {len(self.resolved_events)} events...")
        recal = GradientRecalibrator(lr=0.003, l2=0.005, max_epochs=3000)
        report = recal.recalibrate(self.scorer, self.resolved_events)

        print(f"  Brier: {report['pre_brier']:.4f} → {report['post_brier']:.4f}")
        print(f"  AUC:   {report['pre_auc']:.4f} → {report['post_auc']:.4f}")
        print(f"  Acc:   {report['pre_accuracy']:.4f} → {report['post_accuracy']:.4f}")
        print(f"  Features adjusted: {report['features_changed']}")

        self.save_current_weights()

        # Compute full metrics and check best
        preds = [self.scorer.score(e)["probability"] for e in self.resolved_events]
        actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0
                   for e in self.resolved_events]
        metrics = CalibrationEngine.compute_metrics(preds, actuals)

        h = self.weight_hash()
        v = f"1.0.{self.versions.count() + 1}"
        self.versions.record_version(v, h, {
            "brier": metrics["brier"],
            "auc": metrics["auc"],
            "n": metrics["n"],
        }, note="initial calibration")

        is_best = self.best_tracker.check_and_update(
            self.scorer.weights, metrics, report, v
        )
        if is_best:
            print(f"  ★ NEW BEST CONFIG saved (AUC={metrics['auc']:.4f})")

    # ───────────────────────────────────────────────
    #  SCORING
    # ───────────────────────────────────────────────

    def score_catalyst(self, catalyst_text: str, ticker: str = "",
                       drug: str = "", indication: str = "",
                       stage: str = "", date: str = "2026-01-01") -> dict:
        """Score a readout from catalyst text."""
        features = extract_features(catalyst_text, ticker, drug,
                                    indication, stage, date)
        event = {
            "features": features,
            "ticker": ticker,
            "asset": drug,
            "indication": indication,
            "stage": stage,
            "catalyst_date": date,
            "raw_catalyst_text": catalyst_text,
        }
        result = self.scorer.score(event)
        result["ticker"] = ticker
        result["drug"] = drug
        result["indication"] = indication
        result["stage"] = stage
        return result

    # ───────────────────────────────────────────────
    #  AUTO-HONING DAEMON
    # ───────────────────────────────────────────────

    def start_auto_honing(self, interval_minutes=30):
        """Start background auto-honing thread."""
        self._stop_flag.clear()

        def _loop():
            while not self._stop_flag.is_set():
                try:
                    result = self.run_honing_cycle()
                    ts = datetime.now().strftime("%H:%M:%S")
                    m = result.get("metrics", {})
                    r = result.get("recalibration", {})
                    status = r.get("status", "?")
                    is_best = "★ NEW BEST" if r.get("is_new_best") else ""
                    drift = f" DRIFT:{len(result.get('drift_alerts', []))}" if result.get("drift_alerts") else ""

                    print(f"\n  [{ts}] Cycle #{result.get('cycle', '?')} | "
                          f"AUC={m.get('auc', '?'):.4f} | "
                          f"Brier={m.get('brier', '?'):.4f} | "
                          f"{status}{drift} {is_best}")

                except Exception as ex:
                    print(f"\n  Auto-honing error: {ex}")

                self._stop_flag.wait(interval_minutes * 60)

        self._auto_thread = threading.Thread(target=_loop, daemon=True)
        self._auto_thread.start()
        print(f"  Auto-honing started (every {interval_minutes} min)")

    def stop_auto_honing(self):
        self._stop_flag.set()
        if self._auto_thread:
            self._auto_thread.join(timeout=5)
        print("  Auto-honing stopped.")

    # ───────────────────────────────────────────────
    #  REPORTING
    # ───────────────────────────────────────────────

    def print_status(self):
        """Quick status overview."""
        v = self.versions.latest()
        print(f"\n  ┌─ GUNGNIR STATUS ────────────────────────────┐")
        print(f"  │  Engine:     v{ENGINE_VERSION:36s}│")
        print(f"  │  Runner:     v{__version__:36s}│")
        print(f"  │  Model:      {v.get('version', 'uncalibrated'):37s}│")
        print(f"  │  Hash:       {self.weight_hash():37s}│")
        print(f"  │  Events:     {len(self.resolved_events):>5d} resolved{' '*24}│")
        print(f"  │  Versions:   {self.versions.count():>5d} recorded{' '*24}│")
        print(f"  │  Cycles:     {len(self.honing_log.cycles):>5d} logged{' '*26}│")

        if self.best_tracker.best:
            b = self.best_tracker.best
            print(f"  │  Best AUC:   {b['auc']:.4f} ({b['version']}){' '*20}│")
        print(f"  └────────────────────────────────────────────┘")

    def print_report(self):
        """Full model report."""
        print(f"\n{'='*72}")
        print(f"  GUNGNIR MODEL REPORT")
        print(f"{'='*72}")

        v = self.versions.latest()
        print(f"  Engine:      v{ENGINE_VERSION}")
        print(f"  Model:       {v.get('version', 'uncalibrated')}")
        print(f"  Weight hash: {self.weight_hash()}")
        print(f"  Features:    {len(FEATURE_NAMES)} NLP features")
        print(f"  Risk rules:  {len(RISK_RULES)}")

        print(f"\n  Events: {len(self.events)} total, {len(self.resolved_events)} resolved")
        pos = sum(1 for e in self.resolved_events if e["outcome"] == "POSITIVE")
        neg = len(self.resolved_events) - pos
        print(f"    POSITIVE: {pos} ({pos/len(self.resolved_events)*100:.1f}%)")
        print(f"    NEGATIVE: {neg} ({neg/len(self.resolved_events)*100:.1f}%)")

        # Current metrics
        if self.resolved_events:
            preds = [self.scorer.score(e)["probability"] for e in self.resolved_events]
            actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0
                       for e in self.resolved_events]
            metrics = CalibrationEngine.compute_metrics(preds, actuals)

            print(f"\n  Current performance:")
            print(f"    Brier:    {metrics['brier']:.4f}")
            print(f"    AUC:      {metrics['auc']:.4f}")
            print(f"    Accuracy: {metrics['accuracy']:.4f}")

            print(f"\n  Tier breakdown:")
            for t, s in metrics["tiers"].items():
                if s["n"] > 0:
                    print(f"    {t}: n={s['n']:>5}  actual_pos={s['actual_positive_rate']:.1%}")

        # Version history (last 5)
        print(f"\n  Version history (last 5):")
        for v in self.versions.versions[-5:]:
            m = v.get("metrics", {})
            print(f"    {v['version']:>10s} | AUC={m.get('auc', '?'):.4f} | "
                  f"Brier={m.get('brier', '?'):.4f} | {v.get('note', '')}")

        # Best config
        self.best_tracker.print_best()

        print(f"\n{'='*72}")

    def print_weights(self):
        """Dump all current weights."""
        print(f"\n{'='*72}")
        print(f"  GUNGNIR FEATURE WEIGHTS")
        print(f"{'='*72}")
        print(f"  Base logit: {self.scorer.weights['base_logit']:.4f} "
              f"→ P={sigmoid(self.scorer.weights['base_logit']):.3f}")
        print(f"\n  {'Feature':<35s} {'Weight':>8s} {'Direction':>10s}")
        print(f"  {'─'*55}")
        w = self.scorer.weights["features"]
        sorted_feats = sorted(w.items(), key=lambda x: abs(x[1]), reverse=True)
        for fname, wt in sorted_feats:
            if abs(wt) > 0.001:
                arrow = "↑ POSITIVE" if wt > 0 else "↓ NEGATIVE"
                print(f"  {fname:<35s} {wt:>+8.4f} {arrow:>10s}")
        print(f"\n{'='*72}")

    # ───────────────────────────────────────────────
    #  INTERACTIVE CLI
    # ───────────────────────────────────────────────

    def interactive(self):
        """Interactive command loop."""
        # Auto-calibrate on first run if no saved weights
        if not os.path.exists(self.weights_path):
            self.initial_calibration()

        self.print_status()

        print(f"\n  Commands:")
        print(f"    score     Score a catalyst text")
        print(f"    hone      Run honing cycle")
        print(f"    auto      Start auto-honing daemon")
        print(f"    stop      Stop auto-honing")
        print(f"    status    Quick status")
        print(f"    report    Full report")
        print(f"    best      Show best config")
        print(f"    weights   Dump feature weights")
        print(f"    backtest  Run walk-forward backtest")
        print(f"    quit      Exit")

        while True:
            try:
                cmd = input("\n  gungnir> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd in ("quit", "exit", "q"):
                break
            elif cmd == "score":
                self._cmd_score()
            elif cmd == "hone":
                self._cmd_hone()
            elif cmd == "auto":
                self.start_auto_honing()
            elif cmd == "stop":
                self.stop_auto_honing()
            elif cmd == "status":
                self.print_status()
            elif cmd == "report":
                self.print_report()
            elif cmd == "best":
                self.best_tracker.print_best()
            elif cmd == "weights":
                self.print_weights()
            elif cmd == "backtest":
                self._cmd_backtest()
            else:
                print(f"  Unknown command: {cmd}")

        self.save_current_weights()
        print("  Saved weights. Goodbye.")

    def _cmd_score(self):
        """Interactive scoring."""
        print("  ─" * 36)
        catalyst = input("  Catalyst text: ").strip()
        if not catalyst:
            return
        ticker = input("  Ticker []:     ").strip()
        drug = input("  Drug []:       ").strip()
        indication = input("  Indication []: ").strip()
        stage = input("  Stage []:      ").strip()
        date = input("  Date [2026-01-01]: ").strip() or "2026-01-01"

        result = self.score_catalyst(catalyst, ticker, drug, indication, stage, date)
        self._print_scorecard(result)

    def _cmd_hone(self):
        """Manual honing cycle."""
        print("\n  Running honing cycle...")
        result = self.run_honing_cycle(force=True)
        m = result.get("metrics", {})
        r = result.get("recalibration", {})

        print(f"  AUC:    {m.get('auc', '?'):.4f}")
        print(f"  Brier:  {m.get('brier', '?'):.4f}")
        print(f"  Status: {r.get('status', '?')}")
        if r.get("post_auc"):
            print(f"  Post-hone AUC:   {r['post_auc']:.4f}")
            print(f"  Post-hone Brier: {r['post_brier']:.4f}")
        if r.get("is_new_best"):
            print(f"  ★ NEW BEST CONFIG!")

        # Tier breakdown
        for t, s in m.get("tiers", {}).items():
            if s.get("n", 0) > 0:
                print(f"  {t}: n={s['n']:>5}  actual_pos={s['actual_positive_rate']:.1%}")

    def _cmd_backtest(self):
        """Run backtests."""
        if len(self.resolved_events) < 50:
            print("  Need 50+ resolved events.")
            return

        print("\n  Walk-forward backtest (70/30):")
        bt = Backtester.time_split_backtest(self.events)
        if bt.get("status") == "OK":
            print(f"  Train: n={bt['train_n']} | {bt['train_date_range']}")
            print(f"    AUC={bt['train_metrics']['auc']:.4f}  "
                  f"Brier={bt['train_metrics']['brier']:.4f}")
            print(f"  Test:  n={bt['test_n']} | {bt['test_date_range']}")
            print(f"    AUC={bt['test_metrics']['auc']:.4f}  "
                  f"Brier={bt['test_metrics']['brier']:.4f}")
            for t, s in bt["test_metrics"]["tiers"].items():
                if s["n"] > 0:
                    print(f"    {t}: n={s['n']:>5}  actual_pos={s['actual_positive_rate']:.1%}")

        print("\n  5-fold cross-validation:")
        cv = Backtester.kfold_backtest(self.events, k=5)
        if cv.get("status") == "OK":
            print(f"  Overall: AUC={cv['overall_metrics']['auc']:.4f}  "
                  f"Brier={cv['overall_metrics']['brier']:.4f}")
            for i, fm in enumerate(cv["fold_metrics"], 1):
                print(f"    Fold {i}: AUC={fm['auc']:.4f}  "
                      f"Brier={fm['brier']:.4f}  n={fm['n']}")

    def _print_scorecard(self, r):
        """Pretty-print a score result."""
        W = 60
        print(f"\n  {'═'*W}")
        print(f"  GUNGNIR READOUT SCORECARD")
        print(f"  {'═'*W}")
        if r.get("ticker"):
            print(f"  Ticker: {r['ticker']}  Drug: {r.get('drug', '')}")
        if r.get("indication"):
            print(f"  Indication: {r['indication']}  Stage: {r.get('stage', '')}")

        print(f"\n  ML Score:    {r['ml_score']:.1%}")
        if r.get("hard_cap") is not None:
            print(f"  Hard Cap:    {r['hard_cap']:.0%} ← RISK OVERRIDE")
        if r.get("soft_penalty", 0) != 0:
            print(f"  Penalties:   {-r['soft_penalty']:+.0%}")
        print(f"  ► FINAL:     {r['probability']:.1%}")

        tier = r["tier"]
        actions = {
            "TIER_1": ("LONG",          "HIGH"),
            "TIER_2": ("CAUTIOUS LONG", "MODERATE"),
            "TIER_3": ("AVOID",         "LOW"),
            "TIER_4": ("NO TRADE",      "VERY LOW"),
        }
        action, confidence = actions.get(tier, ("?", "?"))

        print(f"\n  ┌{'─'*40}┐")
        print(f"  │  TIER:       {tier:25s}│")
        print(f"  │  ACTION:     {action:25s}│")
        print(f"  │  CONFIDENCE: {confidence:25s}│")
        print(f"  └{'─'*40}┘")

        # Rules fired
        for rule in r.get("rules_fired", []):
            print(f"  {rule['desc']}")

        print(f"  Active features: {r.get('active_features', 0)}/35")
        print(f"  {'═'*W}")


# ═══════════════════════════════════════════════════════════════
#  GUNGNIR API — For programmatic access
# ═══════════════════════════════════════════════════════════════

class GungnirAPI:
    """
    Stateless API for integration with pdufa.bio.

    Usage:
        api = GungnirAPI()
        result = api.score("Phase 3 met primary endpoint...",
                           ticker="ACME", stage="Phase 3")
        api.hone(force=True)
        report = api.report()
        best = api.get_best_config()
    """

    def __init__(self, data_dir: str = None,
                 phase_csv: str = None, hist_csv: str = None):
        self.runner = GungnirRunner(data_dir=data_dir,
                                    phase_csv=phase_csv, hist_csv=hist_csv)
        if not os.path.exists(self.runner.weights_path):
            self.runner.initial_calibration()

    def score(self, catalyst_text: str, **kwargs) -> dict:
        return self.runner.score_catalyst(catalyst_text, **kwargs)

    def hone(self, force=False) -> dict:
        return self.runner.run_honing_cycle(force=force)

    def report(self) -> dict:
        if not self.runner.resolved_events:
            return {"status": "NO_DATA"}
        preds = [self.runner.scorer.score(e)["probability"]
                 for e in self.runner.resolved_events]
        actuals = [1.0 if e["outcome"] == "POSITIVE" else 0.0
                   for e in self.runner.resolved_events]
        return CalibrationEngine.compute_metrics(preds, actuals)

    def get_best_config(self) -> dict:
        return self.runner.best_tracker.best or {}

    def backtest(self, method="walkforward") -> dict:
        if method == "kfold":
            return Backtester.kfold_backtest(self.runner.events, k=5)
        return Backtester.time_split_backtest(self.runner.events)


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Gungnir Perpetual Runner v1.0")
    parser.add_argument("--phase-csv", default=None, help="Path to Phase backtest CSV")
    parser.add_argument("--hist-csv", default=None, help="Path to historical readouts CSV")
    parser.add_argument("--data-dir", default=None, help="Data directory (default: ~/gungnir_data)")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--weights", action="store_true", help="Show feature weights and exit")
    parser.add_argument("--hone", action="store_true", help="Run one honing cycle and exit")
    parser.add_argument("--report", action="store_true", help="Full report and exit")
    parser.add_argument("--backtest", action="store_true", help="Run backtests and exit")
    parser.add_argument("--best", action="store_true", help="Show best config and exit")
    parser.add_argument("--score", default=None, help="Score catalyst text and exit")
    parser.add_argument("--ticker", default="", help="Ticker for scoring")
    parser.add_argument("--drug", default="", help="Drug name for scoring")
    parser.add_argument("--indication", default="", help="Indication for scoring")
    parser.add_argument("--stage", default="", help="Stage for scoring")
    parser.add_argument("--date", default="2026-01-01", help="Date for scoring")
    parser.add_argument("--auto", action="store_true", help="Daemon mode with auto-honing")
    parser.add_argument("--interval", type=int, default=30, help="Auto-hone interval (minutes)")
    parser.add_argument("--calibrate", action="store_true", help="Force initial calibration")
    args = parser.parse_args()

    print(f"\n{'='*72}")
    print(f"  ⚔️  GUNGNIR PERPETUAL RUNNER v{__version__}")
    print(f"  Phase Readout Scoring — Companion to ODIN (PDUFA)")
    print(f"{'='*72}")

    runner = GungnirRunner(
        data_dir=args.data_dir,
        phase_csv=args.phase_csv,
        hist_csv=args.hist_csv,
    )

    # Initial calibration if needed
    if not os.path.exists(runner.weights_path) or args.calibrate:
        runner.initial_calibration()

    # Handle CLI flags
    if args.status:
        runner.print_status()
        return
    if args.weights:
        runner.print_weights()
        return
    if args.best:
        runner.best_tracker.print_best()
        return
    if args.hone:
        result = runner.run_honing_cycle(force=True)
        m = result.get("metrics", {})
        r = result.get("recalibration", {})
        print(f"\n  AUC={m.get('auc', '?'):.4f}  Brier={m.get('brier', '?'):.4f}")
        print(f"  Recalibration: {r.get('status', '?')}")
        if r.get("is_new_best"):
            print(f"  ★ NEW BEST CONFIG!")
        for t, s in m.get("tiers", {}).items():
            if s.get("n", 0) > 0:
                print(f"  {t}: n={s['n']:>5}  actual_pos={s['actual_positive_rate']:.1%}")
        return
    if args.report:
        runner.print_report()
        return
    if args.backtest:
        runner._cmd_backtest()
        return
    if args.score:
        result = runner.score_catalyst(args.score, args.ticker, args.drug,
                                       args.indication, args.stage, args.date)
        runner._print_scorecard(result)
        return

    if args.auto:
        runner.start_auto_honing(interval_minutes=args.interval)
        print(f"\n  Daemon mode (every {args.interval} min). Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            runner.stop_auto_honing()
            runner.save_current_weights()
            print("\n  Shutdown complete.")
        return

    # Default: interactive mode
    runner.interactive()


if __name__ == "__main__":
    main()
