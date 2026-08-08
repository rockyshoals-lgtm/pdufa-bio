#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — KAIZEN LIVE DASHBOARD                                        ║
║                                                                          ║
║  Real-time monitoring for ODIN × GUNGNIR Dual-Spear training.           ║
║                                                                          ║
║  Features:                                                               ║
║    • Live AUC/Brier progression charts (Chart.js)                       ║
║    • Champion ladder history                                             ║
║    • Feature importance visualization                                    ║
║    • Moonshot surge tier distribution                                    ║
║    • Daemon start/stop controls                                          ║
║    • Kaizen adaptive metrics                                             ║
║    • Real-time log streaming                                             ║
║                                                                          ║
║  Usage:  python kaizen_dashboard.py                                      ║
║  Open:   http://localhost:9876                                           ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import subprocess
import sys
import time
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, Response, send_from_directory, request

# ═══════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════
REALMS_ROOT = Path(__file__).resolve().parent
MCP_CORE = REALMS_ROOT / "mcp_core"

# Data sources
DUAL_DASHBOARD = REALMS_ROOT / "kaizen_dual" / "dual_dashboard.json"
GUNGNIR_DASHBOARD = REALMS_ROOT / "kaizen_gungnir" / "kaizen_dashboard.json"
ODIN_DASHBOARD = REALMS_ROOT / "kaizen" / "kaizen_dashboard.json"
GUNGNIR_LADDER = REALMS_ROOT / "models" / "gungnir_lgb_champions" / "gungnir_champion_ladder.json"
ODIN_LADDER = REALMS_ROOT / "models" / "lgb_champions" / "champion_ladder.json"
GUNGNIR_KAIZEN_STATE = REALMS_ROOT / "kaizen_gungnir" / "kaizen_state.json"
ODIN_KAIZEN_STATE = REALMS_ROOT / "kaizen" / "kaizen_state.json"
DUAL_LOG = REALMS_ROOT / "alerts" / "dual_spear_log.txt"

# Stop files
STOP_DUAL = REALMS_ROOT / "STOP_DUAL"
STOP_GUNGNIR = REALMS_ROOT / "STOP_GUNGNIR_LGB"
STOP_ODIN = REALMS_ROOT / "STOP_LGB"

# ═══════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════
app = Flask(__name__)

# Process tracking
daemon_processes = {}
log_buffer = deque(maxlen=500)

def _safe_json(path):
    """Read JSON file safely, return {} on any error."""
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _safe_tail(path, lines=100):
    """Read last N lines of a log file."""
    try:
        if path.exists():
            with open(path, "r") as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
    except Exception:
        pass
    return []

# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return DASHBOARD_HTML

@app.route("/api/status")
def api_status():
    """Master status endpoint — polled every 2s by the frontend."""
    dual = _safe_json(DUAL_DASHBOARD)
    gungnir_kz = _safe_json(GUNGNIR_DASHBOARD)
    odin_kz = _safe_json(ODIN_DASHBOARD)
    gungnir_ladder = _safe_json(GUNGNIR_LADDER)
    odin_ladder = _safe_json(ODIN_LADDER)
    gungnir_state = _safe_json(GUNGNIR_KAIZEN_STATE)
    odin_state = _safe_json(ODIN_KAIZEN_STATE)

    # Daemon running status
    running = {}
    for name, proc in daemon_processes.items():
        running[name] = proc.poll() is None if proc else False

    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "daemons_running": running,
        "dual": dual,
        "gungnir_kaizen": gungnir_kz,
        "odin_kaizen": odin_kz,
        "gungnir_champion": gungnir_ladder.get("current_champion", {}),
        "odin_champion": odin_ladder.get("current_champion", {}),
        "gungnir_state": gungnir_state,
        "odin_state": odin_state,
    })

@app.route("/api/logs")
def api_logs():
    """Stream last 100 lines of dual spear log."""
    lines = _safe_tail(DUAL_LOG, 100)
    return jsonify({"lines": [l.rstrip() for l in lines]})

