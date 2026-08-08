"""
Stage 6c — Form 4 × BIFROST Explosion v5.6 Honest Eval

Goal: test whether Form 4 historical insider time-series features add
TEST AUC lift above the v5.8 honest baseline (Ridge-only, 60 features,
C=0.01, final test AUC 0.8671 CI95 [0.8155, 0.9148]) and — the real bar —
whether they break the v5.6 honest bar of 0.8861.

Methodology (mirrors bifrost_v58_kaizen.py, mods flagged ***):
- 3-way temporal split: train <=2023 / val 2024 / test >=2025 (pdufa_year string)
- FIXED 60-feature v5.8 final_feature_list baseline (NOT pruned) ***
- Val-only C sweep over [0.005, 0.01, 0.03, 0.05, 0.10, 0.25]
- Val-only greedy forward selection over F4 candidates only, gate +0.002 ***
- Arch sweep SKIPPED — v5.8 confirmed Ridge-only wins ***
- Final test fit on train+val, 1 touch, bootstrap 95% CI n_boot=2000 seed=42
- Compare to V56_HONEST_BAR = 0.8861

Saturation thesis: 9 consecutive honest-Kaizen NULLs across BIFROST/ODIN/Gungnir.
Form 4 historical insider time series is the #1 orthogonal signal family remaining.
A lift here breaks the pattern; a null confirms saturation across 3 engines.

I/O:
  in   /sessions/confident-serene-ptolemy/mnt/9realms/pdufa_runup_bifrost*.csv
  in   /sessions/confident-serene-ptolemy/mnt/9realms/bifrost_price_cache.json
  in   /sessions/confident-serene-ptolemy/mnt/9realms/short_interest_snapshot.json
  in   /sessions/confident-serene-ptolemy/mnt/9realms/ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv
  in   /sessions/confident-serene-ptolemy/mnt/9realms/xbi_daily_cache.json
  in   /sessions/confident-serene-ptolemy/form4_event_features.csv
  out  /sessions/confident-serene-ptolemy/form4_bifrost_explosion_honest_results.json
"""

import json
import math
import csv
from pathlib import Path
from datetime import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score


# ============================================================
# PATHS  (BASE = persistent BIFROST data; WORKSPACE = Form 4 + outputs)
# ============================================================
BASE = Path("/sessions/confident-serene-ptolemy/mnt/9realms")
WORKSPACE = Path("/sessions/confident-serene-ptolemy")

BF_CSV = BASE / "pdufa_runup_bifrost.csv"
BF_CSV_V2 = BASE / "pdufa_runup_bifrost_v2.csv"
PRICE_CACHE = BASE / "bifrost_price_cache.json"
SI_SNAP = BASE / "short_interest_snapshot.json"
ODIN_CSV = BASE / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
XBI_CACHE = BASE / "xbi_daily_cache.json"

F4_CSV = WORKSPACE / "form4_event_features.csv"
OUT = WORKSPACE / "form4_bifrost_explosion_honest_results.json"

V56_HONEST_BAR = 0.8861
V55_DEPLOYED_INFLATED = 0.9487


# ============================================================
# HELPERS (verbatim from bifrost_v58_kaizen.py)
# ============================================================
def safe_float(x, default=0.0):
    try:
        if x is None or x == "" or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default


def _xbi_return(xbi, date_str, lookback_days):
    if not xbi:
        return 0.0
    try:
        d1 = datetime.fromisoformat(date_str[:10])
    except Exception:
        return 0.0
    end_val = None
    end_used = None
    for back in range(0, 7):
        ds = (d1 - __import__("datetime").timedelta(days=back)).date().isoformat()
        if ds in xbi:
            end_val = xbi[ds]
            end_used = d1 - __import__("datetime").timedelta(days=back)
            break
    if end_val is None or end_used is None:
        return 0.0
    start_val = None
    d0 = end_used - __import__("datetime").timedelta(days=lookback_days)
    for back in range(0, 7):
        ds = (d0 - __import__("datetime").timedelta(days=back)).date().isoformat()
        if ds in xbi:
            start_val = xbi[ds]
            break
    if start_val is None or start_val <= 0:
        return 0.0
    try:
        return (end_val - start_val) / start_val
    except Exception:
        return 0.0


