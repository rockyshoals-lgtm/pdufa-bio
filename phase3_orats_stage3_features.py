#!/usr/bin/env python3
"""
BIFROST Explosion v5.9 KAIZEN — Phase 3 Stage 3
================================================================================
Honest evaluation of ORATS historical options chain features (T-14, T-7, T-1
snapshots) layered on top of BIFROST v5.8's final 60-feature baseline.

Target: |post_1d| > 25% (explosion). Bar to beat: v5.6/v5.8 honest test AUC
0.8861 with bootstrap CI lower bound above the bar.

Honest methodology:
  • 3-way split:        train <=2023, val 2024, test >=2025
  • Baseline:           v5.8 final 60 features (V54_BASE 57 + 3 v58 survivors)
  • Best C seed:        v5.8 winner C=0.01 (re-sweep in case ORATS shifts optimum)
  • Feature selection:  VAL-only greedy forward on ORATS candidates, gate >= +0.002
  • Architecture sweep: Ridge only vs Ridge+GBM+LGB, 6 weight configs, VAL only
  • Test touched once
  • Bootstrap CI n=2000, seed=42

ORATS feature families (at T-14, T-7, T-1 per event):
  A. IV term structure (summaries)
       iv10d/20d/30d/60d/90d/1y, contango, skewing, impliedMove, rVol30, iv/rv
  B. Skew / risk reversal (summaries)
       dlt5Iv30d, dlt25Iv30d, dlt75Iv30d, dlt95Iv30d, 25d-75d spread, 5d-95d spread
  C. Forward curve (summaries)
       fwd30_20, fwd60_30, fwd90_60, fwd90_30, fwd180_90
  D. IV rank / percentile (ivrank)
       iv, ivRank1m, ivPct1m, ivRank1y, ivPct1y
  E. Borrow / confidence / risk-free (summaries)
       borrow30, borrow2y, confidence, riskFree30, impliedEarningsMove
  F. Cross-snapshot deltas
       iv30d_delta_14_7, iv30d_delta_7_1, iv30d_delta_14_1
       iv60d / iv90d / ivRank1y / skewing same
  G. Strikes aggregates (T-14 and T-1 only, per Stage 2 spec)
       total_call_volume, total_put_volume, cp_vol_ratio
       total_call_oi, total_put_oi, cp_oi_ratio
       max_vol_oi_ratio, atm_call_midIv, atm_put_midIv, atm_iv_spread

Coverage indicators (scorability):
  orats_scorable_T14, orats_scorable_T7, orats_scorable_T1  (core)
  orats_scorable_strikes_T14, orats_scorable_strikes_T1
"""

import json, math, csv, sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

try:
    import pandas as pd
    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False

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
ORATS_DIR = ROOT / "orats_phase3_cache"

OUT = ROOT / "bifrost_v59_kaizen_results.json"
DEPLOY = ROOT / "bifrost_v59_explosion_deploy.json"


# ----------------------------------------------------------------------------
# Helpers (reused from v5.8)
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
# ORATS trade-date helpers (same pattern Stage 2 used)
# ----------------------------------------------------------------------------
def bday_offset(date_str, offset_days):
    """Return YYYY-MM-DD trade date offset_days business days before date_str."""
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
    if HAS_PANDAS:
        try:
            td = (pd.Timestamp(dt) - pd.tseries.offsets.BDay(offset_days)).date()
            return td.strftime("%Y-%m-%d")
        except Exception:
            pass
    # Fallback: naive weekday skip
    d = dt
    steps = 0
    while steps < offset_days:
        d = d - timedelta(days=1)
        if d.weekday() < 5:
            steps += 1
    return d.strftime("%Y-%m-%d")


def orats_path(ticker, trade_date, endpoint):
    return ORATS_DIR / f"{ticker}_{trade_date}_hist_{endpoint}.json"


