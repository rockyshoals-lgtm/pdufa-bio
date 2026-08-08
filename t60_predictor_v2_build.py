#!/usr/bin/env python3
"""
T-60 Runup Gap Predictor v2.0 Build
====================================
Honest 3-way split kaizen expansion of v1.

New feature families:
  A) ChEMBL drug-biology (molecule_type, mechanism, target_class, FIC)
  B) Large x T4 interactions (largest runup-gap segment, +6.42pp p=98.1%)
  C) Designation stacking (btd_x_orphan, pr_x_ft, desig_count_sq)

Methodology (unchanged from v1):
  - 3-way temporal split: train <=2023 / val 2024 / test >=2025
  - Target winsorized to [-50%, +100%]
  - Two heads: mu_AP fit on approvals only, mu_CR fit on CRLs only
  - Predicted gap = mu_AP(X) - mu_CR(X)
  - Val-only feature selection (greedy, gate Delta_val_R2 >= 0.002)
  - Per-head alpha sweep on val
  - Bootstrap 95% CI on predicted gap
  - 20-seed stability check

v1 baseline to beat:
  pred_gap_mean_test = +3.62 pp, CI [+2.99, +4.27]
  seed stability = 95%
  Quintile monotonic: Q1 pred_gap -4.8% -> Q5 pred_gap +11.8%
"""

import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from pathlib import Path
from datetime import datetime

DATA = Path("/sessions/confident-serene-ptolemy/mnt/9realms")

BIFROST_CSV = DATA / "pdufa_runup_bifrost.csv"
ODIN_CSV = DATA / "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv"
CHEMBL_CACHE = DATA / "chembl_enrichment_cache_v2.json"
OUT_DEPLOY = DATA / "t60_runup_gap_predictor_v2_deploy.json"
OUT_TEST_PRED = DATA / "t60_test_predictions_v2.csv"
OUT_RESULTS = DATA / "t60_predictor_v2_results.json"

# Winsorization bounds
WIN_LO, WIN_HI = -0.50, 1.00

# v1 baseline features (50)
V1_FEATURES = [
    'btd', 'orphan', 'priority_review', 'fast_track', 'accelerated_approval',
    'sponsor_prior_approvals', 'manufacturing_risk', 'form_483_issues',
    'ema_cmc_flag', 'cmc_extension_flag', 'had_adcom', 'adcom_vote_pct',
    'prior_crl', 'prior_crl_count', 'resubmission_class', 'ta_base_score',
    'historical_crl_rate', 's22_ped_pk_missing', 's23_signal_strength',
    's6_signal_strength', 'social_sentiment_score', 'gene_therapy',
    'psychedelics', 'surrogate_endpoint', 'single_arm_study',
    'safety_signal_severity', 'ppm_flag', 'btd_oncology_interaction',
    'btd_priority_interaction', 'ta_very_high_risk', 'double_crl_flag',
    'ta_is_very_high', 'ta_is_high', 'ta_is_mod', 'ta_is_low',
    'is_nda', 'is_bla', 'era_post', 'sponsor_x_btd', 'crl_rate_x_resub',
    'ta_vh_x_sponsor', 'ppm_x_small_size', 'desig_count',
    'naive_sponsor', 'experienced_sponsor', 'log_sponsor',
    'mcap_is_large', 'mcap_is_nano', 'mcap_is_micro', 'mcap_is_small'
]


def load_chembl_lookup():
    """Build uppercase-name -> enrichment lookup."""
    with open(CHEMBL_CACHE) as f:
        raw = json.load(f)
    lookup = {}
    for key, val in raw.items():
        lookup[key.upper()] = val
        # also index by token
        for tok in key.upper().split():
            if len(tok) >= 4 and tok not in lookup:
                lookup[tok] = val
    return lookup


def fuzzy_chembl_lookup(asset_str, lookup):
    """Best-effort ChEMBL match on asset string."""
    if not isinstance(asset_str, str):
        return None
    A = asset_str.upper()
    # direct substring hits on lookup keys
    for key in lookup:
        if key in A and len(key) >= 4:
            return lookup[key]
    # first token of asset
    toks = [t.strip("().,;:/[]") for t in A.split()]
    for tok in toks:
        if tok in lookup:
            return lookup[tok]
    return None


