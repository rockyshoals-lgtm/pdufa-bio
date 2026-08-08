"""
Gungnir v52-TRIAL-QUALITY — Tier-1 CT.gov structural features on v51b HEIMDALL base.

Features tested (all from ctgov_t1_dataset.csv via nct_id merge):
  tq_num_primary_outcomes     — multiplicity risk (>= 2 co-primary = harder bar)
  tq_num_secondary_outcomes   — broad exploratory vs focused confirmatory
  tq_masking_rigor            — 0 open-label → 4+ rigorous double-blind + IDMC
  tq_ep_is_hard               — OS/MACE/death (hard endpoint)
  tq_ep_is_surrogate          — PFS/ORR (moderate)
  tq_ep_is_biomarker          — lab-only (noisy)
  tq_is_placebo_controlled    — placebo-controlled binary
  tq_has_active_comparator    — active comparator binary (higher bar)
  tq_has_dmc                  — IDMC present

Gate: greedy val-FS (Δval ≥ 5bp) on v51b 84-feature base.
Red team: 40-iter paired bootstrap + 20-seed stability. Both-metric gate.
"""
import os, json, types, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
import xgboost as xgb, lightgbm as lgb
from scipy import stats

ROOT = "/sessions/elegant-gracious-ramanujan/mnt/Odin Perfection"
BASE = "/sessions/elegant-gracious-ramanujan/mnt/9realms"

# Rebuild v51b base (same as v52 kaizens)
src = open(f'{ROOT}/gungnir_v49g_kaizen.py').read()
i = src.find('# ---------- build everything ----------')
builder_src = "import numpy as np\nimport pandas as pd\n" + src[src.find('# ---------- v47 base'):i]
mod = types.ModuleType('v49g_b'); exec(compile(builder_src, 'v49g_b', 'exec'), mod.__dict__)

df = pd.read_csv(f'{ROOT}/gungnir_readout_ctgov_enriched.csv')
df['date'] = pd.to_datetime(df['date']); df = df.sort_values('date').reset_index(drop=True)

X_v49d = pd.concat([mod.build_base_features(df), mod.build_v49b_features(df),
                    mod.build_v49c_features(df), mod.build_v49d_features(df)], axis=1)
V49G_SHIP = ['v49g_double_x_p3', 'v49g_narms_x_p3', 'v49g_has_placebo_real']
X_v49g = pd.concat([X_v49d, mod.build_v49g_candidates(df)[V49G_SHIP]], axis=1)

heim = pd.read_csv(f'{ROOT}/heimdall_v2_honest_scored_panel.csv', low_memory=False)
heim['catalyst_date'] = pd.to_datetime(heim['catalyst_date'])
h = heim[['ticker','catalyst_date','heimdall_p_v2','heimdall_tier_v2']].drop_duplicates(['ticker','catalyst_date']).rename(columns={'catalyst_date':'date','heimdall_p_v2':'heimdall_p','heimdall_tier_v2':'heimdall_tier'})
m = df[['ticker','date']].merge(h, on=['ticker','date'], how='left')
hp = m['heimdall_p'].fillna(float(h['heimdall_p'].median())).values
stage = df['stage'].fillna('').astype(str).str.lower()
p3 = stage.isin(['phase 3','phase3']).astype(float).values
micro = df['is_micro'].fillna(0).astype(float).values if 'is_micro' in df.columns else np.zeros(len(df))
tm={'BAD':-1.0,'BULL':0.5,'ROCKET':1.0,'NEUTRAL':0.0}
ht = m['heimdall_tier'].fillna('NEUTRAL').map(tm).fillna(0.0).values
X_heim = pd.DataFrame({'heimdall_p_v2':hp,'heimdall_p_v2_sq':hp**2,'heimdall_tier_v2_enc':ht,
                      'heimdall_p_v2_x_p3':hp*p3,'heimdall_p_v2_x_micro':hp*micro,
                      'heimdall_high_v2_flag':(hp>=0.6).astype(float)}, index=df.index)