def load_orats_json(path):
    """Return (data_list, is_error) from an ORATS cache file. Empty/missing ⇒ ([], True)."""
    if not path.exists():
        return [], True
    try:
        j = json.loads(path.read_text())
    except Exception:
        return [], True
    if isinstance(j, dict) and j.get("_error"):
        return [], True
    data = j.get("data") if isinstance(j, dict) else None
    if not isinstance(data, list) or not data:
        return [], True
    return data, False


def extract_summaries(row):
    """Extract curated fields from a /hist/summaries record. Missing -> None."""
    if not isinstance(row, dict):
        return {}
    keys = [
        "iv10d", "iv20d", "iv30d", "iv60d", "iv90d", "iv6m", "iv1y",
        "rVol30", "contango", "skewing", "impliedMove",
        "dlt5Iv30d", "dlt25Iv30d", "dlt75Iv30d", "dlt95Iv30d",
        "fwd30_20", "fwd60_30", "fwd90_60", "fwd90_30", "fwd180_90",
        "confidence", "borrow30", "borrow2y",
        "riskFree30", "impliedEarningsMove",
    ]
    return {k: safe_float(row.get(k), 0.0) for k in keys}


def extract_ivrank(row):
    """Extract iv, iv rank, iv percentile (as 0-100)."""
    if not isinstance(row, dict):
        return {}
    return {
        "iv": safe_float(row.get("iv"), 0.0),
        "ivRank1m": safe_float(row.get("ivRank1m"), 0.0),
        "ivPct1m": safe_float(row.get("ivPct1m"), 0.0),
        "ivRank1y": safe_float(row.get("ivRank1y"), 0.0),
        "ivPct1y": safe_float(row.get("ivPct1y"), 0.0),
    }


def aggregate_strikes(rows, event_date_str):
    """Aggregate strikes chain. Returns per-event microstructure features."""
    if not rows:
        return {}
    # Group: sum call/put vol+OI across all strikes+expirations
    total_cv = 0.0
    total_pv = 0.0
    total_coi = 0.0
    total_poi = 0.0
    max_voi = 0.0
    # For ATM: pick strike closest to stockPrice
    # For event expiry: pick expiration closest to event date
    best_atm_row = None
    best_atm_dist = float("inf")
    best_exp_rows = []
    best_exp_dist = float("inf")
    event_dt = None
    try:
        event_dt = datetime.strptime(str(event_date_str)[:10], "%Y-%m-%d")
    except Exception:
        event_dt = None

    # First pass: find expiry closest to event
    exp_dists = {}
    for r in rows:
        exp = str(r.get("expirDate") or "")[:10]
        if not exp or exp in exp_dists:
            continue
        try:
            ed = datetime.strptime(exp, "%Y-%m-%d")
            if event_dt:
                dist = abs((ed - event_dt).days)
            else:
                dist = int(safe_float(r.get("dte"), 999))
        except Exception:
            dist = 999
        exp_dists[exp] = dist
    best_exp = None
    if exp_dists:
        best_exp = min(exp_dists.items(), key=lambda kv: kv[1])[0]

    for r in rows:
        cv = safe_float(r.get("callVolume"), 0.0)
        pv = safe_float(r.get("putVolume"), 0.0)
        coi = safe_float(r.get("callOpenInterest"), 0.0)
        poi = safe_float(r.get("putOpenInterest"), 0.0)
        sp = safe_float(r.get("stockPrice"), 0.0)
        strike = safe_float(r.get("strike"), 0.0)
        total_cv += cv
        total_pv += pv
        total_coi += coi
        total_poi += poi
        # Vol/OI ratio (both sides combined)
        if coi + poi > 0:
            voi = (cv + pv) / (coi + poi)
            if voi > max_voi:
                max_voi = voi
        # Closest ATM by |strike - spot|
        if sp > 0 and strike > 0:
            dist = abs(strike - sp)
            if dist < best_atm_dist:
                best_atm_dist = dist
                best_atm_row = r
        # Event-expiry aggregates
        if best_exp and str(r.get("expirDate") or "")[:10] == best_exp:
            best_exp_rows.append(r)

    # ATM IVs
    atm_call_iv = safe_float(best_atm_row.get("callMidIv"), 0.0) if best_atm_row else 0.0
    atm_put_iv = safe_float(best_atm_row.get("putMidIv"), 0.0) if best_atm_row else 0.0
    atm_iv_spread = atm_call_iv - atm_put_iv

    # Event-expiry sub-aggregates
    exp_cv = sum(safe_float(r.get("callVolume"), 0.0) for r in best_exp_rows)
    exp_pv = sum(safe_float(r.get("putVolume"), 0.0) for r in best_exp_rows)
    exp_vol = exp_cv + exp_pv
    total_vol = total_cv + total_pv
    event_expiry_vol_share = (exp_vol / total_vol) if total_vol > 0 else 0.0

    cp_vol_ratio = (total_cv / total_pv) if total_pv > 0 else (5.0 if total_cv > 0 else 1.0)
    cp_oi_ratio = (total_coi / total_poi) if total_poi > 0 else (5.0 if total_coi > 0 else 1.0)

    return {
        "total_call_volume": total_cv,
        "total_put_volume": total_pv,
        "total_call_oi": total_coi,
        "total_put_oi": total_poi,
        "cp_vol_ratio": cp_vol_ratio,
        "cp_oi_ratio": cp_oi_ratio,
        "max_vol_oi_ratio": max_voi,
        "atm_call_midIv": atm_call_iv,
        "atm_put_midIv": atm_put_iv,
        "atm_iv_spread": atm_iv_spread,
        "event_expiry_vol_share": event_expiry_vol_share,
        "total_options_vol": total_vol,
    }


