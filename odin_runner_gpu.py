#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ODIN PERPETUAL RUNNER v13.2-GPU                                       ║
║  CUDA-accelerated continuous honing on real PDUFA data                 ║
║                                                                        ║
║  Key GPU improvements over v13.1:                                      ║
║    - Feature matrix encoded once, reused across all epochs             ║
║    - Vectorized forward pass: all 2,210 events scored simultaneously   ║
║    - Adam optimizer + cosine annealing with warm restarts              ║
║    - Autograd replaces manual gradient computation                     ║
║    - 10,000 epochs (vs 3,000) with faster convergence                  ║
║    - Multi-strategy exploration: random restarts + perturbation        ║
║    - GPU-vectorized AUC computation                                    ║
║                                                                        ║
║  Uses ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv                    ║
║  Built for pdufa.bio — Feb 2026                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import os
import sys
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import torch

from odin_honing_engine_gpu import (
    OdinScorer,
    OdinGPUModel,
    CalibrationEngine,
    GradientRecalibratorGPU,
    Backtester,
    DriftDetector,
    PredictionLedger,
    ModelVersionStore,
    VRAMManager,
    get_vram_manager,
    load_csv,
    parse_row,
    encode_events_to_tensor,
    gpu_metrics,
    gpu_auc,
    sigmoid_cpu,
    logit_cpu,
    get_device,
    N_FEATURES,
    BINARY_SIGNAL_NAMES,
    TIER_ACTIONS,
    TA_LOGITS,
    TA_BUCKET_LOGITS,
    SIGNAL_REGISTRY,
    __version__ as ENGINE_VERSION,
)


# ═══════════════════════════════════════════════════════════════
#  DATA DIRECTORY
# ═══════════════════════════════════════════════════════════════

def get_data_dir() -> str:
    d = str(Path.home() / "odin_data")
    os.makedirs(d, exist_ok=True)
    return d


# ═══════════════════════════════════════════════════════════════
#  BEST RUN TRACKER
# ═══════════════════════════════════════════════════════════════

class BestRunTracker:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.best_auc = 0.0
        self.best_brier = 1.0
        os.makedirs(self.log_dir, exist_ok=True)

    def check_and_save(self, base_metrics: dict, recal_report: dict, weights: dict, version: str):
        current_auc = recal_report.get("post_auc", base_metrics.get("auc", 0.0))
        current_brier = recal_report.get("post_brier", base_metrics.get("brier", 1.0))

        improved = False
        if current_auc > self.best_auc:
            self.best_auc = current_auc
            improved = True
        if current_brier < self.best_brier:
            self.best_brier = current_brier
            improved = True

        if improved:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.log_dir, f"best_run_AUC_{current_auc:.4f}_{timestamp}.json")
            payload = {
                "timestamp": timestamp,
                "version": version,
                "metrics": {"auc": current_auc, "brier": current_brier},
                "weights": weights,
            }
            with open(filename, "w") as f:
                json.dump(payload, f, indent=4)
            return filename
        return None


# ═══════════════════════════════════════════════════════════════
#  HONING LOG & WATCHLIST
# ═══════════════════════════════════════════════════════════════

class HoningLog:
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


class Watchlist:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.events = {}
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                self.events = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.events, f, indent=2, default=str)

    def add(self, event_id: str, info: dict):
        self.events[event_id] = {
            **info,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "status": "PENDING",
        }
        self.save()

    def mark_scored(self, event_id: str, score: float, tier: int):
        if event_id in self.events:
            self.events[event_id]["status"] = "SCORED"
            self.events[event_id]["score"] = score
            self.events[event_id]["tier"] = tier
            self.save()

    def mark_resolved(self, event_id: str, outcome: str):
        if event_id in self.events:
            self.events[event_id]["status"] = "RESOLVED"
            self.events[event_id]["outcome"] = outcome
            self.save()

    def get_pending(self) -> list:
        return [v for v in self.events.values() if v["status"] != "RESOLVED"]


# ═══════════════════════════════════════════════════════════════
#  ODIN GPU RUNNER
# ═══════════════════════════════════════════════════════════════