@app.route("/api/start/<daemon>")
def api_start(daemon):
    """Start a daemon: dual, gungnir, or odin."""
    if daemon == "dual":
        # Remove stop file
        if STOP_DUAL.exists():
            STOP_DUAL.unlink()
        script = str(MCP_CORE / "dual_spear_kaizen.py")
    elif daemon == "gungnir":
        if STOP_GUNGNIR.exists():
            STOP_GUNGNIR.unlink()
        script = str(MCP_CORE / "gungnir_historical_evolve.py")
    elif daemon == "odin":
        if STOP_ODIN.exists():
            STOP_ODIN.unlink()
        script = str(MCP_CORE / "lgb_perpetual_daemon.py")
    else:
        return jsonify({"error": f"Unknown daemon: {daemon}"}), 400

    # Check if already running
    if daemon in daemon_processes and daemon_processes[daemon].poll() is None:
        return jsonify({"status": "already_running"})

    proc = subprocess.Popen(
        [sys.executable, script],
        cwd=str(REALMS_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    daemon_processes[daemon] = proc

    # Background thread to capture output
    def _read_output(p, name):
        try:
            for line in p.stdout:
                log_buffer.append(f"[{name}] {line.rstrip()}")
        except Exception:
            pass
    t = threading.Thread(target=_read_output, args=(proc, daemon), daemon=True)
    t.start()

    return jsonify({"status": "started", "pid": proc.pid})

@app.route("/api/stop/<daemon>")
def api_stop(daemon):
    """Stop a daemon by creating its stop file."""
    stop_map = {"dual": STOP_DUAL, "gungnir": STOP_GUNGNIR, "odin": STOP_ODIN}
    if daemon not in stop_map:
        return jsonify({"error": f"Unknown daemon: {daemon}"}), 400

    stop_map[daemon].touch()

    # Also try to terminate the process
    if daemon in daemon_processes and daemon_processes[daemon].poll() is None:
        daemon_processes[daemon].terminate()

    return jsonify({"status": "stopping"})

@app.route("/api/live_log")
def api_live_log():
    """Return captured live log lines from daemon processes."""
    lines = list(log_buffer)
    return jsonify({"lines": lines[-200:]})

# ═══════════════════════════════════════════════════════════════
# AI COPILOT — Diagnostic, Tuning & Recommendation APIs
# ═══════════════════════════════════════════════════════════════

# AI tuning history (persisted to JSON)
AI_TUNING_LOG = REALMS_ROOT / "kaizen_dual" / "ai_tuning_log.json"
ai_recommendations = deque(maxlen=100)

def _load_ai_log():
    try:
        if AI_TUNING_LOG.exists():
            with open(AI_TUNING_LOG) as f:
                return json.load(f)
    except Exception:
        pass
    return {"tunings": [], "recommendations": []}

def _save_ai_log(data):
    AI_TUNING_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AI_TUNING_LOG, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/api/ai/diagnose")
def api_ai_diagnose():
    """AI-readable diagnostic of current training state.

    Returns structured analysis optimized for LLM consumption:
    - Current performance metrics and trends
    - Plateau detection status
    - Feature effectiveness analysis
    - Hyperparameter state and recommendations
    - Actionable suggestions
    """
    gk = _safe_json(GUNGNIR_DASHBOARD)
    ok = _safe_json(ODIN_DASHBOARD)
    gc = _safe_json(GUNGNIR_LADDER).get("current_champion", {})
    oc = _safe_json(ODIN_LADDER).get("current_champion", {})
    gs = _safe_json(GUNGNIR_KAIZEN_STATE)
    os_state = _safe_json(ODIN_KAIZEN_STATE)
    dual = _safe_json(DUAL_DASHBOARD)

    # Extract key metrics
    gk_summary = gk.get("summary", {})
    gk_kaizen = gk.get("kaizen", {})
    gk_adaptive = gk.get("adaptive", {})
    ok_summary = ok.get("summary", {})
    ok_kaizen = ok.get("kaizen", {})
    ok_adaptive = ok.get("adaptive", {})

    # Recent AUC trend (last 20 rounds)
    g_recent = (gk.get("recent_rounds", []) or [])[-20:]
    o_recent = (ok.get("recent_rounds", []) or [])[-20:]

    # Compute trend
    def calc_trend(recent):
        if len(recent) < 4:
            return {"direction": "insufficient_data", "slope": 0}
        half = len(recent) // 2
        first_half = [r["wf_auc"] for r in recent[:half]]
        second_half = [r["wf_auc"] for r in recent[half:]]
        avg1 = sum(first_half) / len(first_half) if first_half else 0
        avg2 = sum(second_half) / len(second_half) if second_half else 0
        diff = avg2 - avg1
        if diff > 0.001:
            return {"direction": "improving", "slope": round(diff, 6)}
        elif diff < -0.001:
            return {"direction": "degrading", "slope": round(diff, 6)}
        else:
            return {"direction": "plateau", "slope": round(diff, 6)}

    # Feature effectiveness
    g_feat_wins = gk.get("feature_win_rates", {})
    g_feat_apps = gk.get("feature_appearances", {})
    top_features = sorted(g_feat_wins.items(), key=lambda x: x[1], reverse=True)[:10]
    worst_features = sorted(g_feat_wins.items(), key=lambda x: x[1])[:5]

    # Build diagnostic
    diagnostic = {
        "generated_at": datetime.now().isoformat(),
        "system_state": {
            "daemons_running": {
                name: (proc.poll() is None if proc else False)
                for name, proc in daemon_processes.items()
            },
        },
        "gungnir": {
            "champion_auc": gc.get("wf_auc"),
            "champion_brier": gc.get("wf_brier"),
            "champion_t4p": gc.get("wf_t4p"),
            "champion_features": gc.get("n_features"),
            "champion_eng_features": gc.get("eng_features", []),
            "total_rounds": gk_summary.get("total_rounds", 0),
            "total_promotions": gk_summary.get("total_promotions", 0),
            "promotion_rate": gk_summary.get("promotion_rate", 0),
            "current_streak": gk_summary.get("current_streak", 0),
            "longest_streak": gk_summary.get("longest_streak", 0),
            "best_auc_ever": gk_summary.get("best_auc_ever", 0),
            "trend": calc_trend(g_recent),
            "kaizen_score": gk_kaizen.get("score", 0),
            "velocity": gk_kaizen.get("improvement_velocity", 0),
            "diversity": gk_kaizen.get("exploration_diversity", 0),
            "adaptive": gk_adaptive,
            "yearly_aucs": gc.get("yearly_aucs", []),
        },
        "odin": {
            "champion_auc": oc.get("wf_auc"),
            "champion_brier": oc.get("wf_brier"),
            "champion_t4p": oc.get("wf_t4p"),
            "total_rounds": ok_summary.get("total_rounds", 0),
            "total_promotions": ok_summary.get("total_promotions", 0),
            "current_streak": ok_summary.get("current_streak", 0),
            "trend": calc_trend(o_recent),
            "adaptive": ok_adaptive,
        },
        "dual_ensemble": {
            "ensemble_auc": (dual.get("summary", {}) or {}).get("dual_ensemble_auc"),
            "dual_rounds": (dual.get("summary", {}) or {}).get("dual_rounds", 0),
        },
        "feature_analysis": {
            "top_performing": [{"name": n, "win_rate": r} for n, r in top_features],
            "underperforming": [{"name": n, "win_rate": r} for n, r in worst_features],
            "total_unique_features_tried": len(g_feat_apps),
        },
        "suggestions": _generate_suggestions(gk_summary, gk_kaizen, gk_adaptive, gc, g_feat_wins),
    }

    return jsonify(diagnostic)

def _generate_suggestions(summary, kaizen, adaptive, champion, feat_wins):
    """Generate actionable AI suggestions based on current state."""
    suggestions = []
    streak = summary.get("current_streak", 0)
    velocity = kaizen.get("improvement_velocity", 0)
    diversity = kaizen.get("exploration_diversity", 0)
    mutation = adaptive.get("mutation_rate", 0.3)
    temp = adaptive.get("temperature", 1.0)

    if streak >= 20:
        suggestions.append({
            "priority": "HIGH",
            "type": "plateau_break",
            "message": f"Stuck for {streak} rounds. Consider: increase mutation_rate to 0.55+, temperature to 1.8+, or inject new engineered features.",
            "params": {"mutation_rate": 0.55, "temperature": 1.8, "search_width": 2.5}
        })
    elif streak >= 10:
        suggestions.append({
            "priority": "MEDIUM",
            "type": "plateau_warning",
            "message": f"No promotion in {streak} rounds. Warming up exploration. Consider wider feature search.",
            "params": {"mutation_rate": 0.40, "temperature": 1.4}
        })

    if velocity < 2 and summary.get("total_rounds", 0) > 30:
        suggestions.append({
            "priority": "MEDIUM",
            "type": "low_velocity",
            "message": "Improvement velocity is low. Try increasing OPTUNA_TRIALS_PER_ROUND or adding new feature interactions.",
        })

    if diversity < 50:
        suggestions.append({
            "priority": "LOW",
            "type": "low_diversity",
            "message": "Search space exploration below 50%. Increase temperature to explore more unique configs.",
            "params": {"temperature": min(2.0, temp + 0.3)}
        })

    # Feature suggestions
    dead_features = [n for n, r in feat_wins.items() if r == 0]
    if len(dead_features) > 5:
        suggestions.append({
            "priority": "LOW",
            "type": "dead_features",
            "message": f"{len(dead_features)} features have 0% win rate. Consider pruning: {dead_features[:5]}",
        })

    best_auc = summary.get("best_auc_ever", 0)
    if best_auc > 0.99:
        suggestions.append({
            "priority": "INFO",
            "type": "near_ceiling",
            "message": f"AUC at {best_auc:.4f} — near theoretical ceiling. Focus on Brier calibration and T4 Precision over raw AUC.",
        })

    if not suggestions:
        suggestions.append({
            "priority": "INFO",
            "type": "healthy",
            "message": "Training is progressing well. No immediate interventions needed.",
        })

    return suggestions

@app.route("/api/ai/tune", methods=["POST"])
def api_ai_tune():
    """Apply parameter adjustments from AI or manual input.

    Accepts JSON body with tunable parameters:
    {
        "source": "claude|perplexity|manual",
        "reason": "why this change is being made",
        "params": {
            "mutation_rate": 0.45,       // 0.10 - 0.65
            "temperature": 1.5,          // 0.5 - 2.5
            "search_width": 2.0,         // 0.5 - 3.5
            "optuna_trials": 60,         // 20 - 200
            "ensemble_pool_size": 15,    // 5 - 30
            "feature_gate": ["feat1"],   // features to force-include
            "feature_block": ["feat2"],  // features to exclude
        }
    }
    """
    data = request.get_json(force=True) or {}
    source = data.get("source", "unknown")
    reason = data.get("reason", "No reason given")
    params = data.get("params", {})

    if not params:
        return jsonify({"error": "No params provided"}), 400

    applied = {}
    errors = []

    # Apply Kaizen state tuning (writes to kaizen_state.json)
    for spear, state_path in [("gungnir", GUNGNIR_KAIZEN_STATE), ("odin", ODIN_KAIZEN_STATE)]:
        state = _safe_json(state_path)
        if not state:
            continue

        changed = False
        if "mutation_rate" in params:
            val = max(0.10, min(0.65, float(params["mutation_rate"])))
            state["mutation_rate"] = val
            applied[f"{spear}_mutation_rate"] = val
            changed = True
        if "temperature" in params:
            val = max(0.5, min(2.5, float(params["temperature"])))
            state["temperature"] = val
            applied[f"{spear}_temperature"] = val
            changed = True
        if "search_width" in params:  # not directly in kaizen_state but we add it
            val = max(0.5, min(3.5, float(params["search_width"])))
            state["search_width"] = val
            applied[f"{spear}_search_width"] = val
            changed = True

        if changed:
            state["last_ai_tune"] = datetime.now().isoformat()
            state["last_ai_source"] = source
            try:
                with open(state_path, "w") as f:
                    json.dump(state, f, indent=2)
            except Exception as e:
                errors.append(f"Failed to write {spear} state: {str(e)}")

    # Apply daemon config overrides (optuna_trials, ensemble_pool, feature gates)
    config_overrides = {}
    if "optuna_trials" in params:
        config_overrides["optuna_trials"] = max(20, min(200, int(params["optuna_trials"])))
    if "ensemble_pool_size" in params:
        config_overrides["ensemble_pool_size"] = max(5, min(30, int(params["ensemble_pool_size"])))
    if "feature_gate" in params:
        config_overrides["feature_gate"] = params["feature_gate"]
    if "feature_block" in params:
        config_overrides["feature_block"] = params["feature_block"]

    if config_overrides:
        override_path = REALMS_ROOT / "kaizen_dual" / "ai_config_override.json"
        override_path.parent.mkdir(parents=True, exist_ok=True)
        existing = _safe_json(override_path)
        existing.update(config_overrides)
        existing["applied_at"] = datetime.now().isoformat()
        existing["source"] = source
        with open(override_path, "w") as f:
            json.dump(existing, f, indent=2)
        applied.update(config_overrides)

    # Log the tuning
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "reason": reason,
        "params_applied": applied,
        "errors": errors,
    }
    ai_log = _load_ai_log()
    ai_log["tunings"].append(log_entry)
    ai_log["tunings"] = ai_log["tunings"][-200:]  # keep last 200
    _save_ai_log(ai_log)

    log_buffer.append(f"[AI-COPILOT] Tuning applied by {source}: {json.dumps(applied)}")

    return jsonify({
        "status": "applied" if not errors else "partial",
        "applied": applied,
        "errors": errors,
        "log_entry": log_entry,
    })

@app.route("/api/ai/history")
def api_ai_history():
    """Return history of AI tunings and recommendations."""
    ai_log = _load_ai_log()
    return jsonify({
        "tunings": ai_log.get("tunings", [])[-50:],
        "recommendations": ai_log.get("recommendations", [])[-50:],
        "total_tunings": len(ai_log.get("tunings", [])),
    })

@app.route("/api/ai/recommend", methods=["POST"])
def api_ai_recommend():
    """Store an AI recommendation for display in the dashboard.

    Body: {"source": "claude", "recommendation": "...", "priority": "HIGH|MEDIUM|LOW"}
    """
    data = request.get_json(force=True) or {}
    rec = {
        "timestamp": datetime.now().isoformat(),
        "source": data.get("source", "unknown"),
        "recommendation": data.get("recommendation", ""),
        "priority": data.get("priority", "MEDIUM"),
        "applied": False,
    }
    ai_log = _load_ai_log()
    ai_log.setdefault("recommendations", []).append(rec)
    ai_log["recommendations"] = ai_log["recommendations"][-200:]
    _save_ai_log(ai_log)

    ai_recommendations.append(rec)

    return jsonify({"status": "stored", "recommendation": rec})

@app.route("/api/ai/brief")
def api_ai_brief():
    """Compact text brief optimized for LLM context windows.

    Returns a plain-text summary of current state in ~500 tokens.
    """
    gk = _safe_json(GUNGNIR_DASHBOARD)
    gc = _safe_json(GUNGNIR_LADDER).get("current_champion", {})
    gs = gk.get("summary", {})
    ka = gk.get("adaptive", {})
    kz = gk.get("kaizen", {})

    brief = f"""9REALMS TRAINING STATUS — {datetime.now().strftime('%Y-%m-%d %H:%M')}

GUNGNIR Champion: AUC={gc.get('wf_auc','?')} Brier={gc.get('wf_brier','?')} T4P={gc.get('wf_t4p','?')} Features={gc.get('n_features','?')}
Rounds: {gs.get('total_rounds',0)} | Promotions: {gs.get('total_promotions',0)} ({gs.get('promotion_rate',0):.1%})
Current Streak: {gs.get('current_streak',0)} (longest: {gs.get('longest_streak',0)})
Kaizen Score: {kz.get('score',0)}/100 | Velocity: {kz.get('improvement_velocity',0):.1f} | Diversity: {kz.get('exploration_diversity',0):.0f}%
Adaptive: mutation={ka.get('mutation_rate','?')} temp={ka.get('temperature','?')} width={ka.get('search_width','?')}x
Best AUC Ever: {gs.get('best_auc_ever',0):.6f} | Unique Configs: {gs.get('unique_configs',0)} | Duplicates: {gs.get('duplicate_count',0)}
Avg Round Time: {gs.get('avg_round_time_s',0):.0f}s

Top Features: {', '.join(f[:2] for f in list((gc.get('feature_importance',{}) or {}).keys())[:8])}
Eng Features: {', '.join((gc.get('eng_features',[]) or [])[:6])}

ACTIONS AVAILABLE: POST /api/ai/tune with mutation_rate, temperature, search_width, optuna_trials, feature_gate, feature_block
"""
    return Response(brief, mimetype="text/plain")

# ═══════════════════════════════════════════════════════════════
# DASHBOARD HTML (embedded single-file)
# ═══════════════════════════════════════════════════════════════

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>9REALMS — Kaizen Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  --bg-primary: #0a0e17;
  --bg-card: #111827;
  --bg-card-hover: #1a2332;
  --border: #1e293b;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent-blue: #3b82f6;
  --accent-cyan: #06b6d4;
  --accent-purple: #8b5cf6;
  --accent-green: #10b981;
  --accent-amber: #f59e0b;
  --accent-red: #ef4444;
  --accent-rose: #f43f5e;
  --glow-blue: rgba(59, 130, 246, 0.15);
  --glow-green: rgba(16, 185, 129, 0.15);
  --glow-purple: rgba(139, 92, 246, 0.15);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── Header ── */
.header {
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
  border-bottom: 1px solid var(--border);
  padding: 20px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left { display: flex; align-items: center; gap: 16px; }
.logo {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}
.logo-sub { color: var(--text-muted); font-size: 12px; letter-spacing: 1px; }
.status-dot {
  width: 10px; height: 10px; border-radius: 50%;
  display: inline-block; margin-right: 6px;
}
.status-dot.live { background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); animation: pulse 2s infinite; }
.status-dot.off { background: var(--text-muted); }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
.header-right { display: flex; gap: 12px; align-items: center; }
.header-time { color: var(--text-muted); font-size: 11px; }

/* ── Controls ── */
.controls {
  display: flex;
  gap: 10px;
  padding: 16px 32px;
  background: rgba(17, 24, 39, 0.6);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
  align-items: center;
}
.btn {
  padding: 8px 18px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn:hover { background: var(--bg-card-hover); border-color: var(--accent-blue); }
.btn.start { border-color: var(--accent-green); }
.btn.start:hover { background: rgba(16, 185, 129, 0.15); }
.btn.stop { border-color: var(--accent-red); }
.btn.stop:hover { background: rgba(239, 68, 68, 0.15); }
.btn.active { background: rgba(16, 185, 129, 0.2); border-color: var(--accent-green); }
.ctrl-label { color: var(--text-muted); font-size: 11px; margin-right: 4px; }
.ctrl-sep { width: 1px; height: 24px; background: var(--border); margin: 0 6px; }

/* ── Grid Layout ── */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
  padding: 20px 32px;
}
.grid-full { grid-column: 1 / -1; }

/* ── Cards ── */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.3s;
}
.card:hover { border-color: #334155; }
.card-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--text-muted);
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-title .icon { font-size: 14px; }