# ----------------------------------------------------------------------------
# Per-event ORATS feature extraction
# ----------------------------------------------------------------------------
def build_orats_features(ticker, pdufa_date):
    """Build ORATS feature dict for one event. Missing snapshots fill 0 + indicator=0."""
    feats = {}
    snaps = {"T-14": 14, "T-7": 7, "T-1": 1}
    summaries_by_snap = {}
    ivrank_by_snap = {}
    for label, off in snaps.items():
        td = bday_offset(pdufa_date, off)
        if not td:
            feats[f"orats_scorable_{label.replace('-', '')}"] = 0.0
            summaries_by_snap[label] = {}
            ivrank_by_snap[label] = {}
            continue

        # summaries (most fields come from here)
        sdata, s_err = load_orats_json(orats_path(ticker, td, "summaries"))
        # ivrank
        rdata, r_err = load_orats_json(orats_path(ticker, td, "ivrank"))

        if s_err or not sdata:
            summaries_by_snap[label] = {}
        else:
            summaries_by_snap[label] = extract_summaries(sdata[0])
        if r_err or not rdata:
            ivrank_by_snap[label] = {}
        else:
            ivrank_by_snap[label] = extract_ivrank(rdata[0])

        scorable = 1.0 if (summaries_by_snap[label] or ivrank_by_snap[label]) else 0.0
        feats[f"orats_scorable_{label.replace('-', '')}"] = scorable

    # Emit A-E level features per snapshot
    for label in snaps:
        lbl = label.replace("-", "")
        s = summaries_by_snap[label]
        r = ivrank_by_snap[label]
        # IV term structure
        for k in ("iv10d", "iv20d", "iv30d", "iv60d", "iv90d", "iv1y"):
            feats[f"orats_{k}_{lbl}"] = safe_float(s.get(k), 0.0)
        # Risk metrics
        feats[f"orats_contango_{lbl}"] = safe_float(s.get("contango"), 0.0)
        feats[f"orats_skewing_{lbl}"] = safe_float(s.get("skewing"), 0.0)
        feats[f"orats_impliedMove_{lbl}"] = safe_float(s.get("impliedMove"), 0.0)
        feats[f"orats_rVol30_{lbl}"] = safe_float(s.get("rVol30"), 0.0)
        # IV / RV ratio
        iv30 = safe_float(s.get("iv30d"), 0.0)
        rv30 = safe_float(s.get("rVol30"), 0.0)
        feats[f"orats_ivrv_ratio_{lbl}"] = (iv30 / rv30) if rv30 > 0 else 1.0
        # Skew
        d5 = safe_float(s.get("dlt5Iv30d"), 0.0)
        d25 = safe_float(s.get("dlt25Iv30d"), 0.0)
        d75 = safe_float(s.get("dlt75Iv30d"), 0.0)
        d95 = safe_float(s.get("dlt95Iv30d"), 0.0)
        feats[f"orats_skew_25_75_{lbl}"] = d25 - d75
        feats[f"orats_skew_5_95_{lbl}"] = d5 - d95
        feats[f"orats_put_skew_{lbl}"] = d25 - iv30 if iv30 else 0.0
        # Forward curve
        for k in ("fwd30_20", "fwd60_30", "fwd90_60", "fwd90_30", "fwd180_90"):
            feats[f"orats_{k}_{lbl}"] = safe_float(s.get(k), 0.0)
        # IV rank/percentile
        for k in ("iv", "ivRank1m", "ivPct1m", "ivRank1y", "ivPct1y"):
            feats[f"orats_{k}_{lbl}"] = safe_float(r.get(k), 0.0)
        # Borrow / confidence / impliedEarningsMove
        feats[f"orats_borrow30_{lbl}"] = safe_float(s.get("borrow30"), 0.0)
        feats[f"orats_confidence_{lbl}"] = safe_float(s.get("confidence"), 0.0)
        feats[f"orats_implEarnMove_{lbl}"] = safe_float(s.get("impliedEarningsMove"), 0.0)

    # Cross-snapshot deltas
    def _iv(snap, key):
        return safe_float(summaries_by_snap.get(snap, {}).get(key), 0.0)
    def _rank(snap, key):
        return safe_float(ivrank_by_snap.get(snap, {}).get(key), 0.0)

    feats["orats_iv30d_delta_14_7"] = _iv("T-7", "iv30d") - _iv("T-14", "iv30d")
    feats["orats_iv30d_delta_7_1"] = _iv("T-1", "iv30d") - _iv("T-7", "iv30d")
    feats["orats_iv30d_delta_14_1"] = _iv("T-1", "iv30d") - _iv("T-14", "iv30d")
    feats["orats_iv60d_delta_14_1"] = _iv("T-1", "iv60d") - _iv("T-14", "iv60d")
    feats["orats_iv90d_delta_14_1"] = _iv("T-1", "iv90d") - _iv("T-14", "iv90d")
    feats["orats_iv10d_delta_14_1"] = _iv("T-1", "iv10d") - _iv("T-14", "iv10d")
    feats["orats_skewing_delta_14_1"] = _iv("T-1", "skewing") - _iv("T-14", "skewing")
    feats["orats_contango_delta_14_1"] = _iv("T-1", "contango") - _iv("T-14", "contango")
    feats["orats_ivrank1y_delta_14_1"] = _rank("T-1", "ivRank1y") - _rank("T-14", "ivRank1y")
    feats["orats_ivpct1y_delta_14_1"] = _rank("T-1", "ivPct1y") - _rank("T-14", "ivPct1y")
    feats["orats_impliedMove_delta_14_1"] = _iv("T-1", "impliedMove") - _iv("T-14", "impliedMove")

    # Strikes aggregates at T-14 and T-1
    for label, off in [("T-14", 14), ("T-1", 1)]:
        lbl = label.replace("-", "")
        td = bday_offset(pdufa_date, off)
        if not td:
            feats[f"orats_scorable_strikes_{lbl}"] = 0.0
            continue
        sdata, s_err = load_orats_json(orats_path(ticker, td, "strikes"))
        if s_err or not sdata:
            feats[f"orats_scorable_strikes_{lbl}"] = 0.0
            # default zeros for aggregates
            for k in ("total_call_volume", "total_put_volume", "total_call_oi",
                      "total_put_oi", "cp_vol_ratio", "cp_oi_ratio",
                      "max_vol_oi_ratio", "atm_call_midIv", "atm_put_midIv",
                      "atm_iv_spread", "event_expiry_vol_share",
                      "total_options_vol"):
                feats[f"orats_{k}_{lbl}"] = 0.0
            continue
        feats[f"orats_scorable_strikes_{lbl}"] = 1.0
        agg = aggregate_strikes(sdata, pdufa_date)
        for k, v in agg.items():
            feats[f"orats_{k}_{lbl}"] = v

    # Strikes cross-snapshot deltas (T-14 vs T-1)
    for k in ("total_options_vol", "cp_vol_ratio", "cp_oi_ratio",
              "atm_call_midIv", "atm_put_midIv", "max_vol_oi_ratio"):
        a = safe_float(feats.get(f"orats_{k}_T14"), 0.0)
        b = safe_float(feats.get(f"orats_{k}_T1"), 0.0)
        feats[f"orats_{k}_delta_14_1"] = b - a

    # Overall ORATS coverage score (0-5)
    cov = (feats.get("orats_scorable_T14", 0)
           + feats.get("orats_scorable_T7", 0)
           + feats.get("orats_scorable_T1", 0)
           + feats.get("orats_scorable_strikes_T14", 0)
           + feats.get("orats_scorable_strikes_T1", 0))
    feats["orats_coverage_score"] = float(cov)
    return feats


