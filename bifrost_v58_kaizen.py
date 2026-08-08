#!/usr/bin/env python3
"""
BIFROST Explosion v5.8 KAIZEN — Honest Architecture + New Local Features
================================================================================
Approach: Under strict 3-way split (train ≤2023, val 2024, test ≥2025) — the
same discipline v5.6 used — test whether NEW locally-computable features +
architecture sweep can honestly beat v5.6's 0.8861 test AUC baseline.

No lookahead sources. No conference/SENTINEL/short-interest (v5.6 already
tested those; all regressed or were zeroed). No fabricated historical ORATS
(the 3,215-file cache the memo referenced does not exist on disk).

NEW feature families (all computable from existing data files):
  P1. Multi-lookback XBI  — xbi_7d, xbi_14d, xbi_60d returns + xbi_vol_30d
  P2. Time features       — month_sin/cos, day_of_week, quarter_end
  P3. Runup-vs-sector α   — runup_30d − xbi_30d, runup_7d − xbi_7d
  P4. Volume quantiles    — vol_ratio_log, vol_ratio_sq, vol_extreme flag
  P5. Regulatory stacking — desig_count_sq, btd×orphan×pr, gt×nano, ft×safety

Honest methodology:
  • 3-way split: train ≤2023, val 2024, test ≥2025
  • Feature selection + hyperparameter tuning ONLY on VAL
  • TEST touched exactly once at the end
  • Bootstrap 95% CI on test AUC (n_boot=2000, seed=42)

Bar to beat:
  v5.6 honest baseline test AUC = 0.8861
  v5.7 honest final test AUC (minimal baseline)    = 0.7799
  v5.5 DEPLOYED (inflated by greedy selection)     = 0.9487
"""

import json, math, csv
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

try:
    from sklearn.ensemble import GradientBoostingClassifier
    HAS_GBM = True
except Exception:
    HAS_GBM = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except Exception:
    HAS_LGB = False

ROOT = Path("/sessions/confident-serene-ptolemy/mnt/9realms")
BF_CSV = ROOT / "pdufa_runup_bifrost.csv"
BF_CSV_V2 = ROOT / "pdufa_runup_bifrost_v2.csv"
PRICE_CACHE = ROOT / "bifrost_price_cache.json"
SI_SNAP = ROOT / "short_interest_snapshot.json"
ODIN_CSV = ROOT / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
XBI_CACHE = ROOT / "xbi_daily_cache.json"

OUT = ROOT / "bifrost_v58_kaizen_results.json"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def safe_float(x, default=0.0):
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _xbi_return(xbi, date_str, lookback_days):
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0.0
    end_p = None
    for off in range(7):
        d = (dt - timedelta(days=off)).strftime("%Y-%m-%d")
        if d in xbi and xbi[d] is not None:
            end_p = xbi[d]
            break
    start_p = None
    st = dt - timedelta(days=lookback_days)
    for off in range(7):
        d = (st - timedelta(days=off)).strftime("%Y-%m-%d")
        if d in xbi and xbi[d] is not None:
            start_p = xbi[d]
            break
    if end_p and start_p and start_p > 0:
        return (end_p - start_p) / start_p
    return 0.0


def _xbi_vol_30d(xbi, date_str):
    """Annualized 30d vol of daily XBI returns ending at date_str."""
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0.0
    prices = []
    for off in range(40):
        d = (dt - timedelta(days=off)).strftime("%Y-%m-%d")
        if d in xbi and xbi[d] is not None:
            prices.append(xbi[d])
    if len(prices) < 10:
        return 0.0
    prices = list(reversed(prices))
    rets = [(prices[i] - prices[i - 1]) / prices[i - 1]
            for i in range(1, len(prices)) if prices[i - 1] > 0]
    if len(rets) < 5:
        return 0.0
    return float(np.std(rets) * math.sqrt(252))


# ----------------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------------
print("=" * 80)
print("  BIFROST v5.8 KAIZEN — Honest Architecture + New Local Features")
print("=" * 80)

# Use v2 CSV (has v9_score, ta_risk, crl_rate, mcap fields beyond v1)
csv_path = BF_CSV_V2 if BF_CSV_V2.exists() else BF_CSV
print(f"  Loading: {csv_path.name}")
with open(csv_path) as f:
    bf_rows = list(csv.DictReader(f))
print(f"  BIFROST events: {len(bf_rows)}")

with open(PRICE_CACHE) as f:
    price_cache = json.load(f)
print(f"  Price cache: {len(price_cache)} entries")

si_data = {}
si_cutoff = None
if SI_SNAP.exists():
    with open(SI_SNAP) as f:
        si_data = json.load(f)
    if si_data and isinstance(si_data, dict):
        sample = next(iter(si_data.values()), None)
        if isinstance(sample, dict):
            si_cutoff = sample.get("fetch_date")
