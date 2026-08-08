#!/usr/bin/env python3
"""
BIFROST Strategy Engine v1.0 — Portfolio Sim + Opportunity Scanner
================================================================
Part 1: Simulate compound returns 2020-2026 using ODIN tier × BIFROST timing
Part 2: Score all 2026 PDUFA events for upcoming trade opportunities
"""

import csv, json, math, os, sys
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import numpy as np

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# BIFROST Decision Matrix — optimal window per tier × mcap
BIFROST_WINDOWS = {
    ("T1", "nano"):  ("T-45_T-7",  "LEAN_LONG",  0.52, 5.0),
    ("T1", "micro"): ("T-90_T-7",  "STRONG_BUY", 0.55, 13.7),
    ("T1", "small"): ("T-25_T-3",  "BUY",        0.54, 1.3),
    ("T1", "mid"):   ("T-25_T-1",  "LEAN_LONG",  1.00, 12.5),
    ("T1", "large"): ("T-45_T-7",  "STRONG_BUY", 0.72, 5.1),
    ("T2", "nano"):  ("T-90_T-7",  "BUY",        0.75, 49.0),
    ("T2", "micro"): ("T-60_T-3",  "STRONG_BUY", 0.62, 13.2),
    ("T2", "small"): ("T-45_T-7",  "STRONG_BUY", 0.63, 8.5),
    ("T2", "mid"):   ("T-45_T-7",  "STRONG_BUY", 0.60, 9.4),
    ("T2", "large"): ("T-25_T-3",  "STRONG_BUY", 0.67, 6.9),
    ("T3", "nano"):  ("T-25_T-7",  "NEUTRAL",    0.50, 2.0),
    ("T3", "micro"): ("T-25_T-7",  "NEUTRAL",    0.52, 3.0),
    ("T3", "small"): ("T-25_T-7",  "LEAN_LONG",  0.55, 5.0),
    ("T3", "mid"):   ("T-25_T-7",  "NEUTRAL",    0.50, 2.0),
    ("T3", "large"): ("T-25_T-7",  "NEUTRAL",    0.48, 1.0),
    ("T4", "nano"):  ("",          "AVOID",       0.39, 4.4),
    ("T4", "micro"): ("T-25_T-3",  "BUY",        0.54, 6.5),
    ("T4", "small"): ("T-25_T-1",  "BUY",        0.63, 6.8),
    ("T4", "mid"):   ("T-25_T-1",  "LEAN_LONG",  0.55, 3.0),
    ("T4", "large"): ("T-25_T-1",  "LEAN_LONG",  0.79, 3.4),
}

POSITION_SIZE = {
    "STRONG_BUY": 0.05,
    "BUY":        0.03,
    "LEAN_LONG":  0.02,
    "NEUTRAL":    0.00,
    "AVOID":      0.00,
}


def map_mcap(raw):
    r = raw.lower().strip()
    if "nano" in r: return "nano"
    if "micro" in r: return "micro"
    if "small" in r: return "small"
    if "mid" in r: return "mid"
    if "large" in r: return "large"
    return "small"


def simulate_portfolio(events):
    """Run historical portfolio simulation."""
    portfolio = 100_000.0
    peak = portfolio
    max_dd = 0.0
    trades = []
    yearly = defaultdict(lambda: {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0})

    for ev in events:
        tier = ev["tier"]
        mcap = ev["mcap"]
        key = (tier, mcap)

        window_col, action, hist_hit, hist_mean = BIFROST_WINDOWS.get(key, ("", "NEUTRAL", 0.5, 0))

        alloc = POSITION_SIZE.get(action, 0)
        if alloc == 0 or not window_col:
            continue

        ret_str = ev.get(window_col, "")
        if not ret_str or ret_str in ("", "nan", "None"):
            continue

        try:
            ret = float(ret_str)
        except:
            continue

        ret = max(-1.0, min(2.0, ret))  # cap extremes

        position_value = portfolio * alloc
        pnl = position_value * ret
        portfolio += pnl

        year = ev["pdufa_date"][:4]
        win = 1 if pnl > 0 else 0
        trades.append({
            "ticker": ev["ticker"], "pdufa_date": ev["pdufa_date"],
            "tier": tier, "mcap": mcap, "action": action, "window": window_col,
            "return_pct": round(ret * 100, 2), "position_pct": round(alloc * 100, 1),
            "pnl": round(pnl, 2), "portfolio_after": round(portfolio, 2), "win": win,
        })

        yearly[year]["trades"] += 1
        yearly[year]["wins"] += win
        yearly[year]["losses"] += (1 - win)
        yearly[year]["pnl"] += pnl

        if portfolio > peak: peak = portfolio
        dd = (portfolio - peak) / peak
        if dd < max_dd: max_dd = dd

    total_return = (portfolio - 100_000) / 100_000 * 100
    n_trades = len(trades)
    win_rate = sum(t["win"] for t in trades) / n_trades if n_trades else 0

    returns = [t["return_pct"] / 100 for t in trades]
    if len(returns) > 1:
        avg_ret = np.mean(returns)
        std_ret = np.std(returns)
        trades_per_year = max(n_trades / 6, 1)
        sharpe = (avg_ret / std_ret) * math.sqrt(trades_per_year) if std_ret > 0 else 0
    else:
        sharpe = 0

    yearly_summary = {}
    for yr in sorted(yearly.keys()):
        y = yearly[yr]
        wr = y["wins"] / y["trades"] if y["trades"] else 0
        yearly_summary[yr] = {
            "trades": y["trades"], "wins": y["wins"], "losses": y["losses"],
            "win_rate": round(wr, 3), "pnl": round(y["pnl"], 2),
        }

    return {
        "start_value": 100_000, "end_value": round(portfolio, 2),
        "total_return_pct": round(total_return, 2), "total_trades": n_trades,
        "win_rate": round(win_rate, 3), "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_return_per_trade": round(np.mean(returns) * 100, 2) if returns else 0,
        "yearly_breakdown": yearly_summary,
        "top_trades": sorted(trades, key=lambda t: -t["return_pct"])[:10],
        "bottom_trades": sorted(trades, key=lambda t: t["return_pct"])[:10],
    }