# ----------------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------------
print("=" * 80)
print("  BIFROST v5.9 KAIZEN — Phase 3 ORATS Honest Evaluation")
print("=" * 80)

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

n_orats_files = len(list(ORATS_DIR.glob("*.json")))
print(f"  ORATS cache: {n_orats_files} files")


# ----------------------------------------------------------------------------
# Feature engineering (v5.8 baseline inline + ORATS layer)
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Feature engineering")
print("-" * 80)

features = []
skipped = 0
orats_cov = {"T14": 0, "T7": 0, "T1": 0, "strikes_T14": 0, "strikes_T1": 0}
for row in bf_rows:
    ticker = row.get("ticker", "").upper().strip()
    pdufa_date = row.get("pdufa_date", "")
    eve_price = safe_float(row.get("eve_price"), 0.0)
    post_1d = safe_float(row.get("post_1d"), None) if row.get("post_1d") != "" else None
    if not ticker or not pdufa_date or eve_price <= 0 or post_1d is None:
        skipped += 1
        continue

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

    # v5.8 candidates that survived greedy (and we keep others for optional inclusion)
    v58_abs_runup_7d = abs(runup_7d)
    v58_vol_ratio_log = math.log1p(max(vol_ratio - 1.0, -0.99))
    v58_drawdown_x_small = abs(drawdown) * small_cap

    # Year split
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

    f_dict = {
        "ticker": ticker,
        "pdufa_date": pdufa_date[:10],
        "eve_price": eve_price,
        "post_1d": post_1d,
        "big_move": big_move,
        "split": split,
        # v5.8 baseline (60 features: 57 V54_BASE + 3 v58 survivors)
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
        "v58_abs_runup_7d": v58_abs_runup_7d,
        "v58_vol_ratio_log": v58_vol_ratio_log,
        "v58_drawdown_x_small": v58_drawdown_x_small,
    }

    # ORATS layer
    of = build_orats_features(ticker, pdufa_date)
    f_dict.update(of)

    # Track coverage
    if f_dict.get("orats_scorable_T14", 0) > 0: orats_cov["T14"] += 1
    if f_dict.get("orats_scorable_T7", 0) > 0: orats_cov["T7"] += 1
    if f_dict.get("orats_scorable_T1", 0) > 0: orats_cov["T1"] += 1
    if f_dict.get("orats_scorable_strikes_T14", 0) > 0: orats_cov["strikes_T14"] += 1
    if f_dict.get("orats_scorable_strikes_T1", 0) > 0: orats_cov["strikes_T1"] += 1

    features.append(f_dict)