print(f"  SI snapshot: {len(si_data)} tickers (cutoff {si_cutoff})")

odin_lookup = {}
with open(ODIN_CSV) as f:
    for r in csv.DictReader(f):
        key = (r.get("ticker", "").upper().strip(),
               (r.get("catalyst_date", "") or "")[:10])
        odin_lookup[key] = r
print(f"  ODIN enrichment: {len(odin_lookup)} rows")

with open(XBI_CACHE) as f:
    xbi = json.load(f)
print(f"  XBI cache: {len(xbi)} days")


# ----------------------------------------------------------------------------
# Feature engineering
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Feature engineering")
print("-" * 80)

features = []
skipped = 0
for row in bf_rows:
    ticker = row.get("ticker", "").upper().strip()
    pdufa_date = row.get("pdufa_date", "")
    eve_price = safe_float(row.get("eve_price"), 0.0)
    post_1d = safe_float(row.get("post_1d"), None) if row.get("post_1d") != "" else None
    if not ticker or not pdufa_date or eve_price <= 0 or post_1d is None:
        skipped += 1
        continue

    # SI guard
    use_si = True
    if si_cutoff:
        try:
            if pdufa_date[:10] < si_cutoff:
                use_si = False
        except Exception:
            pass

    v5_score = safe_float(row.get("v5_score"), 0.5)
    surprise = 1.0 - v5_score

    is_penny = 1.0 if eve_price < 5 else 0.0
    is_low = 1.0 if eve_price < 10 else 0.0
    log_price_inv = max(0.0, math.log(1.0 / max(eve_price, 0.01)))

    mcap_tier = row.get("mcap_tier", "") or ""
    is_nano = 1.0 if "Nano" in mcap_tier else 0.0
    is_micro = 1.0 if "Micro" in mcap_tier else 0.0
    is_small = 1.0 if "Small" in mcap_tier else 0.0
    small_cap = is_nano + is_micro + is_small

    cache_key = row.get("cache_key", "") or ""
    prices = price_cache.get(cache_key, {})
    high_52w = 0.0
    if isinstance(prices, dict) and prices:
        pre = []
        for day_str, p in prices.items():
            try:
                if int(day_str) <= -1:
                    pre.append(p)
            except Exception:
                continue
        if pre:
            high_52w = max(pre)

    compression = eve_price / high_52w if high_52w > 0 else 1.0
    drawdown = (eve_price - high_52w) / high_52w if high_52w > 0 else 0.0
    drawdown = max(-1.0, min(0.0, drawdown))

    runup_30d = safe_float(row.get("runup_30d"), 0.0)
    runup_14d = safe_float(row.get("runup_14d"), 0.0)
    runup_7d = safe_float(row.get("runup_7d"), 0.0)
    runup_3d = safe_float(row.get("runup_3d"), 0.0)
    vol_ratio = safe_float(row.get("vol_ratio"), 1.0)

    beaten_30d = 1.0 if runup_30d < -15 else 0.0
    beaten_surprise = beaten_30d * surprise
    compression_x_surprise = (1.0 - compression) * surprise if high_52w > 0 else 0.0

    si = si_data.get(ticker, {}) if use_si else {}
    if isinstance(si, dict) and "error" in si:
        si = {}
    pct_float_short = safe_float(si.get("short_pct_float"), 0.0) if use_si else 0.0
    dtc_val = safe_float(si.get("short_ratio"), 0.0) if use_si else 0.0
    float_shares = safe_float(si.get("float_shares"), 0.0) if use_si else 0.0
    log_float_inv = math.log(1e9 / max(float_shares, 1)) if (use_si and float_shares > 0) else 0.0
    short_high = 1.0 if (use_si and pct_float_short >= 0.15) else 0.0

    drift_mag = abs(runup_30d)
    drift_7d = abs(runup_7d)

    xbi_30d = _xbi_return(xbi, pdufa_date, 30)
    xbi_7d = _xbi_return(xbi, pdufa_date, 7)
    xbi_14d = _xbi_return(xbi, pdufa_date, 14)
    xbi_60d = _xbi_return(xbi, pdufa_date, 60)
    xbi_vol = _xbi_vol_30d(xbi, pdufa_date)
    xbi_x_surprise = xbi_30d * surprise
    xbi_x_small = xbi_30d * small_cap

    odin_key = (ticker, pdufa_date[:10])
    o = odin_lookup.get(odin_key, {})

    def otrue(k):
        return 1.0 if str(o.get(k, "")).lower() in ("true", "1") else 0.0

    btd = otrue("btd")
    orphan = otrue("orphan")
    priority_rev = otrue("priority_review")
    fast_track = otrue("fast_track")
    gene_th = otrue("gene_therapy")
    is_nda = 1.0 if str(o.get("application_type", "")).upper().strip() == "NDA" else 0.0
    is_bla = 1.0 if str(o.get("application_type", "")).upper().strip() == "BLA" else 0.0
    ppm_flag = otrue("ppm_flag")
    psychedelics = otrue("psychedelics")

    prior_crl_count = int(safe_float(o.get("prior_crl_count"), 0))
    prior_crl_bin = 1.0 if prior_crl_count > 0 else 0.0
    resub_class = int(safe_float(o.get("resubmission_class"), 0))
    is_resub = 1.0 if resub_class > 0 else 0.0
    resub1 = 1.0 if resub_class == 1 else 0.0
    resub2 = 1.0 if resub_class == 2 else 0.0
    spa = int(safe_float(o.get("sponsor_prior_approvals"), 5))
    sponsor_naive = 1.0 if spa == 0 else 0.0
    log_spa = math.log1p(spa)
    sponsor_exp = 1.0 if spa >= 6 else 0.0
    safety_sev = int(safe_float(o.get("safety_signal_severity"), 0))
    safety_high = 1.0 if safety_sev > 1 else 0.0
    ta_vh = otrue("ta_very_high_risk")
    hist_crl = safe_float(o.get("historical_crl_rate"), 0.32)
    desig_count = btd + orphan + priority_rev + fast_track

    vol_high = 1.0 if vol_ratio > 1.5 else 0.0

    # v5.4 interactions
    crl_count_x_small = float(prior_crl_count) * small_cap
    resub_x_surprise = is_resub * surprise
    naive_x_small = sponsor_naive * (is_nano + is_micro)
    drawdown_x_vol = abs(drawdown) * vol_ratio
    ta_vh_x_small = ta_vh * small_cap

    cand_orphan_x_runup_7d_val = orphan * runup_7d
    cand_resub1_x_vol_high = resub1 * vol_high
    cand_ppm_x_runup_30d = ppm_flag * runup_30d
    cand_spa_log_x_is_small = log_spa * is_small
    cand_ppm_x_dtc = ppm_flag * dtc_val
    cand_safety_h_x_dtc = safety_high * dtc_val
    cand_crl_rate_x_is_small = hist_crl * is_small
    cand_resub2_x_log_float_inv = resub2 * log_float_inv
    cand_ta_vh_x_log_float_inv = ta_vh * log_float_inv
    cand_resub1_x_beaten = resub1 * beaten_30d
    cand_ppm_x_is_micro = ppm_flag * is_micro
    cand_btd_x_is_penny_val = btd * is_penny
    cand_resub2_x_xbi_30d = resub2 * xbi_30d
    cand_safety_h_x_short_high = safety_high * short_high
    cand_resub2_x_si_pct = resub2 * pct_float_short
    cand_resub1_x_is_micro = resub1 * is_micro
    cand_ft_x_drawdown = fast_track * abs(drawdown)
    cand_ft_x_is_small = fast_track * is_small
    cand_safety_h_x_is_penny_val = safety_high * is_penny
    cand_fast_track = fast_track
    cand_gene_th_x_small_cap = gene_th * small_cap
    cand_resub2_x_runup_7d_val = resub2 * runup_7d
    t90_t7 = safe_float(row.get("T-90_T-7"), 0.0)

    # v5.8 NEW candidate features
    v58_xbi_7d = xbi_7d
    v58_xbi_14d = xbi_14d
    v58_xbi_60d = xbi_60d
    v58_xbi_vol_30d = xbi_vol
    v58_xbi_x_nano = xbi_30d * is_nano
    v58_xbi_x_micro = xbi_30d * is_micro

    # Time features
    try:
        dt = datetime.strptime(pdufa_date[:10], "%Y-%m-%d")
        month_num = dt.month
        dow = dt.weekday()   # Monday=0
        v58_month_sin = math.sin(2 * math.pi * month_num / 12.0)
        v58_month_cos = math.cos(2 * math.pi * month_num / 12.0)
        v58_dow = float(dow)
        v58_quarter_end = 1.0 if month_num in (3, 6, 9, 12) else 0.0
        v58_is_q4 = 1.0 if month_num in (10, 11, 12) else 0.0
    except Exception:
        v58_month_sin = v58_month_cos = v58_dow = 0.0
        v58_quarter_end = v58_is_q4 = 0.0

    # Alpha (stock - XBI)
    v58_alpha_30d = runup_30d - xbi_30d * 100
    v58_alpha_7d = runup_7d - xbi_7d * 100
    v58_alpha_14d = runup_14d - xbi_14d * 100

    # Volume nonlinear transforms
    v58_vol_ratio_log = math.log1p(max(vol_ratio - 1.0, -0.99))
    v58_vol_ratio_sq = vol_ratio * vol_ratio
    v58_vol_extreme = 1.0 if vol_ratio > 3.0 else 0.0
    v58_vol_quiet = 1.0 if vol_ratio < 0.7 else 0.0

    # Regulatory stacking
    v58_desig_count_sq = desig_count * desig_count
    v58_btd_x_orphan = btd * orphan
    v58_btd_x_pr = btd * priority_rev
    v58_pr_x_ft = priority_rev * fast_track
    v58_all_desig = 1.0 if desig_count >= 3 else 0.0
    v58_ft_x_safety = fast_track * safety_high
    v58_gt_x_nano = gene_th * is_nano
    v58_psych_x_micro = psychedelics * is_micro
    v58_hist_crl_x_resub = hist_crl * is_resub
    v58_hist_crl_x_small_x_resub = hist_crl * small_cap * is_resub
    v58_priorcrl_x_surprise = prior_crl_bin * surprise

    # Runup non-linear
    v58_runup_7d_sq = runup_7d * runup_7d
    v58_runup_30d_sq = runup_30d * runup_30d
    v58_abs_runup_30d = abs(runup_30d)
    v58_abs_runup_7d = abs(runup_7d)

    # Surprise polynomial
    v58_surprise_sq = surprise * surprise
    v58_surprise_cube = surprise ** 3

    # Compression interactions
    v58_drawdown_x_small = abs(drawdown) * small_cap
    v58_compression_x_nano = (1.0 - compression) * is_nano

    # Year gets recorded for split
    pdufa_year = pdufa_date[:4]
    if pdufa_year <= "2023":
        split = "train"
    elif pdufa_year == "2024":
        split = "val"
    elif pdufa_year >= "2025":
        split = "test"
    else:
        continue

    big_move = 1.0 if abs(post_1d) > 25 else 0.0

    features.append({
        "ticker": ticker,
        "pdufa_date": pdufa_date[:10],
        "eve_price": eve_price,
        "post_1d": post_1d,
        "big_move": big_move,
        "split": split,
        # v5.4 base features (57)
        "surprise_factor": surprise,
        "is_penny": is_penny,
        "is_low_price": is_low,
        "log_price_inv": log_price_inv,
        "is_nano": is_nano, "is_micro": is_micro, "is_small": is_small,
        "surprise_x_small_cap": surprise * (is_nano + is_micro),
        "surprise_x_low_price": surprise * is_low,
        "price_compression": compression,
        "drawdown_pct": drawdown,
        "beaten_down_30d": beaten_30d,
        "beaten_surprise": beaten_surprise,
        "compression_x_surprise": compression_x_surprise,
        "vol_ratio": vol_ratio,
        "runup_30d": runup_30d,
        "v5_score": v5_score,
        "log_float_inv": log_float_inv,
        "pct_float_short": pct_float_short,
        "short_high": short_high,
        "days_to_cover": dtc_val,
        "drift_magnitude": drift_mag,
        "xbi_return_30d": xbi_30d,
        "xbi_x_surprise": xbi_x_surprise,
        "xbi_x_small": xbi_x_small,
        "vol_high": vol_high,
        "crl_count_x_small": crl_count_x_small,
        "is_resub": is_resub,
        "drift_7d": drift_7d,
        "resub_x_surprise": resub_x_surprise,
        "naive_x_small": naive_x_small,
        "drawdown_x_vol": drawdown_x_vol,
        "runup_7d": runup_7d,
        "ta_vh_x_small": ta_vh_x_small,
        "cand_orphan_x_runup_7d_val": cand_orphan_x_runup_7d_val,
        "cand_resub1_x_vol_high": cand_resub1_x_vol_high,
        "cand_ppm_x_runup_30d": cand_ppm_x_runup_30d,
        "cand_spa_log_x_is_small": cand_spa_log_x_is_small,
        "cand_ppm_x_dtc": cand_ppm_x_dtc,
        "cand_safety_h_x_dtc": cand_safety_h_x_dtc,
        "cand_crl_rate_x_is_small": cand_crl_rate_x_is_small,
        "cand_resub2_x_log_float_inv": cand_resub2_x_log_float_inv,
        "cand_ta_vh_x_log_float_inv": cand_ta_vh_x_log_float_inv,
        "cand_resub1_x_beaten": cand_resub1_x_beaten,
        "cand_ppm_x_is_micro": cand_ppm_x_is_micro,
        "cand_btd_x_is_penny_val": cand_btd_x_is_penny_val,
        "cand_resub2_x_xbi_30d": cand_resub2_x_xbi_30d,
        "cand_safety_h_x_short_high": cand_safety_h_x_short_high,
        "cand_resub2_x_si_pct": cand_resub2_x_si_pct,
        "cand_resub1_x_is_micro": cand_resub1_x_is_micro,
        "cand_ft_x_drawdown": cand_ft_x_drawdown,
        "cand_ft_x_is_small": cand_ft_x_is_small,
        "cand_safety_h_x_is_penny_val": cand_safety_h_x_is_penny_val,
        "cand_fast_track": cand_fast_track,
        "cand_gene_th_x_small_cap": cand_gene_th_x_small_cap,
        "cand_resub2_x_runup_7d_val": cand_resub2_x_runup_7d_val,
        "cand_t90_t7": t90_t7,
        # v5.8 NEW candidates
        "v58_xbi_7d": v58_xbi_7d,
        "v58_xbi_14d": v58_xbi_14d,
        "v58_xbi_60d": v58_xbi_60d,
        "v58_xbi_vol_30d": v58_xbi_vol_30d,
        "v58_xbi_x_nano": v58_xbi_x_nano,
        "v58_xbi_x_micro": v58_xbi_x_micro,
        "v58_month_sin": v58_month_sin,
        "v58_month_cos": v58_month_cos,
        "v58_dow": v58_dow,
        "v58_quarter_end": v58_quarter_end,
        "v58_is_q4": v58_is_q4,
        "v58_alpha_30d": v58_alpha_30d,
        "v58_alpha_7d": v58_alpha_7d,
        "v58_alpha_14d": v58_alpha_14d,
        "v58_vol_ratio_log": v58_vol_ratio_log,
        "v58_vol_ratio_sq": v58_vol_ratio_sq,
        "v58_vol_extreme": v58_vol_extreme,
        "v58_vol_quiet": v58_vol_quiet,
        "v58_desig_count_sq": v58_desig_count_sq,
        "v58_btd_x_orphan": v58_btd_x_orphan,
        "v58_btd_x_pr": v58_btd_x_pr,
        "v58_pr_x_ft": v58_pr_x_ft,
        "v58_all_desig": v58_all_desig,
        "v58_ft_x_safety": v58_ft_x_safety,
        "v58_gt_x_nano": v58_gt_x_nano,
        "v58_psych_x_micro": v58_psych_x_micro,
        "v58_hist_crl_x_resub": v58_hist_crl_x_resub,
        "v58_hist_crl_x_small_x_resub": v58_hist_crl_x_small_x_resub,
        "v58_priorcrl_x_surprise": v58_priorcrl_x_surprise,
        "v58_runup_7d_sq": v58_runup_7d_sq,
        "v58_runup_30d_sq": v58_runup_30d_sq,
        "v58_abs_runup_30d": v58_abs_runup_30d,
        "v58_abs_runup_7d": v58_abs_runup_7d,
        "v58_surprise_sq": v58_surprise_sq,
        "v58_surprise_cube": v58_surprise_cube,
        "v58_drawdown_x_small": v58_drawdown_x_small,
        "v58_compression_x_nano": v58_compression_x_nano,
    })