/* ── Metric Cards ── */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  padding: 0 32px 4px;
}
.metric {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.metric::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  border-radius: 10px 10px 0 0;
}
.metric.blue::before { background: var(--accent-blue); }
.metric.cyan::before { background: var(--accent-cyan); }
.metric.purple::before { background: var(--accent-purple); }
.metric.green::before { background: var(--accent-green); }
.metric.amber::before { background: var(--accent-amber); }
.metric.rose::before { background: var(--accent-rose); }
.metric-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.metric-value {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.metric-sub { font-size: 10px; color: var(--text-secondary); margin-top: 4px; }
.metric.blue .metric-value { color: var(--accent-blue); }
.metric.cyan .metric-value { color: var(--accent-cyan); }
.metric.purple .metric-value { color: var(--accent-purple); }
.metric.green .metric-value { color: var(--accent-green); }
.metric.amber .metric-value { color: var(--accent-amber); }
.metric.rose .metric-value { color: var(--accent-rose); }

/* ── Spear Badges ── */
.spear-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.spear-badge.odin { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); border: 1px solid rgba(59, 130, 246, 0.3); }
.spear-badge.gungnir { background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); border: 1px solid rgba(139, 92, 246, 0.3); }

/* ── Chart containers ── */
.chart-container { position: relative; height: 260px; }
.chart-container.tall { height: 320px; }

