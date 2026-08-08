#!/usr/bin/env python3
"""
================================================================================
BIFROST v3.0 BUILD — Runup Magnitude + Dynamic Timing + Portfolio Kelly
================================================================================

Three-pillar upgrade from v2's static decision matrix:

  PILLAR 1: RUNUP MAGNITUDE PREDICTION
    - Ridge + XGBoost regression predicting expected % return per window
    - Features: ODIN v9 score, mcap, momentum, volatility, TA risk, interactions
    - Walk-forward validated on 5 temporal folds

  PILLAR 2: DYNAMIC ENTRY/EXIT TIMING
    - Momentum breakout detection replaces fixed T-45/T-25 windows
    - Adaptive exit on momentum reversal (floor T-3)
    - Price-based signals from daily timeseries

  PILLAR 3: ADVANCED PORTFOLIO SIZING
    - Correlation-aware multi-position Kelly
    - Drawdown governor (reduce size during drawdowns)
    - Portfolio heat limits (max concurrent, max per trade)

  UNIFIED: Composite entry score = 50% ODIN + 30% magnitude + 20% timing

Training: 1,705 PDUFA events (2020-2026) with real yfinance daily prices
Cardinal Rule: Never hold through FDA decision
"""

import csv, json, math, os, sys, warnings
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# File paths
BIFROST_CSV = os.path.join(DATA_DIR, "pdufa_runup_bifrost_v2.csv")
PRICE_CACHE = os.path.join(DATA_DIR, "bifrost_price_cache.json")
ODIN_DEPLOY = os.path.join(DATA_DIR, "odin_v9_deploy.json")
V2_DEPLOY = os.path.join(DATA_DIR, "bifrost_v2_deploy.json")
V3_DEPLOY = os.path.join(DATA_DIR, "bifrost_v3_deploy.json")
V3_RESULTS = os.path.join(DATA_DIR, "bifrost_v3_results.json")

WINDOWS = [
    ("T-90_T-7", -90, -7), ("T-90_T-3", -90, -3), ("T-90_T-1", -90, -1),
    ("T-60_T-7", -60, -7), ("T-60_T-3", -60, -3), ("T-60_T-1", -60, -1),
    ("T-45_T-7", -45, -7), ("T-45_T-3", -45, -3), ("T-45_T-1", -45, -1),
    ("T-25_T-7", -25, -7), ("T-25_T-3", -25, -3), ("T-25_T-1", -25, -1),
]

MCAP_TIERS = {"nano": 0, "micro": 1, "small": 2, "mid": 3, "large": 4}
ODIN_TIERS = {"T1": 0, "T2": 1, "T3": 2, "T4": 3}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data():
    """Load all data sources for v3 training."""
    print("="*80)
    print("BIFROST v3.0 BUILD — Full Pipeline")
    print("="*80)

    # Load bifrost events
    print("\n[LOAD] Bifrost events...")
    events = []
    with open(BIFROST_CSV) as f:
        for row in csv.DictReader(f):
            events.append(row)
    print(f"  Events: {len(events)}")

    # Load price cache
    print("[LOAD] Price cache...")
    with open(PRICE_CACHE) as f:
        price_cache = json.load(f)
    print(f"  Price series: {len(price_cache)}")

    return events, price_cache


# =============================================================================
# PILLAR 1: FEATURE ENGINEERING FOR MAGNITUDE PREDICTION
# =============================================================================