X_v51b = pd.concat([X_v49g, X_heim], axis=1)
print(f"v51b base: {X_v51b.shape[1]} features on {len(df)} events")

# Merge CT.gov Tier-1 features
ct = pd.read_csv(f'{BASE}/ctgov_t1_dataset.csv', low_memory=False)
tq_src_cols = ['nct_id', 'num_primary_outcomes', 'num_secondary_outcomes',
               'masking_rigor', 'ep_is_hard', 'ep_is_surrogate', 'ep_is_biomarker',
               'is_placebo_controlled', 'has_active_comparator', 'has_dmc']
ct_slim = ct[tq_src_cols].drop_duplicates('nct_id')
print(f"CT.gov slim has {len(ct_slim)} unique nct_ids")

# Match on nct_id
if 'nct_id' not in df.columns:
    raise RuntimeError("Gungnir panel has no nct_id")
match = df[['nct_id']].merge(ct_slim, on='nct_id', how='left')
coverage = match.drop('nct_id', axis=1).notna().any(axis=1).sum()
print(f"Gungnir ↔ CT.gov nct_id match coverage: {coverage}/{len(df)} ({100*coverage/len(df):.1f}%)")

# Build candidate columns with tq_ prefix
X_tq = pd.DataFrame(index=df.index)
mapping = {
    'num_primary_outcomes': 'tq_n_primary',
    'num_secondary_outcomes': 'tq_n_secondary',
    'masking_rigor': 'tq_masking_rigor',
    'ep_is_hard': 'tq_ep_hard',
    'ep_is_surrogate': 'tq_ep_surrogate',
    'ep_is_biomarker': 'tq_ep_biomarker',
    'is_placebo_controlled': 'tq_placebo_ctrl',
    'has_active_comparator': 'tq_active_comp',
    'has_dmc': 'tq_has_dmc',
}
for src_c, dst_c in mapping.items():
    X_tq[dst_c] = pd.to_numeric(match[src_c], errors='coerce').fillna(0).astype(float).values

# Coverage / MIN_NZ
print("\nTier-1 feature MIN_NZ (train slice):")
tr_mask = (df['date'] <= pd.Timestamp('2023-12-31')).values
te_mask = (df['date'] >= pd.Timestamp('2025-01-01')).values
for c in X_tq.columns:
    nz_tr = int((X_tq.loc[tr_mask, c] != 0).sum())
    nz_te = int((X_tq.loc[te_mask, c] != 0).sum())
    print(f"  {c:22s}  train nz={nz_tr}/{tr_mask.sum()}  test nz={nz_te}/{te_mask.sum()}")

candidates = list(X_tq.columns)

# FS split — proper val window
y = df['is_positive_outcome'].astype(int).values
VAL = pd.Timestamp('2023-07-01')
tr_fs_tr = (df['date'] <= VAL).values
tr_fs_va = ((df['date'] > VAL) & (df['date'] <= pd.Timestamp('2023-12-31'))).values
print(f"\nFS split: train_fs {tr_fs_tr.sum()}  val_fs {tr_fs_va.sum()}")
print(f"Final test: {te_mask.sum()}")

# Ensemble config (same as v51b)
C_R=0.2; XGB=dict(n_estimators=600,learning_rate=0.02,max_depth=3,reg_alpha=0.2,subsample=0.8,colsample_bytree=0.8,eval_metric='auc',use_label_encoder=False,verbosity=0)
LG=dict(n_estimators=400,learning_rate=0.03,num_leaves=15,reg_alpha=0.1,subsample=0.8,colsample_bytree=0.8,verbose=-1)
W_R,W_X,W_L = 0.70, 0.15, 0.15

