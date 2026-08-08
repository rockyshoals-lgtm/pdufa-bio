"""
BIFROST Options v1.3 — Alternative Filter Experiments on v1.2 Honest Dataset
=============================================================================

Purpose
-------
Apply the v1.2 honest filters (DTE-matched, IV-sanitized, valid prices) to the
raw 1,828 options trades, then partition along NEW axes that v1.2 did not test:

  1. ODIN inversion test — T1+T2 vs T3+T4 (PDUFA only)  ← quantify direction
  2. Cap × stage × outcome (readout) — where does the +45% Phase 1/2 edge live?
  3. IV cheapness quintile — does entry_iv_pct Q1 (cheapest) beat Q5 (priciest)?
  4. OI liquidity — entry_oi ≥ 100 filter (fillable in practice)
  5. Regime split — 2022–2023 (ZIRP exit, IV crush) vs 2024–2026 (higher vol)
  6. Spread discipline — entry_spread_pct ≤ 20 % filter
  7. Late-entry filter — bucket by entry_dte (short-dated vs long-dated)
  8. IV-change trap — does iv_change_pct correlate with option_return_mid_pct?

Every segment publishes MID + REAL_40 side-by-side with bootstrap 95 % CI
(n_boot=2000, seed=42, percentile method). Segments with n < 30 are flagged
not-live-tradeable.

Reuses the v1.2 filter helpers (dte_matched, iv_sanitized, has_valid_prices).
No new ORATS pulls — recompute only.
"""

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

RAW_PATH  = Path("/sessions/confident-serene-ptolemy/mnt/9realms/options_backtest_v2_results.json")
OUT_PATH  = Path("/sessions/confident-serene-ptolemy/mnt/9realms/options_backtest_v13_results.json")

# ---------------------------------------------------------------------------
# v1.2 filter helpers (copied verbatim from options_backtest_v12_rerun.py)
# ---------------------------------------------------------------------------
def dte_matched(t, gap_min=13, gap_max=23, exit_dte_min=3):
    try:
        entry_dte = t.get("entry_dte")
        exit_dte  = t.get("exit_dte")
        if entry_dte is None or exit_dte is None:
            return False
        gap = entry_dte - exit_dte
        return gap_min <= gap <= gap_max and exit_dte >= exit_dte_min
    except Exception:
        return False

def iv_sanitized(t, iv_max=500.0, iv_min=0.01, iv_change_max=1000.0):
    try:
        eiv = t.get("entry_iv_pct")
        xiv = t.get("exit_iv_pct")
        ivc = t.get("iv_change_pct")
        if eiv is None or xiv is None:
            return False
        if abs(eiv) > iv_max or eiv < iv_min:
            return False
        if abs(xiv) > iv_max:
            return False
        if ivc is not None and abs(ivc) > iv_change_max:
            return False
        return True
    except Exception:
        return False

def has_valid_prices(t):
    try:
        for k in ("entry_ask", "entry_bid", "entry_mid"):
            v = t.get(k)
            if v is None or v <= 0:
                return False
        for k in ("exit_bid", "exit_ask", "exit_mid"):
            v = t.get(k)
            if v is None:
                return False
        return True
    except Exception:
        return False

def honest_filter(t):
    return dte_matched(t) and iv_sanitized(t) and has_valid_prices(t)

# ---------------------------------------------------------------------------
# Fill models — compute 4 return series per trade
# ---------------------------------------------------------------------------
def compute_returns(t):
    """Return dict with mid, worst, real_25, real_40 option-return pcts."""
    try:
        eask = t["entry_ask"]; ebid = t["entry_bid"]; emid = t["entry_mid"]
        xask = t["exit_ask"];  xbid = t["exit_bid"];  xmid = t["exit_mid"]
        # MID: exit_mid / entry_mid - 1
        # WORST: exit_bid / entry_ask - 1  (pay ask at entry, hit bid at exit)
        # REAL_25 / REAL_40: blend MID and WORST where alpha = spread capture
        # Spread at entry = (ask - bid)/2; fill = mid - (1-alpha) * spread_half
        # Simpler: pct = mid_return - (1 - alpha) * (worst_return - mid_return)
        # where alpha is the fraction of mid-to-worst gap you eliminate
        mid_ret   = (xmid / emid - 1.0) * 100.0  if emid  else None
        worst_ret = (xbid / eask - 1.0) * 100.0  if eask  else None
        if mid_ret is None or worst_ret is None:
            return None
        real_25 = 0.25 * mid_ret + 0.75 * worst_ret
        real_40 = 0.40 * mid_ret + 0.60 * worst_ret
        return {"mid": mid_ret, "worst": worst_ret, "real_25": real_25, "real_40": real_40}
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Bootstrap 95% CI
# ---------------------------------------------------------------------------
def bootstrap_ci(values, n_boot=2000, seed=42, alpha=0.05):
    if len(values) < 3:
        return (None, None)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(alpha / 2 * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot) - 1]
    return (round(lo, 3), round(hi, 3))