print(f"  Events built: {len(features)}  (skipped {skipped})")

V54_BASE = [
    "surprise_factor", "is_penny", "is_low_price", "log_price_inv",
    "is_nano", "is_micro", "is_small",
    "surprise_x_small_cap", "surprise_x_low_price",
    "price_compression", "drawdown_pct", "beaten_down_30d",
    "beaten_surprise", "compression_x_surprise",
    "vol_ratio", "runup_30d", "v5_score",
    "log_float_inv", "pct_float_short", "short_high", "days_to_cover",
    "drift_magnitude", "xbi_return_30d", "xbi_x_surprise",
    "xbi_x_small", "vol_high", "crl_count_x_small", "is_resub",
    "drift_7d", "resub_x_surprise", "naive_x_small",
    "drawdown_x_vol", "runup_7d", "ta_vh_x_small",
    "cand_orphan_x_runup_7d_val", "cand_resub1_x_vol_high",
    "cand_ppm_x_runup_30d", "cand_spa_log_x_is_small",
    "cand_ppm_x_dtc", "cand_safety_h_x_dtc",
    "cand_crl_rate_x_is_small", "cand_resub2_x_log_float_inv",
    "cand_ta_vh_x_log_float_inv", "cand_resub1_x_beaten",
    "cand_ppm_x_is_micro", "cand_btd_x_is_penny_val",
    "cand_resub2_x_xbi_30d", "cand_safety_h_x_short_high",
    "cand_resub2_x_si_pct", "cand_resub1_x_is_micro",
    "cand_ft_x_drawdown", "cand_ft_x_is_small",
    "cand_safety_h_x_is_penny_val", "cand_fast_track",
    "cand_gene_th_x_small_cap", "cand_resub2_x_runup_7d_val",
    "cand_t90_t7",
]

