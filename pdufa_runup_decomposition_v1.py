"""
PDUFA Runup Decomposition v1 (Apr 19, 2026)
===========================================

Does the ODIN v14 engine's optionality inversion (T1+T2 LOSE options, T3+T4 WIN)
hold on EQUITY runup? And do CRLs truly run up as much as approvals across
tiers, caps, TAs, and windows?

Inputs
------
/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_bifrost_v2.csv
  1,705 PDUFA events (2020–2026). Columns include:
    - outcome (APPROVAL / CRL), outcome_bin
    - v5_score, v5_tier, v9_score, v9_tier
    - runup_30d, runup_21d, runup_14d, runup_7d, runup_5d, runup_3d
    - post_1d, post_2d, post_5d
    - vol_ratio, mcap_tier, ta_bucket, ta_risk, crl_rate
    - T-90/T-60/T-45/T-25 × T-7/T-3/T-1 = 12 multi-window runups

Outputs
-------
pdufa_runup_decomposition_v1_results.json

Analyses
--------
A. Overall runup by outcome (APPROVAL vs CRL) across all 6 windows + all 12 multi-windows
B. Runup × mcap_tier × outcome (do micro-caps run up more on CRLs?)
C. Runup × v9_tier × outcome (does the ODIN inversion hold on equity?)
D. Runup × TA bucket × outcome
E. Runup × year × outcome (has the pattern shifted over 2020–2026?)
F. Post-event reversal: for CRLs that ran up, how much did the crash give back?
G. Peak runup-gap segments: where is the APPROVAL − CRL runup gap widest?
H. Vol_ratio × runup interaction (does high vol_ratio pre-event
   predict bigger outcome gap?)

Honesty
-------
Bootstrap 95% CIs on every segment (n_boot=1000, seed=42). Drop segments n<20.
"""

import json
import math
import numpy as np
import pandas as pd
from pathlib import Path

INPUT = Path("/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_bifrost_v2.csv")
OUT   = Path("/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_decomposition_v1_results.json")

df = pd.read_csv(INPUT)
df["pdufa_date"] = pd.to_datetime(df["pdufa_date"], errors="coerce")
df["year"] = df["pdufa_date"].dt.year
df = df.dropna(subset=["outcome", "year"]).copy()

RUNUP_COLS = ["runup_30d", "runup_21d", "runup_14d", "runup_7d", "runup_5d", "runup_3d"]
MULTI_COLS = ["T-90_T-7", "T-90_T-3", "T-90_T-1",
              "T-60_T-7", "T-60_T-3", "T-60_T-1",
              "T-45_T-7", "T-45_T-3", "T-45_T-1",
              "T-25_T-7", "T-25_T-3", "T-25_T-1"]
POST_COLS  = ["post_1d", "post_2d", "post_5d"]
ALL_COLS   = RUNUP_COLS + MULTI_COLS + POST_COLS

# Ensure numeric
for c in ALL_COLS:
    df[c] = pd.to_numeric(df[c], errors="coerce")

print(f"rows: {len(df):,}  approvals: {(df.outcome=='APPROVAL').sum():,}  CRLs: {(df.outcome=='CRL').sum():,}")
print(f"year range: {int(df.year.min())}..{int(df.year.max())}")
print(f"mcap_tier: {df.mcap_tier.value_counts().to_dict()}")
print(f"v9_tier:   {df.v9_tier.value_counts().to_dict()}")

rng = np.random.default_rng(42)

def boot_mean_ci(vals, n_boot=1000, pct=(2.5, 97.5)):
    vals = np.asarray(vals, dtype=float)
    vals = vals[~np.isnan(vals)]
    n = len(vals)
    if n < 5:
        return None, None, None
    mean = float(np.mean(vals))
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        boots[i] = vals[idx].mean()
    lo, hi = np.percentile(boots, pct)
    return round(mean, 4), round(float(lo), 4), round(float(hi), 4)

def segment(vals_series, min_n=20):
    vals = pd.to_numeric(vals_series, errors="coerce").dropna().values
    if len(vals) < min_n:
        return None
    mean, lo, hi = boot_mean_ci(vals)
    return {
        "n": len(vals),
        "mean_pct": mean,
        "median_pct": round(float(np.median(vals)), 4),
        "ci95_lo": lo, "ci95_hi": hi,
        "pct_pos": round(float((vals > 0).mean()), 4),
        "pct_big_up": round(float((vals > 0.10).mean()), 4),  # >+10%
        "pct_big_dn": round(float((vals < -0.10).mean()), 4), # <-10%
    }

