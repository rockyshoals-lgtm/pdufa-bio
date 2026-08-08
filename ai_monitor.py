#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — AI MONITOR: Autonomous Training Copilot                      ║
║                                                                          ║
║  Watches the Kaizen dashboard API, analyzes training metrics, and       ║
║  makes intelligent tuning decisions. Can be run standalone or invoked   ║
║  by Claude/Perplexity through the dashboard.                            ║
║                                                                          ║
║  Modes:                                                                  ║
║    --watch     Continuous monitoring loop (default, every 30s)           ║
║    --once      Single diagnosis + auto-tune cycle                       ║
║    --report    Generate markdown training report                        ║
║                                                                          ║
║  Usage:  python ai_monitor.py [--watch|--once|--report]                 ║
║  Dash:   Must have kaizen_dashboard.py running on localhost:9876        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout on Windows (prevents cp1252 emoji crash)
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", closefd=False)

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "--break-system-packages", "-q"])
    import requests

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
DASHBOARD_URL = "http://localhost:9876"
REPORTS_DIR = Path(__file__).resolve().parent / "ai_reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Tuning thresholds
PLATEAU_MILD = 10       # rounds without promotion before mild intervention
PLATEAU_SEVERE = 25     # rounds before aggressive intervention
VELOCITY_LOW = 3.0      # below this = low improvement velocity
DIVERSITY_LOW = 40.0    # below this = not exploring enough
AUC_CEILING = 0.995     # near theoretical max
BRIER_TARGET = 0.03     # target brier score

# ═══════════════════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════════════════

def api_get(endpoint):
    """GET from dashboard API."""
    try:
        r = requests.get(f"{DASHBOARD_URL}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠ API error ({endpoint}): {e}")
        return None