V58_CANDIDATES = [
    "v58_xbi_7d", "v58_xbi_14d", "v58_xbi_60d", "v58_xbi_vol_30d",
    "v58_xbi_x_nano", "v58_xbi_x_micro",
    "v58_month_sin", "v58_month_cos", "v58_dow",
    "v58_quarter_end", "v58_is_q4",
    "v58_alpha_30d", "v58_alpha_7d", "v58_alpha_14d",
    "v58_vol_ratio_log", "v58_vol_ratio_sq", "v58_vol_extreme", "v58_vol_quiet",
    "v58_desig_count_sq", "v58_btd_x_orphan", "v58_btd_x_pr", "v58_pr_x_ft",
    "v58_all_desig", "v58_ft_x_safety", "v58_gt_x_nano", "v58_psych_x_micro",
    "v58_hist_crl_x_resub", "v58_hist_crl_x_small_x_resub", "v58_priorcrl_x_surprise",
    "v58_runup_7d_sq", "v58_runup_30d_sq", "v58_abs_runup_30d", "v58_abs_runup_7d",
    "v58_surprise_sq", "v58_surprise_cube",
    "v58_drawdown_x_small", "v58_compression_x_nano",
]


# ----------------------------------------------------------------------------
# 3-way split
# ----------------------------------------------------------------------------
train = [f for f in features if f["split"] == "train"]
val = [f for f in features if f["split"] == "val"]
test = [f for f in features if f["split"] == "test"]