def fit(X, ys, xs=42, ls=42):
    sc = StandardScaler().fit(X)
    r = LogisticRegression(C=C_R, solver='lbfgs', max_iter=5000, penalty='l2').fit(sc.transform(X), ys)
    x = xgb.XGBClassifier(random_state=xs, **XGB).fit(X, ys)
    l = lgb.LGBMClassifier(random_state=ls, **LG).fit(X, ys)
    return sc, r, x, l
def scr(sc, r, x, l, X, ys):
    p = W_R*r.predict_proba(sc.transform(X))[:,1] + W_X*x.predict_proba(X)[:,1] + W_L*l.predict_proba(X)[:,1]
    return roc_auc_score(ys, p), brier_score_loss(ys, p)

Xb = X_v51b.values
sc_b0, r_b0, x_b0, l_b0 = fit(Xb[tr_fs_tr], y[tr_fs_tr])
va_auc, va_bri = scr(sc_b0, r_b0, x_b0, l_b0, Xb[tr_fs_va], y[tr_fs_va])
print(f"\nv51b baseline VAL: AUC {va_auc:.4f}  Brier {va_bri:.4f}")

# Single-feature val screen
print("\n=== Single-feature VAL screen ===")
screen = {}
for c in candidates:
    X_try = pd.concat([X_v51b, X_tq[[c]]], axis=1).values
    sc_, r_, x_, l_ = fit(X_try[tr_fs_tr], y[tr_fs_tr])
    a, b = scr(sc_, r_, x_, l_, X_try[tr_fs_va], y[tr_fs_va])
    screen[c] = {'val_auc': float(a), 'val_bri': float(b)}
    mark = '##' if a > va_auc and b < va_bri else '+ ' if a > va_auc else '  '
    print(f"  {mark} {c:22s}  val {a:.4f} (Δ{(a-va_auc)*10000:+6.1f}bp)  bri {b:.4f} (Δ{(b-va_bri)*10000:+6.1f}bp)")

# Greedy val-only FS (both-metric gate)
print("\n=== Greedy val-FS (both-metric gate Δval ≥ 3bp) ===")
selected = []
X_cur = X_v51b.copy()
cur_va_auc, cur_va_bri = va_auc, va_bri
remaining = list(candidates)
while remaining:
    best=None; best_gain=0.0003; best_bri=None; best_auc=None
    for c in remaining:
        X_try = pd.concat([X_cur, X_tq[[c]]], axis=1).values
        sc_, r_, x_, l_ = fit(X_try[tr_fs_tr], y[tr_fs_tr])
        a, b = scr(sc_, r_, x_, l_, X_try[tr_fs_va], y[tr_fs_va])
        if a > cur_va_auc and b < cur_va_bri:
            g = a - cur_va_auc
            if g > best_gain:
                best_gain=g; best=c; best_auc=a; best_bri=b
    if not best: break
    selected.append(best); X_cur = pd.concat([X_cur, X_tq[[best]]], axis=1)
    cur_va_auc=best_auc; cur_va_bri=best_bri; remaining.remove(best)
    print(f"  + {best}  val AUC {cur_va_auc:.4f}  val Bri {cur_va_bri:.4f}")

print(f"\nSelected: {selected}")

if not selected:
    print("KILL_FS — no candidate passes both-metric val gate")
    json.dump({'version':'v52_trial_quality','verdict':'KILL_FS','selected':[],
               'single_feature_screen':screen,
               'coverage':{'match':int(coverage),'total':len(df),'pct':100*coverage/len(df)}},
              open(f'{ROOT}/gungnir_v52_trial_quality_results.json','w'), indent=2)
    raise SystemExit(0)

# Test + red team
Xp = X_cur.values
ytr, yte = y[tr_mask], y[te_mask]
Xb_tr, Xb_te = Xb[tr_mask], Xb[te_mask]
Xp_tr, Xp_te = Xp[tr_mask], Xp[te_mask]