def build_dataset():
    """Merge BIFROST + ODIN, enrich with ChEMBL, add v2 features."""
    df_b = pd.read_csv(BIFROST_CSV)
    df_o = pd.read_csv(ODIN_CSV)
    df_b['pdufa_date'] = pd.to_datetime(df_b['pdufa_date'])
    df_o['catalyst_date'] = pd.to_datetime(df_o['catalyst_date'])
    m = df_b.merge(df_o, left_on=['ticker', 'pdufa_date'],
                   right_on=['ticker', 'catalyst_date'],
                   how='inner', suffixes=('_b', '_o'))
    print(f"[merge] {len(m)} rows")
    m = m[m['T-60_T-1'].notna()].copy()
    m = m[m['outcome_o'].isin(['APPROVAL', 'CRL'])].copy()
    print(f"[clean] {len(m)} rows with T-60 + outcome")

    # Winsorize target
    m['target'] = m['T-60_T-1'].clip(WIN_LO, WIN_HI)
    m['outcome_bin'] = (m['outcome_o'] == 'APPROVAL').astype(int)

    # Coerce boolean-like string columns to numeric 0/1
    def _to_bool_float(s):
        if s.dtype == bool:
            return s.astype(float)
        if s.dtype == 'object':
            mp = {'TRUE': 1, 'FALSE': 0, 'Yes': 1, 'No': 0, 'yes': 1, 'no': 0,
                  'Y': 1, 'N': 0, 'True': 1, 'False': 0, 'true': 1, 'false': 0, '1': 1, '0': 0}
            return s.map(mp).fillna(0).astype(float)
        return s.fillna(0).astype(float)
    for _c in ['accelerated_approval','btd','orphan','priority_review','fast_track',
               'surrogate_endpoint','single_arm_study','prior_crl','gene_therapy',
               'psychedelics','ppm_flag','form_483_issues','ema_cmc_flag','cmc_extension_flag',
               'had_adcom','safety_signal_severity','manufacturing_risk','double_crl_flag']:
        if _c in m.columns:
            m[_c] = _to_bool_float(m[_c])

    # Build v1 base features (mirror v1 construction)
    m['ta_is_very_high'] = (m['ta_base_score'].fillna(0) >= 0.65).astype(float)
    m['ta_is_high'] = ((m['ta_base_score'] >= 0.45) & (m['ta_base_score'] < 0.65)).astype(float)
    m['ta_is_mod'] = ((m['ta_base_score'] >= 0.25) & (m['ta_base_score'] < 0.45)).astype(float)
    m['ta_is_low'] = (m['ta_base_score'].fillna(0) < 0.25).astype(float)
    m['is_nda'] = (m['application_type'].astype(str).str.upper() == 'NDA').astype(float)
    m['is_bla'] = (m['application_type'].astype(str).str.upper() == 'BLA').astype(float)
    m['era_post'] = (m['fda_era'].astype(str).str.upper() == 'POST').astype(float)
    spa = m['sponsor_prior_approvals'].fillna(0)
    m['naive_sponsor'] = (spa <= 2).astype(float)
    m['experienced_sponsor'] = (spa > 5).astype(float)
    m['log_sponsor'] = np.log1p(spa)
    m['desig_count'] = (
        m['btd'].fillna(0).astype(float) +
        m['orphan'].fillna(0).astype(float) +
        m['priority_review'].fillna(0).astype(float) +
        m['fast_track'].fillna(0).astype(float) +
        m['accelerated_approval'].fillna(0).astype(float)
    )
    m['sponsor_x_btd'] = m['log_sponsor'] * m['btd'].fillna(0).astype(float)
    m['crl_rate_x_resub'] = m['historical_crl_rate'].fillna(0) * (m['resubmission_class'].fillna(0) > 0).astype(float)
    m['ta_vh_x_sponsor'] = m['ta_is_very_high'] * m['log_sponsor']
    mcap_str = m['mcap_tier'].astype(str).str.lower()
    m['mcap_is_large'] = mcap_str.eq('large').astype(float)
    m['mcap_is_mid'] = mcap_str.eq('mid').astype(float)
    m['mcap_is_small'] = mcap_str.eq('small').astype(float)
    m['mcap_is_micro'] = mcap_str.eq('micro').astype(float)
    m['mcap_is_nano'] = mcap_str.eq('nano').astype(float)
    m['ppm_x_small_size'] = m['ppm_flag'].fillna(0).astype(float) * (m['mcap_is_small'] + m['mcap_is_micro'] + m['mcap_is_nano'])

    # v1 feature coverage check
    missing = [c for c in V1_FEATURES if c not in m.columns]
    if missing:
        raise RuntimeError(f"Missing v1 features after derivation: {missing}")

    # --- v2 NEW FEATURES ---
    # A) ChEMBL enrichment
    chem = load_chembl_lookup()
    n_hit = 0
    chem_cols = {
        'ch_is_small_molecule': [], 'ch_is_biologic': [],
        'ch_mech_antagonist': [], 'ch_mech_agonist': [], 'ch_mech_inhibitor': [],
        'ch_mech_modulator': [], 'ch_mech_activator': [],
        'ch_tc_gpcr': [], 'ch_tc_kinase': [], 'ch_tc_enzyme': [],
        'ch_tc_ion_channel': [], 'ch_tc_nuclear_receptor': [],
        'ch_first_in_class': [], 'ch_has_approved_comp': [],
        'ch_scorable': []
    }
    for asset in m['asset_b'].tolist():
        hit = fuzzy_chembl_lookup(asset, chem)
        if hit is None:
            for k in chem_cols:
                chem_cols[k].append(0.0)
            continue
        n_hit += 1
        mt = (hit.get('molecule_type') or '').lower()
        mech = (hit.get('mechanism_type') or '').lower()
        tc = (hit.get('target_class') or '').lower()
        chem_cols['ch_is_small_molecule'].append(float(mt == 'small molecule'))
        chem_cols['ch_is_biologic'].append(float(hit.get('is_biologic') is True))
        chem_cols['ch_mech_antagonist'].append(float('antagonist' in mech))
        chem_cols['ch_mech_agonist'].append(float('agonist' in mech and 'antagonist' not in mech))
        chem_cols['ch_mech_inhibitor'].append(float('inhibitor' in mech))
        chem_cols['ch_mech_modulator'].append(float('modulator' in mech))
        chem_cols['ch_mech_activator'].append(float('activator' in mech))
        chem_cols['ch_tc_gpcr'].append(float('gpcr' in tc))
        chem_cols['ch_tc_kinase'].append(float('kinase' in tc))
        chem_cols['ch_tc_enzyme'].append(float('enzyme' in tc))
        chem_cols['ch_tc_ion_channel'].append(float('ion channel' in tc or 'ion_channel' in tc))
        chem_cols['ch_tc_nuclear_receptor'].append(float('nuclear receptor' in tc or 'nuclear_receptor' in tc))
        chem_cols['ch_first_in_class'].append(float(hit.get('first_in_class') is True))
        chem_cols['ch_has_approved_comp'].append(float(hit.get('has_approved_competitor') is True))
        chem_cols['ch_scorable'].append(1.0)
    for k, v in chem_cols.items():
        m[k] = v
    print(f"[chembl] {n_hit} of {len(m)} events matched ({100*n_hit/len(m):.1f}%)")

    # B) Large x T4 interactions (T4 proxy = high CRL risk)
    large = m['mcap_is_large']
    crl_high = (m['historical_crl_rate'].fillna(0) >= 0.40).astype(float)
    m['mcap_large_x_crl_high'] = large * crl_high
    m['mcap_large_x_naive_sponsor'] = large * m['naive_sponsor']
    m['mcap_large_x_double_crl'] = large * m['double_crl_flag'].fillna(0).astype(float)
    m['mcap_large_x_resub_class2'] = large * (m['resubmission_class'].fillna(0) >= 2).astype(float)
    m['mcap_large_x_safety_high'] = large * (m['safety_signal_severity'].fillna(0) >= 2).astype(float)
    m['mcap_large_x_ppm'] = large * m['ppm_flag'].fillna(0).astype(float)
    m['mcap_large_x_ta_vh'] = large * m['ta_is_very_high']
    m['mcap_large_x_t4_composite'] = (
        m['mcap_large_x_crl_high'] + m['mcap_large_x_naive_sponsor'] +
        m['mcap_large_x_double_crl'] + m['mcap_large_x_resub_class2'] +
        m['mcap_large_x_safety_high']
    )

    # C) Designation stacking
    m['btd_x_orphan'] = m['btd'].fillna(0) * m['orphan'].fillna(0)
    m['btd_x_pr'] = m['btd'].fillna(0) * m['priority_review'].fillna(0)
    m['pr_x_ft'] = m['priority_review'].fillna(0) * m['fast_track'].fillna(0)
    m['btd_x_ft'] = m['btd'].fillna(0) * m['fast_track'].fillna(0)
    m['all_desig'] = (m['desig_count'] >= 3).astype(float)
    m['desig_count_sq'] = m['desig_count'] ** 2

    # D) ChEMBL x regulatory interactions
    m['ch_bio_x_btd'] = m['ch_is_biologic'] * m['btd'].fillna(0)
    m['ch_sm_x_orphan'] = m['ch_is_small_molecule'] * m['orphan'].fillna(0)
    m['ch_fic_x_btd'] = m['ch_first_in_class'] * m['btd'].fillna(0)
    m['ch_fic_x_safety'] = m['ch_first_in_class'] * (m['safety_signal_severity'].fillna(0) >= 2).astype(float)

    return m