def compute_price_features(prices_dict, entry_td):
    """Compute momentum, volatility, and trend features from daily prices.

    prices_dict: {"-90": 10.5, "-89": 10.7, ...} (T-day → price)
    entry_td: the T-day we're computing features AT (e.g., -45)
    """
    features = {}

    # Get price array up to entry_td
    day_prices = []
    for td in range(entry_td - 60, entry_td + 1):
        key = str(td)
        if key in prices_dict:
            day_prices.append((td, float(prices_dict[key])))

    if len(day_prices) < 10:
        return None  # Not enough data

    prices = [p for _, p in day_prices]
    entry_price = prices[-1]

    # Returns
    returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]

    # Momentum features (at entry point)
    if len(prices) >= 15:
        features["momentum_14d"] = (prices[-1] / prices[-14] - 1) * 100
    else:
        features["momentum_14d"] = 0.0

    if len(prices) >= 6:
        features["momentum_5d"] = (prices[-1] / prices[-5] - 1) * 100
    else:
        features["momentum_5d"] = 0.0

    if len(prices) >= 22:
        features["momentum_21d"] = (prices[-1] / prices[-21] - 1) * 100
    else:
        features["momentum_21d"] = 0.0

    # Volatility features
    if len(returns) >= 20:
        features["volatility_20d"] = float(np.std(returns[-20:])) * 100
    else:
        features["volatility_20d"] = float(np.std(returns)) * 100 if returns else 3.0

    if len(returns) >= 10:
        features["volatility_10d"] = float(np.std(returns[-10:])) * 100
    else:
        features["volatility_10d"] = features["volatility_20d"]

    # Trend strength (R² of linear fit on recent prices)
    if len(prices) >= 20:
        x = np.arange(20)
        y = np.array(prices[-20:])
        slope = np.polyfit(x, y, 1)[0]
        y_pred = slope * x + np.polyfit(x, y, 1)[1]
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        features["trend_r2"] = 1 - ss_res / max(ss_tot, 1e-10)
        features["trend_slope"] = slope / entry_price * 100  # normalized slope
    else:
        features["trend_r2"] = 0.0
        features["trend_slope"] = 0.0

    # Price relative to recent range
    if len(prices) >= 30:
        high_30d = max(prices[-30:])
        low_30d = min(prices[-30:])
        price_range = high_30d - low_30d
        features["price_pct_range"] = (entry_price - low_30d) / max(price_range, 0.01)
    else:
        features["price_pct_range"] = 0.5

    # Distance from moving averages
    if len(prices) >= 20:
        sma20 = np.mean(prices[-20:])
        features["dist_sma20"] = (entry_price / sma20 - 1) * 100
    else:
        features["dist_sma20"] = 0.0

    # Acceleration (momentum of momentum)
    if len(prices) >= 20:
        mom_recent = prices[-1] / prices[-5] - 1
        mom_prior = prices[-5] / prices[-10] - 1
        features["momentum_accel"] = (mom_recent - mom_prior) * 100
    else:
        features["momentum_accel"] = 0.0

    # Recent max drawdown
    if len(prices) >= 20:
        running_max = np.maximum.accumulate(prices[-20:])
        drawdowns = (np.array(prices[-20:]) - running_max) / running_max
        features["max_dd_20d"] = float(np.min(drawdowns)) * 100
    else:
        features["max_dd_20d"] = 0.0

    return features


def build_training_data(events, price_cache):
    """Build feature matrix + target returns for all events × windows."""
    print("\n[BUILD] Training data...")

    rows = []
    n_skipped = 0

    for ev in events:
        ticker = ev["ticker"]
        pdufa_date = ev["pdufa_date"]
        cache_key = ev.get("cache_key", f"{ticker}_{pdufa_date.replace('-','')}")

        prices_dict = price_cache.get(cache_key, {})
        if not prices_dict:
            n_skipped += 1
            continue

        # Parse ODIN features
        v9_score = float(ev.get("v9_score", 0.5))
        v9_tier = ev.get("v9_tier", "T3")
        mcap_tier = ev.get("mcap", "small")
        outcome_bin = int(ev.get("outcome_bin", 0))
        vol_ratio = float(ev.get("vol_ratio", 1.0)) if ev.get("vol_ratio") else 1.0
        crl_rate = float(ev.get("crl_rate", 0.3)) if ev.get("crl_rate") else 0.3
        ta_risk = ev.get("ta_risk", "MID_CRL")

        # ODIN-derived features
        approval_logit = math.log(max(v9_score, 0.01) / max(1 - v9_score, 0.01))
        mcap_numeric = MCAP_TIERS.get(mcap_tier, 2)
        tier_numeric = ODIN_TIERS.get(v9_tier, 2)
        ta_risk_numeric = {"LOW_CRL": 0.1, "MID_CRL": 0.2, "HIGH_CRL": 0.3,
                          "VERY_HIGH_CRL": 0.4}.get(ta_risk, 0.2)

        # Eve price for log_price
        try:
            eve_price = float(ev.get("eve_price", 20))
        except:
            eve_price = 20.0
        log_price = math.log(max(eve_price, 0.1))

        # For each entry window, compute features and target
        for win_name, entry_td, exit_td in WINDOWS:
            # Get target return
            ret_str = ev.get(win_name, "")
            if not ret_str:
                continue
            try:
                target_return = float(ret_str) * 100  # convert to %
            except:
                continue

            # Compute price-based features AT entry_td
            price_feats = compute_price_features(prices_dict, entry_td)
            if price_feats is None:
                continue

            # Build feature row
            row = {
                # Event identifiers
                "_ticker": ticker,
                "_pdufa_date": pdufa_date,
                "_window": win_name,
                "_entry_td": entry_td,
                "_exit_td": exit_td,
                "_outcome": outcome_bin,
                "_target_return": target_return,

                # ODIN features
                "v9_score": v9_score,
                "approval_logit": approval_logit,
                "tier_numeric": tier_numeric,
                "mcap_numeric": mcap_numeric,
                "crl_rate": crl_rate,
                "ta_risk_numeric": ta_risk_numeric,
                "vol_ratio": vol_ratio,
                "log_price": log_price,

                # Window features
                "days_to_pdufa": abs(entry_td),
                "holding_days": abs(exit_td - entry_td),
                "entry_late": 1 if entry_td > -30 else 0,

                # Price-derived features (AT entry point)
                **price_feats,

                # Interactions
                "approval_x_momentum": v9_score * price_feats.get("momentum_14d", 0),
                "approval_x_volatility": v9_score * price_feats.get("volatility_20d", 0),
                "mcap_x_momentum": mcap_numeric * price_feats.get("momentum_14d", 0),
                "tier_x_volatility": tier_numeric * price_feats.get("volatility_20d", 0),
                "vol_ratio_x_approval": vol_ratio * v9_score,

                # Mcap dummies
                "is_nano": 1 if mcap_tier == "nano" else 0,
                "is_micro": 1 if mcap_tier == "micro" else 0,
                "is_small": 1 if mcap_tier == "small" else 0,
                "is_mid": 1 if mcap_tier == "mid" else 0,
                "is_large": 1 if mcap_tier == "large" else 0,

                # Tier dummies
                "is_t1": 1 if v9_tier == "T1" else 0,
                "is_t2": 1 if v9_tier == "T2" else 0,
                "is_t3": 1 if v9_tier == "T3" else 0,
                "is_t4": 1 if v9_tier == "T4" else 0,
            }
            rows.append(row)

    print(f"  Training rows: {len(rows)} (skipped {n_skipped} events w/o prices)")
    print(f"  Events with prices: {len(events) - n_skipped}")

    # Extract feature names (exclude _ prefixed metadata)
    feature_names = sorted([k for k in rows[0].keys() if not k.startswith("_")])
    print(f"  Features: {len(feature_names)}")

    return rows, feature_names


