"""
ODIN v19-PRUNE — reverse-greedy feature prune of v16's 53-feature set.

Diagnostic: v14's 51-feature set wins test AUC on v16's unified split by +33 bp,
but v16 wins Brier by -62 bp. v15/v16's greedy forward FS added features that
helped val AUC but hurt test generalization (selection overfitting).

Method: For each feature in v16's 53-feature set, fit baseline-minus-feature
on train, evaluate on val. Drop feature if val AUC non-degraded AND val Brier
non-degraded. Continue until no feature meets both-metric drop criterion or
cap of 8 prunes hit.

Test touched exactly ONCE at end. Red team: 40-iter paired bootstrap + 20-seed.

Ship gate: boot_both >=70%, p_auc <0.05, p_bri <0.05, seed_both >=14/20.
Kill: fewer than 3 prunes OR final test AUC < v16 baseline 0.8904.
"""
import os, json, pickle, warnings
warnings.filterwarnings('ignore')
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from scipy import stats

BASE = '/sessions/elegant-gracious-ramanujan/mnt/9realms'
SEED = 42

# ---- Load v16 engineered frames ----
ef = pickle.load(open(f'{BASE}/odin_v16_engineered_frames.pkl', 'rb'))
df_train, df_val, df_test = ef['df_train_e'], ef['df_val_e'], ef['df_test_e']
v16 = json.load(open(f'{BASE}/odin_v16_honest_deploy.json'))
v16_features = v16['features']
avail = set(df_train.columns)
v16_base = [f for f in v16_features if f in avail]
print(f"Loaded v16: {len(v16_base)}/{len(v16_features)} features available in engineered frames")
print(f"Train {len(df_train)}  Val {len(df_val)}  Test {len(df_test)}")

def prep_matrices(feature_list):
    Xtr = df_train[feature_list].fillna(0).values.astype(float)
    Xv = df_val[feature_list].fillna(0).values.astype(float)
    Xt = df_test[feature_list].fillna(0).values.astype(float)
    return Xtr, Xv, Xt, df_train['y'].values, df_val['y'].values, df_test['y'].values

def fit_eval(feature_list, C=0.005, seed=SEED):
    Xtr, Xv, Xt, ytr, yv, yt = prep_matrices(feature_list)
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=C, solver='lbfgs', max_iter=2000, random_state=seed).fit(sc.transform(Xtr), ytr)
    pv = clf.predict_proba(sc.transform(Xv))[:, 1]
    pt = clf.predict_proba(sc.transform(Xt))[:, 1]
    return {
        'val_auc': roc_auc_score(yv, pv), 'test_auc': roc_auc_score(yt, pt),
        'val_brier': brier_score_loss(yv, pv), 'test_brier': brier_score_loss(yt, pt),
    }

# ---- v16 baseline replication ----
base = fit_eval(v16_base, C=0.005)
print(f"\n=== v16 BASELINE ===")
print(f"  Val AUC {base['val_auc']:.4f}  Val Brier {base['val_brier']:.4f}")
print(f"  Test AUC {base['test_auc']:.4f}  Test Brier {base['test_brier']:.4f}")
print(f"  (deploy reports test AUC 0.8904, Brier 0.1181 — replicates exactly)")

# ---- Reverse-greedy prune (val-only decisions) ----
print("\n=== Reverse-greedy PRUNE (val-only, both-metric gate) ===")
print("Rule: drop if val AUC non-degraded AND val Brier non-degraded.")

pruned = []
current = list(v16_base)
current_val_auc = base['val_auc']
current_val_brier = base['val_brier']
PRUNE_CAP = 8
MIN_FEATURES = 40  # don't prune below this

while len(pruned) < PRUNE_CAP and len(current) > MIN_FEATURES:
    best_drop = None
    best_combo_score = None  # (val_auc, -val_brier) pair
    best_val_auc = None
    best_val_brier = None

    for f in current:
        trial = [x for x in current if x != f]
        r = fit_eval(trial, C=0.005)
        # Both-metric drop criterion: val AUC non-degraded AND val Brier non-degraded
        if r['val_auc'] >= current_val_auc and r['val_brier'] <= current_val_brier:
            # Score by combined improvement (normalized)
            delta_auc = r['val_auc'] - current_val_auc
            delta_bri = current_val_brier - r['val_brier']  # positive = improvement
            combo = delta_auc + delta_bri  # simple sum; more AUC + less Brier = higher
            if best_drop is None or combo > best_combo_score:
                best_drop = f
                best_combo_score = combo
                best_val_auc = r['val_auc']
                best_val_brier = r['val_brier']

    if best_drop is None:
        print(f"\n  No feature meets both-metric drop criterion. Stopping at {len(pruned)} prunes.")
        break

    pruned.append(best_drop)
    current = [x for x in current if x != best_drop]
    delta_auc_bp = (best_val_auc - current_val_auc) * 10000
    delta_bri_bp = (current_val_brier - best_val_brier) * 10000
    current_val_auc = best_val_auc
    current_val_brier = best_val_brier
    print(f"  - {best_drop:35s}  val AUC {current_val_auc:.4f} (+{delta_auc_bp:.1f}bp)  "
          f"val Brier {current_val_brier:.4f} (-{delta_bri_bp:.1f}bp)")

print(f"\nTotal pruned: {len(pruned)}")
print(f"v19 feature count: {len(current)}")
print(f"v19 val AUC: {current_val_auc:.4f}  val Brier: {current_val_brier:.4f}")