def split_3way(df):
    """train <= 2023, val 2024, test >= 2025"""
    cutoff_train = pd.Timestamp('2024-01-01')
    cutoff_val = pd.Timestamp('2025-01-01')
    tr = df[df['pdufa_date'] < cutoff_train].copy()
    va = df[(df['pdufa_date'] >= cutoff_train) & (df['pdufa_date'] < cutoff_val)].copy()
    te = df[df['pdufa_date'] >= cutoff_val].copy()
    return tr, va, te


def fit_head(X_tr, y_tr, X_va, y_va, alphas):
    """Sweep alpha on val MAE, return best ridge + scaler + metrics."""
    scaler = StandardScaler().fit(X_tr)
    Xtrs = scaler.transform(X_tr)
    Xvas = scaler.transform(X_va)
    best = None
    for a in alphas:
        r = Ridge(alpha=a, random_state=42).fit(Xtrs, y_tr)
        pv = r.predict(Xvas)
        mae = float(np.mean(np.abs(pv - y_va)))
        r2 = 1.0 - float(np.var(pv - y_va)) / max(1e-9, float(np.var(y_va)))
        if best is None or mae < best['val_MAE']:
            best = {'alpha': a, 'model': r, 'val_MAE': mae, 'val_R2': r2, 'scaler': scaler}
    return best


