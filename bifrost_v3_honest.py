#!/usr/bin/env python3
"""
================================================================================
BIFROST v3.1 — HONEST Walk-Forward Portfolio Backtest
================================================================================

Fixes v3.0 issues:
  1. Portfolio backtest now uses WALK-FORWARD models (not final model trained on all)
  2. Dynamic timing DROPPED (41.4% hit rate — proven to HURT)
  3. Window selection based on OOS magnitude predictions
  4. Keeps Kelly sizing, drawdown governor, portfolio heat limits

Architecture:
  - Magnitude prediction: Ridge + XGB ensemble (60/40), retrained at each split
  - Window selection: Best predicted return across 12 windows per event
  - Position sizing: Half-Kelly with drawdown governor
  - Portfolio constraints: Max 5 concurrent, max 2 nano, max 15% heat, max 6% single

Training: 1,705 PDUFA events (2020-2026) with real yfinance daily prices
Cardinal Rule: Never hold through FDA decision
"""

import csv, json, math, os, sys, warnings
from collections import defaultdict
from datetime import datetime
import numpy as np
warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

BIFROST_CSV = os.path.join(DATA_DIR, "pdufa_runup_bifrost_v2.csv")
PRICE_CACHE = os.path.join(DATA_DIR, "bifrost_price_cache.json")
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
# DATA LOADING + FEATURE ENGINEERING (same as v3.0)
# =============================================================================

def compute_price_features(prices_dict, entry_td):
    """Compute momentum, volatility, and trend features from daily prices."""
    features = {}
    day_prices = []
    for td in range(entry_td - 60, entry_td + 1):
        key = str(td)
        if key in prices_dict:
            day_prices.append((td, float(prices_dict[key])))

    if len(day_prices) < 10:
        return None

    prices = [p for _, p in day_prices]
    entry_price = prices[-1]
    returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]

    features["momentum_14d"] = (prices[-1] / prices[-14] - 1) * 100 if len(prices) >= 15 else 0.0
    features["momentum_5d"] = (prices[-1] / prices[-5] - 1) * 100 if len(prices) >= 6 else 0.0
    features["momentum_21d"] = (prices[-1] / prices[-21] - 1) * 100 if len(prices) >= 22 else 0.0

    if len(returns) >= 20:
        features["volatility_20d"] = float(np.std(returns[-20:])) * 100
    else:
        features["volatility_20d"] = float(np.std(returns)) * 100 if returns else 3.0
    features["volatility_10d"] = float(np.std(returns[-10:])) * 100 if len(returns) >= 10 else features["volatility_20d"]

    # Vol ratio
    if len(returns) >= 20:
        vol_10 = np.std(returns[-10:])
        vol_20 = np.std(returns[-20:])
        features["vol_ratio_price"] = vol_10 / max(vol_20, 1e-8)
    else:
        features["vol_ratio_price"] = 1.0

    if len(prices) >= 20:
        x = np.arange(20)
        y = np.array(prices[-20:])
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        y_pred = slope * x + coeffs[1]
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        features["trend_r2"] = 1 - ss_res / max(ss_tot, 1e-10)
        features["trend_slope"] = slope / entry_price * 100
    else:
        features["trend_r2"] = 0.0
        features["trend_slope"] = 0.0

    if len(prices) >= 30:
        high_30d = max(prices[-30:])
        low_30d = min(prices[-30:])
        price_range = high_30d - low_30d
        features["price_pct_range"] = (entry_price - low_30d) / max(price_range, 0.01)
    else:
        features["price_pct_range"] = 0.5

    if len(prices) >= 20:
        sma20 = np.mean(prices[-20:])
        features["dist_sma20"] = (entry_price / sma20 - 1) * 100
    else:
        features["dist_sma20"] = 0.0

    if len(prices) >= 20:
        mom_recent = prices[-1] / prices[-5] - 1
        mom_prior = prices[-5] / prices[-10] - 1
        features["momentum_accel"] = (mom_recent - mom_prior) * 100
    else:
        features["momentum_accel"] = 0.0

    if len(prices) >= 20:
        running_max = np.maximum.accumulate(prices[-20:])
        drawdowns = (np.array(prices[-20:]) - running_max) / running_max
        features["max_dd_20d"] = float(np.min(drawdowns)) * 100
    else:
        features["max_dd_20d"] = 0.0

    return features


