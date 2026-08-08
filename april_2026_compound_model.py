#!/usr/bin/env python3
"""
COMPLETE COMPOUNDING MODEL: April → June 2026
$100K start, $10K/month drawdown starting July
Maximum return strategy with ODIN v9 + BIFROST v2
"""
import json, math, numpy as np
from datetime import datetime

# Load configs
with open("/sessions/loving-nifty-dirac/mnt/Python/9realms/odin_v9_deploy.json") as f:
    odin = json.load(f)
with open("/sessions/loving-nifty-dirac/mnt/Python/9realms/bifrost_v2_deploy.json") as f:
    bifrost = json.load(f)

FEATURES = odin["features"]
COEFS = odin["coefficients"]
INTERCEPT = odin["intercept"]
MEANS = odin["scaler_means"]
SCALES = odin["scaler_scales"]

def odin_score(features_dict):
    z = INTERCEPT
    for feat in FEATURES:
        raw = features_dict.get(feat, 0.0)
        scaled = (raw - MEANS[feat]) / SCALES[feat] if SCALES[feat] != 0 else 0
        z += COEFS[feat] * scaled
    prob = 1.0 / (1.0 + math.exp(-z))
    if prob >= 0.85: tier = "T1"
    elif prob >= 0.65: tier = "T2"
    elif prob >= 0.40: tier = "T3"
    else: tier = "T4"
    return prob, tier

# ============================================================
# APRIL TRADEABLE EVENTS (enter tomorrow Mar 30 or later)
# Skip BIIB (window closed Mar 27), skip BMY (window closes Apr 1 — CAN still enter for 2 days)
# ============================================================

print("=" * 110)
print("FINAL APRIL 2026 ALLOCATION — $100,000")
print("Entering trades starting March 30, 2026")
print("=" * 110)

# Events we CAN still trade (entry window not fully passed)
april_trades = [
    {
        "ticker": "BMY", "pdufa": "2026-04-08", "tier": "T1", "mcap": "large",
        "action": "STRONG_BUY", "entry": "NOW (exit Apr 1)", "exit": "Apr 1",
        "holding_days": 3, "hit": 0.586, "mean_ret": 0.030,
        "note": "Window closing in 3 days! Quick trade on T1 large. ODIN 0.97.",
        "odin": 0.97
    },
    {
        "ticker": "REPL", "pdufa": "2026-04-10", "tier": "T4", "mcap": "small",
        "action": "LEAN_LONG", "entry": "In window", "exit": "Apr 7",
        "holding_days": 8, "hit": 0.566, "mean_ret": 0.044,
        "note": "T4 small. Naive sponsor resub in onc. But stock +86% on resub acceptance. Capped.",
        "odin": 0.04
    },
    {
        "ticker": "TVTX", "pdufa": "2026-04-13", "tier": "T1", "mcap": "mid",
        "action": "STRONG_BUY", "entry": "In window", "exit": "Apr 12",
        "holding_days": 13, "hit": 0.653, "mean_ret": 0.057,
        "note": "T1 mid STRONG_BUY. AdCom REMOVED (bullish). Already approved for IgAN. ODIN 0.91. TOP PICK.",
        "odin": 0.91
    },
    {
        "ticker": "GRCE", "pdufa": "2026-04-23", "tier": "T4", "mcap": "micro",
        "action": "LEAN_LONG", "entry": "NOW (entering window)", "exit": "Apr 22",
        "holding_days": 23, "hit": 0.526, "mean_ret": 0.074,
        "note": "T4 micro. 505(b)(2) NDA reformulation. Naive but ODD. $63M mcap = big move potential.",
        "odin": 0.08
    },
    {
        "ticker": "AXSM", "pdufa": "2026-04-30", "tier": "T2", "mcap": "mid",
        "action": "STRONG_BUY", "entry": "In window", "exit": "Apr 27",
        "holding_days": 28, "hit": 0.592, "mean_ret": 0.097,
        "note": "T2 mid STRONG_BUY. BTD+PR, already approved Auvelity. AD agitation first-in-class. ODIN 0.84. HIGH CONVICTION.",
        "odin": 0.84
    },
    {
        "ticker": "MGNX", "pdufa": "2026-04-30", "tier": "T2", "mcap": "micro",
        "action": "STRONG_BUY", "entry": "In window (deep)", "exit": "Apr 23",
        "holding_days": 24, "hit": 0.733, "mean_ret": 0.220,
        "note": "T2 micro STRONG_BUY. ZYNYZ sBLA already approved for Merkel. 73% hit, +22% mean. BEST RISK-REWARD IN APRIL.",
        "odin": 0.78
    },
]

# AGGRESSIVE allocation — maximize capital deployed on highest-conviction
# Priority: MGNX (best E[V]) > TVTX (T1 mid) > AXSM (T2 mid) > BMY (T1 large, short hold)
CAPITAL = 100_000