def scan_opportunities(events, as_of="2026-02-01"):
    """Scan upcoming PDUFA events for trade opportunities."""
    as_of_dt = datetime.strptime(as_of, "%Y-%m-%d")
    opportunities = []

    for ev in events:
        try:
            pdufa_dt = datetime.strptime(ev["pdufa_date"], "%Y-%m-%d")
        except:
            continue

        days_to = (pdufa_dt - as_of_dt).days
        if days_to < -5 or days_to > 120:
            continue

        tier = ev["tier"]
        mcap = ev["mcap"]
        key = (tier, mcap)

        window_col, action, hist_hit, hist_mean = BIFROST_WINDOWS.get(key, ("", "NEUTRAL", 0.5, 0))
        alloc = POSITION_SIZE.get(action, 0)
        if alloc == 0:
            continue

        action_score = {"STRONG_BUY": 4, "BUY": 3, "LEAN_LONG": 2}.get(action, 0)
        composite_score = action_score * hist_hit * (hist_mean / 10.0)

        # Parse entry/exit from window column
        entry_map = {"T-90": -90, "T-60": -60, "T-45": -45, "T-25": -25}
        exit_map = {"T-7": -7, "T-3": -3, "T-1": -1}
        entry_day, exit_day = -45, -7
        if window_col:
            parts = window_col.replace("_", " ").split()
            if len(parts) >= 2:
                entry_day = entry_map.get(parts[0], -45)
                exit_day = exit_map.get(parts[1], -7)

        if days_to > abs(entry_day) + 10: timing = "TOO_EARLY"
        elif days_to >= abs(entry_day): timing = "ENTRY_ZONE"
        elif days_to > abs(exit_day): timing = "HOLDING"
        elif days_to >= abs(exit_day): timing = "EXIT_ZONE"
        else: timing = "PAST_EXIT"

        opportunities.append({
            "ticker": ev["ticker"], "company": ev.get("company", ""),
            "asset": ev.get("asset", ""), "indication": ev.get("indication", ""),
            "pdufa_date": ev["pdufa_date"], "days_to_pdufa": days_to,
            "tier": tier, "mcap": mcap, "action": action, "window": window_col,
            "hist_hit_rate": hist_hit, "hist_mean_return": hist_mean,
            "composite_score": round(composite_score, 4),
            "position_size_pct": round(alloc * 100, 1), "timing": timing,
        })

    opportunities.sort(key=lambda x: -x["composite_score"])
    return opportunities