def api_post(endpoint, data):
    """POST to dashboard API."""
    try:
        r = requests.post(f"{DASHBOARD_URL}{endpoint}", json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠ API error ({endpoint}): {e}")
        return None

def get_diagnosis():
    return api_get("/api/ai/diagnose")

def get_brief():
    try:
        r = requests.get(f"{DASHBOARD_URL}/api/ai/brief", timeout=10)
        return r.text
    except:
        return None

def apply_tune(source, reason, params):
    return api_post("/api/ai/tune", {
        "source": source,
        "reason": reason,
        "params": params,
    })

def post_recommendation(source, recommendation, priority="MEDIUM"):
    return api_post("/api/ai/recommend", {
        "source": source,
        "recommendation": recommendation,
        "priority": priority,
    })

# ═══════════════════════════════════════════════════════════════
# ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════

class TrainingAnalyzer:
    """Analyzes training state and generates tuning decisions."""

    def __init__(self):
        self.last_auc = None
        self.last_streak = 0
        self.interventions = 0
        self.cooldown_until = 0  # don't intervene too frequently

    def analyze_and_act(self, diag):
        """Main analysis loop — diagnose and optionally apply tuning."""
        if not diag:
            print("  ⚠ No diagnostic data available")
            return

        now = time.time()
        if now < self.cooldown_until:
            remaining = int(self.cooldown_until - now)
            print(f"  ⏳ Cooldown active ({remaining}s remaining)")
            return

        g = diag.get("gungnir", {})
        suggestions = diag.get("suggestions", [])
        feat_analysis = diag.get("feature_analysis", {})

        streak = g.get("current_streak", 0)
        auc = g.get("champion_auc", 0)
        brier = g.get("champion_brier", 1)
        velocity = g.get("velocity", 0)
        diversity = g.get("diversity", 0)
        trend = g.get("trend", {})
        adaptive = g.get("adaptive", {})
        rounds = g.get("total_rounds", 0)

        print(f"\n{'='*60}")
        print(f"  🔍 AI MONITOR ANALYSIS — Round {rounds}")
        print(f"{'='*60}")
        print(f"  Champion AUC:  {auc:.6f}")
        print(f"  Brier Score:   {brier:.6f}")
        print(f"  Streak:        {streak} (longest: {g.get('longest_streak',0)})")
        print(f"  Trend:         {trend.get('direction','?')} (slope: {trend.get('slope',0):.6f})")
        print(f"  Kaizen Score:  {g.get('kaizen_score',0):.1f}/100")
        print(f"  Velocity:      {velocity:.1f} | Diversity: {diversity:.0f}%")
        print(f"  Adaptive:      mut={adaptive.get('mutation_rate','?')} temp={adaptive.get('temperature','?')} width={adaptive.get('search_width','?')}x")

        # Decision logic
        action_taken = False

        # === SEVERE PLATEAU ===
        if streak >= PLATEAU_SEVERE:
            print(f"\n  🚨 SEVERE PLATEAU ({streak} rounds) — Aggressive intervention")
            params = {
                "mutation_rate": 0.58,
                "temperature": 2.0,
                "search_width": 3.0,
            }
            result = apply_tune("ai_monitor", f"Severe plateau ({streak} rounds). Maximizing exploration.", params)
            if result:
                print(f"  ✅ Applied: {json.dumps(params)}")
                action_taken = True

            post_recommendation("ai_monitor",
                f"Severe plateau at {streak} rounds. Applied max exploration params. "
                f"Consider adding new feature interactions or changing OPTUNA_TRIALS_PER_ROUND.",
                "HIGH")

        # === MILD PLATEAU ===
        elif streak >= PLATEAU_MILD:
            print(f"\n  ⚠ Mild plateau ({streak} rounds) — Warming exploration")
            warmth = min(1.0, (streak - PLATEAU_MILD) / 20)  # 0-1 scale
            params = {
                "mutation_rate": round(0.30 + warmth * 0.25, 3),
                "temperature": round(1.0 + warmth * 0.8, 3),
                "search_width": round(1.0 + warmth * 1.5, 2),
            }
            result = apply_tune("ai_monitor", f"Mild plateau ({streak} rounds). Graduated warmth={warmth:.2f}", params)
            if result:
                print(f"  ✅ Applied: {json.dumps(params)}")
                action_taken = True

        # === JUST PROMOTED — COOL DOWN ===
        elif streak == 0 and self.last_streak > 0:
            print(f"\n  🎉 Fresh promotion! Cooling down to exploit.")
            params = {
                "mutation_rate": 0.18,
                "temperature": 0.75,
                "search_width": 1.0,
            }
            result = apply_tune("ai_monitor", "Fresh promotion — cooling to exploitation mode.", params)
            if result:
                print(f"  ✅ Applied cooldown: {json.dumps(params)}")
                action_taken = True

        # === LOW DIVERSITY ===
        elif diversity < DIVERSITY_LOW and rounds > 20:
            print(f"\n  ⚠ Low diversity ({diversity:.0f}%) — Increasing exploration")
            current_temp = adaptive.get("temperature", 1.0)
            params = {
                "temperature": min(2.0, current_temp + 0.3),
                "mutation_rate": min(0.50, adaptive.get("mutation_rate", 0.3) + 0.1),
            }
            result = apply_tune("ai_monitor", f"Low diversity ({diversity:.0f}%). Boosting exploration.", params)
            if result:
                print(f"  ✅ Applied diversity boost: {json.dumps(params)}")
                action_taken = True

        # === NEAR CEILING ===
        elif auc > AUC_CEILING:
            print(f"\n  🏔 Near AUC ceiling ({auc:.6f}) — Focus on calibration")
            post_recommendation("ai_monitor",
                f"AUC at {auc:.4f} is near theoretical max. Shift focus to Brier score ({brier:.4f}) "
                f"and T4 Precision. Consider ensemble diversification over raw AUC gains.",
                "MEDIUM")

        # === DEGRADING TREND ===
        elif trend.get("direction") == "degrading":
            print(f"\n  📉 Degrading trend detected (slope: {trend.get('slope',0):.6f})")
            params = {
                "mutation_rate": 0.25,
                "temperature": 0.85,
                "search_width": 1.2,
            }
            result = apply_tune("ai_monitor", "Degrading AUC trend — stabilizing exploration.", params)
            if result:
                print(f"  ✅ Applied stabilization: {json.dumps(params)}")
                action_taken = True

        else:
            print(f"\n  ✅ Training healthy — no intervention needed")

        # Feature analysis
        top = feat_analysis.get("top_performing", [])
        weak = feat_analysis.get("underperforming", [])
        if top:
            print(f"\n  📊 Top features: {', '.join(f['name']+'('+str(int(f['win_rate']*100))+'%)' for f in top[:5])}")
        if weak and len(weak) > 3:
            print(f"  📊 Weak features: {', '.join(f['name'] for f in weak[:3])}")

        # Update state
        self.last_auc = auc
        self.last_streak = streak
        if action_taken:
            self.interventions += 1
            self.cooldown_until = time.time() + 60  # 60s cooldown between interventions

        return action_taken

# ═══════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_report():
    """Generate a markdown training report."""
    diag = get_diagnosis()
    brief = get_brief()
    history = api_get("/api/ai/history")

    if not diag:
        print("Cannot generate report — dashboard not reachable")
        return

    g = diag.get("gungnir", {})
    o = diag.get("odin", {})
    feat = diag.get("feature_analysis", {})
    sugs = diag.get("suggestions", [])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"training_report_{ts}.md"

    report = f"""# 9REALMS Training Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

| Metric | GUNGNIR | ODIN |
|--------|---------|------|
| Champion AUC | {g.get('champion_auc', '—')} | {o.get('champion_auc', '—')} |
| Brier Score | {g.get('champion_brier', '—')} | {o.get('champion_brier', '—')} |
| T4 Precision | {g.get('champion_t4p', '—')} | {o.get('champion_t4p', '—')} |
| Total Rounds | {g.get('total_rounds', 0)} | {o.get('total_rounds', 0)} |
| Promotions | {g.get('total_promotions', 0)} | {o.get('total_promotions', 0)} |
| Promotion Rate | {g.get('promotion_rate', 0):.1%} | — |
| Current Streak | {g.get('current_streak', 0)} | {o.get('current_streak', 0)} |

## Kaizen Adaptive State

| Parameter | Value |
|-----------|-------|
| Kaizen Score | {g.get('kaizen_score', 0)}/100 |
| Improvement Velocity | {g.get('velocity', 0):.1f} |
| Exploration Diversity | {g.get('diversity', 0):.0f}% |
| Mutation Rate | {g.get('adaptive', {}).get('mutation_rate', '—')} |
| Temperature | {g.get('adaptive', {}).get('temperature', '—')} |
| Search Width | {g.get('adaptive', {}).get('search_width', '—')}x |
| Trend | {g.get('trend', {}).get('direction', '—')} (slope: {g.get('trend', {}).get('slope', 0):.6f}) |

## Feature Analysis

### Top Performing Features
{chr(10).join(f"- **{f['name']}**: {f['win_rate']*100:.0f}% win rate" for f in feat.get('top_performing', [])[:10])}

### Underperforming Features
{chr(10).join(f"- {f['name']}: {f['win_rate']*100:.0f}% win rate" for f in feat.get('underperforming', [])[:5])}

## AI Suggestions

{chr(10).join(f"- **[{s['priority']}]** {s['message']}" for s in sugs)}

## Champion Features
Engineered features in current GUNGNIR champion:
{chr(10).join(f"- {f}" for f in g.get('champion_eng_features', []))}

## Yearly AUC Breakdown
{chr(10).join(f"- {ya}" for ya in g.get('yearly_aucs', []))}

## AI Tuning History
"""
    tunings = (history or {}).get("tunings", [])[-20:]
    for t in reversed(tunings):
        report += f"- **{t.get('timestamp', '?')}** [{t.get('source', '?')}]: {t.get('reason', '')} → {json.dumps(t.get('params_applied', {}))}\n"

    report += f"""
---
*Report generated by 9REALMS AI Monitor v1.0*
"""

    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n📄 Report saved to: {report_path}")
    return report_path

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="9REALMS AI Training Monitor")
    parser.add_argument("--watch", action="store_true", default=True, help="Continuous monitoring (default)")
    parser.add_argument("--once", action="store_true", help="Single diagnosis + tune cycle")
    parser.add_argument("--report", action="store_true", help="Generate training report")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in seconds (default: 30)")
    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — AI MONITOR v1.0                                              ║