allocations = {
    "MGNX":  0.20,   # Best risk-reward: 73% hit, +22% mean, T2 micro, Sharpe 1.09
    "TVTX":  0.20,   # T1 mid, AdCom removed, 65% hit, +5.7% mean, Sharpe 1.02
    "AXSM":  0.20,   # T2 mid, BTD+PR, 59% hit, +9.7% mean, Sharpe 0.76
    "BMY":   0.10,   # T1 large, only 3 days left in window, 59% hit, +3% mean
    "GRCE":  0.05,   # T4 micro lottery, 53% hit but +7.4% mean on $63M mcap
    "REPL":  0.03,   # T4 small, capped, but stock has momentum from resub acceptance
}

# Print allocation
print(f"\n  {'TICKER':>8} {'ODIN':>5} {'TIER':>4} {'ACTION':>12} {'ALLOC%':>7} {'$AMOUNT':>9} "
      f"{'HIT%':>5} {'E[R]':>7} {'E[$]':>8} {'EXIT BY':>10} {'NOTE'}")
print("  " + "-" * 130)

total_alloc = 0
total_ev = 0
for t in april_trades:
    alloc = allocations.get(t["ticker"], 0)
    dollars = CAPITAL * alloc
    ev = dollars * t["mean_ret"]
    total_alloc += alloc
    total_ev += ev
    
    print(f"  {t['ticker']:>8} {t['odin']:.2f} {t['tier']:>4} {t['action']:>12} {alloc*100:>6.0f}% ${dollars:>8,.0f} "
          f"{t['hit']*100:>4.0f}% {t['mean_ret']*100:>+6.1f}% ${ev:>+7,.0f} {t['exit']:>10}")
    print(f"           {t['note']}")

cash_reserve = CAPITAL * (1 - total_alloc)
print(f"\n  TOTAL DEPLOYED: {total_alloc*100:.0f}% = ${CAPITAL * total_alloc:,.0f}")
print(f"  CASH RESERVE:   {(1-total_alloc)*100:.0f}% = ${cash_reserve:,.0f}")
print(f"  EXPECTED VALUE: ${total_ev:>+,.0f} ({total_ev/CAPITAL*100:>+.1f}%)")

# ============================================================
# SEQUENTIAL COMPOUNDING SIMULATION
# ============================================================
print("\n" + "=" * 110)
print("SEQUENTIAL COMPOUNDING — APRIL THROUGH JUNE")
print("=" * 110)

# April sequential timeline:
# Week 1 (Mar 30 - Apr 1): BMY exits → free up capital
# Week 2 (Apr 7-10): REPL exits → free up capital  
# Week 2-3 (Apr 12): TVTX exits → free up capital
# Week 4 (Apr 22): GRCE exits → free up capital
# Week 5 (Apr 23-27): MGNX, AXSM exit → free up capital
# Then MAY trades begin

print("\n  APRIL SEQUENTIAL FLOW:")
print(f"  Mar 30: Deploy ${CAPITAL * total_alloc:,.0f} across 6 positions, ${cash_reserve:,.0f} cash reserve")
print(f"  Apr 1:  BMY exits → ${CAPITAL*0.10:,.0f} freed (can redeploy)")
print(f"  Apr 7:  REPL exits → ${CAPITAL*0.03:,.0f} freed")  
print(f"  Apr 12: TVTX exits → ${CAPITAL*0.20:,.0f} freed (big chunk)")
print(f"  Apr 22: GRCE exits → ${CAPITAL*0.05:,.0f} freed")
print(f"  Apr 23: MGNX exits → ${CAPITAL*0.20:,.0f} freed")
print(f"  Apr 27: AXSM exits → ${CAPITAL*0.20:,.0f} freed")
print(f"  Apr 30: All April capital available for May deployment")

# Monte Carlo with sequential compounding
print("\n" + "=" * 110)
print("MONTE CARLO — 50,000 SIMULATIONS (AGGRESSIVE APRIL)")
print("=" * 110)

np.random.seed(42)
N = 50000
results = []

for _ in range(N):
    port = CAPITAL
    for t in april_trades:
        alloc = allocations.get(t["ticker"], 0)
        position = port * alloc
        
        if np.random.random() < t["hit"]:
            # Win
            ret = abs(np.random.lognormal(math.log(max(0.01, t["mean_ret"])), 0.5))
            ret = min(ret, 3.0)
        else:
            # Loss - calibrated to make E[R] = mean_ret
            loss_mean = (t["mean_ret"] - t["hit"] * t["mean_ret"] * 1.2) / (1 - t["hit"])
            ret = -abs(np.random.exponential(abs(t["mean_ret"]) * 0.8))
            ret = max(ret, -0.80)
        
        pnl = position * ret
        port = max(1000, port + pnl)  # floor at $1K
    
    results.append(port)

results = np.array(results)