/* ── Feature bars ── */
.feat-bar-row {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  font-size: 11px;
}
.feat-bar-label {
  width: 180px;
  text-align: right;
  padding-right: 10px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.feat-bar-track {
  flex: 1;
  height: 18px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}
.feat-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
  display: flex;
  align-items: center;
  padding-left: 6px;
  font-size: 10px;
  color: white;
  font-weight: 600;
}
.feat-bar-fill.odin { background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)); }
.feat-bar-fill.gungnir { background: linear-gradient(90deg, var(--accent-purple), var(--accent-rose)); }

/* ── Tier distribution ── */
.tier-grid { display: flex; gap: 8px; flex-wrap: wrap; }
.tier-box {
  flex: 1;
  min-width: 80px;
  text-align: center;
  padding: 12px 8px;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.tier-box .tier-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.tier-box .tier-count { font-size: 22px; font-weight: 700; margin: 4px 0; }
.tier-box .tier-pct { font-size: 10px; color: var(--text-secondary); }
.tier-box.t1 { background: rgba(100, 116, 139, 0.1); }
.tier-box.t1 .tier-count { color: var(--text-muted); }
.tier-box.t2 { background: rgba(6, 182, 212, 0.08); }
.tier-box.t2 .tier-count { color: var(--accent-cyan); }
.tier-box.t3 { background: rgba(59, 130, 246, 0.1); }
.tier-box.t3 .tier-count { color: var(--accent-blue); }
.tier-box.t4 { background: rgba(245, 158, 11, 0.1); }
.tier-box.t4 .tier-count { color: var(--accent-amber); }
.tier-box.t5 { background: rgba(239, 68, 68, 0.12); }
.tier-box.t5 .tier-count { color: var(--accent-red); }

/* ── Log viewer ── */
.log-viewer {
  background: #050810;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
  font-size: 11px;
  line-height: 1.7;
  color: var(--text-secondary);
}
.log-viewer::-webkit-scrollbar { width: 6px; }
.log-viewer::-webkit-scrollbar-track { background: transparent; }
.log-viewer::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.log-line { white-space: pre-wrap; word-break: break-all; }
.log-line.promote { color: var(--accent-green); }
.log-line.warning { color: var(--accent-amber); }
.log-line.error { color: var(--accent-red); }

/* ── Champion table ── */
.champ-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.champ-table th {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.champ-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(30, 41, 59, 0.4);
  color: var(--text-secondary);
}
.champ-table tr:hover td { background: rgba(30, 41, 59, 0.3); }
.val-good { color: var(--accent-green); font-weight: 600; }
.val-warn { color: var(--accent-amber); }

/* ── Kaizen gauge ── */
.gauge-wrap { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.gauge {
  width: 100px; height: 100px;
  border-radius: 50%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gauge-inner {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}
.gauge-val { font-size: 20px; font-weight: 700; }
.gauge-label { font-size: 8px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.kaizen-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.kaizen-stat { font-size: 11px; }
.kaizen-stat-label { color: var(--text-muted); font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; }
.kaizen-stat-val { font-weight: 600; margin-top: 2px; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .grid { padding: 12px 16px; gap: 12px; }
  .metrics-row { padding: 0 16px 4px; }
  .header { padding: 16px; }
  .controls { padding: 12px 16px; }
}
</style>
</head>
<body>

<!-- ═══════════════════ HEADER ═══════════════════ -->
<div class="header">
  <div class="header-left">
    <div>
      <div class="logo">9REALMS</div>
      <div class="logo-sub">KAIZEN LIVE DASHBOARD</div>
    </div>
  </div>
  <div class="header-right">
    <span class="spear-badge odin">🔱 ODIN</span>
    <span class="spear-badge gungnir">🔱 GUNGNIR</span>
    <span class="header-time" id="clock"></span>
  </div>
</div>

<!-- ═══════════════════ CONTROLS ═══════════════════ -->
<div class="controls">
  <span class="ctrl-label">DAEMONS:</span>
  <button class="btn start" onclick="startDaemon('dual')">▶ Dual Spear</button>
  <button class="btn start" onclick="startDaemon('gungnir')">▶ Gungnir Only</button>
  <button class="btn start" onclick="startDaemon('odin')">▶ ODIN Only</button>
  <span class="ctrl-sep"></span>
  <button class="btn stop" onclick="stopDaemon('dual')">■ Stop Dual</button>
  <button class="btn stop" onclick="stopDaemon('gungnir')">■ Stop Gungnir</button>
  <button class="btn stop" onclick="stopDaemon('odin')">■ Stop ODIN</button>
  <span class="ctrl-sep"></span>
  <span id="daemon-status" style="font-size:11px;color:var(--text-muted)">
    <span class="status-dot off" id="dot-dual"></span>Dual
    <span class="status-dot off" id="dot-gungnir" style="margin-left:10px"></span>Gungnir
    <span class="status-dot off" id="dot-odin" style="margin-left:10px"></span>ODIN
  </span>
</div>

<!-- ═══════════════════ METRICS ROW ═══════════════════ -->
<div style="padding-top:16px"></div>
<div class="metrics-row">
  <div class="metric blue">
    <div class="metric-label">ODIN AUC</div>
    <div class="metric-value" id="m-odin-auc">—</div>
    <div class="metric-sub" id="m-odin-sub">WF Best</div>
  </div>
  <div class="metric purple">
    <div class="metric-label">GUNGNIR AUC</div>
    <div class="metric-value" id="m-gun-auc">—</div>
    <div class="metric-sub" id="m-gun-sub">WF Best</div>
  </div>
  <div class="metric cyan">
    <div class="metric-label">ENSEMBLE AUC</div>
    <div class="metric-value" id="m-ens-auc">—</div>
    <div class="metric-sub">Dual-Spear</div>
  </div>
  <div class="metric green">
    <div class="metric-label">KAIZEN SCORE</div>
    <div class="metric-value" id="m-kaizen">—</div>
    <div class="metric-sub" id="m-kaizen-sub">Composite</div>
  </div>
  <div class="metric amber">
    <div class="metric-label">FEATURES</div>
    <div class="metric-value" id="m-features">—</div>
    <div class="metric-sub" id="m-feat-sub">Active</div>
  </div>
  <div class="metric rose">
    <div class="metric-label">MOONSHOTS</div>
    <div class="metric-value" id="m-moonshots">—</div>
    <div class="metric-sub">Tier 4+5</div>
  </div>
</div>

<!-- ═══════════════════ MAIN GRID ═══════════════════ -->
<div class="grid">

  <!-- AUC Progression -->
  <div class="card grid-full">
    <div class="card-title"><span class="icon">📈</span> AUC PROGRESSION — ODIN × GUNGNIR</div>
    <div class="chart-container tall"><canvas id="chart-auc"></canvas></div>
  </div>

  <!-- Brier Score -->
  <div class="card">
    <div class="card-title"><span class="icon">🎯</span> BRIER SCORE (CALIBRATION)</div>
    <div class="chart-container"><canvas id="chart-brier"></canvas></div>
  </div>

  <!-- Kaizen Adaptive -->
  <div class="card">
    <div class="card-title"><span class="icon">改</span> KAIZEN ADAPTIVE STATE</div>
    <div class="gauge-wrap" id="kaizen-panel">
      <div class="gauge" id="gauge-main">
        <div class="gauge-inner">
          <div class="gauge-val" id="gauge-val">—</div>
          <div class="gauge-label">Score</div>
        </div>
      </div>
      <div class="kaizen-stats" id="kaizen-stats"></div>
    </div>
  </div>

  <!-- Gungnir Feature Importance -->
  <div class="card">
    <div class="card-title"><span class="icon">🔱</span> GUNGNIR TOP FEATURES</div>
    <div id="gun-features"></div>
  </div>

  <!-- ODIN Feature Importance -->
  <div class="card">
    <div class="card-title"><span class="icon">🔱</span> ODIN TOP FEATURES</div>
    <div id="odin-features"></div>
  </div>

  <!-- Surge Tier Distribution -->
  <div class="card">
    <div class="card-title"><span class="icon">🚀</span> MOONSHOT SURGE TIERS</div>
    <div class="tier-grid" id="tier-grid">
      <div class="tier-box t1"><div class="tier-label">Tier 1</div><div class="tier-count">—</div><div class="tier-pct">&lt;20%</div></div>
      <div class="tier-box t2"><div class="tier-label">Tier 2</div><div class="tier-count">—</div><div class="tier-pct">20-50%</div></div>
      <div class="tier-box t3"><div class="tier-label">Tier 3</div><div class="tier-count">—</div><div class="tier-pct">50-100%</div></div>
      <div class="tier-box t4"><div class="tier-label">Tier 4</div><div class="tier-count">—</div><div class="tier-pct">100-200%</div></div>
      <div class="tier-box t5"><div class="tier-label">Tier 5</div><div class="tier-count">—</div><div class="tier-pct">200%+</div></div>
    </div>
    <div style="margin-top:12px"><div class="chart-container" style="height:180px"><canvas id="chart-tiers"></canvas></div></div>
  </div>

  <!-- Champion Table -->
  <div class="card grid-full">
    <div class="card-title"><span class="icon">🏆</span> CHAMPION LADDER</div>
    <div style="overflow-x:auto">
      <table class="champ-table" id="champ-table">
        <thead>
          <tr>
            <th>Spear</th><th>Round</th><th>WF AUC</th><th>Brier</th>
            <th>T4 Precision</th><th>Features</th><th>Timestamp</th>
          </tr>
        </thead>
        <tbody id="champ-body"></tbody>
      </table>
    </div>
  </div>

  <!-- AI Copilot Panel -->
  <div class="card grid-full" style="border-color: rgba(139,92,246,0.3); background: linear-gradient(135deg, #111827 0%, #1a1033 100%);">
    <div class="card-title"><span class="icon">🤖</span> AI COPILOT — INTELLIGENT TUNING</div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 16px;">
      <!-- Suggestions -->
      <div>
        <div style="font-size:11px;color:var(--accent-purple);margin-bottom:8px;font-weight:600;letter-spacing:0.5px;">DIAGNOSTICS & SUGGESTIONS</div>
        <div id="ai-suggestions" style="font-size:11px;color:var(--text-secondary);max-height:240px;overflow-y:auto;"></div>
      </div>
      <!-- Manual Tune Controls -->
      <div>
        <div style="font-size:11px;color:var(--accent-cyan);margin-bottom:8px;font-weight:600;letter-spacing:0.5px;">PARAMETER CONTROLS</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
          <div>
            <label style="font-size:9px;color:var(--text-muted);text-transform:uppercase;">Mutation Rate</label>
            <input type="range" id="tune-mutation" min="10" max="65" value="30" style="width:100%;">
            <span id="tune-mutation-val" style="font-size:10px;color:var(--text-secondary);">0.30</span>
          </div>
          <div>
            <label style="font-size:9px;color:var(--text-muted);text-transform:uppercase;">Temperature</label>
            <input type="range" id="tune-temp" min="50" max="250" value="100" style="width:100%;">
            <span id="tune-temp-val" style="font-size:10px;color:var(--text-secondary);">1.00</span>
          </div>
          <div>
            <label style="font-size:9px;color:var(--text-muted);text-transform:uppercase;">Search Width</label>
            <input type="range" id="tune-width" min="50" max="350" value="100" style="width:100%;">
            <span id="tune-width-val" style="font-size:10px;color:var(--text-secondary);">1.0x</span>
          </div>
          <div>
            <label style="font-size:9px;color:var(--text-muted);text-transform:uppercase;">Optuna Trials</label>
            <input type="range" id="tune-optuna" min="20" max="200" value="40" step="10" style="width:100%;">
            <span id="tune-optuna-val" style="font-size:10px;color:var(--text-secondary);">40</span>
          </div>
        </div>
        <div style="margin-top:10px;display:flex;gap:8px;">
          <button class="btn" onclick="applyTune('manual')" style="border-color:var(--accent-purple);">⚡ Apply Tuning</button>
          <button class="btn" onclick="fetchDiagnosis()" style="border-color:var(--accent-cyan);">🔍 Run Diagnosis</button>
          <button class="btn" onclick="autoTune()" style="border-color:var(--accent-green);">🤖 Auto-Tune</button>
        </div>
        <!-- Tuning History -->
        <div style="margin-top:12px;">
          <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;margin-bottom:4px;">RECENT AI TUNINGS</div>
          <div id="ai-history" style="font-size:10px;color:var(--text-muted);max-height:120px;overflow-y:auto;"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Live Log -->
  <div class="card grid-full">
    <div class="card-title"><span class="icon">📋</span> LIVE LOG STREAM</div>
    <div class="log-viewer" id="log-viewer"></div>
  </div>

</div>

<script>
// ═══════════════════════════════════════════
// CHART.JS SETUP
// ═══════════════════════════════════════════
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#1e293b';
Chart.defaults.font.family = "'SF Mono', 'Fira Code', monospace";
Chart.defaults.font.size = 10;

const chartOpts = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 600 },
  plugins: { legend: { labels: { usePointStyle: true, pointStyle: 'circle', padding: 16 } } },
  scales: {
    x: { grid: { color: 'rgba(30,41,59,0.4)' }, ticks: { maxRotation: 0 } },
    y: { grid: { color: 'rgba(30,41,59,0.4)' } }
  }
};

// AUC Chart
const aucChart = new Chart(document.getElementById('chart-auc'), {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'ODIN AUC', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.3, pointRadius: 4, pointBackgroundColor: '#3b82f6' },
      { label: 'GUNGNIR AUC', data: [], borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.1)', fill: true, tension: 0.3, pointRadius: 4, pointBackgroundColor: '#8b5cf6' },
    ]
  },
  options: { ...chartOpts, scales: { ...chartOpts.scales, y: { ...chartOpts.scales.y, min: 0.85, max: 1.005 } } }
});