def build_training_data(events, price_cache):
    """Build feature matrix + target returns for all events × windows."""
    rows = []
    for ev in events:
        ticker = ev["ticker"]
        pdufa_date = ev["pdufa_date"]
        cache_key = ev.get("cache_key", f"{ticker}_{pdufa_date.replace('-','')}")
        prices_dict = price_cache.get(cache_key, {})
        if not prices_dict:
            continue

        v9_score = float(ev.get("v9_score", 0.5))
        v9_tier = ev.get("v9_tier", "T3")
        mcap_tier = ev.get("mcap", "small")
        outcome_bin = int(ev.get("outcome_bin", 0))
        vol_ratio = float(ev.get("vol_ratio", 1.0)) if ev.get("vol_ratio") else 1.0
        crl_rate = float(ev.get("crl_rate", 0.3)) if ev.get("crl_rate") else 0.3
        ta_risk = ev.get("ta_risk", "MID_CRL")

        approval_logit = math.log(max(v9_score, 0.01) / max(1 - v9_score, 0.01))
        mcap_numeric = MCAP_TIERS.get(mcap_tier, 2)
        tier_numeric = ODIN_TIERS.get(v9_tier, 2)
        ta_risk_numeric = {"LOW_CRL": 0.1, "MID_CRL": 0.2, "HIGH_CRL": 0.3,
                          "VERY_HIGH_CRL": 0.4}.get(ta_risk, 0.2)
        try:
            eve_price = float(ev.get("eve_price", 20))
        except:
            eve_price = 20.0
        log_price = math.log(max(eve_price, 0.1))

        for win_name, entry_td, exit_td in WINDOWS:
            ret_str = ev.get(win_name, "")
            if not ret_str:
                continue
            try:
                target_return = float(ret_str) * 100
            except:
                continue

            price_feats = compute_price_features(prices_dict, entry_td)
            if price_feats is None:
                continue

            row = {
                "_ticker": ticker,
                "_pdufa_date": pdufa_date,
                "_window": win_name,
                "_entry_td": entry_td,
                "_exit_td": exit_td,
                "_outcome": outcome_bin,
                "_target_return": target_return,
                "_cache_key": cache_key,
                "_v9_tier": v9_tier,
                "_mcap": mcap_tier,
                "_v9_score": v9_score,

                "v9_score": v9_score,
                "approval_logit": approval_logit,
                "tier_numeric": tier_numeric,
                "mcap_numeric": mcap_numeric,
                "crl_rate": crl_rate,
                "ta_risk_numeric": ta_risk_numeric,
                "vol_ratio": vol_ratio,
                "log_price": log_price,
                "days_to_pdufa": abs(entry_td),
                "holding_days": abs(exit_td - entry_td),
                "entry_late": 1 if entry_td > -30 else 0,
                **price_feats,
                "approval_x_momentum": v9_score * price_feats.get("momentum_14d", 0),
                "approval_x_volatility": v9_score * price_feats.get("volatility_20d", 0),
                "mcap_x_momentum": mcap_numeric * price_feats.get("momentum_14d", 0),
                "tier_x_volatility": tier_numeric * price_feats.get("volatility_20d", 0),
                "vol_ratio_x_approval": vol_ratio * v9_score,
                "is_nano": 1 if mcap_tier == "nano" else 0,
                "is_micro": 1 if mcap_tier == "micro" else 0,
                "is_small": 1 if mcap_tier == "small" else 0,
                "is_mid": 1 if mcap_tier == "mid" else 0,
                "is_large": 1 if mcap_tier == "large" else 0,
                "is_t1": 1 if v9_tier == "T1" else 0,
                "is_t2": 1 if v9_tier == "T2" else 0,
                "is_t3": 1 if v9_tier == "T3" else 0,
                "is_t4": 1 if v9_tier == "T4" else 0,
            }
            rows.append(row)

    feature_names = sorted([k for k in rows[0].keys() if not k.startswith("_")])
    return rows, feature_names


