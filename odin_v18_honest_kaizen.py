"""
ODIN v18 HONEST KAIZEN — v16 base + FDA-recall CMC signal family

Baseline: v16_honest (test AUC 0.8904, Brier 0.1181, 53 features, C=0.005).
Candidates tested on v16's train/val/test honest 3-way split (1081/764/365):

  L1_cmc_class3_count_log   — log(1 + class-III recalls for sponsor T-1)
  L2_cmc_class2_count_log   — log(1 + class-II recalls)
  L3_cmc_cgmp_flag          — any prior cGMP/manufacturing-cited recall (binary)
  L4_cmc_class3_x_naive     — class3 × sponsor_naive (v22b interaction pattern)
  L5_cmc_cgmp_x_mfg_risk    — cgmp flag × existing mfg_risk_bin
  L6_cmc_class3_x_onc       — class3 × is_oncology

Gate: greedy forward val-AUC selection, Δval ≥ 5 bp per added feature.
Red team: 40-iter paired bootstrap + 20-seed scan. Ship requires
  boot_both ≥ 70% AND p_auc < 0.05 AND p_bri < 0.05 AND seed_both ≥ 14/20.

Data: fda_recalls_cache.json (from Odin Perfection — same v22b cache,
636 sponsors, 17,583 recalls). Temporal snapshot: for each event,
count only recalls with `recall_initiation_date < catalyst_date`.
"""
import os, re, json, pickle, warnings
warnings.filterwarnings('ignore')
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from scipy import stats

BASE = '/sessions/elegant-gracious-ramanujan/mnt/9realms'
RECALL_CACHE = '/sessions/elegant-gracious-ramanujan/mnt/Odin Perfection/fda_recalls_cache.json'
SEED = 42

# ---- Load v16 engineered frames (from odin_v16_engineer_only.py output) ----
with open(f'{BASE}/odin_v16_engineered_frames.pkl', 'rb') as f:
    ef = pickle.load(f)
df_train_e, df_val_e, df_test_e = ef['df_train_e'], ef['df_val_e'], ef['df_test_e']
v14_features = ef['v14_features']
v16_selected = v14_features.copy()
# v16's full selected features comes from v16_honest_deploy.json
v16_deploy = json.load(open(f'{BASE}/odin_v16_honest_deploy.json'))
v16_features = v16_deploy['features']  # 53 ordered features
# In our v16 rebuild output, v16_features may reference features named slightly
# differently from what engineer() produced — cross-check
avail = set(df_train_e.columns)
present_v16 = [f for f in v16_features if f in avail]
missing_v16 = [f for f in v16_features if f not in avail]
print(f"v16 deploy features: {len(v16_features)}, present in engineered frames: {len(present_v16)}, missing: {len(missing_v16)}")
if missing_v16:
    print(f"  MISSING: {missing_v16}")
    # Fall back to v14 baseline if we can't reproduce v16 fully
    v16_base = v14_features
else:
    v16_base = present_v16

print(f"Baseline feature set: {len(v16_base)} features")
print(f"Train {len(df_train_e)}  Val {len(df_val_e)}  Test {len(df_test_e)}")

# ---- Build CMC features from recall cache ----
print("\nBuilding CMC T-1 features from recall cache...")
cache = json.load(open(RECALL_CACHE))
cgmp_re = re.compile(r'(?i)\b(cGMP|GMP|manufactur|CMC)\b')


def recall_stats_for_event(company, catalyst_date):
    recs = cache.get(company, [])
    if not recs:
        # fuzzy: substring match
        comp_lc = (company or '').lower()
        for k in cache.keys():
            if k and comp_lc in k.lower():
                recs = cache[k]
                break
    if not recs:
        return {'n': 0, 'n_class1': 0, 'n_class2': 0, 'n_class3': 0, 'cgmp_hits': 0}
    prior = []
    for r in recs:
        d = r.get('recall_initiation_date') or r.get('center_classification_date') or r.get('report_date')
        if not d:
            continue
        try:
            rd = datetime.strptime(str(d)[:8], '%Y%m%d')
        except Exception:
            continue
        if rd < catalyst_date:
            prior.append(r)
    return {
        'n': len(prior),
        'n_class1': sum(1 for p in prior if (p.get('classification') or '').strip() == 'Class I'),
        'n_class2': sum(1 for p in prior if (p.get('classification') or '').strip() == 'Class II'),
        'n_class3': sum(1 for p in prior if (p.get('classification') or '').strip() == 'Class III'),
        'cgmp_hits': sum(1 for p in prior if cgmp_re.search(str(p.get('reason_for_recall', '')))),
    }


