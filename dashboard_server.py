#!/usr/bin/env python3
"""
9REALMS — UNIFIED COMMAND CENTER
=================================
One-stop dashboard for ALL engines:
  🔱 ODIN      — FDA PDUFA approval predictor (LightGBM Kaizen)
  🔱 GUNGNIR   — Phase readout predictor (LightGBM Kaizen)
  ⚡ DUAL SPEAR — ODIN × GUNGNIR orchestrator
  🚀 GPU v25   — GUNGNIR GPU optimizer (CuPy / CUDA)
  🤖 AI Monitor — Autonomous training copilot
  🧠 AI Advisor — Embedded in ODIN daemon

Process Control:
  POST /api/start  {"process": "odin"|"gungnir"|"dual"|"gpu25"|"monitor"}
  POST /api/stop   {"process": "..."}
  GET  /api/status → per-process status + all dashboard data

Usage:
    python dashboard_server.py          # port 9090
    python dashboard_server.py 8080     # custom port
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
PORT  = int(sys.argv[1]) if len(sys.argv) > 1 else 9090
BASE  = Path(__file__).parent
PYTHON = sys.executable   # same interpreter running us

# ─────────────────────────────────────────────
# Paths
KAIZEN_ODIN    = BASE / "kaizen"
KAIZEN_GUNGNIR = BASE / "kaizen_gungnir"
KAIZEN_DUAL    = BASE / "kaizen_dual"
MODELS_DIR     = BASE / "models" / "lgb_champions"
ALERTS_DIR     = BASE / "alerts"

# Stop-file paths (daemon convention)
STOP_ODIN    = BASE / "STOP_LGB"
STOP_GUNGNIR = BASE / "STOP_GUNGNIR_LGB"
STOP_DUAL    = BASE / "STOP_DUAL"
STOP_GPU25   = BASE / "STOP_GUNGNIR_LGB"   # shares with gungnir

# ─────────────────────────────────────────────
# Process registry — one thread per engine
_procs: dict[str, subprocess.Popen | None] = {
    "odin":    None,
    "gungnir": None,
    "dual":    None,
    "gpu25":   None,
    "monitor": None,
}
_proc_lock = threading.Lock()

PROCESS_CMDS = {
    "odin":    [PYTHON, str(BASE / "mcp_core" / "lgb_perpetual_daemon.py")],
    "gungnir": [PYTHON, str(BASE / "mcp_core" / "gungnir_historical_evolve.py")],
    "dual":    [PYTHON, str(BASE / "mcp_core" / "dual_spear_kaizen.py")],
    "gpu25":   [PYTHON, str(BASE / "gungnir_perpetual_gpu_v25.py")],
    "monitor": [PYTHON, str(BASE / "ai_monitor.py"), "--watch"],
}

PROCESS_LABELS = {
    "odin":    "🔱 ODIN Daemon",
    "gungnir": "🔱 GUNGNIR Daemon",
    "dual":    "⚡ Dual Spear",
    "gpu25":   "🚀 GPU v25",
    "monitor": "🤖 AI Monitor",
}


def _is_alive(name: str) -> bool:
    p = _procs.get(name)
    return p is not None and p.poll() is None


def start_process(name: str) -> dict:
    with _proc_lock:
        if _is_alive(name):
            return {"ok": False, "msg": f"{name} already running"}
        cmd = PROCESS_CMDS.get(name)
        if not cmd:
            return {"ok": False, "msg": f"Unknown process: {name}"}
        # Remove stop-file if present
        stop_files = {
            "odin": STOP_ODIN, "gungnir": STOP_GUNGNIR,
            "dual": STOP_DUAL, "gpu25": STOP_GPU25,
        }
        sf = stop_files.get(name)
        if sf and sf.exists():
            sf.unlink()
        p = subprocess.Popen(
            cmd, cwd=str(BASE),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        _procs[name] = p
        return {"ok": True, "msg": f"{name} started (pid={p.pid})"}


def stop_process(name: str) -> dict:
    with _proc_lock:
        # Write stop-file for daemons that watch it
        stop_files = {
            "odin": STOP_ODIN, "gungnir": STOP_GUNGNIR,
            "dual": STOP_DUAL, "gpu25": STOP_GPU25,
        }
        sf = stop_files.get(name)
        if sf:
            sf.touch()
        p = _procs.get(name)
        if p and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
            _procs[name] = None
            return {"ok": True, "msg": f"{name} stopped"}
        return {"ok": False, "msg": f"{name} was not running"}


# ─────────────────────────────────────────────
# JSON helpers

def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_jsonl(path):
    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return entries


def tail_log(path, lines=40):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except Exception:
        return ""


# ─────────────────────────────────────────────
# Data aggregators

def _odin_data():
    dashboard = load_json(KAIZEN_ODIN / "kaizen_dashboard.json") or {}
    state      = load_json(KAIZEN_ODIN / "kaizen_state.json") or {}
    ladder     = load_json(MODELS_DIR  / "champion_ladder.json") or {}
    discovered = load_json(KAIZEN_ODIN / "discovered_features.json") or {}
    advisor    = load_jsonl(KAIZEN_ODIN / "ai_advisor_log.jsonl")

    fi = ladder.get("current_champion", {}).get("feature_importance", {})
    fi_sorted = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:20]

    pool      = discovered.get("features", {})
    pool_hits = sum(1 for f in pool.values() if f.get("hits", 0) > 0)

    hits        = state.get("feature_hits", {})
    appearances = state.get("feature_appearances", {})
    win_rates   = {}
    for feat in appearances:
        a = appearances[feat]
        h = hits.get(feat, 0)
        if a > 0:
            win_rates[feat] = {"hits": h, "appearances": a, "rate": round(h / a * 100, 1)}
    wr_sorted = sorted(win_rates.items(), key=lambda x: x[1]["rate"], reverse=True)[:25]

    champ = ladder.get("current_champion", {})
    return {
        "summary":          dashboard.get("summary", {}),
        "kaizen":           dashboard.get("kaizen", {}),
        "adaptive":         dashboard.get("adaptive", {}),
        "auc_series":       dashboard.get("auc_series", []),
        "brier_series":     dashboard.get("brier_series", []),
        "promotions":       dashboard.get("promotion_history", []),
        "plateaus":         dashboard.get("plateau_events", []),
        "feature_importance": fi_sorted,
        "feature_win_rates":  wr_sorted,
        "yearly_aucs":      champ.get("yearly_aucs", []),
        "recent_rounds":    dashboard.get("recent_rounds", []),
        "discovery_pool":   {
            "total": len(pool), "with_hits": pool_hits,
            "zero_hits": len(pool) - pool_hits, "max_capacity": 120,
        },
        "champion": {
            "auc":          champ.get("wf_auc", 0),
            "brier":        champ.get("wf_brier", 0),
            "n_features":   champ.get("n_features", 0),
            "eng_features": champ.get("eng_features", []),
            "round":        champ.get("round", 0),
            "ensemble_auc": champ.get("ensemble_auc_insample", 0),
        },
        "advisor_log": advisor[-20:],
    }


def _gungnir_data():
    dashboard = load_json(KAIZEN_GUNGNIR / "kaizen_dashboard.json") or {}
    state     = load_json(KAIZEN_GUNGNIR / "kaizen_state.json") or {}
    champ_lgb = load_json(BASE / "models" / "lgb_champions" / "gungnir_champion_ladder.json") or {}

    champ = champ_lgb.get("current_champion", {})
    return {
        "summary":      dashboard.get("summary", {}),
        "kaizen":       dashboard.get("kaizen", {}),
        "auc_series":   dashboard.get("auc_series", []),
        "brier_series": dashboard.get("brier_series", []),
        "promotions":   dashboard.get("promotion_history", []),
        "champion": {
            "auc":        champ.get("wf_auc", dashboard.get("summary", {}).get("best_auc_ever", 0)),
            "brier":      champ.get("wf_brier", 0),
            "round":      champ.get("round", dashboard.get("summary", {}).get("total_rounds", 0)),
            "n_features": champ.get("n_features", 0),
        },
    }


def _gpu25_data():
    best  = load_json(BASE / "gungnir_v25_best.json") or {}
    hof_raw = []
    try:
        with open(BASE / "gungnir_v25_hall_of_fame.json", encoding="utf-8") as f:
            hof_raw = json.load(f)
    except Exception:
        pass
    hof = hof_raw if isinstance(hof_raw, list) else []

    # Run history: last 200 lines from jsonl
    run_history = load_jsonl(BASE / "gungnir_v25_run_history.jsonl")[-200:]
    auc_series  = [{"x": e.get("generation", i), "y": e.get("auc", 0)} for i, e in enumerate(run_history)]

    return {
        "best": {
            "generation": best.get("generation", 0),
            "auc":        best.get("auc", 0),
            "brier":      best.get("brier", 0),
            "accuracy":   best.get("accuracy", 0),
            "fitness":    best.get("fitness", 0),
        },
        "hof_count": len(hof),
        "auc_series": auc_series[-300:],
    }


def _dual_data():
    dashboard = load_json(KAIZEN_DUAL / "dual_dashboard.json") or {}
    return {
        "summary":       dashboard.get("summary", {}),
        "odin_summary":  dashboard.get("odin", {}),
        "gungnir_summary": dashboard.get("gungnir", {}),
        "odin_series":   dashboard.get("odin_series", []),
        "gungnir_series": dashboard.get("gungnir_series", []),
    }


def build_api_data():
    return {
        "timestamp":   datetime.now().isoformat(),
        "process_status": {
            name: "running" if _is_alive(name) else "stopped"
            for name in _procs
        },
        "odin":    _odin_data(),
        "gungnir": _gungnir_data(),
        "gpu25":   _gpu25_data(),
        "dual":    _dual_data(),
        "logs": {
            "odin":    tail_log(ALERTS_DIR / "lgb_daemon_log.txt"),
            "gungnir": tail_log(ALERTS_DIR / "gungnir_lgb_daemon_log.txt"),
            "dual":    tail_log(ALERTS_DIR / "dual_spear_log.txt"),
        },
    }


# ─────────────────────────────────────────────
# The Big HTML

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>9REALMS ⚡ Command Center</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Inter:wght@300;400;500;600;700&display=swap');

*{margin:0;padding:0;box-sizing:border-box;}
:root{
  --bg:#0b0f19;--bg2:#111827;--card:#1a2332;--card2:#141e2d;
  --border:#2d3748;--text:#e2e8f0;--text2:#94a3b8;--muted:#64748b;
  --green:#10b981;--green-dim:rgba(16,185,129,.15);
  --blue:#3b82f6;--blue-dim:rgba(59,130,246,.15);
  --purple:#8b5cf6;--purple-dim:rgba(139,92,246,.15);
  --orange:#f59e0b;--orange-dim:rgba(245,158,11,.15);
  --red:#ef4444;--red-dim:rgba(239,68,68,.15);
  --cyan:#06b6d4;--gold:#eab308;--pink:#ec4899;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}

/* ── HEADER ── */
.header{
  background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#0f172a 100%);
  border-bottom:1px solid var(--border);
  padding:16px 28px;
  display:flex;justify-content:space-between;align-items:center;
}
.logo{font-size:24px;font-weight:700;font-family:'JetBrains Mono';}
.logo span{color:var(--purple);}
.subtitle{color:var(--muted);font-size:12px;font-family:'JetBrains Mono';}
.header-right{display:flex;align-items:center;gap:16px;}
.pulse{width:10px;height:10px;border-radius:50%;background:var(--green);position:relative;}
.pulse::before{content:'';position:absolute;inset:-4px;border-radius:50%;
  border:2px solid var(--green);animation:pulse-ring 2s ease-out infinite;}
@keyframes pulse-ring{0%{transform:scale(.8);opacity:1;}100%{transform:scale(2);opacity:0;}}
.status-text{font-family:'JetBrains Mono';font-size:12px;color:var(--green);}
.refresh-timer{font-family:'JetBrains Mono';font-size:11px;color:var(--muted);}

/* ── PROCESS CONTROL BAR ── */
.process-bar{
  background:var(--bg2);border-bottom:1px solid var(--border);
  padding:12px 28px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
}
.proc-block{
  display:flex;align-items:center;gap:8px;
  background:var(--card);border:1px solid var(--border);
  border-radius:8px;padding:8px 12px;min-width:180px;
  transition:border-color .2s;
}
.proc-block.running{border-color:var(--green);}
.proc-block.stopped{border-color:var(--red-dim);}
.proc-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.proc-dot.running{background:var(--green);box-shadow:0 0 6px var(--green);}
.proc-dot.stopped{background:var(--muted);}
.proc-name{font-size:12px;font-family:'JetBrains Mono';flex:1;}
.proc-btn{
  font-size:10px;font-family:'JetBrains Mono';font-weight:700;
  padding:3px 8px;border-radius:4px;border:none;cursor:pointer;
  letter-spacing:.5px;transition:all .15s;
}
.proc-btn.start{background:var(--green-dim);color:var(--green);border:1px solid var(--green);}
.proc-btn.start:hover{background:var(--green);color:#000;}
.proc-btn.stop{background:var(--red-dim);color:var(--red);border:1px solid var(--red);}
.proc-btn.stop:hover{background:var(--red);color:#fff;}
.proc-btn:disabled{opacity:.4;cursor:not-allowed;}

/* ── TABS ── */
.tabs{
  display:flex;gap:4px;padding:16px 28px 0;
  border-bottom:1px solid var(--border);background:var(--bg);
}
.tab{
  font-size:12px;font-family:'JetBrains Mono';
  padding:8px 16px;border-radius:8px 8px 0 0;cursor:pointer;
  border:1px solid transparent;border-bottom:none;color:var(--muted);
  transition:all .15s;user-select:none;
}
.tab:hover{color:var(--text2);}
.tab.active{
  background:var(--card);border-color:var(--border);color:var(--text);
  border-bottom:1px solid var(--card);margin-bottom:-1px;
}

/* ── LAYOUT ── */
.tab-panel{display:none;padding:20px 28px;}
.tab-panel.active{display:block;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:20px;}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;}
.grid-3{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px;margin-bottom:20px;}
.grid-wide{margin-bottom:20px;}

/* ── CARDS ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;transition:border-color .2s;}
.card:hover{border-color:var(--purple);}
.card-title{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin-bottom:6px;font-family:'JetBrains Mono';}
.card-value{font-size:28px;font-weight:700;font-family:'JetBrains Mono';line-height:1.1;}
.card-sub{font-size:11px;color:var(--text2);margin-top:3px;}
.section-title{
  font-size:12px;text-transform:uppercase;letter-spacing:2px;color:var(--purple);
  font-family:'JetBrains Mono';margin:20px 0 10px;
  display:flex;align-items:center;gap:8px;
}
.section-title::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--purple),transparent);}

/* ── CHARTS ── */
.chart-wrap{position:relative;width:100%;height:260px;}
.chart-wrap-tall{position:relative;width:100%;height:380px;}
.chart-wrap-sm{position:relative;width:100%;height:180px;}

/* ── FEATURES ── */
.feat-list{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px;}
.feat-tag{font-size:9px;font-family:'JetBrains Mono';padding:3px 7px;border-radius:5px;
  background:var(--purple-dim);color:var(--purple);border:1px solid rgba(139,92,246,.3);}

/* ── ADVISOR LOG ── */
.advisor-entry{padding:8px 10px;border-left:3px solid var(--cyan);
  background:rgba(6,182,212,.05);border-radius:0 6px 6px 0;margin-bottom:6px;font-size:11px;}
.advisor-entry .atime{color:var(--muted);font-size:9px;font-family:'JetBrains Mono';}
.advisor-entry .amsg{color:var(--text2);margin-top:3px;}

/* ── LOG TERMINAL ── */
.log-box{
  background:#080c14;border:1px solid var(--border);border-radius:8px;
  padding:12px;font-family:'JetBrains Mono';font-size:11px;color:#7dd3a8;
  height:260px;overflow-y:auto;white-space:pre-wrap;line-height:1.6;
}
.log-box::-webkit-scrollbar{width:4px;}
.log-box::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}

/* ── YEARLY BARS ── */
.yearly-bars{display:flex;align-items:flex-end;gap:8px;height:100px;justify-content:center;padding-top:8px;}
.yb{display:flex;flex-direction:column;align-items:center;gap:4px;}
.yb .ybar{width:32px;border-radius:4px 4px 0 0;transition:height .5s;}
.yb .ylabel{font-size:9px;font-family:'JetBrains Mono';color:var(--muted);}
.yb .yval{font-size:10px;font-family:'JetBrains Mono';color:var(--text);font-weight:600;}

/* ── POOL ── */
.pool-center{text-align:center;padding:10px 0;}
.pool-stats{text-align:center;margin-top:8px;}
.pool-stat{display:inline-block;margin:3px 6px;font-size:11px;font-family:'JetBrains Mono';}

/* ── TIER BADGE ── */
.tier{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;font-family:'JetBrains Mono';}
.tier-t1{background:rgba(234,179,8,.15);color:#eab308;border:1px solid #eab308;}
.tier-t2{background:rgba(148,163,184,.1);color:#94a3b8;border:1px solid #94a3b8;}
.tier-t3{background:rgba(180,83,9,.15);color:#b45309;border:1px solid #b45309;}
.tier-t4{background:rgba(30,58,138,.2);color:#6b7280;border:1px solid #374151;}

/* ── COMPARISON ── */
.compare-row{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border);}
.compare-label{font-size:11px;font-family:'JetBrains Mono';color:var(--muted);width:90px;flex-shrink:0;}
.compare-bar-wrap{flex:1;background:var(--bg);border-radius:4px;height:8px;}
.compare-bar{height:8px;border-radius:4px;transition:width .5s;}
.compare-val{font-size:11px;font-family:'JetBrains Mono';width:60px;text-align:right;}

/* ── NO DATA ── */
.no-data{color:var(--muted);font-style:italic;font-size:12px;text-align:center;padding:30px;}

@media(max-width:900px){
  .grid-2,.grid-3{grid-template-columns:1fr;}
  .header{flex-direction:column;gap:8px;}
  .process-bar{gap:6px;}
}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div>
    <div class="logo">9<span>REALMS</span> ⚡ Command Center</div>
    <div class="subtitle">ODIN × GUNGNIR × GPU × AI Monitor — All Engines</div>
  </div>
  <div class="header-right">
    <div class="pulse"></div>
    <div class="status-text" id="status">LOADING...</div>
    <div class="refresh-timer" id="timer">--</div>
  </div>
</div>

<!-- PROCESS CONTROL BAR -->
<div class="process-bar" id="procBar">
  <!-- populated by JS -->
</div>

<!-- TABS -->
<div class="tabs">
  <div class="tab active" onclick="switchTab('odin',this)">🔱 ODIN</div>
  <div class="tab" onclick="switchTab('gungnir',this)">🔱 GUNGNIR LGB</div>
  <div class="tab" onclick="switchTab('gpu25',this)">🚀 GPU v25</div>
  <div class="tab" onclick="switchTab('dual',this)">⚡ Dual Spear</div>
  <div class="tab" onclick="switchTab('logs',this)">📋 Logs</div>
</div>

<!-- ══ TAB: ODIN ══ -->
<div class="tab-panel active" id="panel-odin">
  <div class="grid" id="odin-kpis"></div>

  <div class="section-title">📈 AUC Progression</div>
  <div class="grid-wide card">
    <div class="chart-wrap"><canvas id="odinAucChart"></canvas></div>
  </div>

  <div class="grid-3">
    <div class="card">
      <div class="card-title">Champion Feature Importance (Top 20)</div>
      <div class="chart-wrap-tall"><canvas id="odinFiChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Yearly Fold AUCs</div>
      <div class="yearly-bars" id="odinYearly"></div>
      <div style="margin-top:16px;">
        <div class="card-title">Champion Features</div>
        <div class="feat-list" id="odinFeats"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Discovery Pool</div>
      <div class="pool-center"><canvas id="odinPool" width="140" height="140"></canvas></div>
      <div class="pool-stats" id="odinPoolStats"></div>
    </div>
  </div>

  <div class="section-title">🎯 Feature Win Rates & Brier Score</div>
  <div class="grid-2">
    <div class="card">
      <div class="card-title">Feature Win Rate (Hits / Appearances)</div>
      <div class="chart-wrap-tall"><canvas id="odinWrChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Brier Score (Lower = Better)</div>
      <div class="chart-wrap"><canvas id="odinBrierChart"></canvas></div>
    </div>
  </div>

  <div class="section-title">🤖 AI Advisor Log</div>
  <div class="grid-wide card" id="odinAdvisorCard">
    <div class="no-data" id="odinAdvisorEmpty">No advisor calls yet...</div>
    <div id="odinAdvisorLog"></div>
  </div>
</div>

<!-- ══ TAB: GUNGNIR LGB ══ -->
<div class="tab-panel" id="panel-gungnir">
  <div class="grid" id="gungnir-kpis"></div>

  <div class="section-title">📈 AUC Progression</div>
  <div class="grid-wide card">
    <div class="chart-wrap"><canvas id="gungnirAucChart"></canvas></div>
  </div>

  <div class="section-title">🎯 Brier Score</div>
  <div class="grid-wide card">
    <div class="chart-wrap"><canvas id="gungnirBrierChart"></canvas></div>
  </div>
</div>

<!-- ══ TAB: GPU v25 ══ -->
<div class="tab-panel" id="panel-gpu25">
  <div class="grid" id="gpu25-kpis"></div>

  <div class="section-title">📈 AUC — Generation History</div>
  <div class="grid-wide card">
    <div class="chart-wrap"><canvas id="gpu25AucChart"></canvas></div>
  </div>

  <div class="section-title">📊 Hall of Fame</div>
  <div class="grid-wide card" id="gpu25HofCard">
    <div class="no-data">Hall of Fame data loads here...</div>
  </div>
</div>

<!-- ══ TAB: DUAL SPEAR ══ -->
<div class="tab-panel" id="panel-dual">
  <div class="grid" id="dual-kpis"></div>

  <div class="section-title">📈 ODIN vs GUNGNIR — Head to Head</div>
  <div class="grid-wide card">
    <div class="chart-wrap"><canvas id="dualChart"></canvas></div>
  </div>

  <div class="section-title">⚖️ Engine Comparison</div>
  <div class="grid-wide card" id="dualCompare">
    <div class="no-data">Comparison loads here...</div>
  </div>
</div>

<!-- ══ TAB: LOGS ══ -->
<div class="tab-panel" id="panel-logs">
  <div class="grid-3" style="grid-template-columns:1fr 1fr 1fr;">
    <div class="card">
      <div class="card-title">🔱 ODIN Log (last 40 lines)</div>
      <div class="log-box" id="logOdin">loading...</div>
    </div>
    <div class="card">
      <div class="card-title">🔱 GUNGNIR Log (last 40 lines)</div>
      <div class="log-box" id="logGungnir">loading...</div>
    </div>
    <div class="card">
      <div class="card-title">⚡ Dual Spear Log (last 40 lines)</div>
      <div class="log-box" id="logDual">loading...</div>
    </div>
  </div>
</div>

<div style="text-align:center;padding:16px;color:var(--muted);font-size:10px;font-family:'JetBrains Mono';">
  9REALMS Command Center — 改善 Kaizen Perpetual Training
</div>

<script>
// ─── Charts registry ───────────────────────────────────────────
let charts = {};
let countdown = 30;
let timerInterval;
const COLORS = {
  odin:'#8b5cf6', gungnir:'#10b981', gpu25:'#f59e0b',
  brier:'#ef4444', promo:'#eab308'
};

// ─── Tab switching ────────────────────────────────────────────
function switchTab(name, el) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
}

// ─── Process control ──────────────────────────────────────────
const PROC_LABELS = {
  odin:'🔱 ODIN Daemon', gungnir:'🔱 GUNGNIR Daemon',
  dual:'⚡ Dual Spear', gpu25:'🚀 GPU v25', monitor:'🤖 AI Monitor'
};

function renderProcBar(status) {
  const bar = document.getElementById('procBar');
  bar.innerHTML = Object.entries(PROC_LABELS).map(([k, label]) => {
    const running = status[k] === 'running';
    return `<div class="proc-block ${running ? 'running' : 'stopped'}" id="pb-${k}">
      <div class="proc-dot ${running ? 'running' : 'stopped'}"></div>
      <div class="proc-name">${label}</div>
      ${running
        ? `<button class="proc-btn stop" onclick="procAction('stop','${k}')">■ STOP</button>`
        : `<button class="proc-btn start" onclick="procAction('start','${k}')">▶ START</button>`
      }
    </div>`;
  }).join('');
}

async function procAction(action, name) {
  const btns = document.querySelectorAll(`#pb-${name} .proc-btn`);
  btns.forEach(b => b.disabled = true);
  try {
    const r = await fetch('/api/' + action, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({process: name})
    });
    const d = await r.json();
    console.log(action, name, d.msg);
    setTimeout(refresh, 1500);
  } catch(e) {
    console.error(e);
    btns.forEach(b => b.disabled = false);
  }
}

// ─── KPI Cards ────────────────────────────────────────────────
function kpiCard(title, value, sub, color) {
  return `<div class="card">
    <div class="card-title">${title}</div>
    <div class="card-value" style="color:${color||'var(--text)'}">${value}</div>
    <div class="card-sub">${sub||''}</div>
  </div>`;
}

function renderOdinKpis(d) {
  const s = d.summary || {}, champ = d.champion || {}, k = d.kaizen || {};
  const auc = champ.auc ? champ.auc.toFixed(4) : '--';
  const brier = champ.brier ? champ.brier.toFixed(4) : '--';
  const streak = s.current_streak ?? '--';
  const rounds = s.total_rounds ?? '--';
  const promos = s.total_promotions ?? '--';
  const mr = k.mutation_rate ? (k.mutation_rate * 100).toFixed(1) + '%' : '--';
  document.getElementById('odin-kpis').innerHTML =
    kpiCard('Champion AUC',    auc,    `round ${champ.round||'--'}`,          'var(--purple)') +
    kpiCard('Brier Score',     brier,  'lower = better',                      'var(--cyan)') +
    kpiCard('Total Rounds',    rounds, `${promos} promotions`,                'var(--text)') +
    kpiCard('Plateau Streak',  streak, streak > 20 ? '⚠ plateau detected' : 'rounds w/o promo', streak > 20 ? 'var(--orange)' : 'var(--green)') +
    kpiCard('Features',        champ.n_features ?? '--', 'champion features', 'var(--blue)') +
    kpiCard('Mutation Rate',   mr,     'kaizen adaptive',                     'var(--text2)');
}

function renderGungnirKpis(d) {
  const s = d.summary || {}, champ = d.champion || {};
  const auc = champ.auc ? champ.auc.toFixed(5) : '--';
  document.getElementById('gungnir-kpis').innerHTML =
    kpiCard('Best AUC',       auc,              `round ${champ.round||'--'}`,     'var(--green)') +
    kpiCard('Brier Score',    champ.brier ? champ.brier.toFixed(4) : '--', 'lower = better', 'var(--cyan)') +
    kpiCard('Total Rounds',   s.total_rounds ?? '--', `${s.total_promotions??0} promotions`, 'var(--text)') +
    kpiCard('Streak',         s.current_streak ?? '--', 'rounds w/o promo', 'var(--text2)') +
    kpiCard('Features',       champ.n_features ?? '--', 'champion features', 'var(--blue)') +
    kpiCard('Avg Round (s)',  s.avg_round_time_s ? s.avg_round_time_s.toFixed(1) : '--', 'per round', 'var(--muted)');
}

function renderGpu25Kpis(d) {
  const b = d.best || {};
  document.getElementById('gpu25-kpis').innerHTML =
    kpiCard('Best AUC',      b.auc ? b.auc.toFixed(5) : '--',      `gen ${b.generation||'--'}`,        'var(--orange)') +
    kpiCard('Brier Score',   b.brier ? b.brier.toFixed(4) : '--',  'lower = better',                   'var(--cyan)') +
    kpiCard('Accuracy',      b.accuracy ? (b.accuracy*100).toFixed(2)+'%' : '--', 'validation',       'var(--green)') +
    kpiCard('Fitness',       b.fitness ? b.fitness.toFixed(4) : '--', 'multi-objective',               'var(--purple)') +
    kpiCard('Generation',    b.generation || '--',                  'current',                          'var(--text)') +
    kpiCard('Hall of Fame',  d.hof_count || '--',                   'elite configs',                    'var(--gold)');
}

function renderDualKpis(d) {
  const s = d.summary || {}, os = d.odin_summary || {}, gs = d.gungnir_summary || {};
  document.getElementById('dual-kpis').innerHTML =
    kpiCard('Dual Rounds',    s.dual_rounds ?? '--',   'total orchestrated',         'var(--purple)') +
    kpiCard('ODIN Rounds',    s.odin_rounds ?? '--',   'allocated to ODIN',          'var(--purple)') +
    kpiCard('GUNGNIR Rounds', s.gungnir_rounds ?? '--','allocated to GUNGNIR',       'var(--green)') +
    kpiCard('Allocation',     s.allocation_ratio ? (s.allocation_ratio*100).toFixed(1)+'%' : '--', 'ODIN share', 'var(--text2)') +
    kpiCard('ODIN AUC',       os.best_auc_ever ? os.best_auc_ever.toFixed(4) : '--', 'best ever', 'var(--purple)') +
    kpiCard('GUNGNIR AUC',    gs.best_auc_ever ? gs.best_auc_ever.toFixed(5) : '--', 'best ever', 'var(--green)');
}

// ─── Chart helpers ────────────────────────────────────────────
function mkChart(id, type, data, options) {
  const ctx = document.getElementById(id);
  if (!ctx) return null;
  if (charts[id]) { charts[id].destroy(); }
  charts[id] = new Chart(ctx, { type, data, options });
  return charts[id];
}

const BASE_OPTS = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
  scales: {
    x: { grid: { color: '#1e2a3a' }, ticks: { color: '#64748b', font: { family:'JetBrains Mono', size:10 } } },
    y: { grid: { color: '#1e2a3a' }, ticks: { color: '#64748b', font: { family:'JetBrains Mono', size:10 } } }
  }
};

function lineOpts(yLabel, yMin, color) {
  return JSON.parse(JSON.stringify({
    ...BASE_OPTS,
    plugins: {
      ...BASE_OPTS.plugins,
      legend: { display: true, labels: { color: '#94a3b8', font: { family:'JetBrains Mono', size:10 } } }
    },
    scales: {
      ...BASE_OPTS.scales,
      y: { ...BASE_OPTS.scales.y, min: yMin ?? undefined, title: { display:!!yLabel, text:yLabel||'', color:'#64748b' } }
    }
  }));
}

// ─── ODIN Charts ──────────────────────────────────────────────
function drawOdinAuc(d) {
  const series = d.auc_series || [];
  const promos = d.promotions || [];
  const promoSet = new Set(promos.map(p => p.round));
  const labels = series.map(p => p.x ?? p.round ?? '');
  const vals   = series.map(p => p.y ?? p.auc ?? 0);
  const pointR = labels.map(l => promoSet.has(l) ? 6 : 0);
  const pointC = labels.map(l => promoSet.has(l) ? COLORS.promo : COLORS.odin);

  const annotations = {};
  promos.forEach((p, i) => {
    annotations['p' + i] = {
      type: 'line', xMin: p.round, xMax: p.round,
      borderColor: 'rgba(234,179,8,.5)', borderWidth: 1, borderDash: [4,3],
      label: { display: true, content: '🏆', position: 'start', font: { size: 10 } }
    };
  });

  mkChart('odinAucChart', 'line', {
    labels,
    datasets: [{
      label: 'ODIN AUC', data: vals,
      borderColor: COLORS.odin, backgroundColor: 'rgba(139,92,246,.1)',
      borderWidth: 1.5, fill: true, pointRadius: pointR, pointBackgroundColor: pointC, tension: 0.2
    }]
  }, { ...lineOpts('AUC', null, COLORS.odin), plugins: { ...lineOpts().plugins, annotation: { annotations } } });
}

function drawOdinFi(d) {
  const fi = d.feature_importance || [];
  mkChart('odinFiChart', 'bar', {
    labels: fi.map(([n]) => n),
    datasets: [{ label:'Importance', data: fi.map(([,v]) => v),
      backgroundColor: 'rgba(139,92,246,.6)', borderColor: '#8b5cf6', borderWidth: 1 }]
  }, { ...BASE_OPTS, indexAxis: 'y', scales: { ...BASE_OPTS.scales, x: { ...BASE_OPTS.scales.x }, y: { ...BASE_OPTS.scales.y, ticks: { ...BASE_OPTS.scales.y.ticks, font: { family:'JetBrains Mono', size:9 } } } } });
}

function drawOdinWr(d) {
  const wr = d.feature_win_rates || [];
  mkChart('odinWrChart', 'bar', {
    labels: wr.map(([n]) => n),
    datasets: [
      { label: 'Win Rate %', data: wr.map(([,v]) => v.rate), backgroundColor: 'rgba(16,185,129,.6)', borderColor: '#10b981', borderWidth: 1, yAxisID: 'y' },
      { label: 'Appearances', data: wr.map(([,v]) => v.appearances), type: 'line', borderColor: '#f59e0b', backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y1' }
    ]
  }, { ...BASE_OPTS, indexAxis: 'y',
    plugins: { ...BASE_OPTS.plugins, legend: { display: true, labels: { color:'#94a3b8', font:{family:'JetBrains Mono',size:10} } } },
    scales: { ...BASE_OPTS.scales, y: { ...BASE_OPTS.scales.y, ticks:{...BASE_OPTS.scales.y.ticks,font:{family:'JetBrains Mono',size:9}} }, y1: { position:'right', grid:{display:false}, ticks:{color:'#f59e0b',font:{family:'JetBrains Mono',size:9}} } }
  });
}

function drawOdinBrier(d) {
  const series = d.brier_series || [];
  mkChart('odinBrierChart', 'line', {
    labels: series.map(p => p.x ?? p.round ?? ''),
    datasets: [{
      label: 'Brier Score', data: series.map(p => p.y ?? p.brier ?? 0),
      borderColor: COLORS.brier, backgroundColor: 'rgba(239,68,68,.1)',
      borderWidth: 1.5, fill: true, pointRadius: 0, tension: 0.2
    }]
  }, lineOpts('Brier'));
}

function drawOdinPool(d) {
  const pool = d.discovery_pool || {};
  const ctx = document.getElementById('odinPool');
  if (!ctx) return;
  const arc = (ctx2d, pct, color, inset) => {
    ctx2d.beginPath();
    ctx2d.arc(70,70,70-inset, -Math.PI/2, -Math.PI/2 + Math.PI*2*pct);
    ctx2d.strokeStyle = color; ctx2d.lineWidth = 14; ctx2d.stroke();
  };
  const ctx2 = ctx.getContext('2d');
  ctx2.clearRect(0,0,140,140);
  ctx2.beginPath(); ctx2.arc(70,70,56,0,Math.PI*2); ctx2.strokeStyle='#1e2a3a'; ctx2.lineWidth=14; ctx2.stroke();
  const filled = (pool.total || 0) / (pool.max_capacity || 120);
  const hits   = (pool.with_hits || 0) / (pool.max_capacity || 120);
  arc(ctx2, filled, '#3b82f6', 0);
  arc(ctx2, hits,   '#10b981', 0);
  ctx2.fillStyle='#e2e8f0'; ctx2.font='bold 20px JetBrains Mono'; ctx2.textAlign='center'; ctx2.textBaseline='middle';
  ctx2.fillText(pool.total || 0, 70, 65);
  ctx2.fillStyle='#64748b'; ctx2.font='9px JetBrains Mono';
  ctx2.fillText('FEATURES', 70, 82);
  document.getElementById('odinPoolStats').innerHTML =
    `<div class="pool-stat" style="color:var(--blue)">■ ${pool.total||0} in pool</div>` +
    `<div class="pool-stat" style="color:var(--green)">■ ${pool.with_hits||0} with hits</div>` +
    `<div class="pool-stat" style="color:var(--muted)">■ ${pool.zero_hits||0} unexplored</div>`;
}

function drawOdinYearly(d) {
  const yearly = d.yearly_aucs || [];
  if (!yearly.length) { document.getElementById('odinYearly').innerHTML = '<div class="no-data">No fold data</div>'; return; }
  const maxV = Math.max(...yearly.map(y => y.auc || y[1] || 0));
  const bars = yearly.map(y => {
    const yr  = y.year || y[0] || '';
    const auc = y.auc  || y[1] || 0;
    const h   = Math.max(10, Math.round((auc / maxV) * 80));
    const color = auc > 0.89 ? '#10b981' : auc > 0.85 ? '#f59e0b' : '#ef4444';
    return `<div class="yb">
      <div class="yval">${auc.toFixed(3)}</div>
      <div class="ybar" style="height:${h}px;background:${color};"></div>
      <div class="ylabel">${yr}</div>
    </div>`;
  }).join('');
  document.getElementById('odinYearly').innerHTML = bars;
}

function drawOdinAdvisor(d) {
  const log = d.advisor_log || [];
  const el = document.getElementById('odinAdvisorLog');
  const empty = document.getElementById('odinAdvisorEmpty');
  if (!log.length) { empty.style.display='block'; el.innerHTML=''; return; }
  empty.style.display='none';
  el.innerHTML = [...log].reverse().map(e => {
    const ts = e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '';
    const trigger = e.trigger || '';
    const msg = e.summary || e.response_summary || JSON.stringify(e).slice(0,120);
    return `<div class="advisor-entry">
      <div class="atime">${ts} · ${trigger}</div>
      <div class="amsg">${msg}</div>
    </div>`;
  }).join('');
}

function drawOdinFeats(d) {
  const feats = d.champion?.eng_features || [];
  document.getElementById('odinFeats').innerHTML = feats.map(f =>
    `<span class="feat-tag">${f}</span>`).join('') || '<span class="no-data">—</span>';
}

// ─── GUNGNIR Charts ────────────────────────────────────────────
function drawGungnirAuc(d) {
  const series = d.auc_series || [];
  const promos = d.promotions || [];
  const promoSet = new Set(promos.map(p => p.round));
  const labels = series.map(p => p.x ?? p.round ?? '');
  const vals   = series.map(p => p.y ?? p.auc ?? 0);
  mkChart('gungnirAucChart', 'line', {
    labels,
    datasets: [{
      label:'GUNGNIR AUC', data:vals,
      borderColor: COLORS.gungnir, backgroundColor:'rgba(16,185,129,.1)',
      borderWidth:1.5, fill:true, pointRadius: labels.map(l => promoSet.has(l)?5:0),
      pointBackgroundColor: labels.map(l => promoSet.has(l)?COLORS.promo:COLORS.gungnir), tension:0.2
    }]
  }, lineOpts('AUC'));
}

function drawGungnirBrier(d) {
  const series = d.brier_series || [];
  mkChart('gungnirBrierChart', 'line', {
    labels: series.map(p => p.x ?? p.round ?? ''),
    datasets: [{
      label:'GUNGNIR Brier', data: series.map(p => p.y ?? p.brier ?? 0),
      borderColor: COLORS.brier, backgroundColor:'rgba(239,68,68,.1)',
      borderWidth:1.5, fill:true, pointRadius:0, tension:0.2
    }]
  }, lineOpts('Brier'));
}

// ─── GPU v25 Charts ────────────────────────────────────────────
function drawGpu25Auc(d) {
  const series = d.auc_series || [];
  mkChart('gpu25AucChart', 'line', {
    labels: series.map(p => p.x ?? ''),
    datasets: [{
      label:'GPU v25 AUC', data: series.map(p => p.y ?? 0),
      borderColor: COLORS.gpu25, backgroundColor:'rgba(245,158,11,.1)',
      borderWidth:1.5, fill:true, pointRadius:0, tension:0.1
    }]
  }, lineOpts('AUC'));
}

// ─── Dual Spear Charts ────────────────────────────────────────
function drawDualChart(d) {
  const os = d.odin_series || [];
  const gs = d.gungnir_series || [];
  const maxLen = Math.max(os.length, gs.length);
  const labels = Array.from({length:maxLen}, (_,i) => i+1);
  mkChart('dualChart', 'line', {
    labels,
    datasets: [
      { label:'ODIN',    data: os.map(p => p.y ?? p.auc ?? 0), borderColor: COLORS.odin,    backgroundColor:'rgba(139,92,246,.08)', borderWidth:2, fill:true, pointRadius:0, tension:0.2 },
      { label:'GUNGNIR', data: gs.map(p => p.y ?? p.auc ?? 0), borderColor: COLORS.gungnir, backgroundColor:'rgba(16,185,129,.08)',  borderWidth:2, fill:true, pointRadius:0, tension:0.2 }
    ]
  }, { ...lineOpts('AUC'),
    plugins: { ...lineOpts().plugins, legend: { display:true, labels:{color:'#94a3b8',font:{family:'JetBrains Mono',size:11}} } }
  });
}

function drawDualCompare(d) {
  const os = d.odin_summary || {};
  const gs = d.gungnir_summary || {};
  const oAuc = os.best_auc_ever || 0;
  const gAuc = gs.best_auc_ever || 0;
  const maxAuc = Math.max(oAuc, gAuc, 0.001);

  const rows = [
    { label:'Best AUC', oVal: oAuc.toFixed(4), gVal: gAuc.toFixed(5), oPct: oAuc/maxAuc*100, gPct: gAuc/maxAuc*100 },
    { label:'Rounds',   oVal: os.total_rounds||0, gVal: gs.total_rounds||0,
      oPct: (os.total_rounds||0)/Math.max(os.total_rounds||1,gs.total_rounds||1)*100,
      gPct: (gs.total_rounds||0)/Math.max(os.total_rounds||1,gs.total_rounds||1)*100 },
    { label:'Promos',   oVal: os.total_promotions||0, gVal: gs.total_promotions||0,
      oPct: (os.total_promotions||0)/Math.max(os.total_promotions||1,gs.total_promotions||1)*100,
      gPct: (gs.total_promotions||0)/Math.max(os.total_promotions||1,gs.total_promotions||1)*100 }
  ];

  document.getElementById('dualCompare').innerHTML = `
    <div style="display:grid;grid-template-columns:90px 1fr 1fr;gap:8px;align-items:center;padding:4px 0;">
      <div></div>
      <div style="font-size:12px;font-family:'JetBrains Mono';color:var(--purple);text-align:center;">🔱 ODIN</div>
      <div style="font-size:12px;font-family:'JetBrains Mono';color:var(--green);text-align:center;">🔱 GUNGNIR</div>
    </div>
    ${rows.map(r => `
    <div style="display:grid;grid-template-columns:90px 1fr 1fr;gap:8px;align-items:center;padding:6px 0;border-top:1px solid var(--border);">
      <div style="font-size:11px;font-family:'JetBrains Mono';color:var(--muted);">${r.label}</div>
      <div>
        <div style="background:var(--bg);border-radius:3px;height:8px;margin-bottom:3px;">
          <div style="height:8px;border-radius:3px;background:var(--purple);width:${r.oPct.toFixed(1)}%;transition:width .5s;"></div>
        </div>
        <div style="font-size:11px;font-family:'JetBrains Mono';text-align:center;">${r.oVal}</div>
      </div>
      <div>
        <div style="background:var(--bg);border-radius:3px;height:8px;margin-bottom:3px;">
          <div style="height:8px;border-radius:3px;background:var(--green);width:${r.gPct.toFixed(1)}%;transition:width .5s;"></div>
        </div>
        <div style="font-size:11px;font-family:'JetBrains Mono';text-align:center;">${r.gVal}</div>
      </div>
    </div>`).join('')}`;
}

// ─── Logs ────────────────────────────────────────────────────
function renderLogs(logs) {
  ['odin','gungnir','dual'].forEach(key => {
    const el = document.getElementById('log' + key.charAt(0).toUpperCase() + key.slice(1));
    if (el) { el.textContent = logs[key] || '(no log yet)'; el.scrollTop = el.scrollHeight; }
  });
}

// ─── Main refresh ─────────────────────────────────────────────
async function refresh() {
  try {
    const r = await fetch('/api/data');
    const data = await r.json();
    const ts = new Date(data.timestamp).toLocaleTimeString();

    document.getElementById('status').textContent = 'LIVE · ' + ts;

    renderProcBar(data.process_status || {});

    // ODIN
    const odin = data.odin || {};
    renderOdinKpis(odin);
    drawOdinAuc(odin);
    drawOdinFi(odin);
    drawOdinWr(odin);
    drawOdinBrier(odin);
    drawOdinPool(odin);
    drawOdinYearly(odin);
    drawOdinAdvisor(odin);
    drawOdinFeats(odin);

    // GUNGNIR
    const gungnir = data.gungnir || {};
    renderGungnirKpis(gungnir);
    drawGungnirAuc(gungnir);
    drawGungnirBrier(gungnir);

    // GPU v25
    const gpu25 = data.gpu25 || {};
    renderGpu25Kpis(gpu25);
    drawGpu25Auc(gpu25);

    // Dual
    const dual = data.dual || {};
    renderDualKpis(dual);
    drawDualChart(dual);
    drawDualCompare(dual);

    // Logs
    renderLogs(data.logs || {});

    countdown = 30;
  } catch(e) {
    document.getElementById('status').textContent = 'ERROR — retrying...';
    console.error(e);
  }
}

// ─── Countdown timer ──────────────────────────────────────────
function startTimer() {
  timerInterval = setInterval(() => {
    countdown--;
    document.getElementById('timer').textContent = 'refresh in ' + countdown + 's';
    if (countdown <= 0) { refresh(); }
  }, 1000);
}

// ─── Boot ─────────────────────────────────────────────────────
refresh();
startTimer();
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
# HTTP Handler

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence request log spam

    def _json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type",  "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type",   "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._html(DASHBOARD_HTML)
        elif self.path == "/api/data":
            self._json(build_api_data())
        elif self.path == "/api/status":
            self._json({k: "running" if _is_alive(k) else "stopped" for k in _procs})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length) or b"{}") if length else {}
        proc   = body.get("process", "")

        if self.path == "/api/start":
            self._json(start_process(proc))
        elif self.path == "/api/stop":
            self._json(stop_process(proc))
        else:
            self.send_response(404)
            self.end_headers()


# ─────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(BASE)
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  9REALMS COMMAND CENTER                                  ║
║  http://localhost:{PORT:<5}                                ║
║                                                          ║
║  Engines:  ODIN · GUNGNIR · GPU v25 · Dual · Monitor    ║
║  Control:  Start/Stop each engine from the dashboard     ║
║  Refresh:  Every 30 seconds (auto)                       ║
║                                                          ║
║  Stop this server: Ctrl+C                                ║
╚══════════════════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Stop any running processes
        for name in list(_procs.keys()):
            if _is_alive(name):
                stop_process(name)
        server.server_close()