║  Autonomous Training Copilot                                             ║
║                                                                          ║
║  Dashboard: http://localhost:9876                                        ║
║  Endpoints: /api/ai/diagnose | /api/ai/tune | /api/ai/brief            ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)

    # Check dashboard connectivity
    status = api_get("/api/status")
    if not status:
        print("❌ Cannot connect to dashboard at localhost:9876")
        print("   Start the dashboard first: python kaizen_dashboard.py")
        sys.exit(1)
    print("✅ Connected to Kaizen Dashboard")

    if args.report:
        generate_report()
        return

    analyzer = TrainingAnalyzer()

    if args.once:
        diag = get_diagnosis()
        analyzer.analyze_and_act(diag)
        print(f"\n📊 Interventions applied: {analyzer.interventions}")
        return

    # Watch mode
    print(f"👁 Starting continuous watch (interval: {args.interval}s)")
    print(f"   Press Ctrl+C to stop\n")

    cycle = 0
    report_cycle = 0
    while True:
        try:
            cycle += 1
            report_cycle += 1
            print(f"\n{'─'*40} Cycle {cycle} ({'─'*10}")

            diag = get_diagnosis()
            analyzer.analyze_and_act(diag)

            # Auto-generate report every 50 cycles
            if report_cycle >= 50:
                print("\n📄 Auto-generating periodic report...")
                generate_report()
                report_cycle = 0

            time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n\n🛑 AI Monitor stopped.")
            print(f"   Total interventions: {analyzer.interventions}")
            print(f"   Total cycles: {cycle}")
            break

if __name__ == "__main__":
    main()
