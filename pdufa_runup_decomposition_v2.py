"""
PDUFA Runup Decomposition v2 (Apr 19, 2026) — WINSORIZED
========================================================

v1 had penny-stock outliers contaminating the raw runup_Xd means (runup_7d had
values of 1000%+ in some rows). v2 applies symmetric winsorization at
[-50%, +100%] on all return columns, and emphasizes the T-90/T-60/T-45/T-25
multi-window columns which are more stable.

Also adds:
- MEDIAN (not just mean) for every segment
- Win-rate (runup > 0) for every segment
- T-25_T-1 focus since it's the cleanest pre-event 24-day window
- Post-event CRL reversal analysis with winsorization

Inputs
------
/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_bifrost_v2.csv

Outputs
-------
pdufa_runup_decomposition_v2_results.json
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

INPUT = Path("/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_bifrost_v2.csv")
OUT   = Path("/sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_decomposition_v2_results.json")

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

# Coerce to numeric and winsorize at [-50%, +100%] — symmetric-ish
WIN_LO, WIN_HI = -0.50, 1.00
for c in ALL_COLS:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df[c + "_w"] = df[c].clip(lower=WIN_LO, upper=WIN_HI)

print(f"rows: {len(df):,}  approvals: {(df.outcome=='APPROVAL').sum():,}  CRLs: {(df.outcome=='CRL').sum():,}")
print(f"winsorization: [{WIN_LO:+.0%}, {WIN_HI:+.0%}]")

# Pre-winsorization sanity check
raw = df["runup_7d"].dropna()
w   = df["runup_7d_w"].dropna()
print(f"runup_7d RAW  mean={raw.mean():+.3%}  median={raw.median():+.3%}  max={raw.max():.3f}  min={raw.min():.3f}")
print(f"runup_7d WIN  mean={w.mean():+.3%}  median={w.median():+.3%}  max={w.max():.3f}  min={w.min():.3f}")
print(f"clipped_hi: {(raw > WIN_HI).sum()}  clipped_lo: {(raw < WIN_LO).sum()}  of {len(raw)}")

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

def segment(sub_df, col, min_n=20):
    vals = pd.to_numeric(sub_df[col], errors="coerce").dropna().values
    if len(vals) < min_n:
        return None
    mean, lo, hi = boot_mean_ci(vals)
    return {
        "n": len(vals),
        "mean": mean,
        "median": round(float(np.median(vals)), 4),
        "ci95_lo": lo, "ci95_hi": hi,
        "pct_pos": round(float((vals > 0).mean()), 4),
    }

def compare(sub_df, col):
    out = {}
    for k, g in sub_df.groupby("outcome"):
        s = segment(g, col)
        if s is not None:
            out[str(k)] = s
    if "APPROVAL" in out and "CRL" in out:
        gap = out["APPROVAL"]["mean"] - out["CRL"]["mean"]
        out["gap_ap_minus_crl"] = round(gap, 4)
        ap = pd.to_numeric(sub_df[sub_df.outcome == "APPROVAL"][col], errors="coerce").dropna().values
        cr = pd.to_numeric(sub_df[sub_df.outcome == "CRL"][col], errors="coerce").dropna().values
        if len(ap) >= 10 and len(cr) >= 10:
            boots = np.empty(1000)
            for i in range(1000):
                ai = rng.integers(0, len(ap), len(ap))
                ci = rng.integers(0, len(cr), len(cr))
                boots[i] = ap[ai].mean() - cr[ci].mean()
            lo, hi = np.percentile(boots, (2.5, 97.5))
            out["gap_ci95"] = [round(float(lo), 4), round(float(hi), 4)]
            # Fraction of boots where AP > CR
            out["p_ap_gt_cr"] = round(float((boots > 0).mean()), 4)
    return out

results = {
    "version": "2.0.0",
    "generated": "2026-04-19",
    "input": str(INPUT.name),
    "winsorization": {"lo": WIN_LO, "hi": WIN_HI},
    "n_total": int(len(df)),
    "n_approval": int((df.outcome == "APPROVAL").sum()),
    "n_crl": int((df.outcome == "CRL").sum()),
    "base_approval_rate": round(float((df.outcome == "APPROVAL").mean()), 4),
}

# =============================================================================
# A. Overall runup (WINSORIZED) by outcome, all windows
# =============================================================================
print("\n[A] WINSORIZED runup by outcome, all windows")
print(f"{'window':14s}  {'AP_mean':>8s}  {'CR_mean':>8s}  {'gap':>8s}  {'gap_CI95':>22s}  {'P(AP>CR)':>10s}")
A = {}
for col in RUNUP_COLS + MULTI_COLS:
    c = col + "_w"
    A[col] = compare(df, c)
    if "APPROVAL" in A[col] and "CRL" in A[col]:
        ap = A[col]["APPROVAL"]["mean"]
        cr = A[col]["CRL"]["mean"]
        gap = A[col]["gap_ap_minus_crl"]
        ci = A[col].get("gap_ci95", ["", ""])
        p = A[col].get("p_ap_gt_cr", "")
        print(f"  {col:12s}  {ap:+.3%}  {cr:+.3%}  {gap:+.3%}  [{ci[0]:+.3%}, {ci[1]:+.3%}]  {p:.2%}")
results["A_winsorized_overall"] = A

# =============================================================================
# B. Runup × mcap_tier × outcome (WINSORIZED, T-25_T-1 focus)
# =============================================================================
print("\n[B] WINSORIZED T-25_T-1 × mcap_tier × outcome")
print(f"{'mcap':24s}  {'n':>5s}  {'AP_mean':>8s}  {'CR_mean':>8s}  {'gap':>8s}  {'gap_CI95':>22s}  {'P(AP>CR)':>10s}")
B = {}
for mc, sub in df.groupby("mcap_tier"):
    if len(sub) < 40:
        continue
    B[str(mc)] = {"n": int(len(sub))}
    for col in ["T-90_T-1", "T-45_T-1", "T-25_T-1", "post_1d"]:
        B[str(mc)][col] = compare(sub, col + "_w")
    s = B[str(mc)]["T-25_T-1"]
    if "APPROVAL" in s and "CRL" in s:
        ap = s["APPROVAL"]["mean"]; cr = s["CRL"]["mean"]
        gap = s["gap_ap_minus_crl"]; ci = s.get("gap_ci95", ["",""])
        p = s.get("p_ap_gt_cr", "")
        print(f"  {str(mc):22s}  {len(sub):5d}  {ap:+.3%}  {cr:+.3%}  {gap:+.3%}  [{ci[0]:+.3%}, {ci[1]:+.3%}]  {p:.2%}")
results["B_mcap_tier"] = B

# =============================================================================
# C. Runup × v9_tier × outcome (ODIN inversion test)
# =============================================================================
print("\n[C] WINSORIZED runup × v9_tier × outcome (ODIN inversion test on equity)")
print(f"{'tier':6s}  {'n':>5s}  {'AR':>6s}  {'T-25 AP':>8s}  {'T-25 CR':>8s}  {'T-25 gap':>9s}  {'p1d AP':>8s}  {'p1d CR':>8s}")
C = {}
for t, sub in df.groupby("v9_tier"):
    if len(sub) < 30:
        continue
    C[str(t)] = {
        "n": int(len(sub)),
        "approval_rate": round(float((sub.outcome == "APPROVAL").mean()), 4),
    }
    for col in ["T-90_T-1", "T-45_T-1", "T-25_T-1", "post_1d", "post_5d"]:
        C[str(t)][col] = compare(sub, col + "_w")
    r = C[str(t)]["T-25_T-1"]
    p = C[str(t)]["post_1d"]
    if "APPROVAL" in r and "CRL" in r:
        ar = C[str(t)]["approval_rate"]
        r_ap = r["APPROVAL"]["mean"]; r_cr = r["CRL"]["mean"]
        p_ap = p["APPROVAL"]["mean"] if "APPROVAL" in p else None
        p_cr = p["CRL"]["mean"] if "CRL" in p else None
        print(f"  {str(t):4s}  {len(sub):5d}  {ar:.2%}  {r_ap:+.3%}  {r_cr:+.3%}  {r_ap - r_cr:+.3%}  {p_ap:+.3%}  {p_cr:+.3%}")
results["C_v9_tier"] = C

# =============================================================================
# D. Runup × TA bucket × outcome
# =============================================================================
print("\n[D] WINSORIZED T-25_T-1 × TA bucket × outcome")
D = {}
for ta, sub in df.groupby("ta_bucket"):
    if len(sub) < 40:
        continue
    D[str(ta)] = {
        "n": int(len(sub)),
        "approval_rate": round(float((sub.outcome == "APPROVAL").mean()), 4),
    }
    for col in ["T-45_T-1", "T-25_T-1", "post_1d"]:
        D[str(ta)][col] = compare(sub, col + "_w")
    s = D[str(ta)]["T-25_T-1"]
    if "APPROVAL" in s and "CRL" in s:
        ap = s["APPROVAL"]["mean"]; cr = s["CRL"]["mean"]
        gap = s["gap_ap_minus_crl"]; ci = s.get("gap_ci95", ["",""])
        p = s.get("p_ap_gt_cr", "")
        print(f"  ta={str(ta):6s} n={len(sub):4d}  AR={D[str(ta)]['approval_rate']:.2%}  AP={ap:+.3%}  CR={cr:+.3%}  gap={gap:+.3%}  CI=[{ci[0]:+.3%}, {ci[1]:+.3%}]  p={p:.2%}")
results["D_ta_bucket"] = D

# =============================================================================
# E. Runup × year × outcome (temporal drift)
# =============================================================================
print("\n[E] WINSORIZED T-25_T-1 × year × outcome")
E = {}
for yr, sub in df.groupby("year"):
    if len(sub) < 30:
        continue
    E[str(int(yr))] = {
        "n": int(len(sub)),
        "approval_rate": round(float((sub.outcome == "APPROVAL").mean()), 4),
    }
    for col in ["T-45_T-1", "T-25_T-1", "post_1d"]:
        E[str(int(yr))][col] = compare(sub, col + "_w")
    s = E[str(int(yr))]["T-25_T-1"]
    if "APPROVAL" in s and "CRL" in s:
        ap = s["APPROVAL"]["mean"]; cr = s["CRL"]["mean"]
        gap = s["gap_ap_minus_crl"]; ci = s.get("gap_ci95", ["",""])
        p = s.get("p_ap_gt_cr", "")
        print(f"  yr={int(yr)} n={len(sub):4d}  AR={E[str(int(yr))]['approval_rate']:.2%}  AP={ap:+.3%}  CR={cr:+.3%}  gap={gap:+.3%}  CI=[{ci[0]:+.3%}, {ci[1]:+.3%}]  p={p:.2%}")
results["E_year"] = E

# =============================================================================
# F. Post-event reversal for CRLs
# =============================================================================
print("\n[F] Post-event (post_1d winsorized) by outcome × mcap_tier")
F = {}
for mc, sub in df.groupby("mcap_tier"):
    if len(sub) < 40:
        continue
    F[str(mc)] = {"n": int(len(sub))}
    for oc in ["APPROVAL", "CRL"]:
        cell = sub[sub.outcome == oc]
        if len(cell) < 10:
            continue
        F[str(mc)][oc] = {
            "n": int(len(cell)),
            "runup_T25_T1_w_mean":    round(float(cell["T-25_T-1_w"].mean()), 4),
            "post_1d_w_mean":         round(float(cell["post_1d_w"].mean()), 4),
            "post_5d_w_mean":         round(float(cell["post_5d_w"].mean()), 4),
            "net_T25_plus_post1_w":   round(float((cell["T-25_T-1_w"] + cell["post_1d_w"]).mean()), 4),
            "pct_post_negative":      round(float((cell["post_1d_w"] < 0).mean()), 4),
            "pct_post_under_minus10": round(float((cell["post_1d_w"] < -0.10).mean()), 4),
        }
    if "APPROVAL" in F[str(mc)] and "CRL" in F[str(mc)]:
        a = F[str(mc)]["APPROVAL"]
        c = F[str(mc)]["CRL"]
        print(f"  {str(mc):22s}  AP n={a['n']:3d}  runup={a['runup_T25_T1_w_mean']:+.3%}  post1d={a['post_1d_w_mean']:+.3%}  net={a['net_T25_plus_post1_w']:+.3%}")
        print(f"  {str(mc):22s}  CR n={c['n']:3d}  runup={c['runup_T25_T1_w_mean']:+.3%}  post1d={c['post_1d_w_mean']:+.3%}  net={c['net_T25_plus_post1_w']:+.3%}")
results["F_post_event_reversal"] = F

# =============================================================================
# G. Peak runup-gap segments (WINSORIZED, T-25_T-1)
# =============================================================================
print("\n[G] Peak runup-gap segments T-25_T-1 (AP−CR), n_ap>=20 & n_cr>=20")
G = []
for mc in df.mcap_tier.dropna().unique():
    for t in df.v9_tier.dropna().unique():
        sub = df[(df.mcap_tier == mc) & (df.v9_tier == t)]
        if len(sub) < 40:
            continue
        n_ap = int((sub.outcome == "APPROVAL").sum())
        n_cr = int((sub.outcome == "CRL").sum())
        if n_ap < 20 or n_cr < 20:
            continue
        s = compare(sub, "T-25_T-1_w")
        if "APPROVAL" in s and "CRL" in s:
            G.append({
                "segment": f"{mc} × {t}",
                "n": int(len(sub)),
                "n_ap": n_ap, "n_cr": n_cr,
                "approval_rate": round(n_ap / (n_ap + n_cr), 4),
                "ap_runup_T25_T1": s["APPROVAL"]["mean"],
                "cr_runup_T25_T1": s["CRL"]["mean"],
                "gap": s["gap_ap_minus_crl"],
                "gap_ci95": s.get("gap_ci95"),
                "p_ap_gt_cr": s.get("p_ap_gt_cr"),
            })
G.sort(key=lambda r: abs(r["gap"]), reverse=True)
for r in G[:15]:
    print(f"  {r['segment']:36s}  n_ap={r['n_ap']:3d} n_cr={r['n_cr']:3d}  AR={r['approval_rate']:.2%}  AP={r['ap_runup_T25_T1']:+.3%}  CR={r['cr_runup_T25_T1']:+.3%}  gap={r['gap']:+.3%}  CI={r.get('gap_ci95')}  p={r.get('p_ap_gt_cr')}")
results["G_peak_gap_segments"] = G

# =============================================================================
# H. CRL runup × crash magnitude: do CRLs that run up more crash harder?
# =============================================================================
print("\n[H] CRL runup × crash magnitude (WINSORIZED)")
crl = df[df.outcome == "CRL"].copy()
crl = crl.dropna(subset=["T-25_T-1_w", "post_1d_w"])
# Quintile the T-25_T-1_w runup
crl["runup_q"] = pd.qcut(crl["T-25_T-1_w"].rank(method="first"), 5, labels=["Q1_low","Q2","Q3","Q4","Q5_high"])
H = {}
for q, sub in crl.groupby("runup_q", observed=True):
    H[str(q)] = {
        "n": int(len(sub)),
        "median_runup": round(float(sub["T-25_T-1_w"].median()), 4),
        "mean_runup":   round(float(sub["T-25_T-1_w"].mean()), 4),
        "mean_post_1d": round(float(sub["post_1d_w"].mean()), 4),
        "median_post_1d": round(float(sub["post_1d_w"].median()), 4),
        "pct_crashed_over_25": round(float((sub["post_1d_w"] < -0.25).mean()), 4),
    }
    print(f"  CRL {q:10s} n={len(sub):3d}  med_runup={sub['T-25_T-1_w'].median():+.3%}  mean_post_1d={sub['post_1d_w'].mean():+.3%}  pct<-25%={(sub['post_1d_w'] < -0.25).mean():.2%}")
results["H_crl_runup_quintile_vs_crash"] = H

# =============================================================================
# I. APPROVAL runup × post-event (reversal or continuation?)
# =============================================================================
print("\n[I] APPROVAL runup × post-event (reversal-on-news risk)")
apv = df[df.outcome == "APPROVAL"].copy()
apv = apv.dropna(subset=["T-25_T-1_w", "post_1d_w"])
apv["runup_q"] = pd.qcut(apv["T-25_T-1_w"].rank(method="first"), 5, labels=["Q1_low","Q2","Q3","Q4","Q5_high"])
I_ = {}
for q, sub in apv.groupby("runup_q", observed=True):
    I_[str(q)] = {
        "n": int(len(sub)),
        "median_runup":  round(float(sub["T-25_T-1_w"].median()), 4),
        "mean_runup":    round(float(sub["T-25_T-1_w"].mean()), 4),
        "mean_post_1d":  round(float(sub["post_1d_w"].mean()), 4),
        "median_post_1d": round(float(sub["post_1d_w"].median()), 4),
        "pct_post_neg":  round(float((sub["post_1d_w"] < 0).mean()), 4),
    }
    print(f"  AP  {q:10s} n={len(sub):3d}  med_runup={sub['T-25_T-1_w'].median():+.3%}  mean_post_1d={sub['post_1d_w'].mean():+.3%}  pct_post_neg={(sub['post_1d_w'] < 0).mean():.2%}")
results["I_approval_runup_quintile_vs_post"] = I_

# Write
OUT.write_text(json.dumps(results, indent=2, default=str))
print(f"\nWROTE: {OUT}")
print(f"size:  {OUT.stat().st_size:,} bytes")