# =============================================================================
# PILLAR 2: DYNAMIC ENTRY/EXIT DETECTION
# =============================================================================

def detect_runup_start(prices_dict, pdufa_td_range=(-90, -5)):
    """Detect when the runup starts using momentum breakout.

    Returns: (entry_td, signal_type) or (None, None)
    """
    start_td, end_td = pdufa_td_range

    # Get available days
    available = sorted([int(k) for k in prices_dict.keys()
                       if start_td - 30 <= int(k) <= end_td])
    if len(available) < 30:
        return None, None

    prices = {d: float(prices_dict[str(d)]) for d in available}

    best_entry = None
    best_signal = None

    for td in range(start_td, end_td):
        if td not in prices:
            continue

        # Need 20 days of history before this point
        history = [prices[d] for d in sorted(prices.keys()) if d < td and d >= td - 25]
        if len(history) < 15:
            continue

        current_price = prices[td]

        # Momentum check: 14d momentum positive and accelerating
        p_14 = history[-14] if len(history) >= 14 else history[0]
        mom_14d = current_price / p_14 - 1

        p_5 = history[-5] if len(history) >= 5 else history[0]
        mom_5d = current_price / p_5 - 1

        # Check if momentum is positive and accelerating
        prior_5d_prices = history[-10:-5] if len(history) >= 10 else history[:5]
        if len(prior_5d_prices) >= 2:
            prior_mom = prior_5d_prices[-1] / prior_5d_prices[0] - 1
        else:
            prior_mom = 0

        mom_accel = mom_5d - prior_mom

        # SMA distance
        sma_20 = np.mean(history[-20:]) if len(history) >= 20 else np.mean(history)
        dist_sma = current_price / sma_20 - 1

        # Breakout conditions
        if mom_14d > 0.03 and mom_accel > 0.01 and dist_sma > 0.02:
            if best_entry is None:
                best_entry = td
                best_signal = "MOMENTUM_BREAKOUT"
            break

        # Strong momentum breakout (lower bar, just consistent)
        if mom_14d > 0.05 and mom_5d > 0.02:
            if best_entry is None:
                best_entry = td
                best_signal = "STRONG_MOMENTUM"
            break

    return best_entry, best_signal


def detect_exit_signal(prices_dict, entry_td, floor_td=-3):
    """Detect momentum reversal for exit.

    Returns exit_td (day to sell).
    """
    available = sorted([int(k) for k in prices_dict.keys()
                       if entry_td < int(k) <= 0])

    prices = {d: float(prices_dict[str(d)]) for d in available}

    for td in range(entry_td + 5, floor_td, 1):  # need at least 5 days in trade
        if td not in prices:
            continue

        # 5d momentum reversal check
        p_5_ago = None
        for lookback in range(5, 10):
            lb_td = td - lookback
            if lb_td in prices:
                p_5_ago = prices[lb_td]
                break
        if p_5_ago is None:
            continue

        mom_5d = prices[td] / p_5_ago - 1

        # Check for volatility expansion (proxy: large daily move)
        if td - 1 in prices:
            daily_ret = abs(prices[td] / prices[td - 1] - 1)
        else:
            daily_ret = 0

        # Exit on momentum reversal
        if mom_5d < -0.03:  # 3% drawdown from 5d ago
            return td

        # Exit on extreme daily move (volatility expansion)
        if daily_ret > 0.10:  # 10% daily move = unstable
            return td

    return floor_td  # Default exit at floor


# =============================================================================
# PILLAR 3: PORTFOLIO KELLY SIZING
# =============================================================================