// Brier Chart
const brierChart = new Chart(document.getElementById('chart-brier'), {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'Gungnir Brier', data: [], borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.1)', fill: true, tension: 0.3, pointRadius: 3 },
    ]
  },
  options: chartOpts
});

// Tier chart
const tierChart = new Chart(document.getElementById('chart-tiers'), {
  type: 'bar',
  data: {
    labels: ['Tier 1', 'Tier 2', 'Tier 3', 'Tier 4', 'Tier 5'],
    datasets: [{
      label: 'Events',
      data: [0,0,0,0,0],
      backgroundColor: ['#475569', '#06b6d4', '#3b82f6', '#f59e0b', '#ef4444'],
      borderRadius: 6,
      barThickness: 40,
    }]
  },
  options: {
    ...chartOpts,
    plugins: { legend: { display: false } },
    scales: { ...chartOpts.scales, y: { ...chartOpts.scales.y, beginAtZero: true } }
  }
});

// ═══════════════════════════════════════════
// DATA POLLING
// ═══════════════════════════════════════════
let lastData = null;

async function poll() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    lastData = d;
    updateDashboard(d);
  } catch(e) { console.warn('Poll error:', e); }
}

function updateDashboard(d) {
  // Clock
  document.getElementById('clock').textContent = new Date().toLocaleTimeString();

  // Daemon dots
  const dr = d.daemons_running || {};
  for (const name of ['dual','gungnir','odin']) {
    const dot = document.getElementById('dot-' + name);
    dot.className = dr[name] ? 'status-dot live' : 'status-dot off';
  }

  // Metric cards
  const dual = d.dual || {};
  const summary = dual.summary || {};
  const gc = d.gungnir_champion || {};
  const oc = d.odin_champion || {};
  const gk = d.gungnir_kaizen || {};
  const gkk = gk.kaizen || {};

  setMetric('m-odin-auc', oc.wf_auc, 4);
  setMetric('m-gun-auc', gc.wf_auc, 4);
  setMetric('m-ens-auc', summary.dual_ensemble_auc, 4);
  setMetric('m-kaizen', gkk.score, 1);
  setMetric('m-features', gc.n_features, 0);

  document.getElementById('m-odin-sub').textContent = 'Brier: ' + fmt(oc.wf_brier, 4);
  document.getElementById('m-gun-sub').textContent = 'Brier: ' + fmt(gc.wf_brier, 4);

  // Surge tier from feature importance (estimate from moonshot data)
  const fi = gc.feature_importance || {};
  const moonComp = fi.moonshot_composite || 0;
  document.getElementById('m-moonshots').textContent = moonComp > 0 ? '✓ Active' : '—';

  // AUC Chart
  const odinSeries = dual.odin_series || [];
  const gunSeries = dual.gungnir_series || [];
  const gkSeries = (gk.auc_series || []);

  // Merge and plot
  if (gkSeries.length > 0 || odinSeries.length > 0) {
    const allRounds = [];
    const odinData = {};
    const gunData = {};

    odinSeries.forEach((s,i) => {
      const lbl = 'D-R' + s.round;
      allRounds.push(lbl);
      odinData[lbl] = s.wf_auc;
    });
    gkSeries.forEach((s,i) => {
      const lbl = 'G-S' + (i+1);
      if (!allRounds.includes(lbl)) allRounds.push(lbl);
      gunData[lbl] = s.wf_auc;
    });

    // Build combined labels
    const combined = [];
    const odinVals = [];
    const gunVals = [];
    let idx = 0;
    odinSeries.forEach((s) => {
      combined.push('R' + (++idx));
      odinVals.push(s.wf_auc);
      gunVals.push(null);
    });
    gkSeries.forEach((s) => {
      combined.push('R' + (++idx));
      odinVals.push(null);
      gunVals.push(s.wf_auc);
    });

    aucChart.data.labels = combined;
    aucChart.data.datasets[0].data = odinVals;
    aucChart.data.datasets[1].data = gunVals;
    aucChart.update('none');
  }

  // Brier chart
  const brierSeries = gk.brier_series || [];
  if (brierSeries.length > 0) {
    brierChart.data.labels = brierSeries.map((s,i) => 'R'+(i+1));
    brierChart.data.datasets[0].data = brierSeries.map(s => s.wf_brier);
    brierChart.update('none');
  }

  // Kaizen gauge
  const kScore = gkk.score || 0;
  const hue = kScore > 80 ? 160 : kScore > 50 ? 45 : 0; // green / amber / red
  const gaugeEl = document.getElementById('gauge-main');
  gaugeEl.style.background = `conic-gradient(hsl(${hue},70%,50%) ${kScore*3.6}deg, #1e293b ${kScore*3.6}deg)`;
  document.getElementById('gauge-val').textContent = fmt(kScore, 1);
  document.getElementById('gauge-val').style.color = `hsl(${hue},70%,60%)`;

  const adaptive = gk.adaptive || {};
  const kStats = document.getElementById('kaizen-stats');
  kStats.innerHTML = `
    <div class="kaizen-stat"><div class="kaizen-stat-label">Velocity</div><div class="kaizen-stat-val">${fmt(gkk.improvement_velocity,1)}</div></div>
    <div class="kaizen-stat"><div class="kaizen-stat-label">Diversity</div><div class="kaizen-stat-val">${fmt(gkk.exploration_diversity,0)}</div></div>
    <div class="kaizen-stat"><div class="kaizen-stat-label">Efficiency</div><div class="kaizen-stat-val">${fmt(gkk.efficiency_ratio,1)}</div></div>
    <div class="kaizen-stat"><div class="kaizen-stat-label">Mutation Rate</div><div class="kaizen-stat-val">${fmt(adaptive.mutation_rate,3)}</div></div>
    <div class="kaizen-stat"><div class="kaizen-stat-label">Temperature</div><div class="kaizen-stat-val">${fmt(adaptive.temperature,2)}</div></div>
    <div class="kaizen-stat"><div class="kaizen-stat-label">Search Width</div><div class="kaizen-stat-val">${fmt(adaptive.search_width,1)}x</div></div>
  `;

  // Feature bars
  renderFeatureBars('gun-features', gc.feature_importance || {}, 'gungnir');
  renderFeatureBars('odin-features', oc.feature_importance || {}, 'odin');

  // Surge tiers (parse from kaizen state)
  const gs = d.gungnir_state || {};
  const fh = gs.feature_hits || {};
  // We'll display placeholder tier data from feature counts
  // Real tier data comes from the daemon log — extract if available

  // Champion table
  renderChampions(gc, oc);
}