def add_cmc_features(df):
    out = df.copy()
    cmc_class3, cmc_class2, cmc_cgmp = [], [], []
    for _, row in df.iterrows():
        co = str(row.get('company', '')).strip()
        cd = row.get('catalyst_date')
        if pd.isna(cd):
            cd = datetime(2020, 1, 1)
        elif isinstance(cd, pd.Timestamp):
            cd = cd.to_pydatetime()
        st = recall_stats_for_event(co, cd)
        cmc_class3.append(float(np.log1p(st['n_class3'])))
        cmc_class2.append(float(np.log1p(st['n_class2'])))
        cmc_cgmp.append(1.0 if st['cgmp_hits'] > 0 else 0.0)
    out['cmc_class3_count_log'] = cmc_class3
    out['cmc_class2_count_log'] = cmc_class2
    out['cmc_cgmp_flag'] = cmc_cgmp
    # interactions
    if 'sponsor_naive' not in out.columns:
        # derive from sponsor_prior_approvals or existing features
        spa = df.get('sponsor_prior_approvals', pd.Series([5]*len(df)))
        out['_spa_naive'] = (spa == 0).astype(float)
    else:
        out['_spa_naive'] = out['sponsor_naive'].astype(float)
    out['cmc_class3_x_naive'] = out['cmc_class3_count_log'] * out['_spa_naive']
    out['cmc_cgmp_x_mfg_risk'] = out['cmc_cgmp_flag'] * out.get('mfg_risk_bin', 0).astype(float)
    out['cmc_class3_x_onc'] = out['cmc_class3_count_log'] * out.get('is_oncology', 0).astype(float)
    return out


df_train_e = add_cmc_features(df_train_e)
df_val_e = add_cmc_features(df_val_e)
df_test_e = add_cmc_features(df_test_e)

candidate_cmc = [
    'cmc_class3_count_log', 'cmc_class2_count_log', 'cmc_cgmp_flag',
    'cmc_class3_x_naive', 'cmc_cgmp_x_mfg_risk', 'cmc_class3_x_onc',
]

# Coverage stats
for c in candidate_cmc:
    nz = int((df_train_e[c] != 0).sum())
    print(f"  train MIN_NZ {c:30s}: {nz}/{len(df_train_e)}")

# ---- Eval harness ----
def prep_matrices(feature_list):
    Xtr = df_train_e[feature_list].fillna(0).values.astype(float)
    Xv = df_val_e[feature_list].fillna(0).values.astype(float)
    Xt = df_test_e[feature_list].fillna(0).values.astype(float)
    ytr = df_train_e['y'].values
    yv = df_val_e['y'].values
    yt = df_test_e['y'].values
    return Xtr, Xv, Xt, ytr, yv, yt

def fit_eval(feature_list, C=0.005, seed=SEED):
    Xtr, Xv, Xt, ytr, yv, yt = prep_matrices(feature_list)
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=C, solver='lbfgs', max_iter=2000, random_state=seed).fit(sc.transform(Xtr), ytr)
    pv = clf.predict_proba(sc.transform(Xv))[:, 1]
    pt = clf.predict_proba(sc.transform(Xt))[:, 1]
    return {'val_auc': roc_auc_score(yv, pv), 'test_auc': roc_auc_score(yt, pt),
            'test_brier': brier_score_loss(yt, pt), 'clf': clf, 'scaler': sc, 'pv': pv, 'pt': pt}

