#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — KAIZEN ENGINE: Adaptive Intelligence Layer                   ║
║                                                                          ║
║  Bolts onto the LightGBM Perpetual Daemon to make it self-improving:     ║
║    • Plateau detection (auto-widen search when stuck)                    ║
║    • Adaptive mutation rate (cool down when winning, heat up when stuck) ║
║    • Feature importance memory (bias toward proven features)             ║
║    • Diversity enforcement (reject clones, track param hashes)           ║
║    • Search space annealing (narrow around proven sweet spots)           ║
║    • Real-time metrics export (JSON for dashboard consumption)           ║
║    • Kaizen score: composite improvement velocity metric                 ║
║                                                                          ║
║  Philosophy: 改善 — "change for better" — continuous, never-ending.      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import math
import time
from collections import deque
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# KAIZEN METRICS TRACKER
# ═══════════════════════════════════════════════════════════════

class KaizenTracker:
    """Tracks all improvement metrics and exports JSON for the dashboard."""

    def __init__(self, output_dir: Path, window_size: int = 50):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.window_size = window_size

        # Rolling windows
        self.auc_history = deque(maxlen=10000)
        self.brier_history = deque(maxlen=10000)
        self.promotion_rounds = []
        self.round_times = deque(maxlen=1000)
        self.feature_hits = {}        # feat -> times in champion
        self.feature_appearances = {} # feat -> times tried
        self.param_hashes_seen = set()
        self.duplicate_count = 0

        # Plateau detection
        self.rounds_since_promotion = 0
        self.plateau_events = []
        self.current_streak = 0       # consecutive non-promotions
        self.longest_streak = 0

        # Adaptive state
        self.mutation_rate = 0.30
        self.search_width = 1.0       # multiplier on Optuna trial count
        self.temperature = 1.0        # exploration temperature

        # Session tracking
        self.session_start = datetime.now().isoformat()
        self.total_rounds = 0
        self.total_promotions = 0
        self.best_auc_ever = 0.0
        self.worst_auc_ever = 1.0

        # Kaizen score components
        self.improvement_velocity = 0.0
        self.exploration_diversity = 0.0
        self.efficiency_ratio = 0.0
        self.kaizen_score = 0.0

        # Load existing state if available
        self._load_state()

    def _load_state(self):
        state_path = self.output_dir / "kaizen_state.json"
        if state_path.exists():
            try:
                with open(state_path) as f:
                    s = json.load(f)
                self.total_rounds = s.get("total_rounds", 0)
                self.total_promotions = s.get("total_promotions", 0)
                self.best_auc_ever = s.get("best_auc_ever", 0.0)
                self.worst_auc_ever = s.get("worst_auc_ever", 1.0)
                self.mutation_rate = s.get("mutation_rate", 0.30)
                self.temperature = s.get("temperature", 1.0)
                self.rounds_since_promotion = s.get("rounds_since_promotion", 0)
                self.current_streak = s.get("current_streak", 0)
                self.longest_streak = s.get("longest_streak", 0)
                self.feature_hits = s.get("feature_hits", {})
                self.feature_appearances = s.get("feature_appearances", {})
                self.duplicate_count = s.get("duplicate_count", 0)
                for entry in s.get("auc_history", []):
                    self.auc_history.append(entry)
                for entry in s.get("brier_history", []):
                    self.brier_history.append(entry)
                self.promotion_rounds = s.get("promotion_rounds", [])
                self.plateau_events = s.get("plateau_events", [])
            except Exception:
                pass

    def record_round(self, round_num, wf_auc, wf_brier, wf_t4p,
                     promoted, eng_features, params_hash, elapsed_s,
                     yearly_aucs=None, feature_importance=None):
        """Record one round's results and update all Kaizen metrics."""
        ts = datetime.now().isoformat()
        self.total_rounds = round_num

        # AUC tracking
        self.auc_history.append({
            "round": round_num,
            "wf_auc": round(wf_auc, 6),
            "wf_brier": round(wf_brier, 6),
            "wf_t4p": round(wf_t4p, 4),
            "promoted": promoted,
            "n_eng_features": len(eng_features),
            "timestamp": ts,
            "elapsed_s": round(elapsed_s, 1),
            "yearly_aucs": yearly_aucs or [],
        })
        self.brier_history.append({"round": round_num, "wf_brier": round(wf_brier, 6)})
        self.round_times.append(elapsed_s)

        # Best/worst tracking
        if wf_auc > self.best_auc_ever:
            self.best_auc_ever = wf_auc
        if wf_auc < self.worst_auc_ever and wf_auc > 0:
            self.worst_auc_ever = wf_auc

        # Feature tracking
        for feat in eng_features:
            self.feature_appearances[feat] = self.feature_appearances.get(feat, 0) + 1

        # Duplicate detection
        if params_hash in self.param_hashes_seen:
            self.duplicate_count += 1
        self.param_hashes_seen.add(params_hash)

        # Promotion tracking
        if promoted:
            self.total_promotions += 1
            self.promotion_rounds.append({
                "round": round_num, "wf_auc": round(wf_auc, 6), "timestamp": ts
            })
            for feat in eng_features:
                self.feature_hits[feat] = self.feature_hits.get(feat, 0) + 1
            self.current_streak = 0
            self.rounds_since_promotion = 0
        else:
            self.current_streak += 1
            self.rounds_since_promotion += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak

        # Feature importance memory
        if feature_importance and promoted:
            for feat, imp in feature_importance.items():
                self.feature_hits[feat] = self.feature_hits.get(feat, 0) + 1

        # Plateau detection
        if self.current_streak >= 10 and self.current_streak % 10 == 0:
            self.plateau_events.append({
                "round": round_num, "streak": self.current_streak, "timestamp": ts
            })

        # Update Kaizen metrics
        self._update_kaizen_score()
        self._adapt_parameters()
        self._export_dashboard_json()
        self._save_state()

    def _update_kaizen_score(self):
        """Compute composite Kaizen score (0-100)."""
        # Component 1: Improvement velocity (AUC gain per round, recent 50)
        recent = list(self.auc_history)[-self.window_size:]
        if len(recent) >= 2:
            promoted_in_window = sum(1 for r in recent if r["promoted"])
            self.improvement_velocity = promoted_in_window / len(recent) * 100
        else:
            self.improvement_velocity = 0

        # Component 2: Exploration diversity (unique param hashes / total rounds)
        if self.total_rounds > 0:
            self.exploration_diversity = min(100, len(self.param_hashes_seen) / max(self.total_rounds, 1) * 100)
        else:
            self.exploration_diversity = 0

        # Component 3: Efficiency ratio (promotions per round, overall)
        if self.total_rounds > 0:
            self.efficiency_ratio = self.total_promotions / self.total_rounds * 100
        else:
            self.efficiency_ratio = 0

        # Composite Kaizen score
        self.kaizen_score = (
            0.40 * min(self.improvement_velocity * 5, 100) +  # velocity (heavily weighted)
            0.30 * self.exploration_diversity +                 # diversity
            0.20 * min(self.efficiency_ratio * 10, 100) +      # efficiency
            0.10 * max(0, (1 - self.current_streak / 50) * 100)  # freshness penalty
        )
        self.kaizen_score = round(min(100, max(0, self.kaizen_score)), 1)

    def _adapt_parameters(self):
        """Adaptive mutation and search width based on performance.

        Checks for AI override file first — if present and fresh (<5min),
        uses AI-tuned values instead of auto-adapting.
        """
        # Check for AI override (written by /api/ai/tune)
        ai_override = self._check_ai_override()
        if ai_override:
            if "mutation_rate" in ai_override:
                self.mutation_rate = ai_override["mutation_rate"]
            if "temperature" in ai_override:
                self.temperature = ai_override["temperature"]
            if "search_width" in ai_override:
                self.search_width = ai_override["search_width"]
            return  # Skip auto-adaptation when AI is steering

        # Adaptive mutation rate
        if self.current_streak >= 20:
            # Very stuck — go exploratory
            self.mutation_rate = min(0.60, 0.30 + (self.current_streak - 20) * 0.01)
            self.temperature = min(2.0, 1.0 + (self.current_streak - 20) * 0.05)
        elif self.current_streak >= 10:
            # Moderately stuck — warm up
            self.mutation_rate = min(0.45, 0.30 + (self.current_streak - 10) * 0.015)
            self.temperature = min(1.5, 1.0 + (self.current_streak - 10) * 0.03)
        elif self.current_streak == 0:
            # Just promoted — cool down to exploit
            self.mutation_rate = max(0.15, self.mutation_rate * 0.8)
            self.temperature = max(0.7, self.temperature * 0.9)
        else:
            # Normal — drift back toward baseline
            self.mutation_rate = 0.30 + (self.mutation_rate - 0.30) * 0.9
            self.temperature = 1.0 + (self.temperature - 1.0) * 0.9

        # Search width (multiplier on Optuna trials)
        if self.current_streak >= 15:
            self.search_width = min(3.0, 1.0 + (self.current_streak - 15) * 0.1)
        else:
            self.search_width = max(1.0, self.search_width * 0.95)

    def _check_ai_override(self):
        """Check if AI has recently tuned parameters via the dashboard API."""
        state_path = self.output_dir / "kaizen_state.json"
        try:
            if state_path.exists():
                with open(state_path) as f:
                    s = json.load(f)
                last_tune = s.get("last_ai_tune")
                if last_tune:
                    from datetime import datetime as dt
                    tune_time = dt.fromisoformat(last_tune)
                    age_minutes = (dt.now() - tune_time).total_seconds() / 60
                    if age_minutes < 5:  # AI override valid for 5 minutes
                        return {
                            "mutation_rate": s.get("mutation_rate"),
                            "temperature": s.get("temperature"),
                            "search_width": s.get("search_width", self.search_width),
                        }
        except Exception:
            pass
        return None

    def get_adaptive_config(self):
        """Return current adaptive parameters for the daemon to use."""
        return {
            "mutation_rate": round(self.mutation_rate, 4),
            "temperature": round(self.temperature, 3),
            "search_width": round(self.search_width, 2),
            "feature_bias": self._get_feature_bias(),
        }

    def _get_feature_bias(self):
        """Compute feature bias scores: features that appear in champions get boosted."""
        bias = {}
        for feat, hits in self.feature_hits.items():
            appearances = self.feature_appearances.get(feat, 1)
            # Win rate = how often this feature was in a champion when tried
            win_rate = hits / max(appearances, 1)
            bias[feat] = round(win_rate, 3)
        return bias

    def _export_dashboard_json(self):
        """Export current metrics as JSON for the dashboard to consume."""
        recent_50 = list(self.auc_history)[-50:]
        all_history = list(self.auc_history)

        dashboard_data = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "session_start": self.session_start,
                "daemon_version": "kaizen-v1.0",
            },
            "summary": {
                "total_rounds": self.total_rounds,
                "total_promotions": self.total_promotions,
                "promotion_rate": round(self.total_promotions / max(self.total_rounds, 1), 4),
                "best_auc_ever": round(self.best_auc_ever, 6),
                "worst_auc_ever": round(self.worst_auc_ever, 6),
                "auc_range": round(self.best_auc_ever - self.worst_auc_ever, 6),
                "current_streak": self.current_streak,
                "longest_streak": self.longest_streak,
                "duplicate_count": self.duplicate_count,
                "unique_configs": len(self.param_hashes_seen),
                "avg_round_time_s": round(sum(self.round_times) / max(len(self.round_times), 1), 1),
            },
            "kaizen": {
                "score": self.kaizen_score,
                "improvement_velocity": round(self.improvement_velocity, 2),
                "exploration_diversity": round(self.exploration_diversity, 2),
                "efficiency_ratio": round(self.efficiency_ratio, 2),
                "freshness": round(max(0, (1 - self.current_streak / 50) * 100), 1),
            },
            "adaptive": {
                "mutation_rate": round(self.mutation_rate, 4),
                "temperature": round(self.temperature, 3),
                "search_width": round(self.search_width, 2),
            },
            "auc_series": [
                {"round": e["round"], "wf_auc": e["wf_auc"], "promoted": e["promoted"],
                 "timestamp": e["timestamp"]}
                for e in all_history
            ],
            "brier_series": [
                {"round": e["round"], "wf_brier": e["wf_brier"]}
                for e in list(self.brier_history)
            ],
            "promotion_history": self.promotion_rounds[-50:],
            "plateau_events": self.plateau_events[-20:],
            "feature_win_rates": self._get_feature_bias(),
            "feature_appearances": dict(sorted(
                self.feature_appearances.items(), key=lambda x: x[1], reverse=True
            )[:26]),
            "recent_rounds": [
                {
                    "round": e["round"],
                    "wf_auc": e["wf_auc"],
                    "wf_brier": e["wf_brier"],
                    "wf_t4p": e["wf_t4p"],
                    "promoted": e["promoted"],
                    "n_eng": e["n_eng_features"],
                    "elapsed": e["elapsed_s"],
                    "yearly_aucs": e.get("yearly_aucs", []),
                }
                for e in recent_50
            ],
        }

        out_path = self.output_dir / "kaizen_dashboard.json"
        with open(out_path, "w") as f:
            json.dump(dashboard_data, f, indent=2)

    def _save_state(self):
        """Persist tracker state across daemon restarts."""
        state = {
            "total_rounds": self.total_rounds,
            "total_promotions": self.total_promotions,
            "best_auc_ever": self.best_auc_ever,
            "worst_auc_ever": self.worst_auc_ever,
            "mutation_rate": self.mutation_rate,
            "temperature": self.temperature,
            "rounds_since_promotion": self.rounds_since_promotion,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "feature_hits": self.feature_hits,
            "feature_appearances": self.feature_appearances,
            "duplicate_count": self.duplicate_count,
            "auc_history": list(self.auc_history)[-500:],  # keep last 500
            "brier_history": list(self.brier_history)[-500:],
            "promotion_rounds": self.promotion_rounds[-100:],
            "plateau_events": self.plateau_events[-50:],
            "saved_at": datetime.now().isoformat(),
        }
        with open(self.output_dir / "kaizen_state.json", "w") as f:
            json.dump(state, f, indent=2)
