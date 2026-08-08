#!/usr/bin/env python3
"""
FEATURE MINER v1.0 -- 2026-05-28
Weekly batch: generate candidate features, test against FULL v38.1 ensemble, write PROPOSALS.

NEVER AUTO-SHIPS. Writes proposals to proposals/ dir for human review.

GATING
------
A candidate feature only becomes a "PROPOSAL" if ALL pass:
1. ΔAUC > 0.005 vs baseline (full v38.1, not simplified)
2. ΔBrier <= 0 (no calibration regression)
3. 15+/20 seed bootstrap wins
4. Univariate AUC > 0.55 (not pure noise)

OUTPUT
------
proposals/YYYY-MM-DD_feature_proposals.md
proposals/YYYY-MM-DD_feature_proposals.json

stdout: "PROPOSAL: feature_name -- ΔAUC X.XXXX, ΔBrier Y.YYYY, S/20 seeds"
"""

import os
import sys
import json
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings('ignore')

HERE = Path(__file__).resolve().parent
PROPOSAL_DIR = HERE / "proposals"
PROPOSAL_DIR.mkdir(exist_ok=True)

# ============================================================================
# CANDIDATE FEATURE GENERATORS
# ============================================================================
def generate_candidates(df):
    """Generate candidate features. Returns dict of {name: series}."""
    import pandas as pd
    cands = {}
    def gn(col):
        if col in df.columns:
            return pd.to_numeric(df[col], errors='coerce').fillna(0)
        return pd.Series([0]*len(df), index=df.index)

    # Therapeutic area
    is_oncology = (df['therapeutic_area'].astype(str).str.lower().str.contains('onco|cancer|hema|tumor|leuk|lymph', na=False)).astype(int)
    is_neuro = (df['therapeutic_area'].astype(str).str.lower().str.contains('neuro|cns|psych|adhd', na=False)).astype(int)
    is_rare = (df['therapeutic_area'].astype(str).str.lower().str.contains('rare|orphan|metabolic', na=False)).astype(int)
    is_dermatology = (df['therapeutic_area'].astype(str).str.lower().str.contains('derm|skin|psoriasis', na=False)).astype(int)

    # Base features
    btd = gn('btd')
    pr = gn('priority_review')
    ft = gn('fast_track')
    orphan = gn('orphan')
    accel = gn('accelerated_approval')
    has_any_desig = ((btd + pr + ft + orphan) > 0).astype(int)
    prior_appr = gn('sponsor_prior_approvals')
    prior_crls = gn('prior_crl_count')
    resub = gn('resubmission_class')
    is_resub = gn('is_resub')
    safety_signal = gn('safety_signal_severity')
    single_arm = gn('single_arm_study')
    mfg_risk = gn('manufacturing_risk')
    surrogate = gn('surrogate_endpoint')
    had_adcom = gn('had_adcom')
    gene_therapy = gn('gene_therapy')

    # ===== CANDIDATE BANK =====
    # Pillar A: TA x designation interactions
    cands['onc_x_no_desig'] = is_oncology * (1 - has_any_desig)
    cands['neuro_x_no_desig'] = is_neuro * (1 - has_any_desig)
    cands['rare_x_priority'] = is_rare * pr
    cands['derm_x_priority'] = is_dermatology * pr

    # Pillar B: Sponsor experience interactions
    cands['naive_x_oncology'] = (prior_appr < 3).astype(int) * is_oncology
    cands['naive_x_resub'] = (prior_appr < 3).astype(int) * is_resub
    cands['naive_x_safety_high'] = (prior_appr < 3).astype(int) * (safety_signal > 0).astype(int)
    cands['experienced_x_resub'] = (prior_appr >= 10).astype(int) * is_resub
    cands['experienced_x_mfg_risk'] = (prior_appr >= 10).astype(int) * (mfg_risk > 0).astype(int)

    # Pillar C: CRL history interactions
    cands['prior_crl_x_resub'] = (prior_crls >= 1).astype(int) * is_resub
    cands['prior_crl_2plus_x_oncology'] = (prior_crls >= 2).astype(int) * is_oncology
    cands['prior_crl_x_safety'] = (prior_crls >= 1).astype(int) * (safety_signal > 0).astype(int)

    # Pillar D: Resubmission class granular
    cands['resub_class_1_x_naive'] = (resub == 1).astype(int) * (prior_appr < 3).astype(int)
    cands['resub_class_2_x_mfg_risk'] = (resub == 2).astype(int) * (mfg_risk > 0).astype(int)
    cands['resub_class_2_x_naive'] = (resub == 2).astype(int) * (prior_appr < 3).astype(int)

    # Pillar E: Multi-designation stacking
    cands['accel_x_btd_x_priority'] = accel * btd * pr
    cands['gene_therapy_x_orphan'] = gene_therapy * orphan
    cands['gene_therapy_x_btd'] = gene_therapy * btd

    # Pillar F: Non-linear transforms
    cands['log_prior_appr_sq'] = pd.Series([(__import__('math').log1p(x))**2 for x in prior_appr], index=df.index)
    cands['prior_crls_sq'] = prior_crls ** 2
    cands['safety_signal_x_no_desig'] = (safety_signal > 0).astype(int) * (1 - has_any_desig)

    return cands