def compare(sub_df, col, by="outcome"):
    """Return dict of segment stats keyed by `by` value + the gap."""
    out = {}
    for k, g in sub_df.groupby(by):
        s = segment(g[col])
        if s is not None:
            out[str(k)] = s
    if "APPROVAL" in out and "CRL" in out:
        gap = out["APPROVAL"]["mean_pct"] - out["CRL"]["mean_pct"]
        out["gap_approval_minus_crl_pct"] = round(gap, 4)
        # bootstrap gap CI
        ap = pd.to_numeric(sub_df[sub_df.outcome == "APPROVAL"][col], errors="coerce").dropna().values
        cr = pd.to_numeric(sub_df[sub_df.outcome == "CRL"][col], errors="coerce").dropna().values
        if len(ap) >= 5 and len(cr) >= 5:
            boots = np.empty(1000)
            for i in range(1000):
                ai = rng.integers(0, len(ap), len(ap))
                ci = rng.integers(0, len(cr), len(cr))
                boots[i] = ap[ai].mean() - cr[ci].mean()
            lo, hi = np.percentile(boots, (2.5, 97.5))
            out["gap_ci95"] = [round(float(lo), 4), round(float(hi), 4)]
    return out

results = {
    "version": "1.0.0",
    "generated": "2026-04-19",
    "input": str(INPUT.name),
    "n_total": int(len(df)),
    "n_approval": int((df.outcome == "APPROVAL").sum()),
    "n_crl": int((df.outcome == "CRL").sum()),
    "year_range": [int(df.year.min()), int(df.year.max())],
}

# =============================================================================
# A. Overall runup by outcome (all windows)
# =============================================================================
print("\n[A] Overall runup by outcome, all windows")
A = {}
for col in RUNUP_COLS + MULTI_COLS:
    A[col] = compare(df, col, by="outcome")
    if "APPROVAL" in A[col] and "CRL" in A[col]:
        ap = A[col]["APPROVAL"]["mean_pct"]
        cr = A[col]["CRL"]["mean_pct"]
        gap = A[col]["gap_approval_minus_crl_pct"]
        print(f"  {col:14s}  AP={ap:+.3%}  CRL={cr:+.3%}  gap={gap:+.3%}")
results["A_overall_runup_by_outcome"] = A

# =============================================================================
# B. Runup × mcap_tier × outcome
# =============================================================================
print("\n[B] Runup_7d by mcap_tier × outcome")
B = {}
for mc, sub in df.groupby("mcap_tier"):
    if len(sub) < 40:
        continue
    B[str(mc)] = {
        "n": int(len(sub)),
        "runup_30d": compare(sub, "runup_30d"),
        "runup_7d":  compare(sub, "runup_7d"),
        "runup_3d":  compare(sub, "runup_3d"),
        "T-25_T-1":  compare(sub, "T-25_T-1"),
        "post_1d":   compare(sub, "post_1d"),
    }
    if "APPROVAL" in B[str(mc)]["runup_7d"] and "CRL" in B[str(mc)]["runup_7d"]:
        ap = B[str(mc)]["runup_7d"]["APPROVAL"]["mean_pct"]
        cr = B[str(mc)]["runup_7d"]["CRL"]["mean_pct"]
        print(f"  {mc:8s} n={len(sub):4d}  runup_7d AP={ap:+.3%}  CRL={cr:+.3%}  gap={ap-cr:+.3%}")
results["B_mcap_tier"] = B

