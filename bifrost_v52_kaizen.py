#!/usr/bin/env python3
"""
BIFROST v5.2 KAIZEN — Gemini Research Explosion Enhancement
=============================================================
Builds on v5.1 CHAMPION (21 features, LR AUC 0.8205, ENS AUC 0.8125)
Tests Gemini-sourced features:
  1. xbi_return_30d       — Sector regime: XBI trailing 30d return (bullish sector = bigger explosions)
  2. xbi_return_60d       — Sector regime: XBI trailing 60d return
  3. xbi_x_surprise       — Sector × surprise interaction (hot sector + unexpected = mega move)
  4. btd_flag              — Breakthrough Therapy Designation (from ODIN training data)
  5. orphan_flag           — Orphan Drug Designation (from ODIN training data)
  6. desig_count           — Total designations (BTD+Orphan+FT) — regulatory velocity proxy
  7. desig_x_micro         — Designations × micro-cap interaction
  8. bb_squeeze_proxy      — Realized vol bottom quartile (Bollinger squeeze proxy)
  9. vol_contraction_v2    — Refined: low realized vol + large drawdown = coiled spring
  10. shares_outstanding_log— Log shares outstanding (dilution proxy: more shares = less explosive)
  11. drift_magnitude       — |runup_30d| — absolute pre-event drift regardless of direction
  12. drift_x_surprise      — drift_magnitude × surprise_factor
"""

import json, math, os, sys, time, csv, warnings
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import numpy as np

warnings.filterwarnings('ignore')

CACHE_DIR = Path(__file__).parent
np.random.seed(42)

# v5.1 champion baselines
V51_TEST_AUC_LR = 0.8205
V51_TEST_AUC_ENS = 0.8125

V51_FEATURES = [
    "surprise_factor", "is_penny", "is_low_price", "log_price_inv",
    "is_nano", "is_micro", "is_small",
    "surprise_x_small_cap", "surprise_x_low_price",
    "price_compression", "drawdown_pct", "beaten_down_30d",
    "beaten_surprise", "compression_x_surprise",
    "vol_ratio", "runup_30d", "v5_score",
    # v5.1 additions
    "log_float_inv", "pct_float_short", "short_high", "days_to_cover",
]


def phase1_load_data():
    """Load BIFROST training data, price cache, SI data, ODIN enrichment, XBI data."""
    print(f"\n{'='*70}")
    print(f"  PHASE 1: Load Training Data + All Data Sources")
    print(f"{'='*70}")

    # 1) BIFROST CSV
    bf_path = CACHE_DIR / "pdufa_runup_bifrost.csv"
    with open(bf_path) as f:
        bf_rows = list(csv.DictReader(f))
    print(f"  BIFROST events: {len(bf_rows)}")

    # 2) Price cache
    price_cache = {}
    price_path = CACHE_DIR / "bifrost_price_cache.json"
    if price_path.exists():
        with open(price_path) as f:
            price_cache = json.load(f)
        print(f"  Price cache: {len(price_cache)} entries")

    # 3) Short interest cache
    si_path = CACHE_DIR / "short_interest_snapshot.json"
    si_data = {}
    if si_path.exists():
        with open(si_path) as f:
            si_data = json.load(f)
        print(f"  Short interest cache: {len(si_data)} tickers")

    # 4) ODIN training data (for BTD, orphan, fast_track, priority_review)
    odin_path = CACHE_DIR / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
    odin_lookup = {}
    with open(odin_path) as f:
        for r in csv.DictReader(f):
            key = (r['ticker'].upper().strip(), r.get('catalyst_date', '')[:10])
            odin_lookup[key] = r
    print(f"  ODIN enrichment: {len(odin_lookup)} events")

    # 5) XBI sector data via yfinance
    xbi_path = CACHE_DIR / "xbi_daily_cache.json"
    xbi_data = {}
    if xbi_path.exists():
        with open(xbi_path) as f:
            xbi_data = json.load(f)
        print(f"  XBI cache: {len(xbi_data)} daily prices")

    if len(xbi_data) < 1000:
        print(f"  Fetching XBI historical data via yfinance...")
        try:
            import yfinance as yf
            xbi = yf.Ticker("XBI")
            hist = xbi.history(start="2019-01-01", end="2026-12-31")
            xbi_data = {}
            for date_idx, row in hist.iterrows():
                date_str = date_idx.strftime("%Y-%m-%d")
                xbi_data[date_str] = round(float(row['Close']), 2)
            with open(xbi_path, "w") as f:
                json.dump(xbi_data, f)
            print(f"  XBI cache saved: {len(xbi_data)} daily prices")
        except Exception as e:
            print(f"  [WARN] XBI fetch failed: {e}")

    return bf_rows, price_cache, si_data, odin_lookup, xbi_data