def evaluate_head(best, X_te, y_te):
    Xtes = best['scaler'].transform(X_te)
    pt = best['model'].predict(Xtes)
    mae = float(np.mean(np.abs(pt - y_te)))
    r2 = 1.0 - float(np.var(pt - y_te)) / max(1e-9, float(np.var(y_te)))
    return mae, r2, pt


def greedy_forward(X_tr_all, y_tr, X_va_all, y_va, alphas, all_features, max_rounds=30, gate=0.002):
    """Val-R2 gated greedy forward selection."""
    selected = []
    remaining = list(all_features)
    best_overall_r2 = -np.inf
    history = []

    # seed: pick best single feature
    for rnd in range(max_rounds):
        round_best = None
        round_best_r2 = best_overall_r2
        for feat in remaining:
            trial = selected + [feat]
            Xtr = X_tr_all[trial].values
            Xva = X_va_all[trial].values
            head = fit_head(Xtr, y_tr, Xva, y_va, alphas)
            if head['val_R2'] > round_best_r2:
                round_best_r2 = head['val_R2']
                round_best = (feat, head['val_R2'], head)
        if round_best is None:
            break
        improvement = round_best[1] - best_overall_r2
        if improvement < gate and len(selected) > 0:
            history.append({'round': rnd, 'no_improvement': True, 'best_candidate': round_best[0],
                            'delta': improvement})
            break
        selected.append(round_best[0])
        remaining.remove(round_best[0])
        best_overall_r2 = round_best[1]
        history.append({'round': rnd, 'added': round_best[0],
                        'val_R2': round_best[1], 'delta': improvement,
                        'selected_count': len(selected)})
        print(f"  r{rnd}: +{round_best[0]} -> val_R2={round_best[1]:.4f} (Δ={improvement:+.4f})")
    return selected, history