print(f"  Train (<=2023): {len(train)}  explosion_rate={sum(f['big_move'] for f in train) / max(len(train), 1):.3f}")
print(f"  Val   (2024):   {len(val)}  explosion_rate={sum(f['big_move'] for f in val) / max(len(val), 1):.3f}")
print(f"  Test  (>=2025): {len(test)}  explosion_rate={sum(f['big_move'] for f in test) / max(len(test), 1):.3f}")


def build_matrix(rows, cols):
    return np.array([[safe_float(r.get(c, 0.0), 0.0) for c in cols] for r in rows], dtype=float)


def fit_ridge_auc(train_rows, val_rows, cols, C=0.10):
    X_tr = build_matrix(train_rows, cols)
    X_va = build_matrix(val_rows, cols)
    y_tr = np.array([r["big_move"] for r in train_rows])
    y_va = np.array([r["big_move"] for r in val_rows])
    sc = StandardScaler()
    X_tr = sc.fit_transform(X_tr)
    X_va = sc.transform(X_va)
    clf = LogisticRegression(C=C, penalty="l2", solver="lbfgs",
                             max_iter=1000, random_state=42)
    clf.fit(X_tr, y_tr)
    return roc_auc_score(y_va, clf.predict_proba(X_va)[:, 1])


# ----------------------------------------------------------------------------
# Baseline recalc (v5.4 features on 3-way split)
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Baseline: v5.4 features on train, report val+test")
print("-" * 80)