print(f"  Events built: {len(features)}  (skipped {skipped})")
print(f"  ORATS coverage (of {len(features)} events):")
print(f"    T-14 core:    {orats_cov['T14']}   ({100*orats_cov['T14']/max(len(features),1):.1f}%)")
print(f"    T-7  core:    {orats_cov['T7']}   ({100*orats_cov['T7']/max(len(features),1):.1f}%)")
print(f"    T-1  core:    {orats_cov['T1']}   ({100*orats_cov['T1']/max(len(features),1):.1f}%)")
print(f"    T-14 strikes: {orats_cov['strikes_T14']}   ({100*orats_cov['strikes_T14']/max(len(features),1):.1f}%)")
print(f"    T-1  strikes: {orats_cov['strikes_T1']}   ({100*orats_cov['strikes_T1']/max(len(features),1):.1f}%)")


# ----------------------------------------------------------------------------
# Feature name lists
# ----------------------------------------------------------------------------
V58_FINAL_60 = [
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
    # v5.8 survivors
    "v58_abs_runup_7d", "v58_vol_ratio_log", "v58_drawdown_x_small",
]

# Build candidate list dynamically from features we actually have
# Only keep ORATS features with non-zero variance on train+val
sample = features[0] if features else {}
ORATS_ALL_CANDIDATES = sorted([k for k in sample.keys() if k.startswith("orats_")])
print(f"  Total ORATS features generated: {len(ORATS_ALL_CANDIDATES)}")


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