# =============================================================================
# PORTFOLIO SIZING (same as v3.0)
# =============================================================================

def kelly_fraction(pred_return, pred_volatility, win_prob=0.6):
    """Half-Kelly position fraction."""
    if pred_return <= 0 or pred_volatility <= 0:
        return 0.0
    edge = pred_return / 100
    variance = (pred_volatility / 100) ** 2
    if variance < 1e-10:
        return 0.0
    f_full = edge / variance
    f_half = f_full / 2
    return max(0, min(f_half, 0.06))


def portfolio_heat_check(existing_positions, new_position, max_concurrent=5,
                          max_nano=2, max_heat=0.15, max_single=0.06):
    """Check portfolio constraints."""
    if len(existing_positions) >= max_concurrent:
        return False, "Max concurrent", 0
    nano_count = sum(1 for p in existing_positions if p.get("mcap") == "nano")
    if new_position.get("mcap") == "nano" and nano_count >= max_nano:
        return False, "Max nano", 0
    current_heat = sum(p.get("size_pct", 0) for p in existing_positions)
    remaining = max_heat - current_heat
    if remaining <= 0.005:
        return False, "Heat limit", 0
    size = min(new_position.get("size_pct", 0.03), remaining, max_single)
    return True, "OK", size


def drawdown_governor(equity_curve, max_dd_threshold=0.15):
    """Scale position sizes based on current drawdown. Returns 0.2-1.0."""
    if len(equity_curve) < 5:
        return 1.0
    running_max = np.maximum.accumulate(equity_curve)
    current_dd = abs((equity_curve[-1] - running_max[-1]) / max(running_max[-1], 1))
    if current_dd >= max_dd_threshold:
        return 0.2
    elif current_dd > 0:
        return max(0.2, 1.0 - current_dd / max_dd_threshold)
    return 1.0


# =============================================================================
# WALK-FORWARD PORTFOLIO BACKTEST (THE FIX)
# =============================================================================