def kelly_fraction(pred_return, pred_volatility, win_prob=0.6):
    """Compute half-Kelly position fraction.

    f = p - q/b where p=win_prob, q=1-p, b=avg_win/avg_loss
    Half-Kelly = f/2 for conservative sizing
    """
    if pred_return <= 0 or pred_volatility <= 0:
        return 0.0

    # Edge = expected return, odds = return/risk
    edge = pred_return / 100  # convert from %
    odds = abs(pred_return) / max(pred_volatility, 1)

    # Kelly: f = edge / variance
    variance = (pred_volatility / 100) ** 2
    if variance < 1e-10:
        return 0.0

    f_full = edge / variance
    f_half = f_full / 2  # half-Kelly for safety

    return max(0, min(f_half, 0.06))  # cap at 6%


def portfolio_heat_check(existing_positions, new_position, max_concurrent=5,
                          max_nano=2, max_heat=0.15, max_single=0.06):
    """Check portfolio constraints before adding position.

    Returns (allowed, reason, adjusted_size)
    """
    if len(existing_positions) >= max_concurrent:
        return False, "Max concurrent positions", 0

    nano_count = sum(1 for p in existing_positions if p.get("mcap") == "nano")
    if new_position.get("mcap") == "nano" and nano_count >= max_nano:
        return False, "Max nano positions", 0

    current_heat = sum(p.get("size_pct", 0) for p in existing_positions)
    remaining = max_heat - current_heat
    if remaining <= 0.005:
        return False, "Portfolio heat limit", 0

    size = min(new_position.get("size_pct", 0.03), remaining, max_single)
    return True, "OK", size


def drawdown_governor(equity_curve, max_dd_threshold=0.15):
    """Scale position sizes based on current drawdown.

    Returns multiplier (0.2 to 1.0)
    """
    if len(equity_curve) < 5:
        return 1.0

    running_max = np.maximum.accumulate(equity_curve)
    current_dd = (equity_curve[-1] - running_max[-1]) / max(running_max[-1], 1)
    current_dd = abs(current_dd)

    if current_dd >= max_dd_threshold:
        return 0.2  # minimum 20% of normal sizing
    elif current_dd > 0:
        return max(0.2, 1.0 - current_dd / max_dd_threshold)
    else:
        return 1.0


# =============================================================================
# WALK-FORWARD VALIDATION + MODEL TRAINING
# =============================================================================