sc_b, r_b, x_b, l_b = fit(Xb_tr, ytr)
sc_p, r_p, x_p, l_p = fit(Xp_tr, ytr)
a_b, b_b = scr(sc_b, r_b, x_b, l_b, Xb_te, yte)
a_p, b_p = scr(sc_p, r_p, x_p, l_p, Xp_te, yte)
print(f"\n=== POINT TEST ===")
print(f"  v51b:     AUC {a_b:.4f}  Brier {b_b:.4f}")
print(f"  +TQ{len(selected)}:    AUC {a_p:.4f}  Brier {b_p:.4f}")
print(f"  dAUC {(a_p-a_b)*10000:+.1f}bp  dBri {(b_p-b_b)*10000:+.1f}bp")

# Bootstrap 40
rng = np.random.default_rng(7); n_tr = int(tr_mask.sum())
au=br=bo=0; d_a=[]; d_b=[]
for it in range(40):
    idx = rng.integers(0, n_tr, n_tr)
    sc_b2, r_b2, x_b2, l_b2 = fit(Xb_tr[idx], ytr[idx])
    sc_p2, r_p2, x_p2, l_p2 = fit(Xp_tr[idx], ytr[idx])
    aa, bb = scr(sc_b2, r_b2, x_b2, l_b2, Xb_te, yte)
    ap, bp = scr(sc_p2, r_p2, x_p2, l_p2, Xp_te, yte)
    d_a.append(ap-aa); d_b.append(bp-bb)
    if ap>aa: au+=1
    if bp<bb: br+=1
    if ap>aa and bp<bb: bo+=1
_,pa = stats.ttest_1samp(d_a,0); _,pb = stats.ttest_1samp(d_b,0)
print(f"Boot40: AUC {au}/40 Bri {br}/40 Both {bo}/40  p_auc {pa:.1e} p_bri {pb:.1e}  mean dAUC {np.mean(d_a)*10000:+.1f} dBri {np.mean(d_b)*10000:+.1f}")

sa=sb=sbo=0
for s in range(20):
    sc_bs, r_bs, x_bs, l_bs = fit(Xb_tr, ytr, xs=s, ls=s)
    sc_ps, r_ps, x_ps, l_ps = fit(Xp_tr, ytr, xs=s, ls=s)
    aa, bb = scr(sc_bs, r_bs, x_bs, l_bs, Xb_te, yte)
    ap, bp = scr(sc_ps, r_ps, x_ps, l_ps, Xp_te, yte)
    if ap>aa: sa+=1
    if bp<bb: sb+=1
    if ap>aa and bp<bb: sbo+=1
print(f"Seed20: AUC {sa}/20 Bri {sb}/20 Both {sbo}/20")

gate = (bo/40>=0.70) and pa<0.05 and pb<0.05
verdict = 'SHIP' if (gate and sbo>=14) else 'KILL'
print(f"VERDICT: {verdict}")

json.dump({'version':'v52_trial_quality','base':'v51b','selected':selected,
           'point':{'auc_b':float(a_b),'bri_b':float(b_b),'auc_p':float(a_p),'bri_p':float(b_p),
                    'd_auc_bp':(a_p-a_b)*10000,'d_bri_bp':(b_p-b_b)*10000},
           'boot':{'n':40,'auc_w':au,'bri_w':br,'both_w':bo,'p_auc':float(pa),'p_bri':float(pb),
                   'mean_d_auc':float(np.mean(d_a)),'mean_d_bri':float(np.mean(d_b))},
           'seed':{'n':20,'auc_w':sa,'bri_w':sb,'both_w':sbo},
           'coverage':{'match':int(coverage),'total':len(df),'pct':100*coverage/len(df)},
           'single_feature_screen':screen,
           'verdict':verdict},
          open(f'{ROOT}/gungnir_v52_trial_quality_results.json','w'), indent=2)
print(f"\nSaved gungnir_v52_trial_quality_results.json")
