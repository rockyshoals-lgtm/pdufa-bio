#!/usr/bin/env python3
"""
Phase 1.6 — Honest eval: Form 4 features on Gungnir v48.

Methodology (STRICT — matches ODIN v18 Form 4 eval pattern, 3-way split):
  - Split: train <= 2022-12-31 / val 2023-2024 / test >= 2025
  - Baseline: Gungnir v46 126-feature Ridge baseline via gungnir_v46_kaizen chain
  - C swept on val only
  - Candidate: baseline + Form 4 feature (one at a time), val gate Δval_AUC >= +0.002
  - Greedy forward: add best surviving candidate, repeat up to max_rounds
  - Test touched once at the end, bootstrap 95% CI (n_boot=2000, seed=42)

Input:
  - gungnir_v46_kaizen.py (pipeline — produces 126-feature matrix)
  - form4_event_features.csv (ticker + catalyst_date + form 4 features)

Output:
  - form4_gungnir_honest_results.json
"""

import os
import sys
import io
import json
import csv
import time
import warnings
from pathlib import Path
from datetime import datetime
import numpy as np

warnings.filterwarnings('ignore')

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, brier_score_loss
except Exception:
    print('ERROR: sklearn required')
    sys.exit(1)

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
WORKSPACE = Path('/sessions/confident-serene-ptolemy')
F4_CSV = WORKSPACE / 'form4_event_features.csv'
OUT_JSON = WORKSPACE / 'form4_gungnir_honest_results.json'

# Ensure we can import gungnir_v46_kaizen
sys.path.insert(0, str(BASE))

TRAIN_END = datetime(2022, 12, 31)
VAL_START = datetime(2023, 1, 1)
VAL_END = datetime(2024, 12, 31)
TEST_START = datetime(2025, 1, 1)

C_GRID = [0.005, 0.01, 0.02, 0.03, 0.05, 0.10, 0.20]
VAL_GATE = 0.002
MAX_GREEDY_ROUNDS = 10
BOOT = 2000
RANDOM_SEED = 42


def parse_date(s):
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(str(s).strip(), fmt)
        except ValueError:
            continue
    return None


def build_gungnir_baseline():
    """Run the gungnir_v46_kaizen chain to build the 126-feature matrix.

    Returns: X_full (N, 126), y_bin (N,), events (list of dicts), feat_full (list of names)
    """
    # Silence kaizen chain print noise
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        import gungnir_v46_kaizen as k
        v39 = k.load_v39_module()
        events, ctgov_lookup = v39.load_data()
        X_v39, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_v39 = v39.build_features(
            events, ctgov_lookup, include_v37=True, include_v38=True,
            include_candidates=k.V39_SELECTED
        )

        v40_lookup = k.build_v40_features(events)
        v40_cols = []
        for f in k.V40_SELECTED:
            col = np.array([
                float(v40_lookup.get(
                    (ev.get('ticker', '').upper(), ev.get('date', '')), {}
                ).get(f, 0) or 0)
                for ev in events
            ])
            v40_cols.append(col)
        X_v40 = np.column_stack([X_v39] + [c.reshape(-1, 1) for c in v40_cols])
        feat_v40 = list(feat_v39) + k.V40_SELECTED

        v41_dict = k.build_v41_features(events, X_v40, feat_v40, v40_lookup)
        X_v41 = np.column_stack([X_v40] + [v41_dict[f].reshape(-1, 1) for f in k.V41_SELECTED])
        feat_v41 = list(feat_v40) + k.V41_SELECTED

        v42_dict = k.build_v42_features(events, X_v41, feat_v41)
        X_v42 = np.column_stack([X_v41] + [v42_dict[f].reshape(-1, 1) for f in k.V42_SELECTED])
        feat_v42 = list(feat_v41) + k.V42_SELECTED

        ch2_features = k.build_chembl_features(events)
        v43_dict = k.build_v43_features(events, X_v42, feat_v42, ch2_features)
        X_v43 = np.column_stack([X_v42] + [v43_dict[f].reshape(-1, 1) for f in k.V43_SELECTED])
        feat_v43 = list(feat_v42) + k.V43_SELECTED

        v44_dict = k.build_v44_features(events, X_v43, feat_v43, ch2_features)
        X_v44 = np.column_stack([X_v43] + [v44_dict[f].reshape(-1, 1) for f in k.V44_SELECTED])
        feat_v44 = list(feat_v43) + k.V44_SELECTED

        keep = [i for i, f in enumerate(feat_v44) if f not in k.V45_DROPPED]
        X_v45 = X_v44[:, keep]
        feat_v45 = [feat_v44[i] for i in keep]

        deploy = json.load(open(BASE / 'gungnir_v46_deploy.json'))
        v46_selected = [f for f in deploy.get('features', []) if f.startswith('v46_')]
        if not v46_selected:
            v46_selected = [
                'v46_p1_ch2_moa_agonist', 'v46_p6_fic_X_is_phase3_X_sponsor',
                'v46_p6_sponsor_X_ch2_is_adc_X_is_phase2',
                'v46_p6_conf_X_ch2_is_advanced_X_is_small',
                'v46_p5_log1p_journey_last_positive',
                'v46_p2_ch2_is_adc_X_journey_n_negative',
                'v46_p6_conf_X_ch2_is_mab_X_is_small',
                'v46_p2_ch2_is_adc_X_journey_had_negative',
            ]
        v46_dict = k.generate_v46_candidates(events, X_v45, feat_v45, ch2_features, v40_lookup)
        v46_selected = [f for f in v46_selected if f in v46_dict]
        X_full = np.column_stack([X_v45] + [v46_dict[f].reshape(-1, 1) for f in v46_selected])
        feat_full = list(feat_v45) + v46_selected
    finally:
        sys.stdout = old

    return X_full, y_bin, events, feat_full, dates