function setMetric(id, val, dec) {
  document.getElementById(id).textContent = val != null ? fmt(val, dec) : '—';
}

function fmt(v, dec) {
  if (v == null || v === undefined) return '—';
  return Number(v).toFixed(dec);
}

function renderFeatureBars(containerId, importance, spear) {
  const el = document.getElementById(containerId);
  const sorted = Object.entries(importance).sort((a,b) => b[1]-a[1]).slice(0, 12);
  if (sorted.length === 0) { el.innerHTML = '<span style="color:var(--text-muted);font-size:11px">No data yet</span>'; return; }
  const maxVal = sorted[0][1];

  el.innerHTML = sorted.map(([name, val]) => `
    <div class="feat-bar-row">
      <div class="feat-bar-label">${name}</div>
      <div class="feat-bar-track">
        <div class="feat-bar-fill ${spear}" style="width:${Math.max(3, (val/maxVal)*100)}%">
          ${val}
        </div>
      </div>
    </div>
  `).join('');
}

function renderChampions(gc, oc) {
  const rows = [];
  if (gc.wf_auc) {
    rows.push({
      spear: '<span class="spear-badge gungnir">GUNGNIR</span>',
      round: gc.round || '—',
      auc: gc.wf_auc,
      brier: gc.wf_brier,
      t4p: gc.wf_t4p,
      feat: gc.n_features,
      ts: gc.timestamp || '—'
    });
  }
  if (oc.wf_auc) {
    rows.push({
      spear: '<span class="spear-badge odin">ODIN</span>',
      round: oc.round || '—',
      auc: oc.wf_auc,
      brier: oc.wf_brier,
      t4p: oc.wf_t4p,
      feat: oc.n_features,
      ts: oc.timestamp || '—'
    });
  }

  const body = document.getElementById('champ-body');
  body.innerHTML = rows.map(r => `
    <tr>
      <td>${r.spear}</td>
      <td>${r.round}</td>
      <td class="${r.auc > 0.95 ? 'val-good' : 'val-warn'}">${fmt(r.auc, 6)}</td>
      <td>${fmt(r.brier, 4)}</td>
      <td>${fmt(r.t4p, 4)}</td>
      <td>${r.feat}</td>
      <td style="font-size:10px;color:var(--text-muted)">${r.ts ? new Date(r.ts).toLocaleString() : '—'}</td>
    </tr>
  `).join('');
}