# =============================================================================
# C. Runup × v9_tier × outcome (ODIN inversion test on equity)
# =============================================================================
print("\n[C] Runup × v9_tier × outcome (ODIN inversion test)")
C = {}
for t, sub in df.groupby("v9_tier"):
    if len(sub) < 30:
        continue
    C[str(t)] = {
        "n": int(len(sub)),
        "approval_rate": round(float((sub.outcome == "APPROVAL").mean()), 4),
        "runup_30d": compare(sub, "runup_30d"),
        "runup_7d":  compare(sub, "runup_7d"),
        "runup_3d":  compare(sub, "runup_3d"),
        "T-25_T-1":  compare(sub, "T-25_T-1"),
        "post_1d":   compare(sub, "post_1d"),
    }
    ar = C[str(t)]["approval_rate"]
    r7 = C[str(t)]["runup_7d"]
    if "APPROVAL" in r7 and "CRL" in r7:
        ap = r7["APPROVAL"]["mean_pct"]
        cr = r7["CRL"]["mean_pct"]
        print(f"  {t:8s} n={len(sub):4d}  AR={ar:.2%}  runup_7d AP={ap:+.3%}  CRL={cr:+.3%}  gap={ap-cr:+.3%}")
results["C_v9_tier"] = C

# =============================================================================
# D. Runup × TA bucket × outcome
# =============================================================================
print("\n[D] Runup × TA bucket × outcome")
D = {}
for ta, sub in df.groupby("ta_bucket"):
    if len(sub) < 40:
        continue
    D[str(ta)] = {
        "n": int(len(sub)),
        "approval_rate": round(float((sub.outcome == "APPROVAL").mean()), 4),
        "runup_7d": compare(sub, "runup_7d"),
        "runup_30d": compare(sub, "runup_30d"),
    }
    r7 = D[str(ta)]["runup_7d"]
    if "APPROVAL" in r7 and "CRL" in r7:
        ap = r7["APPROVAL"]["mean_pct"]
        cr = r7["CRL"]["mean_pct"]
        print(f"  {ta:8s} n={len(sub):4d}  runup_7d AP={ap:+.3%}  CRL={cr:+.3%}  gap={ap-cr:+.3%}")
results["D_ta_bucket"] = D

# =============================================================================
# E. Runup × year × outcome (has it shifted?)
# =============================================================================
print("\n[E] Runup × year × outcome")
E = {}
for yr, sub in df.groupby("year"):
    if len(sub) < 30:
        continue
    E[str(int(yr))] = {
        "n": int(len(sub)),
        "approval_rate": round(float((sub.outcome == "APPROVAL").mean()), 4),
        "runup_7d": compare(sub, "runup_7d"),
        "runup_30d": compare(sub, "runup_30d"),
        "post_1d":   compare(sub, "post_1d"),
    }
    r7 = E[str(int(yr))]["runup_7d"]
    if "APPROVAL" in r7 and "CRL" in r7:
        ap = r7["APPROVAL"]["mean_pct"]
        cr = r7["CRL"]["mean_pct"]
        print(f"  {int(yr)} n={len(sub):4d}  runup_7d AP={ap:+.3%}  CRL={cr:+.3%}  gap={ap-cr:+.3%}")
results["E_year"] = E

# =============================================================================
# F. Post-event reversal for CRLs — how much of the runup does the crash eat?
# =============================================================================
print("\n[F] CRL post-event reversal analysis")
crl = df[df.outcome == "CRL"].copy()
F = {"overall": {}, "by_mcap_tier": {}}
for col_pair_name, runup_col, post_col in [
    ("T-25_T-1 → post_1d", "T-25_T-1", "post_1d"),
    ("runup_7d → post_1d", "runup_7d", "post_1d"),
    ("runup_30d → post_5d", "runup_30d", "post_5d"),
]:
    pair = crl.dropna(subset=[runup_col, post_col])
    if len(pair) < 30:
        continue
    runup_vals = pair[runup_col].values
    post_vals  = pair[post_col].values
    net_vals   = runup_vals + post_vals  # net return from pre-runup start through post_event
    reversal   = np.where(runup_vals != 0, -post_vals / np.abs(runup_vals), np.nan)  # crash as multiple of runup magnitude
    F["overall"][col_pair_name] = {
        "n": int(len(pair)),
        "mean_runup":   round(float(np.mean(runup_vals)), 4),
        "mean_post":    round(float(np.mean(post_vals)), 4),
        "mean_net":     round(float(np.mean(net_vals)), 4),
        "median_net":   round(float(np.median(net_vals)), 4),
        "pct_net_pos":  round(float((net_vals > 0).mean()), 4),
    }
    print(f"  {col_pair_name:26s}  n={len(pair):3d}  mean_runup={np.mean(runup_vals):+.3%}  mean_post={np.mean(post_vals):+.3%}  mean_net={np.mean(net_vals):+.3%}")