def main():
    print("="*80)
    print("BIFROST Strategy Engine v1.0")
    print("="*80)

    csv_path = os.path.join(DATA_DIR, "pdufa_runup_bifrost.csv")
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        raw_events = list(reader)

    print(f"\nLoaded {len(raw_events)} PDUFA events")

    events = []
    for r in raw_events:
        ev = {
            "ticker": r["ticker"], "company": r.get("company", ""),
            "asset": r.get("asset", ""), "indication": r.get("indication", ""),
            "pdufa_date": r["pdufa_date"], "outcome": r.get("outcome", ""),
            "tier": r["v5_tier"].strip(), "mcap": map_mcap(r["mcap_tier"]),
        }
        for col in ["T-90_T-7", "T-90_T-3", "T-90_T-1", "T-60_T-7", "T-60_T-3",
                     "T-60_T-1", "T-45_T-7", "T-45_T-3", "T-45_T-1",
                     "T-25_T-7", "T-25_T-3", "T-25_T-1"]:
            ev[col] = r.get(col, "")
        events.append(ev)

    events.sort(key=lambda e: e["pdufa_date"])

    tiers = Counter(e["tier"] for e in events)
    mcaps = Counter(e["mcap"] for e in events)
    print(f"Tiers: {dict(tiers)}")
    print(f"Mcaps: {dict(mcaps)}")

    # Check data availability
    tradeable = sum(1 for e in events
                    if POSITION_SIZE.get(BIFROST_WINDOWS.get((e["tier"], e["mcap"]), ("","NEUTRAL",0,0))[1], 0) > 0
                    and BIFROST_WINDOWS.get((e["tier"], e["mcap"]), ("",))[0]
                    and e.get(BIFROST_WINDOWS.get((e["tier"], e["mcap"]), ("T-45_T-7",))[0], "") not in ("", "nan", "None"))
    print(f"Tradeable events (have window data + action): {tradeable}")

    # ===== PART 1: PORTFOLIO SIMULATION =====
    print("\n" + "="*80)
    print("PART 1: Historical Portfolio Simulation (2020-2026)")
    print("="*80)

    sim = simulate_portfolio(events)

    print(f"\n  Start:          ${sim['start_value']:>12,.0f}")
    print(f"  End:            ${sim['end_value']:>12,.0f}")
    print(f"  Total return:   {sim['total_return_pct']:>+10.2f}%")
    print(f"  Total trades:   {sim['total_trades']:>10d}")
    print(f"  Win rate:       {sim['win_rate']:>10.1%}")
    print(f"  Avg ret/trade:  {sim['avg_return_per_trade']:>+10.2f}%")
    print(f"  Max drawdown:   {sim['max_drawdown_pct']:>10.2f}%")
    print(f"  Sharpe ratio:   {sim['sharpe_ratio']:>10.2f}")

    print(f"\n  Year-by-Year:")
    for yr, yd in sim["yearly_breakdown"].items():
        print(f"    {yr}: {yd['trades']:4d} trades, {yd['win_rate']:.0%} win, ${yd['pnl']:>+10,.0f}")

    if sim["top_trades"]:
        print(f"\n  Top 5 Trades:")
        for t in sim["top_trades"][:5]:
            print(f"    {t['ticker']:>6s} {t['pdufa_date']} {t['tier']}/{t['mcap']:>6s} "
                  f"{t['action']:>12s} {t['return_pct']:>+7.1f}% ${t['pnl']:>+8,.0f}")
        print(f"\n  Worst 5 Trades:")
        for t in sim["bottom_trades"][:5]:
            print(f"    {t['ticker']:>6s} {t['pdufa_date']} {t['tier']}/{t['mcap']:>6s} "
                  f"{t['action']:>12s} {t['return_pct']:>+7.1f}% ${t['pnl']:>+8,.0f}")

    # ===== PART 2: SCANNER =====
    print("\n" + "="*80)
    print("PART 2: 2026 Opportunity Scanner")
    print("="*80)

    # Dataset ends 2026-02-21, scan from 2026-01-01 to catch remaining 2026 events
    opps = scan_opportunities(events, as_of="2026-01-01")
    print(f"\n  2026 Q1 actionable events: {len(opps)}")

    if opps:
        print(f"\n  {'#':>3s} {'Ticker':>6s} {'Date':>10s} {'Days':>5s} {'Tier':>4s} "
              f"{'Mcap':>6s} {'Action':>12s} {'Hit%':>5s} {'AvgRet':>7s} {'Score':>7s}")
        print("  " + "-"*85)
        for i, o in enumerate(opps[:20]):
            print(f"  {i+1:3d} {o['ticker']:>6s} {o['pdufa_date']:>10s} {o['days_to_pdufa']:>5d} "
                  f"{o['tier']:>4s} {o['mcap']:>6s} {o['action']:>12s} "
                  f"{o['hist_hit_rate']*100:>4.0f}% {o['hist_mean_return']:>+6.1f}% "
                  f"{o['composite_score']:>7.2f}")
    else:
        print("  No actionable events found in date range")

    # Save results
    results = {
        "engine": "BIFROST Strategy v1.0",
        "generated": "2026-03-29",
        "simulation": sim,
        "scanner": {
            "as_of": "2026-01-01",
            "total_opportunities": len(opps),
            "opportunities": opps[:30],
        },
    }

    out_path = os.path.join(DATA_DIR, "bifrost_strategy_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