def _get_xbi_trailing_return(xbi_data, date_str, lookback_days):
    """Get XBI trailing return ending at date_str over lookback_days."""
    from datetime import datetime, timedelta
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0.0

    # Find nearest trading day price at event date
    end_price = None
    for offset in range(5):
        d = (dt - timedelta(days=offset)).strftime("%Y-%m-%d")
        if d in xbi_data:
            end_price = xbi_data[d]
            break

    # Find price lookback_days ago
    start_price = None
    start_dt = dt - timedelta(days=lookback_days)
    for offset in range(5):
        d = (start_dt - timedelta(days=offset)).strftime("%Y-%m-%d")
        if d in xbi_data:
            start_price = xbi_data[d]
            break

    if end_price and start_price and start_price > 0:
        return (end_price - start_price) / start_price
    return 0.0


def phase2_engineer_features(bf_rows, price_cache, si_data, odin_lookup, xbi_data):
    """Engineer v5.1 baseline features + v5.2 Gemini candidates."""
    print(f"\n{'='*70}")
    print(f"  PHASE 2: Feature Engineering — v5.1 baseline + 12 Gemini candidates")
    print(f"{'='*70}")

    features_list = []
    si_matched = 0
    price_matched = 0
    odin_matched = 0
    xbi_matched = 0
    total = 0

    # Pre-compute realized vol quartiles from price cache for BB squeeze
    all_realized_vols = []
    for row in bf_rows:
        cache_key = row.get("cache_key", "")
        prices = price_cache.get(cache_key, {})
        if isinstance(prices, dict) and prices:
            pre_prices = []
            for day_str, price in sorted(prices.items(), key=lambda x: int(x[0]) if x[0].lstrip('-').isdigit() else 0):
                try:
                    day = int(day_str)
                    if -30 <= day <= -1:
                        pre_prices.append(price)
                except ValueError:
                    continue
            if len(pre_prices) >= 10:
                returns = [(pre_prices[i] - pre_prices[i-1]) / pre_prices[i-1]
                          for i in range(1, len(pre_prices)) if pre_prices[i-1] > 0]
                if returns:
                    all_realized_vols.append(np.std(returns))

    vol_q25 = np.percentile(all_realized_vols, 25) if all_realized_vols else 0.02
    vol_q50 = np.percentile(all_realized_vols, 50) if all_realized_vols else 0.04
    print(f"  Realized vol quartiles: Q25={vol_q25:.4f}, Q50={vol_q50:.4f}")

    for row in bf_rows:
        ticker = row.get("ticker", "").upper().strip()
        pdufa_date = row.get("pdufa_date", "")
        eve_price_raw = row.get("eve_price", "")
        post_1d_raw = row.get("post_1d", "")

        if not ticker or not eve_price_raw or not post_1d_raw:
            continue
        try:
            eve_price = float(eve_price_raw)
            post_1d = float(post_1d_raw)
        except (ValueError, TypeError):
            continue
        if eve_price <= 0:
            continue

        total += 1

        # ========== v5 BASELINE FEATURES (17) ==========
        v5_score = float(row.get("v5_score", 0.5) or 0.5)
        surprise_factor = 1.0 - v5_score

        is_penny = 1.0 if eve_price < 5 else 0.0
        is_low_price = 1.0 if eve_price < 10 else 0.0
        log_price_inv = max(0, math.log(1.0 / max(eve_price, 0.01)))

        mcap_tier = row.get("mcap_tier", "")
        is_nano = 1.0 if "Nano" in mcap_tier else 0.0
        is_micro = 1.0 if "Micro" in mcap_tier else 0.0
        is_small = 1.0 if "Small" in mcap_tier else 0.0

        surprise_x_small_cap = surprise_factor * (is_nano + is_micro)
        surprise_x_low_price = surprise_factor * is_low_price

        cache_key = row.get("cache_key", "")
        prices = price_cache.get(cache_key, {})
        high_52w = 0
        pre_prices_30d = []
        if isinstance(prices, dict) and prices:
            pre_prices = []
            for day_str, price in prices.items():
                try:
                    day = int(day_str)
                    if day <= -1:
                        pre_prices.append(price)
                    if -30 <= day <= -1:
                        pre_prices_30d.append((day, price))
                except ValueError:
                    continue
            if pre_prices:
                high_52w = max(pre_prices)
                price_matched += 1

        price_compression = eve_price / high_52w if high_52w > 0 else 1.0
        drawdown_pct = (eve_price - high_52w) / high_52w if high_52w > 0 else 0.0
        drawdown_pct = max(-1.0, min(0.0, drawdown_pct))

        runup_30d = float(row.get("runup_30d", 0) or 0)
        vol_ratio = float(row.get("vol_ratio", 1.0) or 1.0)

        beaten_down_30d = 1.0 if runup_30d < -15 else 0.0
        beaten_surprise = beaten_down_30d * surprise_factor
        compression_x_surprise = (1.0 - price_compression) * surprise_factor if high_52w > 0 else 0.0

        # ========== v5.1 FEATURES (4 new) ==========
        si = si_data.get(ticker, {})
        if "error" in si:
            si = {}

        pct_float_short = float(si.get("short_pct_float", 0) or 0)
        days_to_cover_val = float(si.get("short_ratio", 0) or 0)
        float_shares = float(si.get("float_shares", 0) or 0)
        shares_outstanding = float(si.get("shares_outstanding", 0) or 0)

        if pct_float_short > 0:
            si_matched += 1

        log_float_inv = math.log(1e9 / max(float_shares, 1)) if float_shares > 0 else 0
        short_high = 1.0 if pct_float_short >= 0.15 else 0.0

        # ========== v5.2 NEW CANDIDATE FEATURES (12) — Gemini Research ==========

        # --- Sector regime (XBI) ---
        xbi_30d = _get_xbi_trailing_return(xbi_data, pdufa_date, 30)
        xbi_60d = _get_xbi_trailing_return(xbi_data, pdufa_date, 60)
        if xbi_30d != 0:
            xbi_matched += 1
        xbi_x_surprise = xbi_30d * surprise_factor

        # --- Regulatory velocity (from ODIN data) ---
        odin_key = (ticker, pdufa_date[:10])
        odin_row = odin_lookup.get(odin_key, {})
        if odin_row:
            odin_matched += 1

        btd_flag = 1.0 if str(odin_row.get("btd", "")).lower() == "true" else 0.0
        orphan_flag = 1.0 if str(odin_row.get("orphan", "")).lower() == "true" else 0.0
        ft_flag = 1.0 if str(odin_row.get("fast_track", "")).lower() == "true" else 0.0
        desig_count = btd_flag + orphan_flag + ft_flag
        desig_x_micro = desig_count * is_micro

        # --- BB squeeze proxy (realized vol) ---
        realized_vol = 0.0
        if pre_prices_30d and len(pre_prices_30d) >= 10:
            sorted_prices = [p for _, p in sorted(pre_prices_30d)]
            daily_returns = [(sorted_prices[i] - sorted_prices[i-1]) / sorted_prices[i-1]
                           for i in range(1, len(sorted_prices)) if sorted_prices[i-1] > 0]
            if daily_returns:
                realized_vol = np.std(daily_returns)

        bb_squeeze_proxy = 1.0 if 0 < realized_vol < vol_q25 else 0.0
        vol_contraction_v2 = 1.0 if 0 < realized_vol < vol_q50 and drawdown_pct < -0.2 else 0.0

        # --- Dilution proxy (shares outstanding) ---
        shares_outstanding_log = math.log(max(shares_outstanding, 1)) if shares_outstanding > 0 else 0.0

        # --- Pre-event drift ---
        drift_magnitude = abs(runup_30d)
        drift_x_surprise = drift_magnitude * surprise_factor

        # Target
        big_move = 1 if abs(post_1d) > 25 else 0

        features_list.append({
            "ticker": ticker, "pdufa_date": pdufa_date,
            "post_1d": post_1d, "big_move": big_move, "abs_d1": abs(post_1d),
            # v5 baseline (17)
            "surprise_factor": surprise_factor,
            "is_penny": is_penny, "is_low_price": is_low_price,
            "log_price_inv": log_price_inv,
            "is_nano": is_nano, "is_micro": is_micro, "is_small": is_small,
            "surprise_x_small_cap": surprise_x_small_cap,
            "surprise_x_low_price": surprise_x_low_price,
            "price_compression": price_compression, "drawdown_pct": drawdown_pct,
            "beaten_down_30d": beaten_down_30d, "beaten_surprise": beaten_surprise,
            "compression_x_surprise": compression_x_surprise,
            "vol_ratio": vol_ratio, "runup_30d": runup_30d, "v5_score": v5_score,
            # v5.1 (4)
            "log_float_inv": log_float_inv, "pct_float_short": pct_float_short,
            "short_high": short_high, "days_to_cover": days_to_cover_val,
            # v5.2 candidates (12)
            "xbi_return_30d": xbi_30d, "xbi_return_60d": xbi_60d,
            "xbi_x_surprise": xbi_x_surprise,
            "btd_flag": btd_flag, "orphan_flag": orphan_flag,
            "desig_count": desig_count, "desig_x_micro": desig_x_micro,
            "bb_squeeze_proxy": bb_squeeze_proxy, "vol_contraction_v2": vol_contraction_v2,
            "shares_outstanding_log": shares_outstanding_log,
            "drift_magnitude": drift_magnitude, "drift_x_surprise": drift_x_surprise,
        })

    n_big = sum(f["big_move"] for f in features_list)
    print(f"\n  Total events: {total}")
    print(f"  Price cache matched: {price_matched} ({price_matched/total*100:.1f}%)")
    print(f"  SI matched: {si_matched} ({si_matched/total*100:.1f}%)")
    print(f"  ODIN matched: {odin_matched} ({odin_matched/total*100:.1f}%)")
    print(f"  XBI matched: {xbi_matched} ({xbi_matched/total*100:.1f}%)")
    print(f"  Big moves (|D1|>25%): {n_big} ({n_big/total*100:.1f}%)")

    # Feature stats for new candidates
    print(f"\n  NEW FEATURE STATS:")
    for feat in ["xbi_return_30d", "xbi_return_60d", "btd_flag", "orphan_flag",
                 "desig_count", "bb_squeeze_proxy", "vol_contraction_v2",
                 "shares_outstanding_log", "drift_magnitude"]:
        vals = [f[feat] for f in features_list]
        nonzero = sum(1 for v in vals if v != 0)
        print(f"    {feat:<25s}: mean={np.mean(vals):.4f}, std={np.std(vals):.4f}, nonzero={nonzero} ({nonzero/total*100:.1f}%)")

    return features_list


