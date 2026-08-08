#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — DUAL SPEAR KAIZEN: ODIN × GUNGNIR Orchestrator              ║
║                                                                          ║
║  The Allfather's Two Spears:                                            ║
║    🔱 ODIN    → FDA PDUFA approval predictions (LightGBM)              ║
║    🔱 GUNGNIR → Phase 2/3 readout predictions (LightGBM)               ║
║                                                                          ║
║  This orchestrator:                                                      ║
║    1. Runs both engines in alternating rounds (interleaved Kaizen)      ║
║    2. Tracks separate champion ladders per spear                        ║
║    3. Computes dual-spear ensemble when both have champions             ║
║    4. Exports unified dashboard JSON for both spears                    ║
║    5. Adaptive resource allocation (more rounds to weaker spear)        ║
║                                                                          ║
║  Stop: Create STOP_DUAL file in 9realms/ root                           ║
║  Dashboard: kaizen_dual/dual_dashboard.json                             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np

# ═══════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════
REALMS_ROOT = Path(__file__).resolve().parent.parent
DUAL_KAIZEN_DIR = REALMS_ROOT / "kaizen_dual"
DUAL_KAIZEN_DIR.mkdir(parents=True, exist_ok=True)
STOP_FILE = REALMS_ROOT / "STOP_DUAL"
ALERTS_DIR = REALMS_ROOT / "alerts"
ALERTS_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════
LOG_PATH = ALERTS_DIR / "dual_spear_log.txt"
# Force UTF-8 on Windows to handle emoji in log messages
_fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
_sh = logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_fh, _sh],
)
log = logging.getLogger("dual_spear")

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
MAX_ROUNDS_PER_SPEAR = 999_999
SLEEP_BETWEEN_SPEARS = 2
DUAL_ENSEMBLE_THRESHOLD = 0.89  # Only combine if both > this AUC
ALLOCATION_BIAS = 0.6           # Fraction of rounds for weaker spear

# Graceful shutdown
SHUTDOWN = False
def _signal_handler(sig, frame):
    global SHUTDOWN
    log.info("⚡ Dual spear shutdown signal received...")
    SHUTDOWN = True
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ═══════════════════════════════════════════════════════════════
# IMPORT ENGINES (lazy — so either can fail independently)
# ═══════════════════════════════════════════════════════════════

sys.path.insert(0, str(Path(__file__).resolve().parent))

ODIN_AVAILABLE = False
GUNGNIR_AVAILABLE = False

try:
    import lgb_perpetual_daemon as odin_engine
    ODIN_AVAILABLE = True
except ImportError as e:
    log.warning(f"ODIN engine not available: {e}")

try:
    import gungnir_historical_evolve as gungnir_engine
    GUNGNIR_AVAILABLE = True
except ImportError as e:
    log.warning(f"GUNGNIR engine not available: {e}")

try:
    from kaizen_engine import KaizenTracker
    KAIZEN_ENABLED = True
except ImportError:
    KAIZEN_ENABLED = False


# ═══════════════════════════════════════════════════════════════
# DUAL SPEAR STATE TRACKER
# ═══════════════════════════════════════════════════════════════