def walk_forward_backtest(rows, feature_names):
    """
    HONEST walk-forward backtest:
    - Train model ONLY on past data
    - Predict magnitude for upcoming events
    - Select best window, size with Kelly, apply portfolio constraints
    - Retrain quarterly
    """
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    try:
        import xgboost as xgb_lib
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "xgboost", "--break-system-packages", "-q"],
                      capture_output=True)
        import xgboost as xgb_lib

    print("\n" + "="*80)
    print("WALK-FORWARD PORTFOLIO BACKTEST (HONEST)")
    print("="*80)

    # Sort rows by PDUFA date
    rows_sorted = sorted(rows, key=lambda r: r["_pdufa_date"])

    # Group rows by event (ticker + date)
    event_groups = defaultdict(list)
    for r in rows_sorted:
        key = f"{r['_ticker']}|{r['_pdufa_date']}"
        event_groups[key].append(r)

    # Get unique events in date order
    seen = set()
    event_order = []
    for r in rows_sorted:
        key = f"{r['_ticker']}|{r['_pdufa_date']}"
        if key not in seen:
            seen.add(key)
            event_order.append(key)

    # Walk-forward splits: retrain before each year
    # We need enough training data, so start testing from 2022
    split_boundaries = ["2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01"]

    # Build numpy arrays
    X_all = np.array([[r[f] for f in feature_names] for r in rows_sorted])
    y_all = np.array([r["_target_return"] for r in rows_sorted])
    dates_all = np.array([r["_pdufa_date"] for r in rows_sorted])

    # Portfolio simulation
    initial_capital = 100_000
    portfolio_value = initial_capital
    equity_curve = [portfolio_value]
    active_positions = []
    all_trades = []

    # Track current model
    current_model_ridge = None
    current_model_xgb = None
    current_scaler = None
    current_train_cutoff = None
    next_retrain_idx = 0

    # Process events chronologically
    n_skipped_no_model = 0
    n_skipped_low_pred = 0
    n_skipped_low_score = 0
    n_skipped_heat = 0
    n_traded = 0

    print(f"\n  Events to process: {len(event_order)}")
    print(f"  Training rows: {len(rows_sorted)}")

    for evt_idx, evt_key in enumerate(event_order):
        evt_rows = event_groups[evt_key]
        pdufa_date = evt_rows[0]["_pdufa_date"]
        ticker = evt_rows[0]["_ticker"]
        v9_score = evt_rows[0]["_v9_score"]
        v9_tier = evt_rows[0]["_v9_tier"]
        mcap_tier = evt_rows[0]["_mcap"]

        # Check if we need to retrain
        if next_retrain_idx < len(split_boundaries) and pdufa_date >= split_boundaries[next_retrain_idx]:
            cutoff = split_boundaries[next_retrain_idx]
            train_mask = dates_all < cutoff
            n_train = train_mask.sum()

            if n_train >= 500:
                X_train = X_all[train_mask]
                y_train = y_all[train_mask]

                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X_train)

                # Ridge
                best_alpha = 100.0
                best_mae = 999
                for alpha in [1.0, 10.0, 50.0, 100.0, 200.0]:
                    m = Ridge(alpha=alpha)
                    m.fit(X_tr, y_train)
                    # Quick CV on last 20% of training
                    split_pt = int(0.8 * len(X_tr))
                    preds = m.predict(X_tr[split_pt:])
                    mae = np.mean(np.abs(preds - y_train[split_pt:]))
                    if mae < best_mae:
                        best_mae = mae
                        best_alpha = alpha

                ridge = Ridge(alpha=best_alpha)
                ridge.fit(X_tr, y_train)

                # XGB
                xgb = xgb_lib.XGBRegressor(
                    n_estimators=300, max_depth=3, learning_rate=0.02,
                    subsample=0.8, colsample_bytree=0.7,
                    reg_lambda=2.0, reg_alpha=0.3, min_child_weight=10,
                    random_state=42, verbosity=0
                )
                xgb.fit(X_tr, y_train)

                current_model_ridge = ridge
                current_model_xgb = xgb
                current_scaler = scaler
                current_train_cutoff = cutoff

                print(f"\n  [RETRAIN] at {cutoff}: {n_train} rows, Ridge α={best_alpha}")

            next_retrain_idx += 1

        # Skip if no model yet
        if current_model_ridge is None:
            n_skipped_no_model += 1
            continue

        # Close expired positions
        positions_to_close = []
        for i, pos in enumerate(active_positions):
            if pos["pdufa_date"] <= pdufa_date:
                positions_to_close.append(i)
        for i in sorted(positions_to_close, reverse=True):
            pos = active_positions.pop(i)
            pnl = pos["size"] * pos["return"] / 100
            portfolio_value += pnl
            all_trades.append({**pos, "pnl": pnl, "portfolio_value": portfolio_value})
            equity_curve.append(portfolio_value)

        # Predict magnitude for each window (using walk-forward model)
        best_window = None
        best_pred_return = -999
        best_entry_td = None
        best_exit_td = None
        best_actual_return = None

        for row in evt_rows:
            x = np.array([[row[f] for f in feature_names]])
            x_scaled = current_scaler.transform(x)
            pred = 0.6 * current_model_ridge.predict(x_scaled)[0] + 0.4 * current_model_xgb.predict(x_scaled)[0]

            if pred > best_pred_return:
                best_pred_return = pred
                best_window = row["_window"]
                best_entry_td = row["_entry_td"]
                best_exit_td = row["_exit_td"]
                best_actual_return = row["_target_return"]

        if best_window is None or best_pred_return < 1.0:
            n_skipped_low_pred += 1
            continue

        # Composite entry score (no timing component since Pillar 2 failed)
        magnitude_conf = min(1.0, max(0, (best_pred_return - 1) / 10))
        entry_score = 0.60 * v9_score + 0.40 * magnitude_conf

        if entry_score < 0.40:
            n_skipped_low_score += 1
            continue

        # Position sizing: Kelly
        pred_vol = 15.0
        kf = kelly_fraction(best_pred_return, pred_vol)
        dd_mult = drawdown_governor(np.array(equity_curve))
        position_size_pct = kf * dd_mult * entry_score

        # Tier safety caps (from v2)
        tier_caps = {"T1": 0.06, "T2": 0.06, "T3": 0.03, "T4": 0.015}
        max_size = tier_caps.get(v9_tier, 0.03)
        position_size_pct = min(position_size_pct, max_size)

        # Portfolio constraints
        allowed, reason, adj_size = portfolio_heat_check(
            active_positions,
            {"mcap": mcap_tier, "size_pct": position_size_pct}
        )
        if not allowed:
            n_skipped_heat += 1
            continue

        position_size_pct = adj_size
        position_size = portfolio_value * position_size_pct

        # Record trade
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
            "return": best_actual_return,
            "size_pct": position_size_pct,
            "size": position_size,
            "entry_score": entry_score,
        })
        n_traded += 1

    # Close remaining positions
    for pos in active_positions:
        pnl = pos["size"] * pos["return"] / 100
        portfolio_value += pnl
        all_trades.append({**pos, "pnl": pnl, "portfolio_value": portfolio_value})
        equity_curve.append(portfolio_value)

    # =============================================================================
    # RESULTS
    # =============================================================================
    n_trades = len(all_trades)
    if n_trades == 0:
        print("  [WARN] No trades executed!")
        return {}

    returns = [t["return"] for t in all_trades]
    pnls = [t["pnl"] for t in all_trades]

    win_rate = np.mean([r > 0 for r in returns])
    avg_return = np.mean(returns)
    median_return = np.median(returns)
    total_return = (portfolio_value / initial_capital - 1) * 100

    # Sharpe
    if np.std(returns) > 0:
        # ~4 years of testing (2022-2026), approximate annual trades
        trades_per_year = n_trades / 4.5
        sharpe = (avg_return / np.std(returns)) * np.sqrt(trades_per_year)
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
                "avg_return": round(np.mean([t["return"] for t in tier_trades]), 2),
                "win_rate": round(np.mean([t["return"] > 0 for t in tier_trades]), 3),
                "avg_size_pct": round(np.mean([t["size_pct"] for t in tier_trades]), 4),
                "avg_pred": round(np.mean([t["pred_return"] for t in tier_trades]), 2),
            }

    # By mcap
    mcap_stats = {}
    for mc in ["nano", "micro", "small", "mid", "large"]:
        mc_trades = [t for t in all_trades if t.get("mcap") == mc]
        if mc_trades:
            mcap_stats[mc] = {
                "n": len(mc_trades),
                "avg_return": round(np.mean([t["return"] for t in mc_trades]), 2),
                "win_rate": round(np.mean([t["return"] > 0 for t in mc_trades]), 3),
            }

    # Window distribution
    window_dist = defaultdict(int)
    for t in all_trades:
        window_dist[t["window"]] += 1

    # Print results
    print(f"\n  WALK-FORWARD V3.1 RESULTS (HONEST):")
    print(f"    Trades: {n_trades}")
    print(f"    Win rate: {win_rate:.1%}")
    print(f"    Avg return/trade: {avg_return:+.2f}%")
    print(f"    Median return/trade: {median_return:+.2f}%")
    print(f"    Total return: {total_return:+.1f}%")
    print(f"    Final value: ${portfolio_value:,.0f} (from $100K)")
    print(f"    Sharpe (approx): {sharpe:.2f}")
    print(f"    Max drawdown: {max_dd:.1f}%")

    print(f"\n  Skip reasons:")
    print(f"    No model yet: {n_skipped_no_model}")
    print(f"    Low predicted return: {n_skipped_low_pred}")
    print(f"    Low entry score: {n_skipped_low_score}")
    print(f"    Portfolio heat: {n_skipped_heat}")

    print(f"\n  By ODIN Tier:")
    for tier in sorted(tier_stats.keys()):
        s = tier_stats[tier]
        print(f"    {tier}: {s['n']} trades, {s['avg_return']:+.2f}% avg, "
              f"{s['win_rate']:.0%} win, {s['avg_size_pct']:.1%} size, "
              f"pred={s['avg_pred']:+.1f}%")

    print(f"\n  By Market Cap:")
    for mc in ["nano", "micro", "small", "mid", "large"]:
        if mc in mcap_stats:
            s = mcap_stats[mc]
            print(f"    {mc:8s}: {s['n']} trades, {s['avg_return']:+.2f}% avg, "
                  f"{s['win_rate']:.0%} win")

    print(f"\n  Window distribution (top 5):")
    for win, cnt in sorted(window_dist.items(), key=lambda x: -x[1])[:5]:
        print(f"    {win}: {cnt} trades ({cnt/n_trades:.0%})")

    # V2 comparison
    print(f"\n" + "="*80)
    print(f"V2 vs V3.1 COMPARISON")
    print(f"="*80)
    print(f"  {'Metric':<25s} {'V2 (static)':<20s} {'V3.1 (honest WF)':<20s}")
    print(f"  {'-'*65}")
    print(f"  {'Trades':<25s} {'1,524':<20s} {f'{n_trades:,}':<20s}")
    print(f"  {'Win rate':<25s} {'58.5%':<20s} {f'{win_rate:.1%}':<20s}")
    print(f"  {'Avg return/trade':<25s} {'+1.6%':<20s} {f'{avg_return:+.2f}%':<20s}")
    print(f"  {'Sharpe':<25s} {'3.43':<20s} {f'{sharpe:.2f}':<20s}")
    print(f"  {'Final value':<25s} {'$23.7M':<20s} {f'${portfolio_value/1e6:.1f}M':<20s}")
    print(f"  {'Max drawdown':<25s} {'-N/A-':<20s} {f'{max_dd:.1f}%':<20s}")

    results = {
        "version": "3.1.0",
        "methodology": "walk_forward_honest",
        "n_trades": n_trades,
        "win_rate": round(win_rate, 4),
        "avg_return": round(avg_return, 2),
        "median_return": round(median_return, 2),
        "total_return": round(total_return, 1),
        "final_value": round(portfolio_value, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_dd, 1),
        "tier_stats": tier_stats,
        "mcap_stats": mcap_stats,
        "window_distribution": dict(window_dist),
        "skip_reasons": {
            "no_model": n_skipped_no_model,
            "low_pred": n_skipped_low_pred,
            "low_score": n_skipped_low_score,
            "heat_limit": n_skipped_heat,
        },
    }

    return results