// ═══════════════════════════════════════════
// LOG STREAMING
// ═══════════════════════════════════════════
async function pollLogs() {
  try {
    const r = await fetch('/api/live_log');
    const d = await r.json();
    const viewer = document.getElementById('log-viewer');
    if (d.lines && d.lines.length > 0) {
      viewer.innerHTML = d.lines.map(l => {
        let cls = 'log-line';
        if (l.includes('PROMOTED') || l.includes('Champion')) cls += ' promote';
        else if (l.includes('WARNING') || l.includes('plateau')) cls += ' warning';
        else if (l.includes('ERROR') || l.includes('FAIL')) cls += ' error';
        return `<div class="${cls}">${escHtml(l)}</div>`;
      }).join('');
      viewer.scrollTop = viewer.scrollHeight;
    }
    // Also try file-based logs
    if (d.lines.length === 0) {
      const r2 = await fetch('/api/logs');
      const d2 = await r2.json();
      if (d2.lines && d2.lines.length > 0) {
        viewer.innerHTML = d2.lines.map(l => {
          let cls = 'log-line';
          if (l.includes('PROMOTED') || l.includes('Champion')) cls += ' promote';
          else if (l.includes('WARNING') || l.includes('plateau')) cls += ' warning';
          else if (l.includes('ERROR') || l.includes('FAIL')) cls += ' error';
          return `<div class="${cls}">${escHtml(l)}</div>`;
        }).join('');
        viewer.scrollTop = viewer.scrollHeight;
      }
    }
  } catch(e) {}
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ═══════════════════════════════════════════
// DAEMON CONTROLS
// ═══════════════════════════════════════════
async function startDaemon(name) {
  try {
    const r = await fetch('/api/start/' + name);
    const d = await r.json();
    console.log('Start:', d);
  } catch(e) { console.error('Start failed:', e); }
}

async function stopDaemon(name) {
  try {
    const r = await fetch('/api/stop/' + name);
    const d = await r.json();
    console.log('Stop:', d);
  } catch(e) { console.error('Stop failed:', e); }
}

// ═══════════════════════════════════════════
// AI COPILOT
// ═══════════════════════════════════════════

// Slider value display
['mutation','temp','width','optuna'].forEach(name => {
  const slider = document.getElementById('tune-' + name);
  const display = document.getElementById('tune-' + name + '-val');
  slider.addEventListener('input', () => {
    if (name === 'mutation') display.textContent = (slider.value / 100).toFixed(2);
    else if (name === 'temp') display.textContent = (slider.value / 100).toFixed(2);
    else if (name === 'width') display.textContent = (slider.value / 100).toFixed(1) + 'x';
    else display.textContent = slider.value;
  });
});

async function fetchDiagnosis() {
  try {
    const r = await fetch('/api/ai/diagnose');
    const d = await r.json();
    renderSuggestions(d);
    // Update sliders from current state
    const ada = d.gungnir?.adaptive || {};
    if (ada.mutation_rate) {
      document.getElementById('tune-mutation').value = Math.round(ada.mutation_rate * 100);
      document.getElementById('tune-mutation-val').textContent = ada.mutation_rate.toFixed(2);
    }
    if (ada.temperature) {
      document.getElementById('tune-temp').value = Math.round(ada.temperature * 100);
      document.getElementById('tune-temp-val').textContent = ada.temperature.toFixed(2);
    }
    if (ada.search_width) {
      document.getElementById('tune-width').value = Math.round(ada.search_width * 100);
      document.getElementById('tune-width-val').textContent = ada.search_width.toFixed(1) + 'x';
    }
  } catch(e) { console.error('Diagnosis failed:', e); }
}

function renderSuggestions(diag) {
  const el = document.getElementById('ai-suggestions');
  const sugs = diag.suggestions || [];
  const g = diag.gungnir || {};
  const trend = g.trend || {};

  let html = `<div style="margin-bottom:8px;padding:8px;border-radius:6px;background:rgba(30,41,59,0.5);">`;
  html += `<div style="color:var(--text-primary);font-weight:600;">Gungnir: AUC ${fmt(g.champion_auc,4)} | Streak ${g.current_streak} | Trend: `;
  if (trend.direction === 'improving') html += `<span style="color:var(--accent-green);">↑ Improving</span>`;
  else if (trend.direction === 'degrading') html += `<span style="color:var(--accent-red);">↓ Degrading</span>`;
  else if (trend.direction === 'plateau') html += `<span style="color:var(--accent-amber);">→ Plateau</span>`;
  else html += `<span style="color:var(--text-muted);">—</span>`;
  html += `</div></div>`;

  // Feature analysis
  const feats = diag.feature_analysis || {};
  if (feats.top_performing && feats.top_performing.length > 0) {
    html += `<div style="margin-bottom:6px;color:var(--accent-green);font-size:10px;">⬆ Top features: ${feats.top_performing.slice(0,5).map(f => f.name + '(' + (f.win_rate*100).toFixed(0) + '%)').join(', ')}</div>`;
  }
  if (feats.underperforming && feats.underperforming.length > 0) {
    html += `<div style="margin-bottom:8px;color:var(--accent-amber);font-size:10px;">⬇ Weak: ${feats.underperforming.slice(0,3).map(f => f.name).join(', ')}</div>`;
  }

  sugs.forEach(s => {
    const color = s.priority === 'HIGH' ? 'var(--accent-red)' : s.priority === 'MEDIUM' ? 'var(--accent-amber)' : 'var(--accent-cyan)';
    html += `<div style="margin-bottom:6px;padding:6px 8px;border-left:3px solid ${color};background:rgba(30,41,59,0.4);border-radius:0 4px 4px 0;">`;
    html += `<span style="color:${color};font-weight:600;font-size:9px;">[${s.priority}]</span> `;
    html += `<span>${s.message}</span>`;
    if (s.params) {
      html += `<br><button class="btn" onclick='applyAISuggestion(${JSON.stringify(s.params)}, "${s.type}")' style="margin-top:4px;padding:3px 8px;font-size:9px;border-color:${color};">Apply Suggestion</button>`;
    }
    html += `</div>`;
  });

  el.innerHTML = html;
}

async function applyTune(source) {
  const params = {
    mutation_rate: document.getElementById('tune-mutation').value / 100,
    temperature: document.getElementById('tune-temp').value / 100,
    search_width: document.getElementById('tune-width').value / 100,
    optuna_trials: parseInt(document.getElementById('tune-optuna').value),
  };
  try {
    const r = await fetch('/api/ai/tune', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({source, reason: 'Manual dashboard tuning', params})
    });
    const d = await r.json();
    console.log('Tune result:', d);
    fetchAIHistory();
    fetchDiagnosis();
  } catch(e) { console.error('Tune failed:', e); }
}