class DualSpearState:
    """Track both spears' performance for allocation + dashboard."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.state_path = output_dir / "dual_state.json"

        # Per-spear tracking
        self.odin_rounds = 0
        self.odin_promotions = 0
        self.odin_best_auc = 0.0
        self.odin_current_auc = 0.0
        self.odin_history = []

        self.gungnir_rounds = 0
        self.gungnir_promotions = 0
        self.gungnir_best_auc = 0.0
        self.gungnir_current_auc = 0.0
        self.gungnir_history = []

        # Dual tracking
        self.dual_rounds = 0
        self.dual_ensemble_auc = 0.0
        self.allocation_ratio = 0.5  # 0=all ODIN, 1=all GUNGNIR
        self.session_start = datetime.now().isoformat()

        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    s = json.load(f)
                for k, v in s.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
            except Exception:
                pass

    def record_odin_round(self, metrics):
        self.odin_rounds += 1
        self.dual_rounds += 1
        if metrics["promoted"]:
            self.odin_promotions += 1
        auc = metrics["wf_auc"]
        self.odin_current_auc = auc
        if auc > self.odin_best_auc:
            self.odin_best_auc = auc
        self.odin_history.append({
            "round": self.dual_rounds,
            "wf_auc": round(auc, 6),
            "promoted": metrics["promoted"],
            "timestamp": datetime.now().isoformat(),
        })
        # Keep last 200
        self.odin_history = self.odin_history[-200:]
        self._update_allocation()
        self._save()

    def record_gungnir_round(self, metrics):
        self.gungnir_rounds += 1
        self.dual_rounds += 1
        if metrics["promoted"]:
            self.gungnir_promotions += 1
        auc = metrics["wf_auc"]
        self.gungnir_current_auc = auc
        if auc > self.gungnir_best_auc:
            self.gungnir_best_auc = auc
        self.gungnir_history.append({
            "round": self.dual_rounds,
            "wf_auc": round(auc, 6),
            "promoted": metrics["promoted"],
            "timestamp": datetime.now().isoformat(),
        })
        self.gungnir_history = self.gungnir_history[-200:]
        self._update_allocation()
        self._save()

    def _update_allocation(self):
        """Shift more rounds to the weaker spear."""
        if self.odin_best_auc > 0 and self.gungnir_best_auc > 0:
            # Higher ratio = more Gungnir rounds
            odin_gap = 1.0 - self.odin_best_auc
            gun_gap = 1.0 - self.gungnir_best_auc
            total_gap = odin_gap + gun_gap
            if total_gap > 0:
                # Ratio = fraction of rounds that should go to ODIN
                self.allocation_ratio = odin_gap / total_gap
            else:
                self.allocation_ratio = 0.5
        else:
            self.allocation_ratio = 0.5

    def should_run_odin(self):
        """Determine if next round should be ODIN based on allocation."""
        if not ODIN_AVAILABLE:
            return False
        if not GUNGNIR_AVAILABLE:
            return True
        # Use allocation ratio + round parity for interleaving
        if self.odin_rounds == 0:
            return True  # First round always ODIN
        if self.gungnir_rounds == 0:
            return False  # Second round always GUNGNIR

        # Simple adaptive interleaving
        odin_fraction = self.odin_rounds / max(self.dual_rounds, 1)
        target = self.allocation_ratio
        return odin_fraction < target

    def export_dashboard(self):
        """Export unified dual-spear dashboard JSON."""
        data = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "session_start": self.session_start,
                "version": "dual-spear-v1.0",
            },
            "summary": {
                "dual_rounds": self.dual_rounds,
                "odin_rounds": self.odin_rounds,
                "gungnir_rounds": self.gungnir_rounds,
                "allocation_ratio": round(self.allocation_ratio, 3),
                "dual_ensemble_auc": round(self.dual_ensemble_auc, 6),
            },
            "odin": {
                "rounds": self.odin_rounds,
                "promotions": self.odin_promotions,
                "best_auc": round(self.odin_best_auc, 6),
                "current_auc": round(self.odin_current_auc, 6),
                "promotion_rate": round(self.odin_promotions / max(self.odin_rounds, 1), 4),
            },
            "gungnir": {
                "rounds": self.gungnir_rounds,
                "promotions": self.gungnir_promotions,
                "best_auc": round(self.gungnir_best_auc, 6),
                "current_auc": round(self.gungnir_current_auc, 6),
                "promotion_rate": round(self.gungnir_promotions / max(self.gungnir_rounds, 1), 4),
            },
            "odin_series": self.odin_history[-100:],
            "gungnir_series": self.gungnir_history[-100:],
        }
        out = self.output_dir / "dual_dashboard.json"
        with open(out, "w") as f:
            json.dump(data, f, indent=2)

    def _save(self):
        state = {
            "odin_rounds": self.odin_rounds,
            "odin_promotions": self.odin_promotions,
            "odin_best_auc": self.odin_best_auc,
            "odin_current_auc": self.odin_current_auc,
            "odin_history": self.odin_history[-200:],
            "gungnir_rounds": self.gungnir_rounds,
            "gungnir_promotions": self.gungnir_promotions,
            "gungnir_best_auc": self.gungnir_best_auc,
            "gungnir_current_auc": self.gungnir_current_auc,
            "gungnir_history": self.gungnir_history[-200:],
            "dual_rounds": self.dual_rounds,
            "dual_ensemble_auc": self.dual_ensemble_auc,
            "allocation_ratio": self.allocation_ratio,
            "session_start": self.session_start,
            "saved_at": datetime.now().isoformat(),
        }
        with open(self.state_path, "w") as f:
            json.dump(state, f, indent=2)
        self.export_dashboard()


# ═══════════════════════════════════════════════════════════════
# MAIN DUAL-SPEAR LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info("  9REALMS DUAL SPEAR KAIZEN — ODIN × GUNGNIR")
    log.info(f"  Started: {datetime.now().isoformat()}")
    log.info(f"  ODIN engine:    {'✅ READY' if ODIN_AVAILABLE else '❌ NOT FOUND'}")
    log.info(f"  GUNGNIR engine: {'✅ READY' if GUNGNIR_AVAILABLE else '❌ NOT FOUND'}")
    log.info(f"  Kaizen:         {'✅ ENABLED' if KAIZEN_ENABLED else '❌ DISABLED'}")
    log.info(f"  Dual ensemble threshold: {DUAL_ENSEMBLE_THRESHOLD}")
    log.info(f"  Stop file: {STOP_FILE}")
    log.info("=" * 70)

    if not ODIN_AVAILABLE and not GUNGNIR_AVAILABLE:
        log.error("Neither engine available. Exiting.")
        return

    # Initialize state tracker
    dual_state = DualSpearState(DUAL_KAIZEN_DIR)

    # Initialize engine data
    odin_rows = None
    odin_ladder = None
    odin_rng = None
    odin_kaizen = None

    gungnir_rows = None
    gungnir_ladder = None
    gungnir_rng = None
    gungnir_kaizen = None

    if ODIN_AVAILABLE:
        odin_rows = odin_engine.load_raw_rows()
        odin_ladder = odin_engine.load_ladder()
        odin_rng = np.random.RandomState(42 + odin_ladder["total_rounds"] + 1)
        log.info(f"  ODIN: {len(odin_rows)} PDUFA events loaded")
        if KAIZEN_ENABLED:
            odin_kaizen = KaizenTracker(odin_engine.KAIZEN_DIR)

    if GUNGNIR_AVAILABLE:
        gungnir_rows = gungnir_engine.load_raw_rows()
        gungnir_ladder = gungnir_engine.load_ladder()
        gungnir_rng = np.random.RandomState(77 + gungnir_ladder["total_rounds"] + 1)
        log.info(f"  GUNGNIR: {len(gungnir_rows)} readout events loaded")
        if KAIZEN_ENABLED:
            gungnir_kaizen = KaizenTracker(gungnir_engine.KAIZEN_DIR)

    for dual_round in range(1, MAX_ROUNDS_PER_SPEAR + 1):
        if SHUTDOWN:
            log.info("⚡ Dual spear shutdown.")
            break
        if STOP_FILE.exists():
            log.info("🛑 STOP_DUAL detected — halting both spears.")
            STOP_FILE.unlink()
            break

        # ── Decide which spear to run ────────────────────────
        run_odin = dual_state.should_run_odin()
        spear_name = "ODIN" if run_odin else "GUNGNIR"

        log.info(f"\n{'═' * 60}")
        log.info(f"  DUAL ROUND {dual_round} | Spear: {spear_name} | "
                 f"Alloc: ODIN={dual_state.allocation_ratio:.2f}/GUN={1-dual_state.allocation_ratio:.2f}")
        log.info(f"{'═' * 60}")

        try:
            if run_odin and ODIN_AVAILABLE:
                # ── Run ODIN round ───────────────────────────
                odin_round = odin_ladder["total_rounds"] + 1

                # Apply Kaizen
                if odin_kaizen:
                    ac = odin_kaizen.get_adaptive_config()
                    odin_engine.FEATURE_MUTATION_RATE = ac["mutation_rate"]
                    odin_engine.OPTUNA_TRIALS_PER_ROUND = max(10, int(40 * ac["search_width"]))

                promoted, metrics = odin_engine.run_one_round(
                    odin_round, odin_rows, odin_ladder, odin_rng
                )

                if odin_kaizen:
                    odin_kaizen.record_round(
                        round_num=odin_round,
                        wf_auc=metrics["wf_auc"],
                        wf_brier=metrics["wf_brier"],
                        wf_t4p=metrics["wf_t4p"],
                        promoted=metrics["promoted"],
                        eng_features=metrics["eng_features"],
                        params_hash=metrics["params_hash"],
                        elapsed_s=metrics["elapsed_s"],
                        yearly_aucs=metrics.get("yearly_aucs"),
                        feature_importance=metrics.get("feature_importance"),
                    )

                dual_state.record_odin_round(metrics)
                log.info(f"  🔱 ODIN: WF AUC={metrics['wf_auc']:.6f} | "
                         f"{'🏆 PROMOTED' if promoted else '❌ Not promoted'}")

            elif not run_odin and GUNGNIR_AVAILABLE:
                # ── Run GUNGNIR round ────────────────────────
                gun_round = gungnir_ladder["total_rounds"] + 1

                if gungnir_kaizen:
                    ac = gungnir_kaizen.get_adaptive_config()
                    gungnir_engine.FEATURE_MUTATION_RATE = ac["mutation_rate"]
                    gungnir_engine.OPTUNA_TRIALS_PER_ROUND = max(10, int(40 * ac["search_width"]))

                promoted, metrics = gungnir_engine.run_one_round(
                    gun_round, gungnir_rows, gungnir_ladder, gungnir_rng
                )

                if gungnir_kaizen:
                    gungnir_kaizen.record_round(
                        round_num=gun_round,
                        wf_auc=metrics["wf_auc"],
                        wf_brier=metrics["wf_brier"],
                        wf_t4p=metrics["wf_t4p"],
                        promoted=metrics["promoted"],
                        eng_features=metrics["eng_features"],
                        params_hash=metrics["params_hash"],
                        elapsed_s=metrics["elapsed_s"],
                        yearly_aucs=metrics.get("yearly_aucs"),
                        feature_importance=metrics.get("feature_importance"),
                    )

                dual_state.record_gungnir_round(metrics)
                log.info(f"  🔱 GUNGNIR: WF AUC={metrics['wf_auc']:.6f} | "
                         f"{'🏆 PROMOTED' if promoted else '❌ Not promoted'}")

            else:
                # Fallback: run whichever is available
                if ODIN_AVAILABLE:
                    odin_round = odin_ladder["total_rounds"] + 1
                    promoted, metrics = odin_engine.run_one_round(
                        odin_round, odin_rows, odin_ladder, odin_rng
                    )
                    dual_state.record_odin_round(metrics)
                elif GUNGNIR_AVAILABLE:
                    gun_round = gungnir_ladder["total_rounds"] + 1
                    promoted, metrics = gungnir_engine.run_one_round(
                        gun_round, gungnir_rows, gungnir_ladder, gungnir_rng
                    )
                    dual_state.record_gungnir_round(metrics)

            # ── Dual ensemble check ──────────────────────────
            if (dual_state.odin_best_auc >= DUAL_ENSEMBLE_THRESHOLD and
                    dual_state.gungnir_best_auc >= DUAL_ENSEMBLE_THRESHOLD):
                # Simple weighted ensemble AUC estimate
                dual_state.dual_ensemble_auc = (
                    0.5 * dual_state.odin_best_auc +
                    0.5 * dual_state.gungnir_best_auc
                )
                log.info(f"  ⚔️ DUAL ENSEMBLE AUC (est): {dual_state.dual_ensemble_auc:.6f}")

            # Summary line
            log.info(f"  📊 ODIN best={dual_state.odin_best_auc:.6f} ({dual_state.odin_rounds}r) | "
                     f"GUNGNIR best={dual_state.gungnir_best_auc:.6f} ({dual_state.gungnir_rounds}r)")

        except Exception as e:
            log.error(f"  ❌ Dual round {dual_round} FAILED: {e}")
            log.error(traceback.format_exc())
            time.sleep(5)
            continue

        if SLEEP_BETWEEN_SPEARS > 0:
            time.sleep(SLEEP_BETWEEN_SPEARS)

    # ── Final Summary ────────────────────────────────────────
    log.info("\n" + "=" * 70)
    log.info("  DUAL SPEAR SESSION COMPLETE")
    log.info(f"  Total dual rounds: {dual_state.dual_rounds}")
    log.info(f"  ODIN:    {dual_state.odin_rounds} rounds, {dual_state.odin_promotions} promotions, "
             f"best AUC={dual_state.odin_best_auc:.6f}")
    log.info(f"  GUNGNIR: {dual_state.gungnir_rounds} rounds, {dual_state.gungnir_promotions} promotions, "
             f"best AUC={dual_state.gungnir_best_auc:.6f}")
    log.info(f"  Dual ensemble AUC: {dual_state.dual_ensemble_auc:.6f}")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