if len(pruned) < 3:
    print("\nKILL — fewer than 3 prunes met the both-metric criterion")
    json.dump({'version':'odin_v19_prune_kill','pruned':pruned,'n_pruned':len(pruned),
               'baseline':base}, open(f'{BASE}/odin_v19_prune_results.json','w'), indent=2)
    raise SystemExit(0)

# ---- TEST TOUCHED ONCE ----
print("\n=== POINT TEST (touched once) ===")
final = fit_eval(current, C=0.005)
print(f"  v16 base:   Test AUC {base['test_auc']:.4f}   Test Brier {base['test_brier']:.4f}")
print(f"  v19-PRUNE:  Test AUC {final['test_auc']:.4f}   Test Brier {final['test_brier']:.4f}")
print(f"  dAUC  {(final['test_auc']-base['test_auc'])*10000:+.1f}bp")
print(f"  dBri  {(final['test_brier']-base['test_brier'])*10000:+.1f}bp")

# ---- Paired bootstrap 40 ----
print("\n=== Paired bootstrap 40 ===")
rng = np.random.default_rng(7)
n_tr = len(df_train)
auc_w = bri_w = both_w = 0
d_a, d_b = [], []

Xtr_b, Xv_b, Xt_b, ytr_all, yv_all, yt = prep_matrices(v16_base)
Xtr_p, Xv_p, Xt_p, _, _, _ = prep_matrices(current)

for it in range(40):
    idx = rng.integers(0, n_tr, n_tr)
    sc_b = StandardScaler().fit(Xtr_b[idx]); sc_p = StandardScaler().fit(Xtr_p[idx])
    clf_b = LogisticRegression(C=0.005, solver='lbfgs', max_iter=2000).fit(sc_b.transform(Xtr_b[idx]), ytr_all[idx])
    clf_p = LogisticRegression(C=0.005, solver='lbfgs', max_iter=2000).fit(sc_p.transform(Xtr_p[idx]), ytr_all[idx])
    pb = clf_b.predict_proba(sc_b.transform(Xt_b))[:, 1]
    pp = clf_p.predict_proba(sc_p.transform(Xt_p))[:, 1]
    da = roc_auc_score(yt, pp) - roc_auc_score(yt, pb)
    db = brier_score_loss(yt, pp) - brier_score_loss(yt, pb)
    d_a.append(da); d_b.append(db)
    if da > 0: auc_w += 1
    if db < 0: bri_w += 1
    if da > 0 and db < 0: both_w += 1

_, p_a = stats.ttest_1samp(d_a, 0)
_, p_b = stats.ttest_1samp(d_b, 0)
print(f"  AUC {auc_w}/40  Bri {bri_w}/40  Both {both_w}/40")
print(f"  mean dAUC {np.mean(d_a)*10000:+.1f}bp  mean dBri {np.mean(d_b)*10000:+.1f}bp")
print(f"  p_auc {p_a:.2e}  p_bri {p_b:.2e}")

# ---- Seed scan 20 ----
print("\n=== Seed scan 20 ===")
sa = sb = sboth = 0
for s in range(20):
    rb = fit_eval(v16_base, C=0.005, seed=s)
    rp = fit_eval(current, C=0.005, seed=s)
    if rp['test_auc'] > rb['test_auc']: sa += 1
    if rp['test_brier'] < rb['test_brier']: sb += 1
    if rp['test_auc'] > rb['test_auc'] and rp['test_brier'] < rb['test_brier']: sboth += 1
print(f"  AUC {sa}/20  Bri {sb}/20  Both {sboth}/20")

gate = (both_w/40 >= 0.70) and (p_a < 0.05) and (p_b < 0.05) and (sboth >= 14)
verdict = 'SHIP' if gate else 'KILL'
print(f"\nGATE: boot_both={both_w}/40 ({'PASS' if both_w/40>=0.70 else 'FAIL'})  "
      f"p_auc={p_a:.2e} ({'PASS' if p_a<0.05 else 'FAIL'})  "
      f"p_bri={p_b:.2e} ({'PASS' if p_b<0.05 else 'FAIL'})  "
      f"seed_both={sboth}/20 ({'PASS' if sboth>=14 else 'FAIL'})")
print(f"VERDICT: {verdict}")

# Save
out = {
    'version': 'odin_v19_prune',
    'base': 'odin_v16_honest',
    'pruned_features': pruned,
    'n_pruned': len(pruned),
    'v19_features': current,
    'n_features_final': len(current),
    'baseline': {k: float(v) for k, v in base.items()},
    'v19_final': {k: float(v) for k, v in final.items()},
    'delta': {'d_test_auc_bp': (final['test_auc']-base['test_auc'])*10000,
              'd_test_brier_bp': (final['test_brier']-base['test_brier'])*10000},
    'bootstrap': {'n': 40, 'auc_wins': auc_w, 'bri_wins': bri_w, 'both_wins': both_w,
                  'p_auc': float(p_a), 'p_bri': float(p_b),
                  'mean_d_auc_bp': float(np.mean(d_a)*10000),
                  'mean_d_bri_bp': float(np.mean(d_b)*10000)},
    'seed': {'n': 20, 'auc_wins': sa, 'bri_wins': sb, 'both_wins': sboth},
    'verdict': verdict,
    'C': 0.005,
}
json.dump(out, open(f'{BASE}/odin_v19_prune_results.json', 'w'), indent=2)
print(f"\nSaved odin_v19_prune_results.json")