def _xbi_vol_30d(xbi, date_str):
    if not xbi:
        return 0.0
    try:
        d1 = datetime.fromisoformat(date_str[:10])
    except Exception:
        return 0.0
    prices = []
    for back in range(0, 40):
        ds = (d1 - __import__("datetime").timedelta(days=back)).date().isoformat()
        if ds in xbi:
            prices.append(xbi[ds])
    if len(prices) < 10:
        return 0.0
    prices = prices[::-1]
    rets = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)) if prices[i - 1] > 0]
    if not rets:
        return 0.0
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / max(len(rets) - 1, 1)
    return math.sqrt(var) * math.sqrt(252)


# ============================================================
# LOAD
# ============================================================
def main():
    print("=" * 78)
    print("Stage 6c  —  Form 4 × BIFROST Explosion v5.6 Honest Eval")
    print("=" * 78)
    from datetime import timedelta as _td  # noqa: F401  # keep name stable for _xbi_* helpers

    csv_path = BF_CSV_V2 if BF_CSV_V2.exists() else BF_CSV
    print(f"Input CSV:      {csv_path}")

    price_cache = json.load(open(PRICE_CACHE)) if PRICE_CACHE.exists() else {}
    print(f"Price cache:    {len(price_cache)} tickers")

    si_snap_full = json.load(open(SI_SNAP)) if SI_SNAP.exists() else {}
    si_snap = si_snap_full.get("tickers", {}) if isinstance(si_snap_full, dict) else {}
    sample_fetch = None
    for tk in list(si_snap.values())[:1]:
        sample_fetch = (tk or {}).get("fetch_date")
    si_cutoff = None
    if sample_fetch:
        try:
            si_cutoff = datetime.fromisoformat(sample_fetch[:10])
        except Exception:
            si_cutoff = None
    print(f"SI snapshot:    {len(si_snap)} tickers  (cutoff={si_cutoff})")

    xbi = json.load(open(XBI_CACHE)) if XBI_CACHE.exists() else {}
    print(f"XBI cache:      {len(xbi)} daily obs")

    odin_lookup = {}
    if ODIN_CSV.exists():
        with open(ODIN_CSV) as f:
            for row in csv.DictReader(f):
                t = (row.get("ticker") or "").upper().strip()
                d = (row.get("catalyst_date") or "")[:10]
                if t and d:
                    odin_lookup[(t, d)] = row
    print(f"ODIN lookup:    {len(odin_lookup)} events")

    # ---- Form 4 candidate load ----
    if not F4_CSV.exists():
        print(f"\nFATAL: {F4_CSV} not found — Stage 5 must complete first.")
        return
    f4_map = {}
    f4_cols = []
    with open(F4_CSV) as f:
        reader = csv.DictReader(f)
        f4_cols = [c for c in (reader.fieldnames or []) if c.startswith("f4_")]
        for row in reader:
            t = (row.get("ticker") or "").upper().strip()
            d = (row.get("catalyst_date") or row.get("pdufa_date") or "")[:10]
            if not (t and d):
                continue
            f4_map[(t, d)] = {c: safe_float(row.get(c, 0.0), 0.0) for c in f4_cols}
    print(f"F4 candidates:  {len(f4_cols)} features × {len(f4_map)} matched events")

    # ============================================================
    # FEATURE ENGINEERING  (verbatim mirror of bifrost_v58_kaizen.py)
    # ============================================================
    from datetime import timedelta
    rows = []
    skipped = 0

    with open(csv_path) as f:
        bf_rows = list(csv.DictReader(f))
    print(f"\nBIFROST rows:  {len(bf_rows)}")

    for row in bf_rows:
        ticker = (row.get("ticker") or "").upper().strip()
        pdufa_date = (row.get("pdufa_date") or "")[:10]
        if not (ticker and pdufa_date):
            skipped += 1
            continue
        eve_price = safe_float(row.get("eve_price"), 0.0)
        if eve_price <= 0:
            skipped += 1
            continue
        post_1d = safe_float(row.get("post_1d"), None)
        if post_1d is None:
            skipped += 1
            continue
        big_move = 1.0 if abs(post_1d) > 25 else 0.0

        # ---- price features ----
        v5_score = safe_float(row.get("v5_score"), 0.5)
        surprise = 1.0 - v5_score
        mcap_str = (row.get("mcap_tier") or "").strip().lower()
        is_nano = 1.0 if "nano" in mcap_str else 0.0
        is_micro = 1.0 if "micro" in mcap_str else 0.0
        is_small = 1.0 if "small" in mcap_str else 0.0
        is_penny = 1.0 if eve_price < 5 else 0.0
        is_low_price = 1.0 if eve_price < 10 else 0.0
        log_price_inv = 1.0 / math.log1p(eve_price) if eve_price > 0 else 0.0

        # pre-event price series for 52-week high
        pc = price_cache.get(ticker) or {}
        high_52w = eve_price
        try:
            dates_pre = [d for d in pc.keys() if d < pdufa_date]
            if dates_pre:
                dates_pre = sorted(dates_pre)[-260:]
                highs = [safe_float(pc[d].get("high") or pc[d].get("close"), 0.0) for d in dates_pre]
                highs = [h for h in highs if h > 0]
                if highs:
                    high_52w = max(highs)
        except Exception:
            pass
        compression = eve_price / high_52w if high_52w > 0 else 1.0
        drawdown_pct = min(max((eve_price - high_52w) / high_52w if high_52w > 0 else 0.0, -1.0), 0.0)
        beaten_down_30d = 1.0 if drawdown_pct < -0.15 else 0.0
        beaten_surprise = drawdown_pct * surprise

        vol_ratio = safe_float(row.get("vol_ratio_20_90"), 1.0)
        runup_30d = safe_float(row.get("ret_t_30_t_1"), 0.0)
        runup_14d = safe_float(row.get("ret_t_14_t_1"), 0.0)
        runup_7d = safe_float(row.get("ret_t_7_t_1"), 0.0)
        runup_3d = safe_float(row.get("ret_t_3_t_1"), 0.0)

        # SI features (respect T-1 via si_cutoff)
        si_entry = si_snap.get(ticker, {}) or {}
        si_ok = True
        if si_cutoff is not None:
            try:
                if datetime.fromisoformat(pdufa_date) > si_cutoff:
                    si_ok = False
            except Exception:
                si_ok = False
        if si_ok:
            short_pct = safe_float(si_entry.get("pct_float_short"), 0.0)
            days_cov = safe_float(si_entry.get("days_to_cover"), 0.0)
            float_sh = safe_float(si_entry.get("float_shares"), 0.0)
            log_float_inv = 1.0 / math.log1p(float_sh) if float_sh > 0 else 0.0
            short_high = 1.0 if short_pct >= 0.15 else 0.0
        else:
            short_pct = 0.0
            days_cov = 0.0
            log_float_inv = 0.0
            short_high = 0.0

        # XBI features
        xbi_30d = _xbi_return(xbi, pdufa_date, 30)
        xbi_7d = _xbi_return(xbi, pdufa_date, 7)
        xbi_14d = _xbi_return(xbi, pdufa_date, 14)
        xbi_60d = _xbi_return(xbi, pdufa_date, 60)
        xbi_vol = _xbi_vol_30d(xbi, pdufa_date)

        # ODIN enrichment (use otrue helper for boolean fields)
        odin = odin_lookup.get((ticker, pdufa_date)) or {}
        def otrue(k):
            v = odin.get(k)
            if isinstance(v, str):
                vl = v.strip().lower()
                return 1.0 if vl in ("1", "true", "t", "yes", "y") else 0.0
            return 1.0 if safe_float(v, 0.0) >= 0.5 else 0.0

        prior_crl_count = safe_float(odin.get("prior_crl_count"), 0.0)
        resub_class = int(safe_float(odin.get("resub_class"), 0.0))
        spa = safe_float(odin.get("sponsor_prior_approvals"), 0.0)
        log_spa = math.log1p(spa) if spa >= 0 else 0.0
        safety_sev = safe_float(odin.get("safety_signal_severity"), 0.0)
        ta_vh = otrue("ta_very_high_risk")
        hist_crl = safe_float(odin.get("historical_crl_rate"), 0.0)

        btd = otrue("breakthrough_therapy")
        orphan = otrue("orphan_drug")
        priority_rev = otrue("priority_review")
        fast_track = otrue("fast_track")
        ppm_flag = otrue("ppm_flag")
        single_arm = otrue("single_arm_trial")
        gene_therapy = otrue("gene_therapy")
        psychedelic = otrue("psychedelic")
        desig_count = btd + orphan + priority_rev + fast_track

        # composite / interaction flags
        is_naive = 1.0 if spa <= 0 else 0.0
        resub1 = 1.0 if resub_class == 1 else 0.0
        resub2 = 1.0 if resub_class == 2 else 0.0
        vol_high = 1.0 if vol_ratio > 1.3 else 0.0
        safety_h = 1.0 if safety_sev >= 0.66 else 0.0
        beaten = 1.0 if drawdown_pct < -0.20 else 0.0

        # ---- V54_BASE features ----
        feat = {
            "surprise_factor": surprise,
            "is_penny": is_penny,
            "is_low_price": is_low_price,
            "log_price_inv": log_price_inv,
            "is_nano": is_nano,
            "is_micro": is_micro,
            "is_small": is_small,
            "surprise_x_small_cap": surprise * (is_nano + is_micro + is_small),
            "surprise_x_low_price": surprise * is_low_price,
            "price_compression": compression,
            "drawdown_pct": drawdown_pct,
            "beaten_down_30d": beaten_down_30d,
            "beaten_surprise": beaten_surprise,
            "compression_x_surprise": compression * surprise,
            "vol_ratio": vol_ratio,
            "runup_30d": runup_30d,
            "v5_score": v5_score,
            "log_float_inv": log_float_inv,
            "pct_float_short": short_pct,
            "short_high": short_high,
            "days_to_cover": days_cov,
            "drift_magnitude": abs(runup_30d),
            "xbi_return_30d": xbi_30d,
            "xbi_x_surprise": xbi_30d * surprise,
            "xbi_x_small": xbi_30d * (is_nano + is_micro + is_small),
            "vol_high": vol_high,
            "crl_count_x_small": prior_crl_count * (is_nano + is_micro + is_small),
            "is_resub": 1.0 if resub_class >= 1 else 0.0,
            "drift_7d": runup_7d,
            "resub_x_surprise": (1.0 if resub_class >= 1 else 0.0) * surprise,
            "naive_x_small": is_naive * (is_nano + is_micro + is_small),
            "drawdown_x_vol": drawdown_pct * vol_ratio,
            "runup_7d": runup_7d,
            "ta_vh_x_small": ta_vh * (is_nano + is_micro + is_small),

            # ---- cand_ interactions (v5.4 survivors, 23) ----
            "cand_orphan_x_runup_7d_val": orphan * runup_7d,
            "cand_resub1_x_vol_high": resub1 * vol_high,
            "cand_ppm_x_runup_30d": ppm_flag * runup_30d,
            "cand_spa_log_x_is_small": log_spa * is_small,
            "cand_ppm_x_dtc": ppm_flag * days_cov,
            "cand_safety_h_x_dtc": safety_h * days_cov,
            "cand_crl_rate_x_is_small": hist_crl * is_small,
            "cand_resub2_x_log_float_inv": resub2 * log_float_inv,
            "cand_ta_vh_x_log_float_inv": ta_vh * log_float_inv,
            "cand_resub1_x_beaten": resub1 * beaten,
            "cand_ppm_x_is_micro": ppm_flag * is_micro,
            "cand_btd_x_is_penny_val": btd * is_penny,
            "cand_resub2_x_xbi_30d": resub2 * xbi_30d,
            "cand_safety_h_x_short_high": safety_h * short_high,
            "cand_resub2_x_si_pct": resub2 * short_pct,
            "cand_resub1_x_is_micro": resub1 * is_micro,
            "cand_ft_x_drawdown": fast_track * drawdown_pct,
            "cand_ft_x_is_small": fast_track * is_small,
            "cand_safety_h_x_is_penny_val": safety_h * is_penny,
            "cand_fast_track": fast_track,
            "cand_gene_th_x_small_cap": gene_therapy * (is_nano + is_micro + is_small),
            "cand_resub2_x_runup_7d_val": resub2 * runup_7d,
            "cand_t90_t7": safe_float(row.get("ret_t_90_t_7"), 0.0),

            # ---- v58 survivors (3) ----
            "v58_abs_runup_7d": abs(runup_7d),
            "v58_vol_ratio_log": math.log1p(max(vol_ratio - 1.0, 0.0)),
            "v58_drawdown_x_small": drawdown_pct * (is_nano + is_micro + is_small),
        }

        # ---- attach Form 4 candidate features (zero-fill if no match) ----
        f4 = f4_map.get((ticker, pdufa_date), None)
        if f4 is None:
            for c in f4_cols:
                feat[c] = 0.0
        else:
            for c in f4_cols:
                feat[c] = safe_float(f4.get(c, 0.0), 0.0)

        # ---- split ----
        pdufa_year = pdufa_date[:4]
        if pdufa_year <= "2023":
            split = "train"
        elif pdufa_year == "2024":
            split = "val"
        else:
            split = "test"

        feat["big_move"] = big_move
        feat["ticker"] = ticker
        feat["pdufa_date"] = pdufa_date
        feat["post_1d"] = post_1d
        feat["split"] = split
        feat["_f4_has_match"] = 0.0 if f4 is None else 1.0

        rows.append(feat)

    print(f"Built rows:   {len(rows)}  (skipped {skipped})")
    train = [r for r in rows if r["split"] == "train"]
    val   = [r for r in rows if r["split"] == "val"]
    test  = [r for r in rows if r["split"] == "test"]
    print(f"  train: {len(train)}  val: {len(val)}  test: {len(test)}")
    exp_rate = lambda rs: sum(r["big_move"] for r in rs) / max(len(rs), 1)
    print(f"  explosion rate  train={exp_rate(train):.4f}  val={exp_rate(val):.4f}  test={exp_rate(test):.4f}")
    f4_coverage = {
        "train": sum(r["_f4_has_match"] for r in train) / max(len(train), 1),
        "val":   sum(r["_f4_has_match"] for r in val)   / max(len(val), 1),
        "test":  sum(r["_f4_has_match"] for r in test)  / max(len(test), 1),
    }
    print(f"  F4 coverage     train={f4_coverage['train']:.4f}  val={f4_coverage['val']:.4f}  test={f4_coverage['test']:.4f}")

    # ============================================================
    # FIXED 60-FEATURE v5.8 BASELINE
    # ============================================================
    V58_FINAL_60 = [
        "surprise_factor", "is_penny", "is_low_price", "log_price_inv", "is_nano",
        "is_micro", "is_small", "surprise_x_small_cap", "surprise_x_low_price",
        "price_compression", "drawdown_pct", "beaten_down_30d", "beaten_surprise",
        "compression_x_surprise", "vol_ratio", "runup_30d", "v5_score", "log_float_inv",
        "pct_float_short", "short_high", "days_to_cover", "drift_magnitude",
        "xbi_return_30d", "xbi_x_surprise", "xbi_x_small", "vol_high",
        "crl_count_x_small", "is_resub", "drift_7d", "resub_x_surprise",
        "naive_x_small", "drawdown_x_vol", "runup_7d", "ta_vh_x_small",
        "cand_orphan_x_runup_7d_val", "cand_resub1_x_vol_high", "cand_ppm_x_runup_30d",
        "cand_spa_log_x_is_small", "cand_ppm_x_dtc", "cand_safety_h_x_dtc",
        "cand_crl_rate_x_is_small", "cand_resub2_x_log_float_inv",
        "cand_ta_vh_x_log_float_inv", "cand_resub1_x_beaten", "cand_ppm_x_is_micro",
        "cand_btd_x_is_penny_val", "cand_resub2_x_xbi_30d", "cand_safety_h_x_short_high",
        "cand_resub2_x_si_pct", "cand_resub1_x_is_micro", "cand_ft_x_drawdown",
        "cand_ft_x_is_small", "cand_safety_h_x_is_penny_val", "cand_fast_track",
        "cand_gene_th_x_small_cap", "cand_resub2_x_runup_7d_val", "cand_t90_t7",
        "v58_abs_runup_7d", "v58_vol_ratio_log", "v58_drawdown_x_small",
    ]
    assert len(V58_FINAL_60) == 60

    # ============================================================
    # FITTERS
    # ============================================================
    def build_matrix(rs, cols):
        return np.array([[safe_float(r.get(c, 0.0), 0.0) for c in cols] for r in rs], dtype=float)

    def fit_val_auc(train_rs, val_rs, cols, C=0.01):
        X_tr = build_matrix(train_rs, cols)
        X_va = build_matrix(val_rs, cols)
        y_tr = np.array([r["big_move"] for r in train_rs])
        y_va = np.array([r["big_move"] for r in val_rs])
        sc = StandardScaler()
        X_tr = sc.fit_transform(X_tr)
        X_va = sc.transform(X_va)
        clf = LogisticRegression(C=C, penalty="l2", solver="lbfgs", max_iter=1000, random_state=42)
        clf.fit(X_tr, y_tr)
        return roc_auc_score(y_va, clf.predict_proba(X_va)[:, 1])

    def fit_test_auc(trainval_rs, test_rs, cols, C=0.01):
        X_tv = build_matrix(trainval_rs, cols)
        X_te = build_matrix(test_rs, cols)
        y_tv = np.array([r["big_move"] for r in trainval_rs])
        y_te = np.array([r["big_move"] for r in test_rs])
        sc = StandardScaler()
        X_tv = sc.fit_transform(X_tv)
        X_te = sc.transform(X_te)
        clf = LogisticRegression(C=C, penalty="l2", solver="lbfgs", max_iter=1000, random_state=42)
        clf.fit(X_tv, y_tv)
        probs = clf.predict_proba(X_te)[:, 1]
        return roc_auc_score(y_te, probs), probs, y_te

    # ============================================================
    # 1) C SWEEP on fixed 60-feature v5.8 baseline (val-only)
    # ============================================================
    print("\n" + "=" * 78)
    print("Step 1 — C sweep on fixed 60-feature v5.8 baseline (val-only)")
    print("=" * 78)
    C_SWEEP = [0.005, 0.01, 0.03, 0.05, 0.10, 0.25]
    c_results = []
    best_C, best_val = None, -1.0
    for C in C_SWEEP:
        v = fit_val_auc(train, val, V58_FINAL_60, C=C)
        c_results.append({"C": C, "val_auc": round(v, 4)})
        print(f"  C={C:<6}  val_auc={v:.4f}")
        if v > best_val:
            best_val, best_C = v, C
    print(f"  -> best_C={best_C}  val_auc={best_val:.4f}")

    # ============================================================
    # 2) GREEDY FORWARD over F4 candidates only (baseline fixed)
    # ============================================================
    print("\n" + "=" * 78)
    print("Step 2 — Greedy forward selection over F4 candidates (val gate +0.002)")
    print("=" * 78)
    MAX_ROUNDS = 10
    GATE = 0.002
    selected_f4 = []
    current_val = best_val
    greedy_log = []
    remaining = list(f4_cols)

    for rnd in range(1, MAX_ROUNDS + 1):
        best_feat, best_delta, best_new_val = None, -1.0, None
        for cand in remaining:
            cols = V58_FINAL_60 + selected_f4 + [cand]
            v = fit_val_auc(train, val, cols, C=best_C)
            delta = v - current_val
            if delta > best_delta:
                best_delta, best_feat, best_new_val = delta, cand, v
        if best_feat is None or best_delta < GATE:
            print(f"  Round {rnd}: no F4 candidate meets gate (best was {best_feat}: +{best_delta:.4f})")
            greedy_log.append({"round": rnd, "feature": best_feat, "delta": round(best_delta, 4),
                               "val_auc": round(best_new_val or current_val, 4), "accepted": False})
            break
        selected_f4.append(best_feat)
        remaining.remove(best_feat)
        greedy_log.append({"round": rnd, "feature": best_feat, "delta": round(best_delta, 4),
                           "val_auc": round(best_new_val, 4), "accepted": True})
        print(f"  Round {rnd}: ACCEPT {best_feat}  Δ=+{best_delta:.4f}  val={best_new_val:.4f}")
        current_val = best_new_val

    final_cols = V58_FINAL_60 + selected_f4
    print(f"\n  Final feature count: {len(final_cols)}  (baseline 60 + {len(selected_f4)} F4)")

    # ============================================================
    # 3) FINAL TEST AUC — one touch, bootstrap CI
    # ============================================================
    print("\n" + "=" * 78)
    print("Step 3 — Final test (one touch) with bootstrap CI")
    print("=" * 78)
    trainval = train + val
    baseline_test_auc, baseline_probs, y_te = fit_test_auc(trainval, test, V58_FINAL_60, C=best_C)
    final_test_auc, final_probs, _ = fit_test_auc(trainval, test, final_cols, C=best_C)
    print(f"  Baseline 60-feat test AUC:  {baseline_test_auc:.4f}")
    print(f"  +F4 ({len(selected_f4)}) test AUC:         {final_test_auc:.4f}")
    print(f"  Lift (F4 − baseline):       {(final_test_auc - baseline_test_auc):+.4f}")

    # bootstrap
    rng = np.random.RandomState(42)
    N = len(y_te)
    b_base, b_final, b_diff = [], [], []
    for _ in range(2000):
        idx = rng.randint(0, N, size=N)
        y_s = y_te[idx]
        if y_s.sum() == 0 or y_s.sum() == N:
            continue
        b_base.append(roc_auc_score(y_s, baseline_probs[idx]))
        b_final.append(roc_auc_score(y_s, final_probs[idx]))
        b_diff.append(b_final[-1] - b_base[-1])
    pct = lambda xs, p: float(np.percentile(np.array(xs), p))
    ci_baseline = [round(pct(b_base, 2.5), 4), round(pct(b_base, 97.5), 4)]
    ci_final    = [round(pct(b_final, 2.5), 4), round(pct(b_final, 97.5), 4)]
    ci_diff     = [round(pct(b_diff, 2.5), 4), round(pct(b_diff, 97.5), 4)]
    p_lift_gt_0 = float(np.mean(np.array(b_diff) > 0)) if b_diff else 0.0
    print(f"  Baseline CI95: {ci_baseline}")
    print(f"  Final    CI95: {ci_final}")
    print(f"  Lift     CI95: {ci_diff}  p(lift>0)={p_lift_gt_0:.4f}")

    # ============================================================
    # 4) VERDICT
    # ============================================================
    delta_vs_v56_bp = round((final_test_auc - V56_HONEST_BAR) * 10000, 0)
    if final_test_auc > V56_HONEST_BAR + 0.002 and p_lift_gt_0 >= 0.975:
        verdict = "PROMOTE — F4 features break v5.6 honest bar with CI-backed lift"
    elif final_test_auc > V56_HONEST_BAR - 0.005:
        verdict = "FLAT — within noise of v5.6 honest bar; v5.5 remains deployed"
    else:
        verdict = "REGRESSION — F4 features do not clear v5.6 honest bar; v5.5 remains deployed"
    print(f"\n  v5.6 honest bar:     {V56_HONEST_BAR:.4f}")
    print(f"  Δ vs v5.6 (bp):      {delta_vs_v56_bp:+.0f}")
    print(f"  VERDICT:             {verdict}")

    # ============================================================
    # 5) WRITE RESULTS
    # ============================================================
    result = {
        "version": "form4_bifrost_explosion_v1",
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "methodology": {
            "split": "3-way temporal (train<=2023 / val 2024 / test>=2025)",
            "baseline": "FIXED 60-feature v5.8 final list (not pruned)",
            "feature_selection": "val-only greedy forward over F4 candidates, gate +0.002",
            "hyperparameter_tuning": "val-only C sweep on baseline",
            "arch_sweep": "SKIPPED (v5.8 confirmed Ridge-only wins)",
            "test_touches": 1,
            "bootstrap_boot_n": 2000,
            "bootstrap_seed": 42,
            "bootstrap_method": "percentile",
        },
        "data": {
            "input_csv": str(csv_path),
            "f4_csv": str(F4_CSV),
            "n_events": len(rows),
            "split_counts": {"train": len(train), "val": len(val), "test": len(test)},
            "explosion_rates": {
                "train": round(exp_rate(train), 4),
                "val":   round(exp_rate(val), 4),
                "test":  round(exp_rate(test), 4),
            },
            "f4_coverage": {k: round(v, 4) for k, v in f4_coverage.items()},
            "f4_candidates_n": len(f4_cols),
            "f4_candidates": f4_cols,
        },
        "c_sweep_val_aucs": c_results,
        "best_C": best_C,
        "baseline_val_auc_best_C": round(best_val, 4),
        "greedy_log": greedy_log,
        "selected_f4_features": selected_f4,
        "final_n_features": len(final_cols),
        "baseline_test_auc": round(baseline_test_auc, 4),
        "baseline_test_auc_ci95": ci_baseline,
        "final_test_auc": round(final_test_auc, 4),
        "final_test_auc_ci95": ci_final,
        "lift_vs_baseline": round(final_test_auc - baseline_test_auc, 4),
        "lift_ci95": ci_diff,
        "p_lift_gt_0": round(p_lift_gt_0, 4),
        "v56_honest_bar": V56_HONEST_BAR,
        "v55_deployed_inflated": V55_DEPLOYED_INFLATED,
        "delta_vs_v56_bp": delta_vs_v56_bp,
        "verdict": verdict,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(f"\nResults written: {OUT}")
    print("=" * 78)


if __name__ == "__main__":
    main()