def fit_ridge_auc(train_rows, val_rows, cols, C=0.01):
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
# Variance filter on ORATS candidates (min 15 non-zero in train+val)
# ----------------------------------------------------------------------------
trainval = train + val
X_check = build_matrix(trainval, ORATS_ALL_CANDIDATES)
ORATS_CANDIDATES = []
for j, name in enumerate(ORATS_ALL_CANDIDATES):
    col = X_check[:, j]
    n_nonzero = int(np.sum(col != 0))
    if n_nonzero >= 15:
        std = float(np.std(col))
        if std > 0:
            ORATS_CANDIDATES.append(name)
print(f"  ORATS candidates after variance filter (>=15 non-zero, std>0): {len(ORATS_CANDIDATES)}")


# ----------------------------------------------------------------------------
# Baseline check: v5.8 final 60 features on 3-way split with best C=0.01
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Step 1: Reproduce v5.8 60-feature baseline")
print("-" * 80)

base_C = 0.01  # v5.8 honest winner
val_auc_base = fit_ridge_auc(train, val, V58_FINAL_60, C=base_C)
print(f"  v5.8 final 60 features @ C={base_C}: val AUC = {val_auc_base:.4f}")


# ----------------------------------------------------------------------------
# C sweep on baseline before ORATS (in case data mix shifts optimum)
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Step 2: C sweep on baseline")
print("-" * 80)
C_sweep = [0.01, 0.03, 0.05, 0.10, 0.25, 0.50, 1.0]
C_sweep_vals = []
best_C, best_val = base_C, val_auc_base
for C in C_sweep:
    v = fit_ridge_auc(train, val, V58_FINAL_60, C=C)
    C_sweep_vals.append({"C": C, "val_auc": round(v, 4)})
    print(f"    C={C:<6}: val AUC = {v:.4f}")
    if v > best_val:
        best_val, best_C = v, C
print(f"  C sweep winner: C={best_C}  val AUC={best_val:.4f}")


# ----------------------------------------------------------------------------
# Fast Ridge-only pre-screen: single-feature val AUC for each ORATS candidate
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Step 3: Fast single-feature pre-screen")
print("-" * 80)
prescreen = []
for feat in ORATS_CANDIDATES:
    trial = V58_FINAL_60 + [feat]
    try:
        v = fit_ridge_auc(train, val, trial, C=best_C)
    except Exception as e:
        continue
    prescreen.append((feat, v, v - best_val))