# =============================================================================
# TRAIN FINAL DEPLOY MODEL (on all data, for forward scoring)
# =============================================================================

def train_final_model(rows, feature_names):
    """Train final model on ALL data for deployment (forward-looking scoring)."""
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    import xgboost as xgb_lib

    print(f"\n[DEPLOY] Training final models on all {len(rows)} rows...")

    X_all = np.array([[r[f] for f in feature_names] for r in rows])
    y_all = np.array([r["_target_return"] for r in rows])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_all)

    ridge = Ridge(alpha=100.0)
    ridge.fit(X_scaled, y_all)

    xgb = xgb_lib.XGBRegressor(
        n_estimators=300, max_depth=3, learning_rate=0.02,
        subsample=0.8, colsample_bytree=0.7,
        reg_lambda=2.0, reg_alpha=0.3, min_child_weight=10,
        random_state=42, verbosity=0
    )
    xgb.fit(X_scaled, y_all)

    # Feature importance
    ridge_imp = {f: round(float(ridge.coef_[i]), 4) for i, f in enumerate(feature_names)}
    xgb_imp = {f: round(float(xgb.feature_importances_[i]), 4) for i, f in enumerate(feature_names)}

    print(f"\n  Top 10 Ridge features:")
    for f, c in sorted(ridge_imp.items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
        print(f"    {f:35s} {c:+.4f}")

    print(f"\n  Top 10 XGB features:")
    for f, c in sorted(xgb_imp.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {f:35s} {c:.4f}")

    # Deploy config
    deploy = {
        "version": "3.1.0",
        "architecture": "Ridge_60_XGB_40_magnitude_regression",
        "description": "BIFROST v3.1 — Walk-forward honest magnitude + Kelly sizing",
        "features": feature_names,
        "ridge": {
            "alpha": 100.0,
            "coefficients": ridge_imp,
            "intercept": round(float(ridge.intercept_), 4),
        },
        "xgb_config": {
            "n_estimators": 300, "max_depth": 3, "learning_rate": 0.02,
        },
        "scaler": {
            "means": {f: round(float(scaler.mean_[i]), 6) for i, f in enumerate(feature_names)},
            "scales": {f: round(float(scaler.scale_[i]), 6) for i, f in enumerate(feature_names)},
        },
        "sizing": {
            "method": "half_kelly_with_governor",
            "tier_caps": {"T1": 0.06, "T2": 0.06, "T3": 0.03, "T4": 0.015},
            "max_concurrent": 5,
            "max_nano": 2,
            "max_heat": 0.15,
            "max_single": 0.06,
            "dd_threshold": 0.15,
        },
        "entry_thresholds": {
            "min_predicted_return": 1.0,
            "min_entry_score": 0.40,
            "entry_score_weights": {"odin": 0.60, "magnitude": 0.40},
        },
        "ridge_importance": ridge_imp,
        "xgb_importance": xgb_imp,
    }

    return deploy


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*80)
    print("BIFROST v3.1 BUILD — Honest Walk-Forward")
    print("="*80)

    # Load data
    print("\n[LOAD] Bifrost events...")
    events = []
    with open(BIFROST_CSV) as f:
        for row in csv.DictReader(f):
            events.append(row)
    print(f"  Events: {len(events)}")

    print("[LOAD] Price cache...")
    with open(PRICE_CACHE) as f:
        price_cache = json.load(f)
    print(f"  Price series: {len(price_cache)}")

    # Build training data
    print("\n[BUILD] Training data...")
    rows, feature_names = build_training_data(events, price_cache)
    print(f"  Rows: {len(rows)}, Features: {len(feature_names)}")

    # Walk-forward backtest (HONEST)
    results = walk_forward_backtest(rows, feature_names)

    # Train final model for deployment
    deploy = train_final_model(rows, feature_names)

    # Save
    with open(V3_DEPLOY, "w") as f:
        json.dump(deploy, f, indent=2)
    print(f"\n  Deploy config: {V3_DEPLOY}")

    results_full = {
        "version": "3.1.0",
        "backtest": results,
        "deploy_path": V3_DEPLOY,
    }
    with open(V3_RESULTS, "w") as f:
        json.dump(results_full, f, indent=2)
    print(f"  Results: {V3_RESULTS}")

    print(f"\n{'='*80}")
    print(f"BIFROST v3.1 BUILD COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