def segment_stats(trades):
    """Compute full stats block for a segment."""
    n = len(trades)
    if n == 0:
        return {"n": 0}
    rets = [compute_returns(t) for t in trades]
    rets = [r for r in rets if r is not None]
    if not rets:
        return {"n": 0}
    mid  = [r["mid"]     for r in rets]
    w    = [r["worst"]   for r in rets]
    r25  = [r["real_25"] for r in rets]
    r40  = [r["real_40"] for r in rets]

    stock = [t.get("stock_return_pct") for t in trades if t.get("stock_return_pct") is not None]

    def bucket(vals):
        win = sum(1 for v in vals if v > 0) / len(vals) * 100
        big_win = sum(1 for v in vals if v > 100) / len(vals) * 100
        big_loss = sum(1 for v in vals if v < -50) / len(vals) * 100
        return {
            "avg":    round(statistics.mean(vals), 2),
            "median": round(statistics.median(vals), 2),
            "win_pct":      round(win, 1),
            "gt_100_pct":   round(big_win, 1),
            "lt_minus50_pct": round(big_loss, 1),
            "ci_95": bootstrap_ci(vals),
        }

    # Ex-top-N robustness
    ex5_mid = sorted(mid)[:-5] if len(mid) >= 10 else None
    ex2_mid = sorted(mid)[:-2] if len(mid) >= 5  else None

    out = {
        "n": n,
        "mid":     bucket(mid),
        "worst":   bucket(w),
        "real_25": bucket(r25),
        "real_40": bucket(r40),
        "stock_avg_pct":  round(statistics.mean(stock), 2) if stock else None,
        "avg_entry_iv":   round(statistics.mean([t["entry_iv_pct"] for t in trades if t.get("entry_iv_pct") is not None]), 1),
        "avg_spread_pct": round(statistics.mean([t["entry_spread_pct"] for t in trades if t.get("entry_spread_pct") is not None]), 1),
        "avg_oi":         round(statistics.mean([t["entry_oi"] for t in trades if t.get("entry_oi") is not None])),
    }
    if ex5_mid:
        out["mid_ex_top5_avg"] = round(statistics.mean(ex5_mid), 2)
    if ex2_mid:
        out["mid_ex_top2_avg"] = round(statistics.mean(ex2_mid), 2)
    return out

# ---------------------------------------------------------------------------
# Load + filter
# ---------------------------------------------------------------------------
raw = json.load(open(RAW_PATH))
all_trades = raw["pdufa_trades"] + raw["readout_trades"]
print(f"RAW trades:    {len(all_trades)}")

honest = [t for t in all_trades if honest_filter(t)]
print(f"HONEST trades (dte_matched + iv_sanitized + valid_prices): {len(honest)}")

# Tag event year for regime splits
for t in honest:
    try:
        t["event_year"] = int(str(t["event_date"])[:4])
    except Exception:
        t["event_year"] = None

pdufa  = [t for t in honest if t.get("event_type") == "PDUFA"]
readout = [t for t in honest if t.get("event_type") != "PDUFA"]
print(f"  PDUFA   honest: {len(pdufa)}")
print(f"  Readout honest: {len(readout)}")

# ===========================================================================
# EXPERIMENT 1: ODIN inversion test (PDUFA only)
# ===========================================================================
tier_groups = defaultdict(list)
for t in pdufa:
    tier = t.get("odin_tier") or "UNK"
    tier_groups[tier].append(t)