prescreen.sort(key=lambda t: t[1], reverse=True)
print(f"  Top 15 solo additions (vs baseline {best_val:.4f}):")
for feat, v, delta in prescreen[:15]:
    flag = "✅" if delta >= 0.002 else ("≈" if delta >= 0 else "✗")
    print(f"    {flag} {feat:<50} val={v:.4f}  Δ={delta:+.4f}")

prescreen_records = [
    {"feature": f, "val_auc": round(v, 4), "val_delta": round(d, 4)}
    for (f, v, d) in prescreen
]

# Restrict greedy pool to candidates that are at least non-negative solo
greedy_pool = [f for (f, v, d) in prescreen if d > -0.001]
print(f"  Greedy pool (solo Δ >= -0.001): {len(greedy_pool)}")


# ----------------------------------------------------------------------------
# Greedy forward selection on ORATS candidates (VAL only)
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Step 4: Greedy forward selection on ORATS candidates")
print("-" * 80)

selected = list(V58_FINAL_60)
current_val = best_val
gains = []
pool = list(greedy_pool)

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
    print(f"  round {rnd + 1}: +{best_feat:<50}  val={best_after:.4f}  Δ={best_after - current_val:+.4f}")
    current_val = best_after

print(f"\n  Final selected features: {len(selected)}  (baseline 60 + {len(selected) - 60} ORATS)")


# ----------------------------------------------------------------------------
# Architecture sweep on VAL (Ridge only vs Ridge+GBM+LGB)
# ----------------------------------------------------------------------------
print("\n" + "-" * 80)
print("  Step 5: Architecture sweep on VAL")
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
    return roc_auc_score(y_va, p_ens)


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
    auc = fit_ensemble(train, val, selected, C=best_C, w_r=wr, w_g=wg, w_l=wl)
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

# Bootstrap CI
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
V58_HONEST = 0.8671

print(f"  Final test AUC (Ridge only):        {final_test_auc_ridge:.4f}  CI95=[{ci_lo_r:.4f}, {ci_hi_r:.4f}]")
print(f"  Final test AUC (ensemble):          {final_test_auc_ens:.4f}  CI95=[{ci_lo_e:.4f}, {ci_hi_e:.4f}]")
print(f"  v5.6 honest bar:                    {V56_HONEST_BAR:.4f}")
print(f"  v5.8 honest recent:                 {V58_HONEST:.4f}")
print(f"  Δ vs v5.6 bar (ensemble):           {(final_test_auc_ens - V56_HONEST_BAR) * 100:+.2f} pp")
print(f"  Δ vs v5.8 (ensemble):               {(final_test_auc_ens - V58_HONEST) * 100:+.2f} pp")

# Strict promote gate: point > 0.8861+0.002 AND CI lower > 0.8861
promote_point = final_test_auc_ens > V56_HONEST_BAR + 0.002
promote_ci = (ci_lo_e is not None) and (ci_lo_e > V56_HONEST_BAR)
if promote_point and promote_ci:
    verdict = "PROMOTE — v5.9 beats v5.6 honest bar and CI lower bound clears"
elif final_test_auc_ens > V58_HONEST + 0.005:
    verdict = "PARTIAL — beats v5.8 honest but fails v5.6 strict gate; advisory only"
elif final_test_auc_ens > V56_HONEST_BAR - 0.005:
    verdict = "FLAT — within noise of v5.6 honest bar; v5.5 remains deployed"
else:
    verdict = "REGRESSION — hold v5.5 deployment"
print(f"  VERDICT: {verdict}")