base_C = 0.10
val_auc_base = fit_ridge_auc(train, val, V54_BASE, C=base_C)
print(f"  v5.4 on train, val AUC = {val_auc_base:.4f}")

# C sweep on VAL only
C_sweep = [0.01, 0.03, 0.05, 0.10, 0.25, 0.50, 1.0]
best_C, best_val = base_C, val_auc_base
for C in C_sweep:
    v = fit_ridge_auc(train, val, V54_BASE, C=C)
    print(f"    C={C:<6}: val AUC = {v:.4f}")
    if v > best_val:
        best_val, best_C = v, C
print(f"  C sweep winner: C={best_C}  val AUC={best_val:.4f}")


# ----------------------------------------------------------------------------
# v5.8 greedy forward selection on VAL only
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  v5.8 greedy forward selection on VAL (cap 10 rounds, Δval >= +0.002)")
print("-" * 80)

selected = list(V54_BASE)
pool = list(V58_CANDIDATES)
current_val = best_val
gains = []

MAX_ROUNDS = 10
GATE = 0.002

for rnd in range(MAX_ROUNDS):
    best_gain = 0.0
    best_feat = None
    best_after = current_val
    for feat in pool:
        if feat in selected:
            continue
        trial = selected + [feat]
        try:
            v = fit_ridge_auc(train, val, trial, C=best_C)
        except Exception:
            continue
        if v > best_after:
            best_after = v
            best_feat = feat
            best_gain = v - current_val
    if best_feat is None or best_gain < GATE:
        print(f"  round {rnd + 1}: no candidate meets gate (best gain {best_gain:+.4f})")
        break
    selected.append(best_feat)
    pool.remove(best_feat)
    gains.append({"feature": best_feat,
                  "val_auc_after": round(best_after, 4),
                  "val_delta": round(best_after - current_val, 4)})
    print(f"  round {rnd + 1}: +{best_feat:<40}  val AUC = {best_after:.4f}  (Δ={best_after - current_val:+.4f})")
    current_val = best_after