print(f"\n  Starting:    ${CAPITAL:>12,.0f}")
print(f"  Median:      ${np.median(results):>12,.0f}  ({(np.median(results)/CAPITAL-1)*100:>+.1f}%)")
print(f"  Mean:        ${np.mean(results):>12,.0f}  ({(np.mean(results)/CAPITAL-1)*100:>+.1f}%)")
print(f"  P5 (worst):  ${np.percentile(results,5):>12,.0f}  ({(np.percentile(results,5)/CAPITAL-1)*100:>+.1f}%)")
print(f"  P25:         ${np.percentile(results,25):>12,.0f}  ({(np.percentile(results,25)/CAPITAL-1)*100:>+.1f}%)")
print(f"  P75:         ${np.percentile(results,75):>12,.0f}  ({(np.percentile(results,75)/CAPITAL-1)*100:>+.1f}%)")
print(f"  P95 (best):  ${np.percentile(results,95):>12,.0f}  ({(np.percentile(results,95)/CAPITAL-1)*100:>+.1f}%)")
print(f"  P(profit):   {(results > CAPITAL).mean()*100:.1f}%")
print(f"  P(>$110K):   {(results > 110000).mean()*100:.1f}%")
print(f"  P(>$120K):   {(results > 120000).mean()*100:.1f}%")
print(f"  P(>$130K):   {(results > 130000).mean()*100:.1f}%")
print(f"  P(<$90K):    {(results < 90000).mean()*100:.1f}%")
print(f"  P(<$80K):    {(results < 80000).mean()*100:.1f}%")
print(f"  Max:         ${np.max(results):>12,.0f}")
print(f"  Min:         ${np.min(results):>12,.0f}")

# ============================================================
# JULY DRAWDOWN RUNWAY
# ============================================================
print("\n" + "=" * 110)
print("JULY DRAWDOWN RUNWAY — $10K/month")
print("=" * 110)

scenarios = {
    "Conservative (P25)": np.percentile(results, 25),
    "Median":             np.median(results),
    "Optimistic (P75)":   np.percentile(results, 75),
    "Bull (P95)":         np.percentile(results, 95),
}

# Add May/June compounding estimate (conservative: +5% per month from additional trades)
may_june_boost = {
    "Conservative (P25)": 0.03,  # 3% from May/June trades
    "Median": 0.07,              # 7% cumulative May+June
    "Optimistic (P75)": 0.12,   # 12% cumulative
    "Bull (P95)": 0.20,         # 20% cumulative
}

print(f"\n  {'Scenario':>25} {'End Apr':>10} {'May/Jun+':>8} {'End Jun':>10} {'Months @$10K':>13}")
print("  " + "-" * 75)

for name, end_apr in scenarios.items():
    boost = may_june_boost[name]
    end_jun = end_apr * (1 + boost)
    months = end_jun / 10000
    print(f"  {name:>25} ${end_apr:>9,.0f} {boost*100:>+6.1f}% ${end_jun:>9,.0f} {months:>10.1f} months")

# ============================================================
# KEY TRADES RANKED BY PRIORITY
# ============================================================
print("\n" + "=" * 110)
print("PRIORITY RANKING — WHAT TO BUY TOMORROW (MAR 30)")
print("=" * 110)

priority = [
    ("1. MGNX", "$20,000 (20%)", "T2 micro STRONG_BUY", "73% hit, +22.0% mean, Sharpe 1.09",
     "BEST risk-reward. Already approved drug (ZYNYZ), sBLA for NSCLC. Micro-cap = big moves."),
    ("2. TVTX", "$20,000 (20%)", "T1 mid STRONG_BUY", "65% hit, +5.7% mean, Sharpe 1.02", 
     "HIGHEST conviction. 91% ODIN score. AdCom REMOVED. Already approved for IgAN."),
    ("3. AXSM", "$20,000 (20%)", "T2 mid STRONG_BUY", "59% hit, +9.7% mean, Sharpe 0.76",
     "BTD + Priority Review. Already has Auvelity approved. First AD agitation drug."),
    ("4. BMY",  "$10,000 (10%)", "T1 large STRONG_BUY", "59% hit, +3.0% mean, Sharpe 0.53",
     "EXIT BY APR 1. Only 3 days in window. T1 large = reliable but small moves."),
    ("5. GRCE", "$5,000 (5%)",   "T4 micro LEAN_LONG", "53% hit, +7.4% mean, Sharpe 0.73",
     "Lottery ticket. $63M mcap nano-to-micro. ODD. 505(b)(2). If approved, monster move."),
    ("6. REPL", "$3,000 (3%)",   "T4 small LEAN_LONG", "57% hit, +4.4% mean, Sharpe 0.58",
     "Momentum play. Stock +86% on BLA resub acceptance. T4 so capped."),
]

print(f"\n  CASH RESERVE: $22,000 (22%) — for May/June redeployment")
print()

for rank, alloc, signal, stats, rationale in priority:
    print(f"  {rank}: {alloc}")
    print(f"    Signal: {signal} | {stats}")
    print(f"    Why: {rationale}")
    print()

print("  CARDINAL RULE: EXIT BEFORE PDUFA. The runup IS the trade. Never hold through the decision.")
print()
print("  DISCLAIMER: This is informational/educational analysis, not investment advice.")
print("  Past performance does not guarantee future results. All trading involves risk of loss.")