def bootstrap_gap_ci(pred_ap, pred_cr, n_boot=2000, seed=42):
    """Bootstrap CI on mean(pred_ap - pred_cr) per-event."""
    rng = np.random.default_rng(seed)
    gaps = pred_ap - pred_cr
    n = len(gaps)
    means = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        means.append(float(np.mean(gaps[idx])))
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(np.mean(gaps)), float(lo), float(hi)


def seed_stability(X_tr_ap, y_tr_ap, X_tr_cr, y_tr_cr, X_te, feats, alpha_ap, alpha_cr, n_seeds=20):
    """Refit both heads under seed perturbation; report pct seeds with positive mean gap."""
    rng_master = np.random.default_rng(42)
    seeds = rng_master.integers(0, 10**6, n_seeds)
    means = []
    for s in seeds:
        rng = np.random.default_rng(s)
        # bootstrap training data
        idx_ap = rng.integers(0, len(X_tr_ap), len(X_tr_ap))
        idx_cr = rng.integers(0, len(X_tr_cr), len(X_tr_cr))
        sc_ap = StandardScaler().fit(X_tr_ap.iloc[idx_ap])
        sc_cr = StandardScaler().fit(X_tr_cr.iloc[idx_cr])
        r_ap = Ridge(alpha=alpha_ap, random_state=int(s)).fit(sc_ap.transform(X_tr_ap.iloc[idx_ap]), y_tr_ap[idx_ap])
        r_cr = Ridge(alpha=alpha_cr, random_state=int(s)).fit(sc_cr.transform(X_tr_cr.iloc[idx_cr]), y_tr_cr[idx_cr])
        pa = r_ap.predict(sc_ap.transform(X_te))
        pc = r_cr.predict(sc_cr.transform(X_te))
        means.append(float(np.mean(pa - pc)))
    means = np.array(means)
    return {
        'n_seeds': n_seeds,
        'mean': float(np.mean(means)),
        'std': float(np.std(means)),
        'positive_pct': float(100 * np.sum(means > 0) / n_seeds),
        'values': means.tolist(),
    }


def quintile_validate(pred_gap_test, actual_gap_test, outcome_test):
    """Sort predicted gap into 5 quintiles, check monotonicity."""
    df = pd.DataFrame({
        'pred_gap': pred_gap_test,
        'actual_ret': actual_gap_test,
        'outcome_bin': outcome_test,
    })
    df = df.dropna()
    df['q'] = pd.qcut(df['pred_gap'], 5, duplicates='drop')
    # Re-label quintiles by rank after any dedup
    unique_bins = df['q'].cat.categories
    q_labels = [f'Q{i+1}' for i in range(len(unique_bins))]
    df['q'] = df['q'].cat.rename_categories(q_labels)
    agg = df.groupby('q', observed=True).agg(
        n=('pred_gap', 'size'),
        pred_gap_mean=('pred_gap', 'mean'),
        actual_ap_mean=('actual_ret', lambda x: x[df.loc[x.index, 'outcome_bin'] == 1].mean() if (df.loc[x.index, 'outcome_bin'] == 1).any() else np.nan),
        actual_cr_mean=('actual_ret', lambda x: x[df.loc[x.index, 'outcome_bin'] == 0].mean() if (df.loc[x.index, 'outcome_bin'] == 0).any() else np.nan),
    )
    agg['actual_gap'] = agg['actual_ap_mean'] - agg['actual_cr_mean']
    q_thresholds = df.groupby('q', observed=True)['pred_gap'].max().to_dict()
    return agg.reset_index().to_dict('records'), {str(k): float(v) for k, v in q_thresholds.items()}