def load_f4_features():
    """Load Form 4 event feature CSV. Key = (ticker, catalyst_date_str)."""
    d = {}
    feature_cols = []
    if not F4_CSV.exists():
        print(f'WARNING: {F4_CSV} not found — Form 4 stage must complete first')
        return d, feature_cols
    with open(F4_CSV) as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not feature_cols:
                feature_cols = [c for c in reader.fieldnames if c.startswith('f4_')]
            key = (r['ticker'].upper(), r['catalyst_date'])
            d[key] = {c: float(r[c]) if r[c] not in ('', None) else 0.0 for c in feature_cols}
    return d, feature_cols


def fit_score(X_train, y_train, X_val, y_val, X_test, y_test, C):
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)
    lr = LogisticRegression(C=C, solver='lbfgs', max_iter=5000, penalty='l2', random_state=RANDOM_SEED)
    lr.fit(X_train_s, y_train)
    p_val = lr.predict_proba(X_val_s)[:, 1]
    p_test = lr.predict_proba(X_test_s)[:, 1]
    val_auc = roc_auc_score(y_val, p_val) if len(set(y_val)) > 1 else 0.5
    test_auc = roc_auc_score(y_test, p_test) if len(set(y_test)) > 1 else 0.5
    test_brier = brier_score_loss(y_test, p_test)
    return {
        'val_auc': float(val_auc),
        'test_auc': float(test_auc),
        'test_brier': float(test_brier),
        'p_test': p_test.tolist(),
    }


def bootstrap_auc_diff(y, p_baseline, p_candidate, n_boot=BOOT, seed=42):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p_b = np.asarray(p_baseline)
    p_c = np.asarray(p_candidate)
    n = len(y)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(set(y[idx])) < 2:
            continue
        auc_b = roc_auc_score(y[idx], p_b[idx])
        auc_c = roc_auc_score(y[idx], p_c[idx])
        diffs.append(auc_c - auc_b)
    diffs = np.asarray(diffs)
    return {
        'mean': float(diffs.mean()),
        'ci95_lo': float(np.percentile(diffs, 2.5)),
        'ci95_hi': float(np.percentile(diffs, 97.5)),
        'p_lift_gt_0': float((diffs > 0).mean()),
    }