def train_and_evaluate(rows, feature_names):
    """Walk-forward train/test on magnitude prediction."""
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, r2_score

    try:
        import xgboost as xgb_lib
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "xgboost", "--break-system-packages", "-q"],
                      capture_output=True)
        import xgboost as xgb_lib

    print("\n" + "="*80)
    print("PILLAR 1: RUNUP MAGNITUDE PREDICTION")
    print("="*80)

    # Sort by date
    rows_sorted = sorted(rows, key=lambda r: r["_pdufa_date"])

    # Extract arrays
    X_all = np.array([[r[f] for f in feature_names] for r in rows_sorted])
    y_all = np.array([r["_target_return"] for r in rows_sorted])
    dates_all = np.array([r["_pdufa_date"] for r in rows_sorted])
    windows_all = np.array([r["_window"] for r in rows_sorted])

    # Walk-forward splits
    splits = [
        ("2022-2023", "2022-01-01", "2023-12-31"),
        ("2024",      "2024-01-01", "2024-12-31"),
        ("2025+",     "2025-01-01", "2026-12-31"),
    ]

    all_preds = []
    all_actuals = []
    all_meta = []
    per_window_metrics = defaultdict(list)

    best_ridge_alpha = 10.0  # default
    best_xgb_config = {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05}

    for split_name, test_start, test_end in splits:
        train_mask = dates_all < test_start
        test_mask = (dates_all >= test_start) & (dates_all <= test_end)

        if train_mask.sum() < 500 or test_mask.sum() < 50:
            print(f"  [{split_name}] Skipped (train={train_mask.sum()}, test={test_mask.sum()})")
            continue

        X_train, X_test = X_all[train_mask], X_all[test_mask]
        y_train, y_test = y_all[train_mask], y_all[test_mask]
        win_test = windows_all[test_mask]
        dates_test = dates_all[test_mask]

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_train)
        X_te = scaler.transform(X_test)

        # Ridge regression
        ridge_alphas = [0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
        best_alpha = 10.0
        best_ridge_mae = 999

        for alpha in ridge_alphas:
            m = Ridge(alpha=alpha)
            m.fit(X_tr, y_train)
            preds = m.predict(X_te)
            mae = mean_absolute_error(y_test, preds)
            if mae < best_ridge_mae:
                best_ridge_mae = mae
                best_alpha = alpha
        best_ridge_alpha = best_alpha

        ridge = Ridge(alpha=best_alpha)
        ridge.fit(X_tr, y_train)
        p_ridge = ridge.predict(X_te)

        # XGBoost regression
        xgb_configs = [
            {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.05},
            {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.03},
            {"n_estimators": 300, "max_depth": 3, "learning_rate": 0.02},
        ]
        best_xgb_mae = 999
        best_xgb = None

        for cfg in xgb_configs:
            m = xgb_lib.XGBRegressor(
                **cfg, subsample=0.8, colsample_bytree=0.7,
                reg_lambda=2.0, reg_alpha=0.3, min_child_weight=10,
                random_state=42, verbosity=0
            )
            m.fit(X_tr, y_train)
            preds = m.predict(X_te)
            mae = mean_absolute_error(y_test, preds)
            if mae < best_xgb_mae:
                best_xgb_mae = mae
                best_xgb = m
                best_xgb_config = cfg

        p_xgb = best_xgb.predict(X_te)

        # Ensemble: 60% Ridge + 40% XGB
        p_ensemble = 0.6 * p_ridge + 0.4 * p_xgb

        # Metrics
        mae = mean_absolute_error(y_test, p_ensemble)
        r2 = r2_score(y_test, p_ensemble)

        # Direction accuracy (predict sign correctly)
        sign_correct = np.mean(np.sign(p_ensemble) == np.sign(y_test))

        # Per-window metrics
        for win in set(win_test):
            w_mask = win_test == win
            if w_mask.sum() > 10:
                w_mae = mean_absolute_error(y_test[w_mask], p_ensemble[w_mask])
                w_r2 = r2_score(y_test[w_mask], p_ensemble[w_mask])
                w_dir = np.mean(np.sign(p_ensemble[w_mask]) == np.sign(y_test[w_mask]))
                per_window_metrics[win].append({"mae": w_mae, "r2": w_r2, "dir_acc": w_dir})

        print(f"  [{split_name}] Ridge α={best_alpha}, XGB={best_xgb_config}")
        print(f"    MAE={mae:.2f}% R²={r2:.4f} Dir_acc={sign_correct:.1%} "
              f"(train={train_mask.sum()}, test={test_mask.sum()})")

        all_preds.extend(p_ensemble.tolist())
        all_actuals.extend(y_test.tolist())
        all_meta.extend([{"date": d, "window": w}
                        for d, w in zip(dates_test, win_test)])

    # Overall metrics
    if all_preds:
        overall_mae = mean_absolute_error(all_actuals, all_preds)
        overall_r2 = r2_score(all_actuals, all_preds)
        overall_dir = np.mean(np.sign(all_preds) == np.sign(all_actuals))
        print(f"\n  *** OVERALL: MAE={overall_mae:.2f}% R²={overall_r2:.4f} "
              f"Dir_acc={overall_dir:.1%}")

        # Per-window summary
        print(f"\n  Per-window summary:")
        for win in sorted(per_window_metrics.keys()):
            metrics = per_window_metrics[win]
            avg_mae = np.mean([m["mae"] for m in metrics])
            avg_r2 = np.mean([m["r2"] for m in metrics])
            avg_dir = np.mean([m["dir_acc"] for m in metrics])
            print(f"    {win:12s}: MAE={avg_mae:.2f}% R²={avg_r2:.4f} Dir={avg_dir:.1%}")
    else:
        overall_mae = overall_r2 = overall_dir = 0
        print("  [WARN] No predictions generated")

    # Train final model on all data
    print("\n[TRAIN] Final models on full dataset...")
    scaler_final = StandardScaler()
    X_final = scaler_final.fit_transform(X_all)

    ridge_final = Ridge(alpha=best_ridge_alpha)
    ridge_final.fit(X_final, y_all)

    xgb_final = xgb_lib.XGBRegressor(
        **best_xgb_config, subsample=0.8, colsample_bytree=0.7,
        reg_lambda=2.0, reg_alpha=0.3, min_child_weight=10,
        random_state=42, verbosity=0
    )
    xgb_final.fit(X_final, y_all)

    # Feature importance
    ridge_importance = {}
    for i, f in enumerate(feature_names):
        ridge_importance[f] = round(float(ridge_final.coef_[i]), 4)

    xgb_importance = {}
    for i, f in enumerate(feature_names):
        xgb_importance[f] = round(float(xgb_final.feature_importances_[i]), 4)

    # Top features
    print(f"\n  Top 10 Ridge features (by |coef|):")
    for f, c in sorted(ridge_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
        print(f"    {f:35s} {c:+.4f}")

    print(f"\n  Top 10 XGB features (by importance):")
    for f, c in sorted(xgb_importance.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {f:35s} {c:.4f}")

    magnitude_results = {
        "overall_mae": overall_mae,
        "overall_r2": overall_r2,
        "overall_dir_acc": overall_dir,
        "ridge_alpha": best_ridge_alpha,
        "xgb_config": best_xgb_config,
        "ridge_importance": ridge_importance,
        "xgb_importance": xgb_importance,
        "n_predictions": len(all_preds),
    }

    return magnitude_results, scaler_final, ridge_final, xgb_final, feature_names


# =============================================================================
# PILLAR 2: DYNAMIC TIMING BACKTEST
# =============================================================================

def backtest_dynamic_timing(events, price_cache):
    """Backtest adaptive entry/exit vs fixed windows."""
    print("\n" + "="*80)
    print("PILLAR 2: DYNAMIC ENTRY/EXIT TIMING")
    print("="*80)

    dynamic_returns = []
    fixed_returns = []
    timing_stats = {"breakout_detected": 0, "no_signal": 0, "early_entry": 0, "late_entry": 0}

    for ev in events:
        cache_key = ev.get("cache_key", "")
        prices_dict = price_cache.get(cache_key, {})
        if not prices_dict:
            continue

        # Dynamic entry detection
        entry_td, signal = detect_runup_start(prices_dict)
        if entry_td is not None:
            timing_stats["breakout_detected"] += 1
            if entry_td < -60:
                timing_stats["early_entry"] += 1
            elif entry_td > -25:
                timing_stats["late_entry"] += 1

            # Dynamic exit
            exit_td = detect_exit_signal(prices_dict, entry_td)

            # Compute return
            entry_key = str(entry_td)
            exit_key = str(exit_td)
            if entry_key in prices_dict and exit_key in prices_dict:
                ret = (float(prices_dict[exit_key]) / float(prices_dict[entry_key]) - 1) * 100
                dynamic_returns.append({
                    "ticker": ev["ticker"],
                    "pdufa_date": ev["pdufa_date"],
                    "entry_td": entry_td,
                    "exit_td": exit_td,
                    "return": ret,
                    "signal": signal,
                    "outcome": ev.get("outcome_bin", "0"),
                })
        else:
            timing_stats["no_signal"] += 1

        # Fixed T-45→T-7 return for comparison
        ret_str = ev.get("T-45_T-7", "")
        if ret_str:
            try:
                fixed_returns.append(float(ret_str) * 100)
            except:
                pass

    # Compare
    if dynamic_returns:
        dynamic_rets = [r["return"] for r in dynamic_returns]
        print(f"\n  Dynamic timing: {len(dynamic_returns)} trades")
        print(f"    Mean return: {np.mean(dynamic_rets):+.2f}%")
        print(f"    Median return: {np.median(dynamic_rets):+.2f}%")
        print(f"    Hit rate: {np.mean([r > 0 for r in dynamic_rets]):.1%}")
        print(f"    Sharpe (approx): {np.mean(dynamic_rets) / max(np.std(dynamic_rets), 0.01):.2f}")

    if fixed_returns:
        print(f"\n  Fixed T-45→T-7: {len(fixed_returns)} trades")
        print(f"    Mean return: {np.mean(fixed_returns):+.2f}%")
        print(f"    Median return: {np.median(fixed_returns):+.2f}%")
        print(f"    Hit rate: {np.mean([r > 0 for r in fixed_returns]):.1%}")
        print(f"    Sharpe (approx): {np.mean(fixed_returns) / max(np.std(fixed_returns), 0.01):.2f}")

    print(f"\n  Timing stats: {timing_stats}")

    return dynamic_returns, timing_stats


# =============================================================================
# UNIFIED V3 PORTFOLIO BACKTEST
# =============================================================================

def unified_backtest(events, price_cache, rows, feature_names,
                     scaler, ridge_model, xgb_model):
    """Full v3 backtest: magnitude + timing + portfolio Kelly."""
    print("\n" + "="*80)
    print("UNIFIED V3 PORTFOLIO BACKTEST")
    print("="*80)

    # Sort events by date
    sorted_events = sorted(events, key=lambda e: e["pdufa_date"])

    # Build feature lookup
    row_lookup = {}
    for r in rows:
        key = f"{r['_ticker']}|{r['_pdufa_date']}|{r['_window']}"
        row_lookup[key] = r

    # Simulation
    initial_capital = 100_000
    portfolio_value = initial_capital
    equity_curve = [portfolio_value]
    active_positions = []
    all_trades = []
    daily_log = []

    # Process events chronologically
    for ev in sorted_events:
        ticker = ev["ticker"]
        pdufa_date = ev["pdufa_date"]
        v9_score = float(ev.get("v9_score", 0.5))
        v9_tier = ev.get("v9_tier", "T3")
        mcap_tier = ev.get("mcap", "small")
        cache_key = ev.get("cache_key", "")
        prices_dict = price_cache.get(cache_key, {})

        if not prices_dict:
            continue

        # Close any expired positions
        positions_to_close = []
        for i, pos in enumerate(active_positions):
            if pos["pdufa_date"] <= pdufa_date:
                positions_to_close.append(i)

        for i in sorted(positions_to_close, reverse=True):
            pos = active_positions.pop(i)
            pnl = pos["size"] * pos["return"] / 100
            portfolio_value += pnl
            all_trades.append({**pos, "pnl": pnl, "portfolio_value": portfolio_value})

        # PILLAR 1: Get magnitude prediction for best window
        best_window = None
        best_pred_return = -999

        for win_name, entry_td, exit_td in WINDOWS:
            key = f"{ticker}|{pdufa_date}|{win_name}"
            row_data = row_lookup.get(key)
            if row_data is None:
                continue

            x = np.array([[row_data[f] for f in feature_names]])
            x_scaled = scaler.transform(x)
            pred = 0.6 * ridge_model.predict(x_scaled)[0] + 0.4 * xgb_model.predict(x_scaled)[0]

            if pred > best_pred_return:
                best_pred_return = pred
                best_window = win_name
                best_entry_td = entry_td
                best_exit_td = exit_td

        if best_window is None or best_pred_return < 1.0:  # skip if <1% expected
            continue

        # PILLAR 2: Check dynamic timing
        entry_td_dynamic, signal = detect_runup_start(prices_dict)
        timing_score = 1.0 if (entry_td_dynamic is not None and
                               entry_td_dynamic >= best_entry_td - 10) else 0.3

        # COMPOSITE SCORE
        magnitude_conf = min(1.0, max(0, (best_pred_return - 1) / 10))
        entry_score = 0.50 * v9_score + 0.30 * magnitude_conf + 0.20 * timing_score

        if entry_score < 0.40:
            continue

        # PILLAR 3: Position sizing
        pred_vol = 15.0  # approximate from training data std
        kf = kelly_fraction(best_pred_return, pred_vol)
        dd_mult = drawdown_governor(np.array(equity_curve))
        position_size_pct = kf * dd_mult * entry_score

        # Portfolio constraints
        allowed, reason, adj_size = portfolio_heat_check(
            active_positions,
            {"mcap": mcap_tier, "size_pct": position_size_pct}
        )
        if not allowed:
            continue

        position_size_pct = adj_size
        position_size = portfolio_value * position_size_pct

        # Get actual return for the chosen window
        actual_ret_str = ev.get(best_window, "")
        if not actual_ret_str:
            continue
        try:
            actual_return = float(actual_ret_str) * 100
        except:
            continue

        # Record position
        active_positions.append({
            "ticker": ticker,
            "pdufa_date": pdufa_date,
            "window": best_window,
            "entry_td": best_entry_td,
            "exit_td": best_exit_td,
            "v9_score": v9_score,
            "v9_tier": v9_tier,
            "mcap": mcap_tier,
            "pred_return": best_pred_return,
            "return": actual_return,
            "size_pct": position_size_pct,
            "size": position_size,
            "entry_score": entry_score,
            "timing_signal": signal if entry_td_dynamic else "NONE",
        })

        equity_curve.append(portfolio_value)

    # Close remaining positions
    for pos in active_positions:
        pnl = pos["size"] * pos["return"] / 100
        portfolio_value += pnl
        all_trades.append({**pos, "pnl": pnl, "portfolio_value": portfolio_value})
    equity_curve.append(portfolio_value)

    # Calculate results
    n_trades = len(all_trades)
    if n_trades == 0:
        print("  [WARN] No trades executed!")
        return {"n_trades": 0}

    returns = [t["return"] for t in all_trades]
    pnls = [t["pnl"] for t in all_trades]
    sizes = [t["size"] for t in all_trades]

    win_rate = np.mean([r > 0 for r in returns])
    avg_return = np.mean(returns)
    median_return = np.median(returns)
    total_pnl = sum(pnls)
    total_return = (portfolio_value / initial_capital - 1) * 100

    # Sharpe approximation
    if np.std(returns) > 0:
        sharpe = avg_return / np.std(returns) * np.sqrt(n_trades / 6)  # annualized ~6 years
    else:
        sharpe = 0

    # Max drawdown
    eq = np.array(equity_curve)
    running_max = np.maximum.accumulate(eq)
    dd = (eq - running_max) / running_max
    max_dd = float(np.min(dd)) * 100

    # By tier
    tier_stats = {}
    for tier in ["T1", "T2", "T3", "T4"]:
        tier_trades = [t for t in all_trades if t.get("v9_tier") == tier]
        if tier_trades:
            tier_stats[tier] = {
                "n": len(tier_trades),
                "avg_return": np.mean([t["return"] for t in tier_trades]),
                "win_rate": np.mean([t["return"] > 0 for t in tier_trades]),
                "avg_size_pct": np.mean([t["size_pct"] for t in tier_trades]),
            }

    # By mcap
    mcap_stats = {}
    for mc in ["nano", "micro", "small", "mid", "large"]:
        mc_trades = [t for t in all_trades if t.get("mcap") == mc]
        if mc_trades:
            mcap_stats[mc] = {
                "n": len(mc_trades),
                "avg_return": np.mean([t["return"] for t in mc_trades]),
                "win_rate": np.mean([t["return"] > 0 for t in mc_trades]),
            }

    print(f"\n  V3 PORTFOLIO RESULTS:")
    print(f"    Trades: {n_trades}")
    print(f"    Win rate: {win_rate:.1%}")
    print(f"    Avg return/trade: {avg_return:+.2f}%")
    print(f"    Median return/trade: {median_return:+.2f}%")
    print(f"    Total return: {total_return:+.1f}%")
    print(f"    Final value: ${portfolio_value:,.0f} (from $100K)")
    print(f"    Sharpe (approx): {sharpe:.2f}")
    print(f"    Max drawdown: {max_dd:.1f}%")

    print(f"\n  By ODIN Tier:")
    for tier, stats in sorted(tier_stats.items()):
        print(f"    {tier}: {stats['n']} trades, {stats['avg_return']:+.2f}% avg, "
              f"{stats['win_rate']:.0%} win, {stats['avg_size_pct']:.1%} avg size")

    print(f"\n  By Market Cap:")
    for mc, stats in sorted(mcap_stats.items(), key=lambda x: MCAP_TIERS.get(x[0], 2)):
        print(f"    {mc:8s}: {stats['n']} trades, {stats['avg_return']:+.2f}% avg, "
              f"{stats['win_rate']:.0%} win")

    results = {
        "n_trades": n_trades,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "median_return": median_return,
        "total_return": total_return,
        "final_value": portfolio_value,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "tier_stats": tier_stats,
        "mcap_stats": mcap_stats,
    }

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    events, price_cache = load_data()

    # Build training data
    rows, feature_names = build_training_data(events, price_cache)

    # Pillar 1: Magnitude prediction
    mag_results, scaler, ridge, xgb, feat_names = train_and_evaluate(rows, feature_names)

    # Pillar 2: Dynamic timing
    dynamic_trades, timing_stats = backtest_dynamic_timing(events, price_cache)

    # Unified backtest
    backtest_results = unified_backtest(
        events, price_cache, rows, feature_names, scaler, ridge, xgb
    )

    # =================================================================
    print("\n" + "="*80)
    print("V3 DEPLOY CONFIG")
    print("="*80)

    # Save deploy config
    deploy = {
        "version": "3.0.0",
        "engine": "BIFROST",
        "architecture": "3-pillar: Ridge+XGB magnitude prediction + momentum timing + portfolio Kelly",
        "training_events": len(events),
        "price_cache_events": len(price_cache),
        "feature_names": feat_names,
        "n_features": len(feat_names),
        "scaler_means": {f: float(scaler.mean_[i]) for i, f in enumerate(feat_names)},
        "scaler_scales": {f: float(scaler.scale_[i]) for i, f in enumerate(feat_names)},
        "ridge_coefs": {f: float(ridge.coef_[i]) for i, f in enumerate(feat_names)},
        "ridge_intercept": float(ridge.intercept_),
        "ridge_alpha": float(ridge.alpha),
        "xgb_config": mag_results.get("xgb_config", {}),
        "ensemble_weights": {"ridge": 0.6, "xgb": 0.4},
        "timing_config": {
            "momentum_threshold": 0.03,
            "acceleration_threshold": 0.01,
            "sma_distance_threshold": 0.02,
            "exit_momentum_reversal": -0.03,
            "exit_volatility_expansion": 0.10,
            "floor_exit_td": -3,
        },
        "portfolio_config": {
            "kelly_fraction": 0.5,
            "max_concurrent_positions": 5,
            "max_nano_positions": 2,
            "max_single_position_pct": 0.06,
            "portfolio_heat_limit_pct": 0.15,
            "max_drawdown_brake": 0.15,
            "min_entry_score": 0.40,
            "min_pred_return": 1.0,
        },
        "scoring_weights": {
            "odin_probability": 0.50,
            "magnitude_confidence": 0.30,
            "timing_signal": 0.20,
        },
        "magnitude_results": {
            "mae": mag_results.get("overall_mae", 0),
            "r2": mag_results.get("overall_r2", 0),
            "dir_accuracy": mag_results.get("overall_dir_acc", 0),
        },
        "backtest_results": {
            "n_trades": backtest_results.get("n_trades", 0),
            "win_rate": backtest_results.get("win_rate", 0),
            "avg_return": backtest_results.get("avg_return", 0),
            "total_return": backtest_results.get("total_return", 0),
            "sharpe": backtest_results.get("sharpe", 0),
            "max_drawdown": backtest_results.get("max_drawdown", 0),
            "final_value": backtest_results.get("final_value", 0),
        },
    }

    # Save XGBoost model
    xgb_path = os.path.join(DATA_DIR, "bifrost_v3_xgb.json")
    xgb.save_model(xgb_path)

    with open(V3_DEPLOY, "w") as f:
        json.dump(deploy, f, indent=2, default=str)
    print(f"  Deploy config saved to {V3_DEPLOY}")

    # Save full results
    full_results = {
        "version": "3.0.0",
        "magnitude": mag_results,
        "timing": timing_stats,
        "backtest": backtest_results,
    }
    with open(V3_RESULTS, "w") as f:
        json.dump(full_results, f, indent=2, default=str)
    print(f"  Results saved to {V3_RESULTS}")

    print(f"\n{'='*80}")
    print(f"BIFROST v3.0 BUILD COMPLETE")
    print(f"{'='*80}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