async function applyAISuggestion(params, type) {
  try {
    const r = await fetch('/api/ai/tune', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({source: 'dashboard_ai', reason: 'AI suggestion: ' + type, params})
    });
    const d = await r.json();
    console.log('AI suggestion applied:', d);
    fetchAIHistory();
    fetchDiagnosis();
  } catch(e) { console.error('Apply suggestion failed:', e); }
}

async function autoTune() {
  // Fetch diagnosis, then auto-apply the highest priority suggestion
  try {
    const r = await fetch('/api/ai/diagnose');
    const d = await r.json();
    const sugs = (d.suggestions || []).filter(s => s.params);
    if (sugs.length > 0) {
      const best = sugs[0]; // highest priority
      await fetch('/api/ai/tune', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({source: 'auto_tune', reason: best.message, params: best.params})
      });
      fetchAIHistory();
      fetchDiagnosis();
    }
  } catch(e) { console.error('Auto-tune failed:', e); }
}

async function fetchAIHistory() {
  try {
    const r = await fetch('/api/ai/history');
    const d = await r.json();
    const el = document.getElementById('ai-history');
    const tunings = (d.tunings || []).slice(-10).reverse();
    el.innerHTML = tunings.map(t => {
      const time = new Date(t.timestamp).toLocaleTimeString();
      const params = Object.entries(t.params_applied || {}).map(([k,v]) => k.split('_').pop() + '=' + (typeof v === 'number' ? v.toFixed(2) : v)).join(', ');
      return `<div style="margin-bottom:3px;"><span style="color:var(--text-muted);">${time}</span> <span style="color:var(--accent-purple);">[${t.source}]</span> ${params}</div>`;
    }).join('');
  } catch(e) {}
}

// ═══════════════════════════════════════════
// BOOT
// ═══════════════════════════════════════════
poll();
setInterval(poll, 2000);
setInterval(pollLogs, 3000);
// AI Copilot auto-refresh
fetchDiagnosis();
fetchAIHistory();
setInterval(fetchDiagnosis, 10000); // diagnose every 10s
setInterval(fetchAIHistory, 15000);
setInterval(() => {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}, 1000);
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — KAIZEN LIVE DASHBOARD                                        ║
║                                                                          ║
║  Open in browser:  http://localhost:9876                                 ║
║                                                                          ║
║  Controls:                                                               ║
║    ▶ Start/Stop daemons from the UI                                     ║
║    📈 Live AUC, Brier, Feature charts (2s refresh)                      ║
║    📋 Real-time log streaming                                           ║
║    🏆 Champion ladder tracking                                          ║
║                                                                          ║
║  Press Ctrl+C to stop the dashboard server.                              ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=9876, debug=False, threaded=True)