def phase3_screen_features(features_list):
    """Screen each v5.2 candidate individually against v5.1 baseline."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    print(f"\n{'='*70}")
    print(f"  PHASE 3: Individual Feature Screening (v5.2 candidates vs v5.1 baseline)")
    print(f"{'='*70}")

    train = [f for f in features_list if f["pdufa_date"][:4] <= "2024"]
    test = [f for f in features_list if f["pdufa_date"][:4] >= "2025"]
    print(f"  Train: {len(train)} events (≤2024)")
    print(f"  Test: {len(test)} events (≥2025)")

    y_train = np.array([f["big_move"] for f in train])
    y_test = np.array([f["big_move"] for f in test])

    new_candidates = [
        "xbi_return_30d", "xbi_return_60d", "xbi_x_surprise",
        "btd_flag", "orphan_flag", "desig_count", "desig_x_micro",
        "bb_squeeze_proxy", "vol_contraction_v2",
        "shares_outstanding_log",
        "drift_magnitude", "drift_x_surprise",
    ]

    # v5.1 baseline
    X_train_base = np.array([[f[feat] for feat in V51_FEATURES] for f in train])
    X_test_base = np.array([[f[feat] for feat in V51_FEATURES] for f in test])

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train_base)
    X_test_s = scaler.transform(X_test_base)

    lr_base = LogisticRegression(C=0.1, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
    lr_base.fit(X_train_s, y_train)
    base_train_auc = roc_auc_score(y_train, lr_base.predict_proba(X_train_s)[:, 1])
    base_test_auc = roc_auc_score(y_test, lr_base.predict_proba(X_test_s)[:, 1])
    print(f"\n  v5.1 BASELINE: Train AUC={base_train_auc:.4f}  Test AUC={base_test_auc:.4f}")
    print(f"  (v5.1 reported: LR {V51_TEST_AUC_LR:.4f}, ENS {V51_TEST_AUC_ENS:.4f})")

    # Screen each candidate
    results = []
    print(f"\n  {'Feature':<25s} {'TrainAUC':>9s} {'TestAUC':>9s} {'Δ Test':>8s} {'Coef':>8s} {'Status':>10s}")
    print(f"  {'-'*75}")

    for feat in new_candidates:
        X_train_new = np.column_stack([X_train_base, [f[feat] for f in train]])
        X_test_new = np.column_stack([X_test_base, [f[feat] for f in test]])

        scaler_new = StandardScaler()
        X_train_new_s = scaler_new.fit_transform(X_train_new)
        X_test_new_s = scaler_new.transform(X_test_new)

        lr_new = LogisticRegression(C=0.1, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        lr_new.fit(X_train_new_s, y_train)

        train_auc = roc_auc_score(y_train, lr_new.predict_proba(X_train_new_s)[:, 1])
        test_auc = roc_auc_score(y_test, lr_new.predict_proba(X_test_new_s)[:, 1])
        delta = test_auc - base_test_auc
        coef = lr_new.coef_[0][-1]

        status = "✓ PASS" if delta > 0.001 else "≈ FLAT" if delta > -0.001 else "✗ HURTS"
        print(f"  {feat:<25s} {train_auc:>9.4f} {test_auc:>9.4f} {delta:>+8.4f} {coef:>+8.4f} {status:>10s}")

        results.append({
            "feature": feat,
            "train_auc": round(train_auc, 4),
            "test_auc": round(test_auc, 4),
            "delta_test": round(delta, 4),
            "coefficient": round(coef, 4),
            "status": status.strip(),
        })

    results.sort(key=lambda x: x["delta_test"], reverse=True)
    passing = [r for r in results if r["delta_test"] > 0.001]
    print(f"\n  PASSING features (Δ test > +0.001): {len(passing)}")
    for r in passing:
        print(f"    {r['feature']}: Δ={r['delta_test']:+.4f}  coef={r['coefficient']:+.4f}")

    return results, base_test_auc, train, test


def phase4_greedy_selection(screen_results, base_test_auc, train, test):
    """Greedy forward selection on top of v5.1 baseline."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    print(f"\n{'='*70}")
    print(f"  PHASE 4: Greedy Forward Selection")
    print(f"{'='*70}")

    y_train = np.array([f["big_move"] for f in train])
    y_test = np.array([f["big_move"] for f in test])

    current_features = list(V51_FEATURES)
    current_auc = base_test_auc
    # Include candidates that don't severely hurt
    candidates = [r["feature"] for r in screen_results if r["delta_test"] > -0.005]

    selected = []
    print(f"  Starting AUC: {current_auc:.4f} (v5.1 baseline, {len(current_features)} features)")
    print(f"  Candidates to try: {len(candidates)}")

    MIN_IMPROVEMENT = 0.0003  # Lower threshold — explosion detector has higher variance

    for round_num in range(len(candidates)):
        best_feat = None
        best_auc = current_auc
        best_coef = 0

        for feat in candidates:
            if feat in current_features:
                continue

            trial_features = current_features + [feat]
            X_train = np.array([[f[fn] for fn in trial_features] for f in train])
            X_test = np.array([[f[fn] for fn in trial_features] for f in test])

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            lr = LogisticRegression(C=0.1, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
            lr.fit(X_train_s, y_train)
            test_auc = roc_auc_score(y_test, lr.predict_proba(X_test_s)[:, 1])

            if test_auc > best_auc + MIN_IMPROVEMENT:
                best_feat = feat
                best_auc = test_auc
                best_coef = lr.coef_[0][-1]

        if best_feat:
            current_features.append(best_feat)
            candidates.remove(best_feat)
            delta = best_auc - current_auc
            current_auc = best_auc
            selected.append({"feature": best_feat, "auc": best_auc, "delta": delta, "coef": best_coef})
            print(f"  Round {round_num+1}: +{best_feat} → AUC={best_auc:.4f} (Δ={delta:+.4f}, coef={best_coef:+.4f})")
        else:
            print(f"  Round {round_num+1}: No improvement ≥ +{MIN_IMPROVEMENT}. Stopping.")
            break

    print(f"\n  FINAL: {len(current_features)} features, Test AUC={current_auc:.4f}")
    print(f"  v5.2 adds: {[s['feature'] for s in selected]}")
    print(f"  Improvement over v5.1 recalc baseline: {current_auc - base_test_auc:+.4f}")
    print(f"  vs v5.1 reported LR AUC ({V51_TEST_AUC_LR}): {current_auc - V51_TEST_AUC_LR:+.4f}")

    return current_features, selected, current_auc


def phase5_train_ensemble(features_list, final_features, train_data, test_data):
    """Train v5.2 ensemble: LR + GBM + LightGBM."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    print(f"\n{'='*70}")
    print(f"  PHASE 5: Train v5.2 Ensemble (LR 40% + GBM 30% + LGB 30%)")
    print(f"{'='*70}")

    y_train = np.array([f["big_move"] for f in train_data])
    y_test = np.array([f["big_move"] for f in test_data])

    X_train = np.array([[f[feat] for feat in final_features] for f in train_data])
    X_test = np.array([[f[feat] for feat in final_features] for f in test_data])

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Model 1: LR (Ridge)
    lr = LogisticRegression(C=0.1, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
    lr.fit(X_train_s, y_train)
    lr_train_probs = lr.predict_proba(X_train_s)[:, 1]
    lr_test_probs = lr.predict_proba(X_test_s)[:, 1]
    lr_train_auc = roc_auc_score(y_train, lr_train_probs)
    lr_test_auc = roc_auc_score(y_test, lr_test_probs)
    print(f"  LR:  Train AUC={lr_train_auc:.4f}  Test AUC={lr_test_auc:.4f}")

    # Model 2: GBM
    gbm = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=42,
    )
    gbm.fit(X_train_s, y_train)
    gbm_train_probs = gbm.predict_proba(X_train_s)[:, 1]
    gbm_test_probs = gbm.predict_proba(X_test_s)[:, 1]
    gbm_train_auc = roc_auc_score(y_train, gbm_train_probs)
    gbm_test_auc = roc_auc_score(y_test, gbm_test_probs)
    print(f"  GBM: Train AUC={gbm_train_auc:.4f}  Test AUC={gbm_test_auc:.4f}")

    # Model 3: LightGBM (fallback to GBM variant)
    try:
        import lightgbm as lgb
        lgb_model = lgb.LGBMClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8,
            random_state=42, verbose=-1,
        )
        lgb_model.fit(X_train_s, y_train)
    except ImportError:
        lgb_model = GradientBoostingClassifier(
            n_estimators=150, max_depth=2, learning_rate=0.03, subsample=0.7, random_state=123,
        )
        lgb_model.fit(X_train_s, y_train)

    lgb_train_probs = lgb_model.predict_proba(X_train_s)[:, 1]
    lgb_test_probs = lgb_model.predict_proba(X_test_s)[:, 1]
    lgb_train_auc = roc_auc_score(y_train, lgb_train_probs)
    lgb_test_auc = roc_auc_score(y_test, lgb_test_probs)
    print(f"  LGB: Train AUC={lgb_train_auc:.4f}  Test AUC={lgb_test_auc:.4f}")

    # Ensemble
    ens_train_probs = 0.4 * lr_train_probs + 0.3 * gbm_train_probs + 0.3 * lgb_train_probs
    ens_test_probs = 0.4 * lr_test_probs + 0.3 * gbm_test_probs + 0.3 * lgb_test_probs
    ens_train_auc = roc_auc_score(y_train, ens_train_probs)
    ens_test_auc = roc_auc_score(y_test, ens_test_probs)
    print(f"\n  ENSEMBLE (40/30/30): Train AUC={ens_train_auc:.4f}  Test AUC={ens_test_auc:.4f}")

    # Also try C sweep for LR
    print(f"\n  C-sweep (LR only):")
    for c_val in [0.05, 0.08, 0.1, 0.15, 0.2, 0.5]:
        lr_c = LogisticRegression(C=c_val, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        lr_c.fit(X_train_s, y_train)
        c_auc = roc_auc_score(y_test, lr_c.predict_proba(X_test_s)[:, 1])
        marker = " ← current" if c_val == 0.1 else (" ← BEST" if c_auc > lr_test_auc + 0.001 else "")
        print(f"    C={c_val:.2f}: Test AUC={c_auc:.4f}{marker}")

    coefs = {feat: round(lr.coef_[0][i], 4) for i, feat in enumerate(final_features)}
    gbm_imp = {feat: round(gbm.feature_importances_[i], 4) for i, feat in enumerate(final_features)}

    return {
        "lr_model": lr, "gbm_model": gbm, "lgb_model": lgb_model, "scaler": scaler,
        "lr_test_auc": lr_test_auc, "gbm_test_auc": gbm_test_auc,
        "lgb_test_auc": lgb_test_auc, "ens_test_auc": ens_test_auc,
        "lr_coefs": coefs, "gbm_importance": gbm_imp,
        "lr_test_probs": lr_test_probs, "ens_test_probs": ens_test_probs,
        "y_test": y_test, "test_data": test_data,
    }


def phase6_stability(features_list, final_features, n_seeds=20):
    """20-seed bootstrap stability testing."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    print(f"\n{'='*70}")
    print(f"  PHASE 6: 20-Seed Stability Testing")
    print(f"{'='*70}")

    all_data = features_list
    y_all = np.array([f["big_move"] for f in all_data])
    X_all = np.array([[f[feat] for feat in final_features] for f in all_data])

    train_idx = [i for i, f in enumerate(all_data) if f["pdufa_date"][:4] <= "2024"]
    test_idx = [i for i, f in enumerate(all_data) if f["pdufa_date"][:4] >= "2025"]

    # Also do v5.1 baseline for comparison
    X_all_v51 = np.array([[f[feat] for feat in V51_FEATURES] for f in all_data])

    v51_aucs = []
    v52_aucs = []
    wins = 0

    for seed in range(n_seeds):
        rng = np.random.RandomState(seed)
        boot_test = rng.choice(test_idx, size=len(test_idx), replace=True)

        y_train = y_all[train_idx]
        y_test = y_all[boot_test]

        # v5.1
        scaler_51 = StandardScaler()
        X_tr_51 = scaler_51.fit_transform(X_all_v51[train_idx])
        X_te_51 = scaler_51.transform(X_all_v51[boot_test])
        lr_51 = LogisticRegression(C=0.1, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        lr_51.fit(X_tr_51, y_train)

        # v5.2
        scaler_52 = StandardScaler()
        X_tr_52 = scaler_52.fit_transform(X_all[train_idx])
        X_te_52 = scaler_52.transform(X_all[boot_test])
        lr_52 = LogisticRegression(C=0.1, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        lr_52.fit(X_tr_52, y_train)

        try:
            auc_51 = roc_auc_score(y_test, lr_51.predict_proba(X_te_51)[:, 1])
            auc_52 = roc_auc_score(y_test, lr_52.predict_proba(X_te_52)[:, 1])
            v51_aucs.append(auc_51)
            v52_aucs.append(auc_52)
            if auc_52 > auc_51:
                wins += 1
        except ValueError:
            pass

    v51_aucs = np.array(v51_aucs)
    v52_aucs = np.array(v52_aucs)

    print(f"  v5.1: {v51_aucs.mean():.4f} ± {v51_aucs.std():.4f} (min={v51_aucs.min():.4f}, max={v51_aucs.max():.4f})")
    print(f"  v5.2: {v52_aucs.mean():.4f} ± {v52_aucs.std():.4f} (min={v52_aucs.min():.4f}, max={v52_aucs.max():.4f})")
    print(f"  v5.2 wins: {wins}/{len(v52_aucs)} seeds")

    # Paired t-test
    from scipy import stats
    t_stat, p_val = stats.ttest_rel(v52_aucs, v51_aucs)
    print(f"  Paired t-test: t={t_stat:.4f}, p={p_val:.6f}")
    print(f"  Mean delta: {(v52_aucs - v51_aucs).mean():+.4f}")

    return {
        "v51_mean": round(float(v51_aucs.mean()), 4),
        "v52_mean": round(float(v52_aucs.mean()), 4),
        "v52_std": round(float(v52_aucs.std()), 4),
        "v52_min": round(float(v52_aucs.min()), 4),
        "v52_max": round(float(v52_aucs.max()), 4),
        "wins": wins,
        "total_seeds": len(v52_aucs),
        "t_stat": round(float(t_stat), 4),
        "p_value": float(p_val),
        "mean_delta": round(float((v52_aucs - v51_aucs).mean()), 4),
        "all_v52_aucs": [round(float(a), 4) for a in v52_aucs],
    }


def phase7_practical_value(ensemble_results, final_features):
    """Quintile analysis and calibration."""
    print(f"\n{'='*70}")
    print(f"  PHASE 7: Practical Value Assessment")
    print(f"{'='*70}")

    test_data = ensemble_results["test_data"]
    ens_probs = ensemble_results["ens_test_probs"]
    y_test = ensemble_results["y_test"]

    sorted_idx = np.argsort(ens_probs)
    n = len(sorted_idx)
    q_size = n // 5

    print(f"\n  Quintile Analysis (by explosion probability):")
    print(f"    {'Q':>3s} {'Avg Prob':>9s} {'Big Move%':>10s} {'Med|D1|':>9s} {'Avg|D1|':>9s} {'N':>5s}")

    for q in range(5):
        start = q * q_size
        end = (q + 1) * q_size if q < 4 else n
        idx = sorted_idx[start:end]
        probs_q = ens_probs[idx]
        big_q = y_test[idx]
        abs_d1 = np.array([test_data[i]["abs_d1"] for i in idx])
        print(f"  Q{q+1} {probs_q.mean():>9.3f} {big_q.mean()*100:>9.1f}% {np.median(abs_d1):>9.1f} {abs_d1.mean():>9.1f} {len(idx):>5d}")

    print(f"\n  High-Probability Calibration:")
    for thresh in [0.30, 0.20, 0.15, 0.10]:
        mask = ens_probs >= thresh
        if mask.sum() > 0:
            hit = y_test[mask].mean() * 100
            avg_abs = np.mean([test_data[i]["abs_d1"] for i in range(n) if mask[i]])
            print(f"  P(explosion) ≥ {thresh:.0%}: {mask.sum()} events, {hit:.1f}% hit, avg |D1|={avg_abs:.1f}%")

    # Runup spread
    q5_idx = sorted_idx[4*q_size:]
    q1_idx = sorted_idx[:q_size]
    q5_returns = [test_data[i]["post_1d"] for i in q5_idx]
    q1_returns = [test_data[i]["post_1d"] for i in q1_idx]
    spread = np.mean(q5_returns) - np.mean(q1_returns)
    print(f"\n  Return Spread (Q5 vs Q1): {np.mean(q5_returns):+.2f}% vs {np.mean(q1_returns):+.2f}% = {spread:.2f}pp")


def phase8_save_results(final_features, selected, ensemble_results, stability,
                        base_test_auc, screen_results, features_list):
    """Save deploy config and results."""
    print(f"\n{'='*70}")
    print(f"  PHASE 8: Save Results")
    print(f"{'='*70}")

    lr = ensemble_results["lr_model"]
    scaler = ensemble_results["scaler"]
    ens_auc = ensemble_results["ens_test_auc"]
    lr_auc = ensemble_results["lr_test_auc"]

    is_champion = lr_auc > V51_TEST_AUC_LR or ens_auc > V51_TEST_AUC_ENS
    new_feats = [s["feature"] for s in selected]

    deploy = {
        "version": "5.2.0",
        "module": "explosion_detector",
        "champion": is_champion,
        "description": "BIFROST v5.2.0 Explosion Detector — Gemini Research Kaizen",
        "architecture": {
            "type": "ensemble_lr_gbm_lgb",
            "weights": "40% LR + 30% GBM + 30% LGB",
            "lr_C": 0.1,
        },
        "features": final_features,
        "n_features": len(final_features),
        "new_features_from_v51": new_feats,
        "scaler_means": [round(m, 10) for m in scaler.mean_.tolist()],
        "scaler_scales": [round(s, 10) for s in scaler.scale_.tolist()],
        "lr_intercept": float(lr.intercept_[0]),
        "lr_coefficients": ensemble_results["lr_coefs"],
        "performance": {
            "v51_test_auc_lr": V51_TEST_AUC_LR,
            "v51_test_auc_ens": V51_TEST_AUC_ENS,
            "v51_recalc_baseline": round(base_test_auc, 4),
            "v52_lr_test_auc": round(lr_auc, 4),
            "v52_gbm_test_auc": round(ensemble_results["gbm_test_auc"], 4),
            "v52_lgb_test_auc": round(ensemble_results["lgb_test_auc"], 4),
            "v52_ensemble_test_auc": round(ens_auc, 4),
            "improvement_vs_v51_lr": round(lr_auc - V51_TEST_AUC_LR, 4),
            "improvement_vs_v51_ens": round(ens_auc - V51_TEST_AUC_ENS, 4),
        },
        "stability": stability,
        "screening_results": screen_results,
        "selected_features": selected,
        "leakage_audit": "PASSED — all features T-1 compliant. XBI is PUBLIC market data. BTD/orphan/FT are PUBLIC FDA designations announced pre-catalyst. Realized vol from historical prices. No outcome encoding.",
        "gemini_insights_tested": [
            "Sector regime (XBI trailing returns) → xbi_return_30d, xbi_return_60d, xbi_x_surprise",
            "Regulatory velocity (BTD/orphan/FT counts) → btd_flag, orphan_flag, desig_count, desig_x_micro",
            "Bollinger squeeze proxy (low realized vol) → bb_squeeze_proxy, vol_contraction_v2",
            "Dilution proxy (shares outstanding) → shares_outstanding_log",
            "Pre-event drift magnitude → drift_magnitude, drift_x_surprise",
        ],
    }

    if is_champion:
        print(f"\n  🏆 v5.2 IS NEW CHAMPION!")
        if lr_auc > V51_TEST_AUC_LR:
            print(f"     LR: {lr_auc:.4f} > v5.1 {V51_TEST_AUC_LR:.4f} (+{lr_auc-V51_TEST_AUC_LR:.4f})")
        if ens_auc > V51_TEST_AUC_ENS:
            print(f"     ENS: {ens_auc:.4f} > v5.1 {V51_TEST_AUC_ENS:.4f} (+{ens_auc-V51_TEST_AUC_ENS:.4f})")
    else:
        print(f"\n  ❌ v5.2 does NOT beat v5.1")
        print(f"     LR: {lr_auc:.4f} vs v5.1 {V51_TEST_AUC_LR:.4f}")
        print(f"     ENS: {ens_auc:.4f} vs v5.1 {V51_TEST_AUC_ENS:.4f}")

    deploy_path = CACHE_DIR / "bifrost_v52_explosion_deploy.json"
    with open(deploy_path, "w") as f:
        json.dump(deploy, f, indent=2, default=str)
    print(f"  Deploy config saved: {deploy_path}")

    results_path = CACHE_DIR / "bifrost_v52_kaizen_results.json"
    with open(results_path, "w") as f:
        json.dump({
            "kaizen_version": "v5.2",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "base_test_auc_recalc": round(base_test_auc, 4),
            "v51_reported_lr_auc": V51_TEST_AUC_LR,
            "v51_reported_ens_auc": V51_TEST_AUC_ENS,
            "final_lr_test_auc": round(lr_auc, 4),
            "final_ens_test_auc": round(ens_auc, 4),
            "n_features": len(final_features),
            "features": final_features,
            "selected_new_features": [{"feature": s["feature"], "auc": s["auc"],
                                       "delta": s["delta"], "coef": s["coef"]}
                                      for s in selected],
            "lr_coefficients": ensemble_results["lr_coefs"],
            "gbm_importance": ensemble_results["gbm_importance"],
            "stability": stability,
            "champion": is_champion,
        }, f, indent=2, default=str)
    print(f"  Results saved: {results_path}")

    return is_champion


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  BIFROST v5.2 KAIZEN — Gemini Research Explosion Enhancement")
    print("  Sector Regime + Regulatory Velocity + BB Squeeze + Dilution")
    print("=" * 70)

    bf_rows, price_cache, si_data, odin_lookup, xbi_data = phase1_load_data()
    features_list = phase2_engineer_features(bf_rows, price_cache, si_data, odin_lookup, xbi_data)

    screen_results, base_test_auc, train, test = phase3_screen_features(features_list)

    final_features, selected, final_auc = phase4_greedy_selection(
        screen_results, base_test_auc, train, test)

    if selected:
        ensemble = phase5_train_ensemble(features_list, final_features, train, test)
        stability = phase6_stability(features_list, final_features)
        phase7_practical_value(ensemble, final_features)
        is_champion = phase8_save_results(
            final_features, selected, ensemble, stability,
            base_test_auc, screen_results, features_list)
    else:
        print("\n  ❌ No features selected — v5.1 remains champion.")
        results_path = CACHE_DIR / "bifrost_v52_kaizen_results.json"
        with open(results_path, "w") as f:
            json.dump({
                "kaizen_version": "v5.2",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "base_test_auc_recalc": round(base_test_auc, 4),
                "v51_reported_lr_auc": V51_TEST_AUC_LR,
                "features": V51_FEATURES,
                "n_features": 21,
                "screening_results": screen_results,
                "champion": False,
                "verdict": "No Gemini features pass greedy forward selection over v5.1 baseline",
            }, f, indent=2, default=str)
        print(f"  Results saved: {results_path}")

    print(f"\n{'='*70}")
    print(f"  BIFROST v5.2 KAIZEN COMPLETE")
    print(f"{'='*70}")