# ----------------------------------------------------------------------------
# Architecture sweep — Ridge only vs Ridge+GBM vs Ridge+GBM+LGB on VAL
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Architecture sweep on VAL (Ridge only vs ensemble)")
print("-" * 80)


def fit_ensemble(train_rows, val_rows, cols, C, w_r=1.0, w_g=0.0, w_l=0.0,
                 gbm_trees=200, lgb_trees=300):
    X_tr = build_matrix(train_rows, cols)
    X_va = build_matrix(val_rows, cols)
    y_tr = np.array([r["big_move"] for r in train_rows])
    y_va = np.array([r["big_move"] for r in val_rows])

    sc = StandardScaler()
    X_tr_s = sc.fit_transform(X_tr)
    X_va_s = sc.transform(X_va)

    ridge = LogisticRegression(C=C, penalty="l2", solver="lbfgs",
                               max_iter=1000, random_state=42)
    ridge.fit(X_tr_s, y_tr)
    p_r = ridge.predict_proba(X_va_s)[:, 1]

    p_g = np.zeros_like(p_r)
    if w_g > 0 and HAS_GBM:
        gbm = GradientBoostingClassifier(n_estimators=gbm_trees, max_depth=3,
                                          learning_rate=0.03, random_state=42)
        gbm.fit(X_tr, y_tr)
        p_g = gbm.predict_proba(X_va)[:, 1]

    p_l = np.zeros_like(p_r)
    if w_l > 0 and HAS_LGB:
        lgm = lgb.LGBMClassifier(n_estimators=lgb_trees, max_depth=3,
                                 learning_rate=0.03, random_state=42, verbose=-1)
        lgm.fit(X_tr, y_tr)
        p_l = lgm.predict_proba(X_va)[:, 1]

    tot = w_r + w_g + w_l
    p_ens = (w_r * p_r + w_g * p_g + w_l * p_l) / tot
    return roc_auc_score(y_va, p_ens), ridge, (p_r, p_g, p_l, tot)


arch_configs = [
    (1.0, 0.0, 0.0),
    (0.9, 0.05, 0.05),
    (0.8, 0.1, 0.1),
    (0.7, 0.15, 0.15),
    (0.6, 0.2, 0.2),
    (0.5, 0.25, 0.25),
]

arch_results = []
for (wr, wg, wl) in arch_configs:
    if wg > 0 and not HAS_GBM:
        continue
    if wl > 0 and not HAS_LGB:
        continue
    auc, _, _ = fit_ensemble(train, val, selected, C=best_C, w_r=wr, w_g=wg, w_l=wl)
    arch_results.append({"weights": [wr, wg, wl], "val_auc": round(auc, 4)})
    print(f"  R={wr:.2f} G={wg:.2f} L={wl:.2f}: val AUC = {auc:.4f}")

best_arch = max(arch_results, key=lambda d: d["val_auc"])
print(f"  BEST arch: weights={best_arch['weights']}  val AUC={best_arch['val_auc']}")


# ----------------------------------------------------------------------------
# ONE-SHOT final test (touched once)
# ----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("  FINAL TEST (touched once)")
print("=" * 80)

# Fit on train+val, predict on test with best config
trainval = train + val
X_trv = build_matrix(trainval, selected)
X_te = build_matrix(test, selected)
y_trv = np.array([r["big_move"] for r in trainval])
y_te = np.array([r["big_move"] for r in test])

sc = StandardScaler()
X_trv_s = sc.fit_transform(X_trv)
X_te_s = sc.transform(X_te)

ridge = LogisticRegression(C=best_C, penalty="l2", solver="lbfgs",
                           max_iter=1000, random_state=42)
ridge.fit(X_trv_s, y_trv)
p_te_r = ridge.predict_proba(X_te_s)[:, 1]

wr, wg, wl = best_arch["weights"]
p_te_g = np.zeros_like(p_te_r)
if wg > 0 and HAS_GBM:
    gbm = GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                      learning_rate=0.03, random_state=42)
    gbm.fit(X_trv, y_trv)
    p_te_g = gbm.predict_proba(X_te)[:, 1]
p_te_l = np.zeros_like(p_te_r)
if wl > 0 and HAS_LGB:
    lgm = lgb.LGBMClassifier(n_estimators=300, max_depth=3,
                             learning_rate=0.03, random_state=42, verbose=-1)
    lgm.fit(X_trv, y_trv)
    p_te_l = lgm.predict_proba(X_te)[:, 1]

tot = wr + wg + wl
p_te_final = (wr * p_te_r + wg * p_te_g + wl * p_te_l) / tot