# ---- Baseline ----
print("\n=== v16 baseline replication ===")
base_res = fit_eval(v16_base, C=0.005)
print(f"  val AUC {base_res['val_auc']:.4f}  test AUC {base_res['test_auc']:.4f}  Brier {base_res['test_brier']:.4f}")
print(f"  (v16 deploy reported test AUC 0.8904, Brier 0.1181 — if close, replication is valid)")

# ---- Single-feature val screen ----
print("\n=== Single-feature val-AUC screen (no FS on test) ===")
screen = {}
for c in candidate_cmc:
    r = fit_eval(v16_base + [c], C=0.005)
    delta_val = (r['val_auc'] - base_res['val_auc']) * 10000
    delta_te = (r['test_auc'] - base_res['test_auc']) * 10000
    delta_br = (r['test_brier'] - base_res['test_brier']) * 10000
    mark = '##' if delta_val > 5 and delta_br < 0 else ('+ ' if delta_val > 5 else '  ')
    screen[c] = {'val_auc': float(r['val_auc']), 'test_auc': float(r['test_auc']),
                 'test_brier': float(r['test_brier']), 'delta_val_bp': delta_val,
                 'delta_test_bp': delta_te, 'delta_brier_bp': delta_br}
    print(f"  {mark} {c:30s}  val {r['val_auc']:.4f} (Δ{delta_val:+6.1f}bp)  test {r['test_auc']:.4f} (Δ{delta_te:+6.1f}bp)  bri {r['test_brier']:.4f} (Δ{delta_br:+6.1f}bp)")

# ---- Greedy FS on val only ----
print("\n=== Greedy forward val-FS (Δval ≥ 5bp gate) ===")
selected_new = []
current = list(v16_base)
current_val = base_res['val_auc']
remaining = list(candidate_cmc)
while remaining:
    best_gain = 0.0005; best = None; best_val = current_val
    for c in remaining:
        r = fit_eval(current + [c], C=0.005)
        if r['val_auc'] - current_val > best_gain:
            best_gain = r['val_auc'] - current_val; best = c; best_val = r['val_auc']
    if not best:
        break
    current.append(best); selected_new.append(best); current_val = best_val
    remaining.remove(best)
    print(f"  + {best:30s}  val→{current_val:.4f}  gain +{best_gain*10000:.1f}bp")

print(f"\nSelected new features: {selected_new}")

if not selected_new:
    print("NO FS PASS — v18 KILL at FS stage (no CMC feature beats Δ=5bp val gate)")
    json.dump({'version': 'odin_v18_kill_fs', 'selected': [], 'single_feature_screen': screen,
               'baseline_test_auc': base_res['test_auc'], 'baseline_test_brier': base_res['test_brier']},
              open(f'{BASE}/odin_v18_honest_results.json', 'w'), indent=2)
    raise SystemExit(0)

# ---- Test red team ----
plus_res = fit_eval(v16_base + selected_new, C=0.005)
print(f"\n=== POINT TEST ===")
print(f"  v16 base:       AUC {base_res['test_auc']:.4f}  Brier {base_res['test_brier']:.4f}")
print(f"  +CMC{len(selected_new)}:     AUC {plus_res['test_auc']:.4f}  Brier {plus_res['test_brier']:.4f}")
print(f"  dAUC {(plus_res['test_auc']-base_res['test_auc'])*10000:+.1f}bp  dBri {(plus_res['test_brier']-base_res['test_brier'])*10000:+.1f}bp")