# ----------------------------------------------------------------------------
# Save
# ----------------------------------------------------------------------------
result = {
    "version": "5.9.0",
    "generated_utc": datetime.utcnow().isoformat() + "Z",
    "methodology": {
        "split": "3-way (train <=2023 / val 2024 / test >=2025)",
        "baseline": "v5.8 final 60 features (locked)",
        "baseline_features_n": len(V58_FINAL_60),
        "feature_selection": "VAL-only greedy forward on ORATS candidates, gate Δval >= +0.002",
        "hyperparameter_tuning": "VAL-only C sweep + arch weight sweep",
        "test_touches": 1,
        "bootstrap_boot_n": 2000,
        "promote_gate": "point > 0.8861 + 0.002 AND CI_lo > 0.8861",
    },
    "input": csv_path.name,
    "n_events": len(features),
    "n_orats_files": n_orats_files,
    "orats_coverage": orats_cov,
    "split_counts": {"train": len(train), "val": len(val), "test": len(test)},
    "train_explosion_rate": round(sum(f["big_move"] for f in train) / max(len(train), 1), 4),
    "val_explosion_rate":   round(sum(f["big_move"] for f in val) / max(len(val), 1), 4),
    "test_explosion_rate":  round(sum(f["big_move"] for f in test) / max(len(test), 1), 4),
    "orats_candidates_total": len(ORATS_ALL_CANDIDATES),
    "orats_candidates_after_variance_filter": len(ORATS_CANDIDATES),
    "baseline_val_auc_C01":  round(val_auc_base, 4),
    "baseline_val_auc_best_C":   round(best_val, 4),
    "best_C": best_C,
    "C_sweep_val_aucs": C_sweep_vals,
    "prescreen_top20": prescreen_records[:20],
    "prescreen_n_positive": sum(1 for r in prescreen_records if r["val_delta"] > 0),
    "prescreen_n_pass_gate": sum(1 for r in prescreen_records if r["val_delta"] >= 0.002),
    "greedy_pool_n": len(greedy_pool),
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
    "v58_honest":     V58_HONEST,
    "v55_deployed_inflated": 0.9487,
    "delta_vs_v56_bp_ensemble": round((final_test_auc_ens - V56_HONEST_BAR) * 10000),
    "delta_vs_v58_bp_ensemble": round((final_test_auc_ens - V58_HONEST) * 10000),
    "promote_point": promote_point,
    "promote_ci":    promote_ci,
    "verdict": verdict,
    "has_gbm": HAS_GBM,
    "has_lgb": HAS_LGB,
    "has_pandas": HAS_PANDAS,
}

OUT.write_text(json.dumps(result, indent=2, default=str))
print(f"\n  WROTE {OUT}")

# Deploy config (only if promoted)
if promote_point and promote_ci:
    # Save ridge weights for deployment
    final_scaler = StandardScaler()
    X_full = build_matrix(trainval, selected)
    final_scaler.fit(X_full)
    ridge_final = LogisticRegression(C=best_C, penalty="l2", solver="lbfgs",
                                     max_iter=1000, random_state=42)
    X_full_s = final_scaler.transform(X_full)
    ridge_final.fit(X_full_s, y_trv)
    deploy = {
        "version": "5.9.0",
        "features": selected,
        "C": best_C,
        "arch_weights": best_arch["weights"],
        "ridge_coef": ridge_final.coef_[0].tolist(),
        "ridge_intercept": float(ridge_final.intercept_[0]),
        "scaler_mean": final_scaler.mean_.tolist(),
        "scaler_scale": final_scaler.scale_.tolist(),
        "final_test_auc_ensemble": round(final_test_auc_ens, 4),
        "final_test_auc_ens_ci95": [round(ci_lo_e, 4), round(ci_hi_e, 4)],
        "v56_honest_bar": V56_HONEST_BAR,
        "verdict": verdict,
    }
    DEPLOY.write_text(json.dumps(deploy, indent=2, default=str))
    print(f"  WROTE {DEPLOY}  (PROMOTED)")
else:
    print(f"  NOT PROMOTED — no deploy file written")

print("=" * 80)