final_test_auc_ridge = roc_auc_score(y_te, p_te_r)
final_test_auc_ens = roc_auc_score(y_te, p_te_final)

# Bootstrap CI on ensemble test AUC
rng = np.random.default_rng(42)
n_te = len(y_te)
boot_ens, boot_rid = [], []
for _ in range(2000):
    idx = rng.integers(0, n_te, n_te)
    if len(np.unique(y_te[idx])) < 2:
        continue
    boot_ens.append(roc_auc_score(y_te[idx], p_te_final[idx]))
    boot_rid.append(roc_auc_score(y_te[idx], p_te_r[idx]))
boot_ens.sort()
boot_rid.sort()


def ci(b):
    if not b:
        return (None, None)
    lo = b[int(0.025 * len(b))]
    hi = b[int(0.975 * len(b)) - 1]
    return (lo, hi)


ci_lo_e, ci_hi_e = ci(boot_ens)
ci_lo_r, ci_hi_r = ci(boot_rid)

V56_HONEST_BAR = 0.8861

print(f"  Final test AUC (Ridge only):        {final_test_auc_ridge:.4f}  CI95=[{ci_lo_r:.4f}, {ci_hi_r:.4f}]")
print(f"  Final test AUC (Ridge+GBM+LGB ens): {final_test_auc_ens:.4f}  CI95=[{ci_lo_e:.4f}, {ci_hi_e:.4f}]")
print(f"  v5.6 honest bar:                    {V56_HONEST_BAR:.4f}")
print(f"  Δ vs bar (ensemble):                {(final_test_auc_ens - V56_HONEST_BAR) * 100:+.2f} pp")

if final_test_auc_ens > V56_HONEST_BAR + 0.002:
    verdict = "PROMOTE — v5.8 beats v5.6 honest bar"
elif final_test_auc_ens > V56_HONEST_BAR - 0.005:
    verdict = "FLAT — within noise of v5.6 honest bar; v5.5 remains deployed"
else:
    verdict = "REGRESSION — hold v5.5 deployment"
print(f"  VERDICT: {verdict}")


# ----------------------------------------------------------------------------
# Save
# ----------------------------------------------------------------------------
result = {
    "version": "5.8.0",
    "generated_utc": datetime.utcnow().isoformat() + "Z",
    "methodology": {
        "split": "3-way (train <=2023 / val 2024 / test >=2025)",
        "feature_selection": "VAL-only greedy forward, gate Δval >= +0.002",
        "hyperparameter_tuning": "VAL-only C sweep + arch weight sweep",
        "test_touches": 1,
        "bootstrap_boot_n": 2000,
    },
    "input": csv_path.name,
    "n_events": len(features),
    "split_counts": {"train": len(train), "val": len(val), "test": len(test)},
    "train_explosion_rate": round(sum(f["big_move"] for f in train) / max(len(train), 1), 4),
    "val_explosion_rate":   round(sum(f["big_move"] for f in val) / max(len(val), 1), 4),
    "test_explosion_rate":  round(sum(f["big_move"] for f in test) / max(len(test), 1), 4),
    "baseline_features_n": len(V54_BASE),
    "v58_candidates_n": len(V58_CANDIDATES),
    "v58_candidates": V58_CANDIDATES,
    "baseline_val_auc_initial":  round(val_auc_base, 4),
    "baseline_val_auc_best_C":   round(best_val, 4),
    "best_C": best_C,
    "C_sweep_val_aucs": [{"C": c, "val_auc": round(fit_ridge_auc(train, val, V54_BASE, C=c), 4)} for c in C_sweep],
    "greedy_selections": gains,
    "final_n_features": len(selected),
    "final_feature_list": selected,
    "arch_sweep_val_aucs": arch_results,
    "best_arch_weights": best_arch["weights"],
    "final_test_auc_ridge_only": round(final_test_auc_ridge, 4),
    "final_test_auc_ensemble":   round(final_test_auc_ens, 4),
    "final_test_auc_ridge_ci95":  [round(ci_lo_r, 4) if ci_lo_r else None,
                                    round(ci_hi_r, 4) if ci_hi_r else None],
    "final_test_auc_ens_ci95":    [round(ci_lo_e, 4) if ci_lo_e else None,
                                    round(ci_hi_e, 4) if ci_hi_e else None],
    "v56_honest_bar": V56_HONEST_BAR,
    "v55_deployed_inflated": 0.9487,
    "delta_vs_v56_bp_ensemble": round((final_test_auc_ens - V56_HONEST_BAR) * 10000),
    "verdict": verdict,
    "has_gbm": HAS_GBM,
    "has_lgb": HAS_LGB,
}

OUT.write_text(json.dumps(result, indent=2, default=str))
print(f"\n  WROTE {OUT}")
print("=" * 80)