# Paired bootstrap 40
print("\n=== Paired bootstrap 40 iters ===")
rng = np.random.default_rng(7)
n_tr = len(df_train_e)
auc_w = bri_w = both_w = 0
d_a, d_b = [], []
for it in range(40):
    idx = rng.integers(0, n_tr, n_tr)
    Xtr_base, _, Xt_base, ytr_all, _, yt = prep_matrices(v16_base)
    Xtr_plus, _, Xt_plus, _, _, _ = prep_matrices(v16_base + selected_new)
    sc_b = StandardScaler().fit(Xtr_base[idx]); sc_p = StandardScaler().fit(Xtr_plus[idx])
    clf_b = LogisticRegression(C=0.005, solver='lbfgs', max_iter=2000).fit(sc_b.transform(Xtr_base[idx]), ytr_all[idx])
    clf_p = LogisticRegression(C=0.005, solver='lbfgs', max_iter=2000).fit(sc_p.transform(Xtr_plus[idx]), ytr_all[idx])
    pb = clf_b.predict_proba(sc_b.transform(Xt_base))[:, 1]
    pp = clf_p.predict_proba(sc_p.transform(Xt_plus))[:, 1]
    da = roc_auc_score(yt, pp) - roc_auc_score(yt, pb)
    db = brier_score_loss(yt, pp) - brier_score_loss(yt, pb)
    d_a.append(da); d_b.append(db)
    if da > 0: auc_w += 1
    if db < 0: bri_w += 1
    if da > 0 and db < 0: both_w += 1
_, p_a = stats.ttest_1samp(d_a, 0); _, p_b = stats.ttest_1samp(d_b, 0)
print(f"  AUC {auc_w}/40  Bri {bri_w}/40  Both {both_w}/40  p_auc {p_a:.2e}  p_bri {p_b:.2e}  mean dAUC {np.mean(d_a)*10000:+.1f}bp dBri {np.mean(d_b)*10000:+.1f}bp")

# Seed 20 (vary train random_state)
sa = sb = sboth = 0
for s in range(20):
    r_b = fit_eval(v16_base, C=0.005, seed=s)
    r_p = fit_eval(v16_base + selected_new, C=0.005, seed=s)
    if r_p['test_auc'] > r_b['test_auc']: sa += 1
    if r_p['test_brier'] < r_b['test_brier']: sb += 1
    if r_p['test_auc'] > r_b['test_auc'] and r_p['test_brier'] < r_b['test_brier']: sboth += 1
print(f"\n=== Seed scan 20 ===")
print(f"  AUC {sa}/20  Bri {sb}/20  Both {sboth}/20")

gate = (both_w/40 >= 0.70) and (p_a < 0.05) and (p_b < 0.05)
verdict = 'SHIP' if (gate and sboth >= 14) else 'KILL'
print(f"\nGate: boot_both={both_w}/40 ({'PASS' if both_w/40>=0.70 else 'FAIL'}), "
      f"p_auc {p_a:.2e} ({'PASS' if p_a<0.05 else 'FAIL'}), "
      f"p_bri {p_b:.2e} ({'PASS' if p_b<0.05 else 'FAIL'}), "
      f"seed_both={sboth}/20 ({'PASS' if sboth>=14 else 'FAIL'})")
print(f"VERDICT: {verdict}")

# Save
out = {
    'version': 'odin_v18_honest',
    'base': 'odin_v16_honest',
    'selected_new_features': selected_new,
    'baseline': {'val_auc': float(base_res['val_auc']), 'test_auc': float(base_res['test_auc']),
                 'test_brier': float(base_res['test_brier'])},
    'plus': {'val_auc': float(plus_res['val_auc']), 'test_auc': float(plus_res['test_auc']),
             'test_brier': float(plus_res['test_brier'])},
    'delta': {'test_auc_bp': (plus_res['test_auc']-base_res['test_auc'])*10000,
              'test_brier_bp': (plus_res['test_brier']-base_res['test_brier'])*10000},
    'single_feature_screen': screen,
    'bootstrap': {'n': 40, 'auc_wins': auc_w, 'bri_wins': bri_w, 'both_wins': both_w,
                  'p_auc': float(p_a), 'p_bri': float(p_b),
                  'mean_d_auc_bp': float(np.mean(d_a)*10000), 'mean_d_bri_bp': float(np.mean(d_b)*10000)},
    'seed': {'n': 20, 'auc_wins': sa, 'bri_wins': sb, 'both_wins': sboth},
    'verdict': verdict,
}
json.dump(out, open(f'{BASE}/odin_v18_honest_results.json', 'w'), indent=2)
print(f"\nSaved odin_v18_honest_results.json")