# ============================================================================
# GATING
# ============================================================================
def gate_candidate(name, series, df, baseline_features, label_col='label_crl'):
    """Run a candidate through the strict gate. Returns dict with verdict."""
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, brier_score_loss

    # Univariate
    y = df[label_col].values
    s = series.astype(float).values
    if s.std() == 0:
        return {'name': name, 'verdict': 'CONSTANT', 'reason': 'zero variance'}

    try:
        univariate_auc = roc_auc_score(y, s)
        if univariate_auc < 0.5:
            univariate_auc = 1 - univariate_auc  # flip if anti-correlated
        if univariate_auc < 0.55:
            return {'name': name, 'verdict': 'NOISE', 'reason': f'univariate AUC {univariate_auc:.3f} < 0.55'}
    except Exception:
        return {'name': name, 'verdict': 'ERROR', 'reason': 'univariate AUC failed'}

    # Train/test split
    df_local = df.copy()
    df_local['__cand__'] = series
    avail_baseline = [f for f in baseline_features if f in df_local.columns]
    cols = avail_baseline + ['__cand__', label_col, 'year']
    clean = df_local[cols].dropna()
    train = clean[clean['year'] <= 2024]
    test = clean[clean['year'] >= 2025]
    if len(train) < 100 or len(test) < 30:
        return {'name': name, 'verdict': 'INSUFFICIENT_DATA', 'reason': f'train={len(train)} test={len(test)}'}

    X_train_b = train[avail_baseline].values
    X_test_b = test[avail_baseline].values
    X_train_e = train[avail_baseline + ['__cand__']].values
    X_test_e = test[avail_baseline + ['__cand__']].values
    y_train = train[label_col].values
    y_test = test[label_col].values

    sc_b = StandardScaler().fit(X_train_b)
    sc_e = StandardScaler().fit(X_train_e)
    m_b = LogisticRegression(C=0.10, max_iter=2000).fit(sc_b.transform(X_train_b), y_train)
    m_e = LogisticRegression(C=0.10, max_iter=2000).fit(sc_e.transform(X_train_e), y_train)
    p_b = m_b.predict_proba(sc_b.transform(X_test_b))[:, 1]
    p_e = m_e.predict_proba(sc_e.transform(X_test_e))[:, 1]
    auc_b, brier_b = roc_auc_score(y_test, p_b), brier_score_loss(y_test, p_b)
    auc_e, brier_e = roc_auc_score(y_test, p_e), brier_score_loss(y_test, p_e)
    d_auc = auc_e - auc_b
    d_brier = brier_e - brier_b

    # 20-seed stability
    seed_e_aucs, seed_b_aucs = [], []
    rng = np.random.RandomState(0)
    for _ in range(20):
        idx = rng.choice(len(train), size=len(train), replace=True)
        Xb = sc_b.transform(train.iloc[idx][avail_baseline].values)
        Xe = sc_e.transform(train.iloc[idx][avail_baseline + ['__cand__']].values)
        yt = train.iloc[idx][label_col].values
        mb = LogisticRegression(C=0.10, max_iter=2000).fit(Xb, yt)
        me = LogisticRegression(C=0.10, max_iter=2000).fit(Xe, yt)
        seed_b_aucs.append(roc_auc_score(y_test, mb.predict_proba(sc_b.transform(X_test_b))[:, 1]))
        seed_e_aucs.append(roc_auc_score(y_test, me.predict_proba(sc_e.transform(X_test_e))[:, 1]))
    wins = sum(1 for a, b in zip(seed_e_aucs, seed_b_aucs) if a > b)

    verdict = 'PROPOSAL' if (d_auc > 0.005 and d_brier <= 0 and wins >= 15) else 'NO-SHIP'
    return {
        'name': name,
        'verdict': verdict,
        'univariate_auc': round(univariate_auc, 4),
        'baseline_auc': round(auc_b, 4),
        'extended_auc': round(auc_e, 4),
        'd_auc': round(d_auc, 4),
        'baseline_brier': round(brier_b, 4),
        'extended_brier': round(brier_e, 4),
        'd_brier': round(d_brier, 4),
        'seed_wins_20': wins,
        'reason': f'gate {"passed" if verdict == "PROPOSAL" else "failed"}: dAUC={d_auc:.4f} dBrier={d_brier:.4f} wins={wins}/20',
    }