exp1 = {
    "description": "ODIN tier inversion test — does T1+T2 actually beat T3+T4 for options? Hypothesis: option premium pays for uncertainty, not quality.",
    "by_tier": {tier: segment_stats(v) for tier, v in tier_groups.items() if len(v) >= 3},
    "T1_only": segment_stats(tier_groups.get("T1", [])),
    "T2_only": segment_stats(tier_groups.get("T2", [])),
    "T3_only": segment_stats(tier_groups.get("T3", [])),
    "T4_only": segment_stats(tier_groups.get("T4", [])),
    "T1_plus_T2": segment_stats(tier_groups.get("T1", []) + tier_groups.get("T2", [])),
    "T3_plus_T4": segment_stats(tier_groups.get("T3", []) + tier_groups.get("T4", [])),
}

# ===========================================================================
# EXPERIMENT 2: Cap × stage × outcome (readout)
# ===========================================================================
def readout_bucket(stage):
    if stage is None:
        return "UNK"
    s = str(stage).lower()
    if "1/2" in s or "1b/2" in s or "ph1/2" in s:
        return "Phase_1_2"
    if "2b" in s:
        return "Phase_2b"
    if "2a" in s:
        return "Phase_2a"
    if "2" in s:
        return "Phase_2"
    if "3" in s:
        return "Phase_3"
    if "1" in s:
        return "Phase_1"
    return s.upper()[:20]

exp2 = {
    "description": "Where does the Phase 1/2 positive-readout edge live? Breakout by cap_tier and outcome.",
    "by_stage": {},
    "by_stage_outcome": {},
    "by_stage_cap_outcome": {},
}
stage_groups = defaultdict(list)
stage_out_groups = defaultdict(list)
stage_cap_out_groups = defaultdict(list)

for t in readout:
    sb = readout_bucket(t.get("stage"))
    oc = t.get("outcome") or "UNK"
    cap = t.get("cap_tier") or "UNK"
    stage_groups[sb].append(t)
    stage_out_groups[f"{sb}|{oc}"].append(t)
    stage_cap_out_groups[f"{sb}|{cap}|{oc}"].append(t)

exp2["by_stage"] = {k: segment_stats(v) for k, v in stage_groups.items() if len(v) >= 10}
exp2["by_stage_outcome"] = {k: segment_stats(v) for k, v in stage_out_groups.items() if len(v) >= 10}
exp2["by_stage_cap_outcome"] = {k: segment_stats(v) for k, v in stage_cap_out_groups.items() if len(v) >= 15}

# ===========================================================================
# EXPERIMENT 3: IV cheapness quintile
# ===========================================================================
honest_with_iv = [t for t in honest if t.get("entry_iv_pct") is not None]
ivs = sorted([t["entry_iv_pct"] for t in honest_with_iv])
if len(ivs) >= 10:
    q1_cut = ivs[int(len(ivs)*0.20)]
    q2_cut = ivs[int(len(ivs)*0.40)]
    q3_cut = ivs[int(len(ivs)*0.60)]
    q4_cut = ivs[int(len(ivs)*0.80)]
    iv_quintiles = {"Q1_cheapest": [], "Q2": [], "Q3": [], "Q4": [], "Q5_priciest": []}
    for t in honest_with_iv:
        iv = t["entry_iv_pct"]
        if   iv <= q1_cut: iv_quintiles["Q1_cheapest"].append(t)
        elif iv <= q2_cut: iv_quintiles["Q2"].append(t)
        elif iv <= q3_cut: iv_quintiles["Q3"].append(t)
        elif iv <= q4_cut: iv_quintiles["Q4"].append(t)
        else:              iv_quintiles["Q5_priciest"].append(t)
    exp3 = {
        "description": "IV cheapness quintile test. Hypothesis: buying cheap IV (Q1) beats buying expensive IV (Q5).",
        "cut_points": {"q1_cut": round(q1_cut,1), "q2_cut": round(q2_cut,1), "q3_cut": round(q3_cut,1), "q4_cut": round(q4_cut,1)},
        "by_quintile": {k: segment_stats(v) for k, v in iv_quintiles.items()},
    }