# CRL reversal by mcap_tier (did micro-cap CRLs crash harder?)
for mc, sub in crl.groupby("mcap_tier"):
    pair = sub.dropna(subset=["T-25_T-1", "post_1d"])
    if len(pair) < 20:
        continue
    F["by_mcap_tier"][str(mc)] = {
        "n": int(len(pair)),
        "mean_runup_T25_T1": round(float(pair["T-25_T-1"].mean()), 4),
        "mean_post_1d":      round(float(pair["post_1d"].mean()), 4),
        "mean_net":          round(float((pair["T-25_T-1"] + pair["post_1d"]).mean()), 4),
    }
    print(f"  CRL {mc:8s}  n={len(pair):3d}  runup={pair['T-25_T-1'].mean():+.3%}  post_1d={pair['post_1d'].mean():+.3%}  net={(pair['T-25_T-1']+pair['post_1d']).mean():+.3%}")
results["F_crl_reversal"] = F

# =============================================================================
# G. Peak runup-gap segments — WHERE is approval−crl runup gap widest?
# =============================================================================
print("\n[G] Peak runup-gap segments (approval−CRL runup_7d gap, n>=30)")
G = []
# mcap × v9_tier
for mc in df.mcap_tier.dropna().unique():
    for t in df.v9_tier.dropna().unique():
        sub = df[(df.mcap_tier == mc) & (df.v9_tier == t)]
        if len(sub) < 30:
            continue
        s = compare(sub, "runup_7d")
        if "APPROVAL" in s and "CRL" in s:
            gap = s["gap_approval_minus_crl_pct"]
            G.append({
                "segment": f"mcap={mc}, v9_tier={t}",
                "n": int(len(sub)),
                "n_ap": s["APPROVAL"]["n"],
                "n_cr": s["CRL"]["n"],
                "approval_runup_7d": s["APPROVAL"]["mean_pct"],
                "crl_runup_7d": s["CRL"]["mean_pct"],
                "gap_pct": gap,
                "gap_ci95": s.get("gap_ci95"),
            })
# Sort by |gap|
G.sort(key=lambda r: abs(r["gap_pct"]), reverse=True)
for r in G[:15]:
    print(f"  {r['segment']:36s} n={r['n']:3d} (AP={r['n_ap']}, CR={r['n_cr']})  gap={r['gap_pct']:+.3%}  CI={r.get('gap_ci95')}")
results["G_peak_gap_segments"] = G

# =============================================================================
# H. Vol_ratio × outcome runup interaction
# =============================================================================
print("\n[H] Vol_ratio quintiles × outcome (does high pre-event vol predict bigger gap?)")
df_vr = df.dropna(subset=["vol_ratio", "runup_7d"]).copy()
df_vr["vol_q"] = pd.qcut(df_vr.vol_ratio.rank(method="first"), 5, labels=["Q1_lowest","Q2","Q3","Q4","Q5_highest"])
H = {}
for q, sub in df_vr.groupby("vol_q"):
    H[str(q)] = {
        "n": int(len(sub)),
        "median_vol_ratio": round(float(sub.vol_ratio.median()), 4),
        "approval_rate": round(float((sub.outcome == "APPROVAL").mean()), 4),
        "runup_7d": compare(sub, "runup_7d"),
        "post_1d":  compare(sub, "post_1d"),
    }
    r7 = H[str(q)]["runup_7d"]
    if "APPROVAL" in r7 and "CRL" in r7:
        ap = r7["APPROVAL"]["mean_pct"]
        cr = r7["CRL"]["mean_pct"]
        print(f"  vol_q={q}  n={len(sub):4d}  med_vol={sub.vol_ratio.median():.2f}  AR={(sub.outcome=='APPROVAL').mean():.2%}  AP_r7={ap:+.3%}  CR_r7={cr:+.3%}  gap={ap-cr:+.3%}")
results["H_vol_ratio_quintile"] = H

# Write JSON
OUT.write_text(json.dumps(results, indent=2, default=str))
print(f"\nWROTE: {OUT}")
print(f"size:  {OUT.stat().st_size:,} bytes")