class OdinRunnerGPU:
    def __init__(self, data_dir: str = None, csv_path: str = None,
                 max_memory_fraction: float = 0.5):
        self.data_dir = data_dir or get_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)

        # Setup dynamic VRAM management
        self.vram_mgr = get_vram_manager(max_memory_fraction)
        self.device = self.vram_mgr.get_device()
        self.vram_mgr.print_status()

        # File paths
        self.weights_path = os.path.join(self.data_dir, "model_weights.json")
        self.ledger_path = os.path.join(self.data_dir, "ledger.json")
        self.versions_path = os.path.join(self.data_dir, "versions.json")
        self.honing_path = os.path.join(self.data_dir, "honing_log.json")
        self.watchlist_path = os.path.join(self.data_dir, "watchlist.json")
        self.events_path = os.path.join(self.data_dir, "events.json")

        # Components
        self.scorer = OdinScorer()
        self.ledger = PredictionLedger(self.ledger_path)
        self.versions = ModelVersionStore(self.versions_path)
        self.honing_log = HoningLog(self.honing_path)
        self.watchlist = Watchlist(self.watchlist_path)
        self.best_run_tracker = BestRunTracker(os.path.join(self.data_dir, "best_runs"))

        # Events cache
        self.events = []
        self.resolved_events = []
        self.unresolved_events = []

        # GPU model + cached tensor (built once, reused across honing cycles)
        self.gpu_model = None
        self._X_cache = None
        self._y_cache = None

        # Auto-honing state
        self._auto_thread = None
        self._stop_flag = threading.Event()

        # Load saved weights
        if os.path.exists(self.weights_path):
            with open(self.weights_path, "r") as f:
                saved = json.load(f)
                self.scorer.import_weights(saved)
                print(f"  Loaded saved model weights")

        # Load cached events
        if os.path.exists(self.events_path):
            with open(self.events_path, "r") as f:
                self.events = json.load(f)
                self._split_events()
                print(f"  Loaded {len(self.events)} cached events")

        # Load from CSV
        if csv_path and os.path.exists(csv_path):
            self.load_csv(csv_path)

    def _split_events(self):
        self.resolved_events = [e for e in self.events if e.get("outcome") in ("APPROVED", "CRL")]
        self.unresolved_events = [e for e in self.events if e.get("outcome") is None]

    def _build_gpu_tensors(self):
        """Encode all resolved events to GPU tensor (re-checks VRAM availability)."""
        # Dynamic device selection: re-check VRAM each time
        n = len(self.resolved_events)
        self.device = self.vram_mgr.get_device(n_events=n)

        if self.resolved_events:
            self._X_cache, self._y_cache = encode_events_to_tensor(
                self.resolved_events, self.device
            )
            print(f"  GPU tensors: {self._X_cache.shape[0]} events × {self._X_cache.shape[1]} features on {self.device}")
        else:
            self._X_cache, self._y_cache = None, None

    def _build_gpu_model(self):
        """Build GPU model from current scorer weights."""
        self.gpu_model = OdinGPUModel(self.scorer.weights).to(self.device)

    def load_csv(self, csv_path: str):
        print(f"\n  Loading CSV: {csv_path}")
        self.events = load_csv(csv_path)
        self._split_events()
        print(f"  Loaded {len(self.events)} events ({len(self.resolved_events)} resolved)")

        with open(self.events_path, "w") as f:
            json.dump(self.events, f, indent=2, default=str)

        for ev in self.unresolved_events:
            eid = ev.get("event_id", "")
            if eid and eid not in self.watchlist.events:
                self.watchlist.add(eid, {
                    "ticker": ev.get("ticker", ""),
                    "drug_name": ev.get("drug_name", ""),
                    "therapeutic_area": ev.get("therapeutic_area", ""),
                    "catalyst_date": ev.get("catalyst_date", ""),
                })

        # Build GPU tensors
        self._build_gpu_tensors()

    def save_weights(self):
        weights = self.scorer.export_weights()
        with open(self.weights_path, "w") as f:
            json.dump(weights, f, indent=2)

    def score_event(self, event: dict) -> dict:
        result = self.scorer.score(event)
        eid = event.get("event_id", "")
        if eid:
            self.ledger.record_prediction(eid, result, event)
            self.ledger.save()
            self.watchlist.mark_scored(eid, result["probability"], result["tier"])
        return result

    def score_ticker(self, ticker: str) -> list:
        matches = [e for e in self.events if e.get("ticker", "").upper() == ticker.upper()]
        if not matches:
            print(f"  No events for: {ticker}")
            return []
        results = []
        for ev in matches:
            r = self.score_event(ev)
            results.append((r, ev))
            print(f"  {r['ticker']:<8s} P={r['probability']:.4f} Tier={r['tier']} ({r['action']})")
        return results

    def run_honing_cycle(self, force=False, max_epochs=10000, lr=0.003,
                         l2=0.005, patience=500, explore=False) -> dict:
        """
        GPU-accelerated honing cycle with dynamic VRAM management.

        Re-checks available VRAM before each cycle. Falls back to CPU
        if another GPU app has claimed memory since last cycle.

        If explore=True, runs multiple random restarts with perturbation
        to escape local optima (useful for breaking through AUC plateaus).
        """
        # Dynamic VRAM re-check: device may have changed since last cycle
        old_device = self.device
        n = len(self.resolved_events) if self.resolved_events else 0
        self.device = self.vram_mgr.get_device(n_events=n)

        # If device changed (GPU→CPU or vice versa), rebuild tensors
        if str(self.device) != str(old_device):
            print(f"  ♻️  Device changed: {old_device} → {self.device}")
            self._X_cache, self._y_cache = None, None

        if self._X_cache is None or len(self._X_cache) < 20:
            self._build_gpu_tensors()
            if self._X_cache is None:
                return {"status": "INSUFFICIENT_DATA", "n": 0}

        # Pre-cycle metrics (fast on GPU)
        self._build_gpu_model()
        with torch.no_grad():
            pre_preds = self.gpu_model(self._X_cache)
            metrics = gpu_metrics(pre_preds, self._y_cache)

        drift_alerts = DriftDetector.detect(self.scorer, self.resolved_events)
        should_recal = force or metrics["brier"] > 0.15 or len(drift_alerts) > 0
        recal_report = {"status": "NOT_NEEDED"}

        if should_recal:
            best_report = None
            best_weights = None
            best_post_brier = 1.0

            n_runs = 5 if explore else 1

            for run in range(n_runs):
                # Build fresh model from current weights
                self._build_gpu_model()

                # For exploration runs > 0, perturb weights slightly
                if run > 0:
                    with torch.no_grad():
                        noise_scale = 0.02 * (run / n_runs)  # Increasing noise
                        self.gpu_model.weights.add_(
                            torch.randn_like(self.gpu_model.weights) * noise_scale
                        )
                        self.gpu_model.bias.add_(
                            torch.randn(1, device=self.device).item() * noise_scale * 0.5
                        )

                # Configure recalibrator
                recal = GradientRecalibratorGPU(
                    lr=lr,
                    l2=l2,
                    max_epochs=max_epochs,
                    convergence=1e-9,
                    patience=patience,
                    cosine_restarts=4,
                    verbose=(run == 0),  # Only verbose on first run
                )

                report = recal.recalibrate(self.gpu_model, self._X_cache, self._y_cache)

                # Release optimizer/autograd state between runs
                recal.release_memory()

                if report.get("post_brier", 1.0) < best_post_brier:
                    best_post_brier = report["post_brier"]
                    best_report = report
                    best_weights = self.gpu_model.export_weights()

                    if n_runs > 1:
                        print(f"    Run {run+1}/{n_runs}: Brier={report['post_brier']:.6f} "
                              f"AUC={report['post_auc']:.6f} {'★ NEW BEST' if run > 0 else ''}")

            recal_report = best_report

            # Apply best weights to CPU scorer
            self.scorer.import_weights(best_weights)
            self.save_weights()

            h = self.scorer.weight_hash()
            v = f"13.2.{len(self.versions.versions) + 1}"
            self.versions.record_version(v, h, {
                "brier": recal_report.get("post_brier"),
                "auc": recal_report.get("post_auc"),
                "n": recal_report.get("n"),
                "device": str(self.device),
                "epochs_per_sec": recal_report.get("epochs_per_sec"),
                "vram_allocated_mb": recal_report.get("vram_allocated_mb"),
            }, note="gpu-auto-honing" if not force else "gpu-forced")

        self.honing_log.log_cycle(metrics, recal_report, drift_alerts)

        # Release autograd/optimizer VRAM back to system after each cycle
        self.vram_mgr.release()

        return {
            "metrics": metrics,
            "drift_alerts": drift_alerts,
            "recalibration": recal_report,
        }

    def initial_calibration(self):
        if len(self.resolved_events) < 20:
            print("  Not enough resolved events for calibration.")
            return

        self._build_gpu_tensors()
        self._build_gpu_model()

        print(f"\n  Running GPU initial calibration on {len(self.resolved_events)} events...")
        recal = GradientRecalibratorGPU(
            lr=0.003, l2=0.005, max_epochs=10000,
            patience=500, cosine_restarts=4, verbose=True,
        )
        report = recal.recalibrate(self.gpu_model, self._X_cache, self._y_cache)

        print(f"\n  Brier: {report['pre_brier']:.6f} → {report['post_brier']:.6f}")
        print(f"  AUC:   {report['pre_auc']:.6f} → {report['post_auc']:.6f}")
        print(f"  Epochs: {report['epochs']} at {report.get('epochs_per_sec', '?')} eps")

        self.scorer.import_weights(self.gpu_model.export_weights())
        self.save_weights()

        h = self.scorer.weight_hash()
        self.versions.record_version("13.2.1", h, {
            "brier": report["post_brier"],
            "auc": report["post_auc"],
            "n": report["n"],
        }, note="gpu initial calibration")

    def start_auto_honing(self, interval_minutes=5, explore=False, max_epochs=10000):
        """
        Start autonomous GPU honing loop.
        Default interval is 5 min (vs 30 min CPU) since GPU is much faster.
        """
        self._stop_flag.clear()

        def _loop():
            cycle = 0
            while not self._stop_flag.is_set():
                cycle += 1
                try:
                    # Every 10th cycle, do exploration with random restarts
                    do_explore = explore or (cycle % 10 == 0)

                    result = self.run_honing_cycle(
                        force=True,
                        max_epochs=max_epochs,
                        explore=do_explore,
                    )

                    ts = datetime.now().strftime("%H:%M:%S")
                    recal_report = result.get("recalibration", {})
                    base_metrics = result.get("metrics", {})

                    current_brier = recal_report.get("post_brier", base_metrics.get("brier", "?"))
                    current_auc = recal_report.get("post_auc", base_metrics.get("auc", "?"))
                    eps = recal_report.get("epochs_per_sec", "?")
                    epochs = recal_report.get("epochs", "?")

                    print(f"\n  [{ts}] Cycle {cycle}: Brier={current_brier} AUC={current_auc} "
                          f"| {epochs} epochs @ {eps} eps"
                          f"{' [EXPLORE]' if do_explore else ''}")

                    # Log VRAM status between cycles
                    vram_s = self.vram_mgr.status()
                    if vram_s.get("gpu"):
                        print(f"    VRAM: {vram_s['allocated_mb']:.0f} MB alloc / "
                              f"{vram_s['free_mb']:.0f} MB free / "
                              f"budget {vram_s['budget_mb']:.0f} MB")

                    # Check and save best
                    latest_v = self.versions.latest()
                    v_str = latest_v.get("version", "unknown") if latest_v else "unknown"

                    saved_file = self.best_run_tracker.check_and_save(
                        base_metrics=base_metrics,
                        recal_report=recal_report,
                        weights=self.scorer.weights,
                        version=v_str,
                    )
                    if saved_file:
                        print(f"  🏆 NEW BEST → {saved_file}")

                except Exception as ex:
                    print(f"\n  ❌ Auto-honing error: {ex}")
                    import traceback
                    traceback.print_exc()

                self._stop_flag.wait(interval_minutes * 60)

        self._auto_thread = threading.Thread(target=_loop, daemon=True)
        self._auto_thread.start()
        print(f"  🚀 GPU auto-honing started (every {interval_minutes} min, explore every 10th cycle)")

    def stop_auto_honing(self):
        self._stop_flag.set()
        if self._auto_thread:
            self._auto_thread.join(timeout=5)
        # Release all VRAM back to system on shutdown
        self.vram_mgr.release()
        print("  Auto-honing stopped. VRAM released.")

    def record_outcome(self, event_id: str, outcome: str):
        outcome = outcome.upper()
        if outcome not in ("APPROVED", "CRL"):
            return
        for ev in self.events:
            if ev.get("event_id") == event_id:
                ev["outcome"] = outcome
                break
        self.ledger.record_outcome(event_id, outcome)
        self.ledger.save()
        self.watchlist.mark_resolved(event_id, outcome)
        self._split_events()
        self._build_gpu_tensors()  # Rebuild GPU tensors with new outcome
        with open(self.events_path, "w") as f:
            json.dump(self.events, f, indent=2, default=str)
        print(f"  Recorded: {event_id} → {outcome}")

    def print_report(self):
        print(f"\n{'═' * 70}")
        print(f"  ODIN GPU MODEL REPORT")
        print(f"{'═' * 70}")
        v = self.versions.latest()
        print(f"  Engine:      v{ENGINE_VERSION}")
        print(f"  Model:       {v.get('version', 'uncalibrated') if v else 'uncalibrated'}")
        print(f"  Weight hash: {self.scorer.weight_hash()}")
        print(f"  Device:      {self.device}")
        print(f"  Features:    {N_FEATURES}")

        # VRAM status
        vram_s = self.vram_mgr.status()
        if vram_s.get("gpu"):
            print(f"\n  VRAM:        {vram_s['free_mb']:.0f} MB free of {vram_s['total_mb']:.0f} MB")
            print(f"               {vram_s['allocated_mb']:.0f} MB allocated (cap: {vram_s['fraction_cap']:.0%} of free)")
        else:
            print(f"\n  VRAM:        N/A (CPU mode)")
        print(f"\n  Events:      {len(self.events)} total")
        print(f"    Resolved:  {len(self.resolved_events)}")
        print(f"    Pending:   {len(self.unresolved_events)}")

        if self._X_cache is not None:
            with torch.no_grad():
                self._build_gpu_model()
                preds = self.gpu_model(self._X_cache)
                m = gpu_metrics(preds, self._y_cache)
            print(f"\n  GPU Calibration (n={m['n']}):")
            print(f"    Brier:     {m['brier']:.6f}")
            print(f"    AUC-ROC:   {m['auc']:.6f}")
            print(f"    Accuracy:  {m['accuracy']:.6f}")
            print(f"    Log Loss:  {m['log_loss']:.6f}")
        print(f"{'═' * 70}")

    def print_signals(self):
        w = self.scorer.weights
        print(f"\n  Base logit: {w['base_logit']:.4f} → P={sigmoid_cpu(w['base_logit']):.3f}")
        print(f"\n  Binary Signals ({len(w['signals'])}):")
        for sig, val in sorted(w['signals'].items(), key=lambda x: abs(x[1]), reverse=True):
            print(f"    {sig:<35s} {val:>+8.4f}")
        print(f"\n  TA Offsets:")
        for ta, val in sorted(w['ta_offsets'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {ta:<25s} {val:>+8.4f}")
        print(f"\n  Continuous:")
        for c, val in w['continuous'].items():
            print(f"    {c:<30s} {val:>+8.4f}")

    def print_status(self):
        print(f"\n  ODIN v{ENGINE_VERSION} | {self.device} | Hash: {self.scorer.weight_hash()}")
        print(f"  Events: {len(self.events)} total, {len(self.resolved_events)} resolved")

    def interactive(self):
        print(f"\n{'═' * 70}")
        print(f"  ODIN GPU COMMAND CENTER v{ENGINE_VERSION}")
        print(f"{'═' * 70}")
        self.print_status()

        while True:
            print(f"\n  1. Score ticker          5. Full report")
            print(f"  2. Score all pending     6. Watchlist")
            print(f"  3. Record outcome        7. Signal weights")
            print(f"  4. Run honing cycle      8. Run backtest")
            print(f"  9. Status                0. Exit")

            try:
                choice = input("\n  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "1":
                ticker = input("  Ticker: ").strip().upper()
                self.score_ticker(ticker)
            elif choice == "2":
                for ev in self.unresolved_events:
                    r = self.score_event(ev)
                    print(f"  {r['ticker']:<8s} {r['probability']:>6.3f}")
            elif choice == "3":
                eid = input("  Event ID: ").strip()
                outcome = input("  Outcome (APPROVED/CRL): ").strip()
                self.record_outcome(eid, outcome)
            elif choice == "4":
                self.run_honing_cycle(force=True)
            elif choice == "5":
                self.print_report()
            elif choice == "6":
                for ev in self.watchlist.get_pending():
                    print(f"  {ev.get('ticker', '?'):<8s} {ev.get('status', '?')}")
            elif choice == "7":
                self.print_signals()
            elif choice == "8":
                result = Backtester.time_split_backtest(self.resolved_events, device=self.device)
                if result.get("status") == "OK":
                    print(f"  Train: {result['train_metrics']}")
                    print(f"  Test:  {result['test_metrics']}")
            elif choice == "9":
                self.print_status()
            elif choice == "0":
                self.save_weights()
                print("  Weights saved. Goodbye!")
                break


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

DEFAULT_CSV = "ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv"

def find_csv() -> str:
    candidates = [
        DEFAULT_CSV,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), DEFAULT_CSV),
        os.path.join(str(Path.home()), DEFAULT_CSV),
        os.path.join(str(Path.home()), "Downloads", DEFAULT_CSV),
        os.path.join(str(Path.home()), "Documents", "Python", DEFAULT_CSV),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def main():
    parser = argparse.ArgumentParser(description=f"ODIN GPU Runner v{ENGINE_VERSION}")
    parser.add_argument("--csv", default=None, help="Path to ODIN CSV file")
    parser.add_argument("--data-dir", default=None, help="Data directory")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--signals", action="store_true")
    parser.add_argument("--hone", action="store_true", help="Run one GPU honing cycle")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--score", default=None, help="Score a ticker")
    parser.add_argument("--auto", action="store_true", help="Daemon mode with GPU auto-honing")
    parser.add_argument("--interval", type=int, default=5, help="Auto-hone interval (minutes, default 5)")
    parser.add_argument("--epochs", type=int, default=10000, help="Max epochs per cycle (default 10000)")
    parser.add_argument("--lr", type=float, default=0.003, help="Learning rate (default 0.003)")
    parser.add_argument("--l2", type=float, default=0.005, help="L2 regularization (default 0.005)")
    parser.add_argument("--patience", type=int, default=500, help="Early stop patience (default 500)")
    parser.add_argument("--explore", action="store_true", help="Enable exploration with random restarts")
    parser.add_argument("--calibrate", action="store_true", help="Run initial calibration")
    parser.add_argument("--vram-fraction", type=float, default=0.5,
                        help="Max fraction of free VRAM to use (0.05-0.95, default 0.5). "
                             "Lower values leave more room for other GPU apps.")
    parser.add_argument("--vram-status", action="store_true", help="Print VRAM status and exit")
    args = parser.parse_args()

    csv_path = args.csv or find_csv()

    print(f"\n{'═' * 70}")
    print(f"  ODIN GPU PERPETUAL RUNNER v{ENGINE_VERSION}")
    print(f"{'═' * 70}")

    # Initialize VRAMManager BEFORE runner so it's available globally
    vram_frac = max(0.05, min(0.95, args.vram_fraction))
    mgr = get_vram_manager(vram_frac)

    if args.vram_status:
        mgr.print_status()
        return

    runner = OdinRunnerGPU(data_dir=args.data_dir, csv_path=csv_path,
                            max_memory_fraction=vram_frac)

    if runner.resolved_events and not os.path.exists(runner.weights_path):
        print("\n  No saved model found. Running GPU initial calibration...")
        runner.initial_calibration()
    elif args.calibrate:
        runner.initial_calibration()

    if args.status:
        runner.print_status()
        return
    if args.signals:
        runner.print_signals()
        return
    if args.hone:
        runner.run_honing_cycle(force=True, max_epochs=args.epochs, lr=args.lr,
                                 l2=args.l2, patience=args.patience, explore=args.explore)
        runner.print_report()
        return
    if args.report:
        runner.print_report()
        return
    if args.score:
        runner.score_ticker(args.score)
        return
    if args.backtest:
        result = Backtester.time_split_backtest(runner.resolved_events, device=runner.device)
        if result.get("status") == "OK":
            print(f"\n  Train (n={result['train_n']}): {result['train_metrics']}")
            print(f"  Test  (n={result['test_n']}):  {result['test_metrics']}")
        return

    if args.auto:
        runner.start_auto_honing(
            interval_minutes=args.interval,
            explore=args.explore,
            max_epochs=args.epochs,
        )
        print(f"\n  GPU Daemon active. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            runner.stop_auto_honing()
            runner.save_weights()
            print("\n  Shutdown complete.")
        return

    runner.interactive()


if __name__ == "__main__":
    main()