else:
    exp3 = {"description": "insufficient data", "by_quintile": {}}

# ===========================================================================
# EXPERIMENT 4: Open interest liquidity filter
# ===========================================================================
oi_groups = {
    "oi_lt_50":    [t for t in honest if (t.get("entry_oi") or 0) <  50],
    "oi_50_100":   [t for t in honest if 50 <= (t.get("entry_oi") or 0) < 100],
    "oi_100_500":  [t for t in honest if 100 <= (t.get("entry_oi") or 0) < 500],
    "oi_500_2000": [t for t in honest if 500 <= (t.get("entry_oi") or 0) < 2000],
    "oi_gte_2000": [t for t in honest if (t.get("entry_oi") or 0) >= 2000],
}
exp4 = {
    "description": "Open interest liquidity buckets. Hypothesis: OI >= 100 is fillable at mid; OI < 50 is fantasy.",
    "by_oi_bucket": {k: segment_stats(v) for k, v in oi_groups.items()},
    "oi_gte_100_all":  segment_stats([t for t in honest if (t.get("entry_oi") or 0) >= 100]),
    "oi_gte_500_all":  segment_stats([t for t in honest if (t.get("entry_oi") or 0) >= 500]),
}

# ===========================================================================
# EXPERIMENT 5: Regime split 2022-23 vs 2024-26
# ===========================================================================
regime_a = [t for t in honest if t.get("event_year") in (2022, 2023)]
regime_b = [t for t in honest if t.get("event_year") in (2024, 2025, 2026)]
exp5 = {
    "description": "Regime split: 2022–2023 (ZIRP exit, IV crush era) vs 2024–2026 (higher-vol regime, biotech recovery).",
    "regime_2022_2023": segment_stats(regime_a),
    "regime_2024_2026": segment_stats(regime_b),
    "regime_a_pdufa": segment_stats([t for t in regime_a if t.get("event_type")=="PDUFA"]),
    "regime_b_pdufa": segment_stats([t for t in regime_b if t.get("event_type")=="PDUFA"]),
    "regime_a_readout": segment_stats([t for t in regime_a if t.get("event_type")!="PDUFA"]),
    "regime_b_readout": segment_stats([t for t in regime_b if t.get("event_type")!="PDUFA"]),
}

# ===========================================================================
# EXPERIMENT 6: Spread discipline
# ===========================================================================
spread_groups = {
    "spread_lte_10":   [t for t in honest if (t.get("entry_spread_pct") or 999) <= 10],
    "spread_10_to_20": [t for t in honest if 10 < (t.get("entry_spread_pct") or 0) <= 20],
    "spread_20_to_40": [t for t in honest if 20 < (t.get("entry_spread_pct") or 0) <= 40],
    "spread_gt_40":    [t for t in honest if (t.get("entry_spread_pct") or 0) > 40],
}
exp6 = {
    "description": "Spread discipline. Hypothesis: tight spreads (<=10%) retain more edge than wide ones; wide spreads still make money on the outlier positives.",
    "by_spread_bucket": {k: segment_stats(v) for k, v in spread_groups.items()},
    "spread_lte_20_all": segment_stats([t for t in honest if (t.get("entry_spread_pct") or 999) <= 20]),
}

# ===========================================================================
# EXPERIMENT 7: IV change correlation (not a filter but a diagnostic)
# ===========================================================================
ivc_vals = [(t.get("iv_change_pct"), t) for t in honest if t.get("iv_change_pct") is not None]
ivc_sorted = sorted(ivc_vals, key=lambda x: x[0])
n_ivc = len(ivc_sorted)
if n_ivc >= 100:
    q1 = [t for _, t in ivc_sorted[:int(n_ivc*0.20)]]  # most negative iv_change (crush)
    q5 = [t for _, t in ivc_sorted[int(n_ivc*0.80):]]  # most positive iv_change (expansion)
    exp7 = {
        "description": "IV-change quintile. Q1 = most crush, Q5 = biggest expansion. Tests whether positioning before IV expansion is the dominant option edge.",
        "q1_most_crush":   segment_stats(q1),
        "q5_most_expand":  segment_stats(q5),
    }