def main():
    print("[1/7] Build dataset")
    df = build_dataset()

    # Candidate features
    new_chembl = [c for c in df.columns if c.startswith('ch_')]
    new_large_t4 = [c for c in df.columns if c.startswith('mcap_large_x_')]
    new_desig = ['btd_x_orphan', 'btd_x_pr', 'pr_x_ft', 'btd_x_ft', 'all_desig', 'desig_count_sq']
    CANDIDATES = V1_FEATURES + new_chembl + new_large_t4 + new_desig
    CANDIDATES = [c for c in CANDIDATES if c in df.columns]
    print(f"  total candidates: {len(CANDIDATES)} (v1=50, new={len(CANDIDATES)-50})")

    # Fill NaN
    for c in CANDIDATES:
        df[c] = df[c].fillna(0).astype(float)

    print("\n[2/7] Temporal split")
    tr, va, te = split_3way(df)
    print(f"  train: {len(tr)}, val: {len(va)}, test: {len(te)}")
    print(f"  train AP: {(tr.outcome_bin==1).sum()}, CR: {(tr.outcome_bin==0).sum()}")
    print(f"  val   AP: {(va.outcome_bin==1).sum()}, CR: {(va.outcome_bin==0).sum()}")
    print(f"  test  AP: {(te.outcome_bin==1).sum()}, CR: {(te.outcome_bin==0).sum()}")

    ALPHAS = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0]

    # ---- Fit mu_AP head on APPROVALS
    print("\n[3/7] Train mu_AP head (approvals only) - greedy forward")
    tr_ap = tr[tr.outcome_bin == 1]
    va_ap = va[va.outcome_bin == 1]
    y_tr_ap = tr_ap['target'].values
    y_va_ap = va_ap['target'].values
    sel_ap, hist_ap = greedy_forward(tr_ap[CANDIDATES], y_tr_ap,
                                      va_ap[CANDIDATES], y_va_ap,
                                      ALPHAS, CANDIDATES, max_rounds=25, gate=0.002)
    print(f"  mu_AP features selected: {len(sel_ap)}")

    # ---- Fit mu_CR head on CRLs
    print("\n[4/7] Train mu_CR head (CRLs only) - greedy forward")
    tr_cr = tr[tr.outcome_bin == 0]
    va_cr = va[va.outcome_bin == 0]
    y_tr_cr = tr_cr['target'].values
    y_va_cr = va_cr['target'].values
    sel_cr, hist_cr = greedy_forward(tr_cr[CANDIDATES], y_tr_cr,
                                      va_cr[CANDIDATES], y_va_cr,
                                      ALPHAS, CANDIDATES, max_rounds=25, gate=0.002)
    print(f"  mu_CR features selected: {len(sel_cr)}")

    # Union of selected features
    SEL = list(dict.fromkeys(sel_ap + sel_cr))
    print(f"\n[5/7] Fit final heads on union feature set: {len(SEL)} features")

    # Refit both heads on SEL
    head_ap = fit_head(tr_ap[SEL].values, y_tr_ap,
                       va_ap[SEL].values, y_va_ap, ALPHAS)
    head_cr = fit_head(tr_cr[SEL].values, y_tr_cr,
                       va_cr[SEL].values, y_va_cr, ALPHAS)
    print(f"  mu_AP alpha={head_ap['alpha']} val_MAE={head_ap['val_MAE']:.4f} val_R2={head_ap['val_R2']:.4f}")
    print(f"  mu_CR alpha={head_cr['alpha']} val_MAE={head_cr['val_MAE']:.4f} val_R2={head_cr['val_R2']:.4f}")

    # Test metrics
    X_te = te[SEL].values
    y_te = te['target'].values
    outcome_te = te['outcome_bin'].values
    mae_ap, r2_ap, pred_ap = evaluate_head(head_ap, X_te, y_te)
    mae_cr, r2_cr, pred_cr = evaluate_head(head_cr, X_te, y_te)
    print(f"  mu_AP test_MAE={mae_ap:.4f} test_R2={r2_ap:.4f}")
    print(f"  mu_CR test_MAE={mae_cr:.4f} test_R2={r2_cr:.4f}")

    # Bootstrap CI on predicted gap
    print("\n[6/7] Bootstrap gap CI + seed stability")
    pred_gap = pred_ap - pred_cr
    gm, lo, hi = bootstrap_gap_ci(pred_ap, pred_cr, n_boot=2000, seed=42)
    print(f"  mean pred_gap = {gm*100:.2f} pp, CI95 [{lo*100:.2f}, {hi*100:.2f}]")

    # Actual gap on test
    act_ap_mean = float(np.mean(y_te[outcome_te == 1])) if (outcome_te == 1).any() else np.nan
    act_cr_mean = float(np.mean(y_te[outcome_te == 0])) if (outcome_te == 0).any() else np.nan
    act_gap = act_ap_mean - act_cr_mean

    # Seed stability
    stab = seed_stability(
        tr_ap[SEL], y_tr_ap, tr_cr[SEL], y_tr_cr, te[SEL],
        SEL, head_ap['alpha'], head_cr['alpha'], n_seeds=20
    )
    print(f"  seed stability: {stab['positive_pct']:.1f}% positive, mean={stab['mean']*100:.2f}pp")

    # Quintile validate
    q_records, q_thresh = quintile_validate(pred_gap, y_te, outcome_te)
    print("  quintile sort:")
    for r in q_records:
        print(f"    {r['q']}: n={r['n']:3d} pred_gap={r['pred_gap_mean']*100:+.2f}pp "
              f"actual AP={(r['actual_ap_mean'] or 0)*100:+.2f} CR={(r['actual_cr_mean'] or 0)*100:+.2f} "
              f"actual_gap={(r['actual_gap'] or 0)*100:+.2f}pp")

    # ---- Persist deploy + test predictions ----
    print("\n[7/7] Persist deploy + results")

    deploy = {
        'version': '2.0.0',
        'generated': datetime.utcnow().isoformat() + 'Z',
        'target': 'T-60_T-1 returns, winsorized to [-50%, +100%]',
        'winsorization': {'lo': WIN_LO, 'hi': WIN_HI},
        'split': {
            'train_n': int(len(tr)), 'val_n': int(len(va)), 'test_n': int(len(te)),
            'train_cutoff': '<2024-01-01', 'val': '2024', 'test': '>=2025-01-01',
        },
        'features': SEL,
        'feature_provenance': {
            'from_v1': [f for f in SEL if f in V1_FEATURES],
            'chembl': [f for f in SEL if f.startswith('ch_')],
            'large_t4': [f for f in SEL if f.startswith('mcap_large_x_')],
            'desig_stacking': [f for f in SEL if f in new_desig],
        },
        'mu_AP': {
            'alpha': head_ap['alpha'],
            'intercept': float(head_ap['model'].intercept_),
            'coefs': [float(c) for c in head_ap['model'].coef_],
            'scaler_mean': [float(x) for x in head_ap['scaler'].mean_],
            'scaler_scale': [float(x) for x in head_ap['scaler'].scale_],
            'val_MAE': head_ap['val_MAE'], 'val_R2': head_ap['val_R2'],
            'test_MAE': mae_ap, 'test_R2': r2_ap,
            'n_train': int(len(tr_ap)),
        },
        'mu_CR': {
            'alpha': head_cr['alpha'],
            'intercept': float(head_cr['model'].intercept_),
            'coefs': [float(c) for c in head_cr['model'].coef_],
            'scaler_mean': [float(x) for x in head_cr['scaler'].mean_],
            'scaler_scale': [float(x) for x in head_cr['scaler'].scale_],
            'val_MAE': head_cr['val_MAE'], 'val_R2': head_cr['val_R2'],
            'test_MAE': mae_cr, 'test_R2': r2_cr,
            'n_train': int(len(tr_cr)),
        },
        'gap_validation': {
            'actual_ap_mean_test': act_ap_mean,
            'actual_cr_mean_test': act_cr_mean,
            'actual_gap_test': act_gap,
            'pred_gap_mean_test': gm,
            'pred_gap_ci95': [lo, hi],
            'seed_stability_positive_pct': stab['positive_pct'],
            'seed_mean': stab['mean'],
            'seed_std': stab['std'],
        },
        'quintile_thresholds': q_thresh,
        'quintile_records': q_records,
        'v1_comparison': {
            'v1_pred_gap_mean': 0.03620725760357731,
            'v1_pred_gap_ci95': [0.029875382001194106, 0.042732240247764106],
            'v1_seed_stability_pct': 95.0,
            'v1_feature_count': 50,
            'v2_vs_v1_delta_gap_pp': float(gm - 0.03620725760357731) * 100,
            'v2_vs_v1_delta_ci_width_pp': float((hi - lo) - (0.042732240247764106 - 0.029875382001194106)) * 100,
            'v2_vs_v1_feature_count_delta': len(SEL) - 50,
        },
        'decomposition_reference': 'PDUFA Runup Decomposition v2.0 — Large x T4 segment +6.42pp',
        'notes': [
            'v2 adds ChEMBL drug-biology + Large×T4 interaction + designation stacking features',
            'Honest 3-way split: train <=2023 / val 2024 / test >=2025',
            'Val-only greedy forward selection, gate Delta_val_R2 >= 0.002',
            'Alpha sweep per head, independent convergence',
            'GATING FILTER ONLY — use quintile rank, not magnitude',
        ],
    }

    with open(OUT_DEPLOY, 'w') as f:
        json.dump(deploy, f, indent=2)
    print(f"  wrote {OUT_DEPLOY}")

    # Test predictions CSV
    pred_df = te[['ticker', 'asset_b', 'pdufa_date', 'outcome_o', 'mcap_tier', 'T-60_T-1']].copy()
    pred_df['pred_mu_AP'] = pred_ap
    pred_df['pred_mu_CR'] = pred_cr
    pred_df['pred_gap'] = pred_gap
    pred_df.to_csv(OUT_TEST_PRED, index=False)
    print(f"  wrote {OUT_TEST_PRED}")

    # Results JSON (summary for memo)
    results = {
        'version': '2.0.0',
        'generated': datetime.utcnow().isoformat() + 'Z',
        'candidates_tested': len(CANDIDATES),
        'features_from_v1': sum(1 for f in SEL if f in V1_FEATURES),
        'features_v2_new': sum(1 for f in SEL if f not in V1_FEATURES),
        'final_feature_count': len(SEL),
        'mu_AP_greedy_history': hist_ap,
        'mu_CR_greedy_history': hist_cr,
        'mu_AP_test_R2': r2_ap,
        'mu_CR_test_R2': r2_cr,
        'pred_gap_mean_test_pp': gm * 100,
        'pred_gap_ci95_pp': [lo * 100, hi * 100],
        'seed_stability_pct': stab['positive_pct'],
        'v2_vs_v1_delta_gap_pp': float(gm - 0.03620725760357731) * 100,
        'v2_selected_features': SEL,
    }
    with open(OUT_RESULTS, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  wrote {OUT_RESULTS}")

    print("\n=== DONE ===")
    print(f"v1 baseline: pred_gap +3.62 pp, CI [+2.99, +4.27], seeds 95% positive, 50 features")
    print(f"v2 result:   pred_gap {gm*100:+.2f} pp, CI [{lo*100:+.2f}, {hi*100:+.2f}], seeds {stab['positive_pct']:.1f}% positive, {len(SEL)} features")
    delta = (gm - 0.03620725760357731) * 100
    print(f"v2 - v1:     Δ gap {delta:+.2f} pp, Δ features {len(SEL) - 50:+d}")


if __name__ == '__main__':
    main()