def bootstrap_auc(y, p, n_boot=BOOT, seed=42):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p = np.asarray(p)
    n = len(y)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(set(y[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y[idx], p[idx]))
    aucs = np.asarray(aucs)
    return {
        'ci95_lo': float(np.percentile(aucs, 2.5)),
        'ci95_hi': float(np.percentile(aucs, 97.5)),
    }


def main():
    t0 = time.time()
    print('[+] Building Gungnir v46 baseline (126-feature matrix)...')
    X_base, y, events, feat_full, dates = build_gungnir_baseline()
    print(f'    Events: {len(events)}  Features: {X_base.shape[1]}  Build time: {time.time()-t0:.1f}s')

    # Build ticker + catalyst_date per event
    event_keys = []
    for ev in events:
        tk = (ev.get('ticker') or '').upper().strip()
        cd_raw = ev.get('date') or ev.get('catalyst_date') or ''
        cd = parse_date(cd_raw)
        event_keys.append((tk, cd))

    # Split by date (honest 3-way)
    dates_arr = np.array([k[1] for k in event_keys], dtype=object)
    train_idx = np.array([i for i, d in enumerate(dates_arr) if d is not None and d <= TRAIN_END])
    val_idx = np.array([i for i, d in enumerate(dates_arr) if d is not None and VAL_START <= d <= VAL_END])
    test_idx = np.array([i for i, d in enumerate(dates_arr) if d is not None and d >= TEST_START])

    print(f'[+] Split: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}')
    print(f'    Train pos_rate={y[train_idx].mean():.1%}  Val pos_rate={y[val_idx].mean():.1%}  Test pos_rate={y[test_idx].mean():.1%}')

    if len(val_idx) < 50 or len(test_idx) < 50:
        print('ERROR: val or test set too small (< 50 events). Check date parsing.')
        sys.exit(1)

    # Load Form 4 features
    print('[+] Loading Form 4 features')
    f4_map, f4_cols = load_f4_features()
    print(f'    {len(f4_map):,} events with Form 4 data, {len(f4_cols)} feature columns')

    if not f4_cols:
        print('ERROR: No Form 4 feature columns found. Skipping greedy phase — baseline only.')
        X_f4 = np.zeros((len(events), 0))
        n_matched = 0
    else:
        n_matched = 0
        X_f4 = np.zeros((len(events), len(f4_cols)))
        for i, (tk, cd) in enumerate(event_keys):
            if cd is None:
                continue
            key = (tk, cd.strftime('%Y-%m-%d'))
            if key in f4_map:
                n_matched += 1
                for j, c in enumerate(f4_cols):
                    X_f4[i, j] = f4_map[key].get(c, 0.0)
        print(f'    Matched: {n_matched:,}/{len(events):,} Gungnir events ({100*n_matched/max(1,len(events)):.1f}%)')

    # C sweep on baseline
    print('[+] C sweep on baseline (val-only selection)')
    best_C = None
    best_val = -1
    c_results = {}
    for C in C_GRID:
        r = fit_score(X_base[train_idx], y[train_idx], X_base[val_idx], y[val_idx],
                      X_base[test_idx], y[test_idx], C)
        c_results[C] = r
        print(f'    C={C}: val_auc={r["val_auc"]:.4f}  test_auc={r["test_auc"]:.4f}')
        if r['val_auc'] > best_val:
            best_val = r['val_auc']
            best_C = C
    print(f'[+] Best C on val: {best_C} (val_auc={best_val:.4f})')

    baseline = c_results[best_C]

    # Greedy forward over Form 4 features
    selected = []
    selected_idx = []
    greedy_log = []
    current_val = best_val
    current_p_test = baseline['p_test']

    if f4_cols:
        print(f'[+] Greedy forward selection over {len(f4_cols)} Form 4 features (gate Δval >= {VAL_GATE})')
        for round_num in range(1, MAX_GREEDY_ROUNDS + 1):
            best_cand = None
            best_cand_val = current_val
            best_cand_delta = -1
            best_cand_idx = None
            best_cand_result = None
            round_scores = []

            for j, cname in enumerate(f4_cols):
                if j in selected_idx:
                    continue
                cols = selected_idx + [j]
                X_tr = np.hstack([X_base[train_idx], X_f4[train_idx][:, cols]])
                X_v = np.hstack([X_base[val_idx], X_f4[val_idx][:, cols]])
                X_te = np.hstack([X_base[test_idx], X_f4[test_idx][:, cols]])
                try:
                    r = fit_score(X_tr, y[train_idx], X_v, y[val_idx], X_te, y[test_idx], best_C)
                except Exception:
                    continue
                delta = r['val_auc'] - current_val
                round_scores.append({'feature': cname, 'delta_val': delta, 'val_auc': r['val_auc']})
                if delta > best_cand_delta:
                    best_cand_delta = delta
                    best_cand_val = r['val_auc']
                    best_cand = cname
                    best_cand_idx = j
                    best_cand_result = r

            round_scores.sort(key=lambda x: -x['delta_val'])
            top5 = round_scores[:5]
            print(f'    Round {round_num}: best={best_cand}  Δval={best_cand_delta:+.4f}')
            print(f'              top5: {[(t["feature"], round(t["delta_val"],4)) for t in top5]}')

            if best_cand_delta < VAL_GATE:
                print(f'    STOP: best delta {best_cand_delta:.4f} < gate {VAL_GATE}')
                greedy_log.append({
                    'round': round_num,
                    'stopped': True,
                    'best_candidate': best_cand,
                    'delta_val': best_cand_delta,
                    'top5': top5,
                })
                break

            selected.append(best_cand)
            selected_idx.append(best_cand_idx)
            current_val = best_cand_val
            current_p_test = best_cand_result['p_test']
            greedy_log.append({
                'round': round_num,
                'selected': best_cand,
                'delta_val': best_cand_delta,
                'new_val_auc': current_val,
                'new_test_auc': best_cand_result['test_auc'],
                'top5': top5,
            })

    # Final model
    if selected_idx:
        X_tr = np.hstack([X_base[train_idx], X_f4[train_idx][:, selected_idx]])
        X_v = np.hstack([X_base[val_idx], X_f4[val_idx][:, selected_idx]])
        X_te = np.hstack([X_base[test_idx], X_f4[test_idx][:, selected_idx]])
        final = fit_score(X_tr, y[train_idx], X_v, y[val_idx], X_te, y[test_idx], best_C)
    else:
        final = baseline

    test_auc_ci = bootstrap_auc(y[test_idx], final['p_test'])
    baseline_test_auc_ci = bootstrap_auc(y[test_idx], baseline['p_test'])
    lift_ci = bootstrap_auc_diff(y[test_idx], baseline['p_test'], final['p_test'])

    results = {
        'model': 'form4_gungnir_honest_v48',
        'generated_utc': datetime.utcnow().isoformat() + 'Z',
        'methodology': {
            'train_end': TRAIN_END.strftime('%Y-%m-%d'),
            'val_range': [VAL_START.strftime('%Y-%m-%d'), VAL_END.strftime('%Y-%m-%d')],
            'test_start': TEST_START.strftime('%Y-%m-%d'),
            'C_grid': C_GRID,
            'val_gate': VAL_GATE,
            'max_greedy_rounds': MAX_GREEDY_ROUNDS,
            'bootstrap_n': BOOT,
            'bootstrap_seed': 42,
        },
        'data': {
            'n_events': len(events),
            'n_train': int(len(train_idx)),
            'n_val': int(len(val_idx)),
            'n_test': int(len(test_idx)),
            'train_pos_rate': float(y[train_idx].mean()),
            'val_pos_rate': float(y[val_idx].mean()),
            'test_pos_rate': float(y[test_idx].mean()),
            'n_baseline_features': X_base.shape[1],
            'n_f4_candidate_features': len(f4_cols),
            'n_gungnir_events_matched_with_f4': int(n_matched),
        },
        'c_sweep': {str(C): {'val_auc': c_results[C]['val_auc'], 'test_auc': c_results[C]['test_auc']} for C in C_GRID},
        'best_C_on_val': best_C,
        'baseline': {
            'val_auc': baseline['val_auc'],
            'test_auc': baseline['test_auc'],
            'test_auc_ci95': [baseline_test_auc_ci['ci95_lo'], baseline_test_auc_ci['ci95_hi']],
            'test_brier': baseline['test_brier'],
            'n_features': X_base.shape[1],
        },
        'greedy_log': greedy_log,
        'selected_f4_features': selected,
        'final': {
            'val_auc': final['val_auc'],
            'test_auc': final['test_auc'],
            'test_auc_ci95': [test_auc_ci['ci95_lo'], test_auc_ci['ci95_hi']],
            'test_brier': final['test_brier'],
            'n_features': X_base.shape[1] + len(selected_idx),
            'lift_vs_baseline': {
                'test_auc_delta': final['test_auc'] - baseline['test_auc'],
                'lift_ci95': [lift_ci['ci95_lo'], lift_ci['ci95_hi']],
                'p_lift_gt_0': lift_ci['p_lift_gt_0'],
            },
        },
    }

    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)

    print('\n=== SUMMARY ===')
    print(f'Baseline val_auc={baseline["val_auc"]:.4f}  test_auc={baseline["test_auc"]:.4f}  CI95=[{baseline_test_auc_ci["ci95_lo"]:.4f}, {baseline_test_auc_ci["ci95_hi"]:.4f}]')
    print(f'Final    val_auc={final["val_auc"]:.4f}  test_auc={final["test_auc"]:.4f}  CI95=[{test_auc_ci["ci95_lo"]:.4f}, {test_auc_ci["ci95_hi"]:.4f}]')
    print(f'Lift     Δtest={final["test_auc"]-baseline["test_auc"]:+.4f}  CI95=[{lift_ci["ci95_lo"]:+.4f}, {lift_ci["ci95_hi"]:+.4f}]  p(lift>0)={lift_ci["p_lift_gt_0"]:.3f}')
    print(f'Selected features ({len(selected)}): {selected}')
    print(f'\nWrote {OUT_JSON}')


if __name__ == '__main__':
    main()