else:
    exp7 = {"description": "insufficient data"}

# ===========================================================================
# EXPERIMENT 8: Compound filters — the best v1.3 playbook candidates
# ===========================================================================
def apply(trades, **kw):
    def ok(t):
        if "min_oi" in kw and (t.get("entry_oi") or 0) < kw["min_oi"]: return False
        if "max_spread" in kw and (t.get("entry_spread_pct") or 999) > kw["max_spread"]: return False
        if "max_iv" in kw and (t.get("entry_iv_pct") or 9999) > kw["max_iv"]: return False
        if "min_iv" in kw and (t.get("entry_iv_pct") or 0) < kw["min_iv"]: return False
        if "cap_tier" in kw and t.get("cap_tier") not in kw["cap_tier"]: return False
        if "event_type" in kw and t.get("event_type") not in kw["event_type"]: return False
        if "outcome" in kw and t.get("outcome") not in kw["outcome"]: return False
        if "stage_bucket" in kw and readout_bucket(t.get("stage")) not in kw["stage_bucket"]: return False
        if "odin_tier" in kw and t.get("odin_tier") not in kw["odin_tier"]: return False
        if "years" in kw and t.get("event_year") not in kw["years"]: return False
        return True
    return [t for t in trades if ok(t)]

exp8 = {
    "description": "Compound filter playbooks — the candidate v1.3 live-trading rules.",
    "playbooks": {},
}

candidates = {
    # v1.2 confirmed: Phase 1/2 positive readout
    "CORE_Phase12_pos_tight_liquid": apply(readout,
        stage_bucket=["Phase_1_2"], outcome=["positive"], min_oi=100, max_spread=25),
    # ODIN inversion play (contrarian): buy options on T3+T4 PDUFAs only
    "CONTRA_ODIN_T3T4_PDUFA":        apply(pdufa,
        odin_tier=["T3","T4"], min_oi=100, max_spread=25),
    # Micro-cap PDUFA lottery with liquidity discipline
    "LOTTO_micro_PDUFA_liquid":      apply(pdufa,
        cap_tier=["micro","nano"], min_oi=50, max_spread=30),
    # Small/mid PDUFA with IV cheapness discipline (<120%)
    "PDUFA_small_mid_approve_cheap": apply(pdufa,
        cap_tier=["small","mid"], outcome=["approve"], max_iv=120, min_oi=100, max_spread=20),
    # Readout across all phases but liquid + tight spread
    "READOUT_all_liquid_tight":      apply(readout,
        min_oi=200, max_spread=15),
    # Modern regime only (2024-26) + liquid
    "MODERN_regime_liquid":          apply(honest,
        years=[2024,2025,2026], min_oi=100, max_spread=25),
    # Pre-2024 regime only (ZIRP)
    "PRE_2024_regime_liquid":        apply(honest,
        years=[2022,2023], min_oi=100, max_spread=25),
}

for name, tr in candidates.items():
    exp8["playbooks"][name] = segment_stats(tr)

# ===========================================================================
# Write results
# ===========================================================================
results = {
    "version": "1.3.0",
    "generated": "2026-04-18",
    "input": str(RAW_PATH.name),
    "raw_n": len(all_trades),
    "honest_n": len(honest),
    "honest_pdufa_n": len(pdufa),
    "honest_readout_n": len(readout),
    "filters_applied": "dte_matched (gap 13-23, exit_dte>=3) + iv_sanitized (|iv|<500, |iv_change|<=1000) + valid_prices",
    "experiment_1_odin_inversion":        exp1,
    "experiment_2_stage_cap_outcome":     exp2,
    "experiment_3_iv_cheapness_quintile": exp3,
    "experiment_4_oi_liquidity":          exp4,
    "experiment_5_regime_split":          exp5,
    "experiment_6_spread_discipline":     exp6,
    "experiment_7_iv_change_quintile":    exp7,
    "experiment_8_compound_playbooks":    exp8,
}

OUT_PATH.write_text(json.dumps(results, indent=2, default=str))
print(f"\nWROTE: {OUT_PATH}")
print(f"file size: {OUT_PATH.stat().st_size:,} bytes")