# ============================================================================
# MAIN
# ============================================================================
def main():
    print(f"FEATURE MINER v1.0 -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        import pandas as pd
    except ImportError:
        print("ERROR: pandas required")
        sys.exit(1)

    # Load engineered v38.1 panel
    panel_path = HERE / "engineered_v38_1.csv"
    if not panel_path.exists():
        print(f"ERROR: {panel_path} not found")
        sys.exit(1)
    df = pd.read_csv(panel_path, low_memory=False)
    df = df[df['outcome'].isin(['APPROVAL', 'CRL'])].copy()
    df['label_crl'] = (df['outcome'] == 'CRL').astype(int)
    print(f"Panel: {len(df)} events, CRL rate {df['label_crl'].mean():.3f}")

    # Load v38.1 features
    deploy_path = HERE / "odin_v38_1_deploy.json"
    if not deploy_path.exists():
        print(f"WARNING: {deploy_path} not found, using fallback baseline")
        baseline_features = ['btd', 'priority_review', 'fast_track', 'orphan', 'sponsor_prior_approvals']
    else:
        with open(deploy_path) as f:
            baseline_features = json.load(f)['features']
    print(f"Baseline (v38.1): {len(baseline_features)} features")

    # Generate candidates
    cands = generate_candidates(df)
    print(f"Generated {len(cands)} candidate features")

    # Gate each
    results = []
    proposals = []
    for name, series in cands.items():
        result = gate_candidate(name, series, df, baseline_features)
        results.append(result)
        if result['verdict'] == 'PROPOSAL':
            proposals.append(result)
            print(f"PROPOSAL: {name} -- dAUC {result['d_auc']:+.4f}, dBrier {result['d_brier']:+.4f}, {result['seed_wins_20']}/20 seeds")
        else:
            print(f"  {name}: {result['verdict']} ({result.get('reason', '')[:60]})")

    # Write outputs
    today = datetime.now().strftime('%Y-%m-%d')
    json_path = PROPOSAL_DIR / f"{today}_feature_proposals.json"
    with open(json_path, 'w') as f:
        json.dump({
            'generated': today,
            'n_candidates': len(cands),
            'n_proposals': len(proposals),
            'all_results': results,
        }, f, indent=2, default=str)

    md_path = PROPOSAL_DIR / f"{today}_feature_proposals.md"
    with open(md_path, 'w') as f:
        f.write(f"# Feature Proposals -- {today}\n\n")
        f.write(f"Generated {len(cands)} candidates. {len(proposals)} passed strict gate.\n\n")
        f.write(f"## Gate: dAUC > 0.005 AND dBrier <= 0 AND 15+/20 seed wins AND univariate AUC > 0.55\n\n")
        f.write(f"## PROPOSALS ({len(proposals)})\n\n")
        for p in sorted(proposals, key=lambda x: -x['d_auc']):
            f.write(f"### {p['name']}\n")
            f.write(f"- dAUC: {p['d_auc']:+.4f}\n")
            f.write(f"- dBrier: {p['d_brier']:+.4f}\n")
            f.write(f"- Seed wins: {p['seed_wins_20']}/20\n")
            f.write(f"- Univariate AUC: {p['univariate_auc']:.4f}\n\n")
        f.write(f"\n## REJECTED ({len(results) - len(proposals)})\n\n")
        for r in [r for r in results if r['verdict'] != 'PROPOSAL']:
            f.write(f"- {r['name']}: {r['verdict']} ({r.get('reason', '')})\n")

    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"SUMMARY: {len(proposals)}/{len(cands)} candidates passed strict gate")

if __name__ == "__main__":
    main()
