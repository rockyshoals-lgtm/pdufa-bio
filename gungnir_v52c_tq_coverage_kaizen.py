"""
Gungnir v52c — TQ-COVERAGE. 4-tier fallback matcher to push nct_id coverage from 51.7% to 75%+.

Fallback tiers (precision-ordered):
  Tier 1: exact nct_id match
  Tier 2: sponsor token match + drug token match
  Tier 3: sponsor token match + ta match + phase match + start_date ±180d
  Tier 4: drug token match + ta match + phase match + start_date ±180d

Merge tq_* features (num_primary_outcomes, num_secondary_outcomes, masking_rigor,
ep_is_hard, ep_is_surrogate, ep_is_biomarker, is_placebo_controlled,
has_active_comparator, has_dmc) from ctgov_t1_dataset.csv.

Re-run v52-TRIAL-QUALITY kaizen on expanded panel. Same red team.
Ship gate: boot_both >=70%, p_auc & p_bri <0.05, seed_both >=14/20.
"""
import os, json, re, types, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
import xgboost as xgb, lightgbm as lgb
from scipy import stats

ROOT = "/sessions/elegant-gracious-ramanujan/mnt/Odin Perfection"
BASE = "/sessions/elegant-gracious-ramanujan/mnt/9realms"

print("Loading Gungnir panel + CT.gov dataset...")
gp = pd.read_csv(f'{ROOT}/gungnir_readout_ctgov_enriched.csv', low_memory=False)
gp['date'] = pd.to_datetime(gp['date'], errors='coerce')
ct = pd.read_csv(f'{BASE}/ctgov_t1_dataset.csv', low_memory=False)
ct['start_date'] = pd.to_datetime(ct['start_date'], errors='coerce')
ct['primary_completion_date'] = pd.to_datetime(ct['primary_completion_date'], errors='coerce')

tq_fields = ['num_primary_outcomes','num_secondary_outcomes','masking_rigor',
             'ep_is_hard','ep_is_surrogate','ep_is_biomarker',
             'is_placebo_controlled','has_active_comparator','has_dmc']

# -------- Build tokenized lookups --------
_token_re = re.compile(r'[a-z0-9]+')
def tokens(s):
    if pd.isna(s): return set()
    return set(t for t in _token_re.findall(str(s).lower()) if len(t) >= 3)

ct['_sponsor_toks'] = ct['lead_sponsor_name'].apply(tokens)
ct['_drug_toks'] = ct['drug_names'].apply(tokens)
ct['_cond_toks'] = ct['conditions_raw'].apply(tokens)
ct['_phase_n'] = ct['phase_numeric'].fillna(0).astype(float)

gp['_sponsor_toks'] = gp['ctgov_sponsor_exact'].apply(tokens)
gp['_drug_toks'] = gp['drug'].apply(tokens)
gp['_cond_toks'] = gp['indication'].apply(tokens)
# parse phase: 'Phase 3' -> 3.0
gp['_phase_n'] = gp['stage'].fillna('').astype(str).str.extract(r'(\d)', expand=False).astype(float).fillna(0)

# -------- Tier 1: nct_id exact --------
ct_tq = ct[['nct_id'] + tq_fields].drop_duplicates('nct_id')
gp_merged = gp.merge(ct_tq, on='nct_id', how='left', suffixes=('', '_ct'))
t1_match = gp_merged['num_primary_outcomes'].notna()
print(f"Tier 1 (nct_id exact): {t1_match.sum()}/{len(gp)} ({100*t1_match.mean():.1f}%)")

# -------- Tier 2: sponsor + drug fuzzy --------
# For unmatched rows, find best ct row by (sponsor_tok ∩) + (drug_tok ∩) size
need_idx = gp_merged.index[~t1_match].tolist()
tier2_hit = 0
for i in need_idx:
    sponsor_t = gp.at[i, '_sponsor_toks']
    drug_t = gp.at[i, '_drug_toks']
    if not sponsor_t or not drug_t:
        continue
    best = None; best_score = 0
    # shortlist: ct rows with any sponsor token overlap
    cand_mask = ct['_sponsor_toks'].apply(lambda s: len(s & sponsor_t) >= 1 if s else False)
    cands = ct[cand_mask]
    if len(cands) == 0:
        continue
    for _, ct_row in cands.iterrows():
        sp_ov = len(ct_row['_sponsor_toks'] & sponsor_t)
        dr_ov = len(ct_row['_drug_toks'] & drug_t)
        if sp_ov >= 1 and dr_ov >= 1:
            score = sp_ov * 2 + dr_ov
            if score > best_score:
                best_score = score; best = ct_row
    if best is not None and best_score >= 3:
        for f in tq_fields:
            gp_merged.at[i, f] = best[f]
        tier2_hit += 1
print(f"Tier 2 (sponsor+drug): +{tier2_hit}  cumulative {int(t1_match.sum()) + tier2_hit}/{len(gp)} ({100*(int(t1_match.sum()) + tier2_hit)/len(gp):.1f}%)")

# -------- Tier 3: sponsor + indication + phase + date±180d --------
now_matched = gp_merged['num_primary_outcomes'].notna()
need_idx = gp_merged.index[~now_matched].tolist()
tier3_hit = 0
for i in need_idx:
    sponsor_t = gp.at[i, '_sponsor_toks']
    cond_t = gp.at[i, '_cond_toks']
    phase = gp.at[i, '_phase_n']
    ev_date = gp.at[i, 'date']
    if not sponsor_t or not cond_t or phase == 0 or pd.isna(ev_date):
        continue
    # CT.gov has start_date; catalyst is ~1-3y after start — so shift window
    lo = ev_date - pd.Timedelta(days=1825)  # up to 5y lookback
    hi = ev_date - pd.Timedelta(days=90)   # trial started >=90d before readout
    cand_mask = ((ct['_sponsor_toks'].apply(lambda s: len(s & sponsor_t) >= 1 if s else False)) &
                 (ct['_phase_n'] == phase) &
                 (ct['start_date'] >= lo) & (ct['start_date'] <= hi))
    cands = ct[cand_mask]
    if len(cands) == 0:
        continue
    best = None; best_score = 0
    for _, ct_row in cands.iterrows():
        cond_ov = len(ct_row['_cond_toks'] & cond_t)
        if cond_ov >= 1:
            score = cond_ov
            if score > best_score:
                best_score = score; best = ct_row
    if best is not None and best_score >= 1:
        for f in tq_fields:
            gp_merged.at[i, f] = best[f]
        tier3_hit += 1
now_matched = gp_merged['num_primary_outcomes'].notna()
print(f"Tier 3 (sponsor+indication+phase+date): +{tier3_hit}  cumulative {int(now_matched.sum())}/{len(gp)} ({100*now_matched.mean():.1f}%)")

# -------- Tier 4: drug + indication + phase + date±180d --------
need_idx = gp_merged.index[~now_matched].tolist()
tier4_hit = 0
for i in need_idx:
    drug_t = gp.at[i, '_drug_toks']
    cond_t = gp.at[i, '_cond_toks']
    phase = gp.at[i, '_phase_n']
    ev_date = gp.at[i, 'date']
    if not drug_t or not cond_t or phase == 0 or pd.isna(ev_date):
        continue
    lo = ev_date - pd.Timedelta(days=1825)
    hi = ev_date - pd.Timedelta(days=90)
    cand_mask = ((ct['_drug_toks'].apply(lambda s: len(s & drug_t) >= 1 if s else False)) &
                 (ct['_phase_n'] == phase) &
                 (ct['start_date'] >= lo) & (ct['start_date'] <= hi))
    cands = ct[cand_mask]
    if len(cands) == 0:
        continue
    best = None; best_score = 0
    for _, ct_row in cands.iterrows():
        cond_ov = len(ct_row['_cond_toks'] & cond_t)
        if cond_ov >= 1:
            score = cond_ov
            if score > best_score:
                best_score = score; best = ct_row
    if best is not None and best_score >= 1:
        for f in tq_fields:
            gp_merged.at[i, f] = best[f]
        tier4_hit += 1
final_match = gp_merged['num_primary_outcomes'].notna()
print(f"Tier 4 (drug+indication+phase+date): +{tier4_hit}  cumulative {int(final_match.sum())}/{len(gp)} ({100*final_match.mean():.1f}%)")

# -------- Now run v52-TRIAL-QUALITY kaizen with the enriched panel --------
df = gp_merged.sort_values('date').reset_index(drop=True)
match = df[tq_fields]

# Rebuild v51b base
src = open(f'{ROOT}/gungnir_v49g_kaizen.py').read()
i = src.find('# ---------- build everything ----------')
builder_src = "import numpy as np\nimport pandas as pd\n" + src[src.find('# ---------- v47 base'):i]
mod = types.ModuleType('v49g_b'); exec(compile(builder_src, 'v49g_b', 'exec'), mod.__dict__)

X_v49d = pd.concat([mod.build_base_features(df), mod.build_v49b_features(df),
                    mod.build_v49c_features(df), mod.build_v49d_features(df)], axis=1)
V49G_SHIP = ['v49g_double_x_p3','v49g_narms_x_p3','v49g_has_placebo_real']
X_v49g = pd.concat([X_v49d, mod.build_v49g_candidates(df)[V49G_SHIP]], axis=1)

heim = pd.read_csv(f'{ROOT}/heimdall_v2_honest_scored_panel.csv', low_memory=False)
heim['catalyst_date'] = pd.to_datetime(heim['catalyst_date'])
h = heim[['ticker','catalyst_date','heimdall_p_v2','heimdall_tier_v2']].drop_duplicates(['ticker','catalyst_date']).rename(columns={'catalyst_date':'date','heimdall_p_v2':'heimdall_p','heimdall_tier_v2':'heimdall_tier'})
m = df[['ticker','date']].merge(h, on=['ticker','date'], how='left')
hp = m['heimdall_p'].fillna(float(h['heimdall_p'].median())).values
stage = df['stage'].fillna('').astype(str).str.lower()
p3 = stage.isin(['phase 3','phase3']).astype(float).values
micro = df['is_micro'].fillna(0).astype(float).values if 'is_micro' in df.columns else np.zeros(len(df))
tm = {'BAD':-1.0,'BULL':0.5,'ROCKET':1.0,'NEUTRAL':0.0}
ht = m['heimdall_tier'].fillna('NEUTRAL').map(tm).fillna(0.0).values
X_heim = pd.DataFrame({'heimdall_p_v2':hp,'heimdall_p_v2_sq':hp**2,'heimdall_tier_v2_enc':ht,
                      'heimdall_p_v2_x_p3':hp*p3,'heimdall_p_v2_x_micro':hp*micro,
                      'heimdall_high_v2_flag':(hp>=0.6).astype(float)}, index=df.index)
X_v51b = pd.concat([X_v49g, X_heim], axis=1)

# Build tq_ features
X_tq = pd.DataFrame(index=df.index)
for src_c, dst_c in [('num_primary_outcomes','tq_n_primary'),('num_secondary_outcomes','tq_n_secondary'),
                      ('masking_rigor','tq_masking_rigor'),('ep_is_hard','tq_ep_hard'),
                      ('ep_is_surrogate','tq_ep_surrogate'),('ep_is_biomarker','tq_ep_biomarker'),
                      ('is_placebo_controlled','tq_placebo_ctrl'),('has_active_comparator','tq_active_comp'),
                      ('has_dmc','tq_has_dmc')]:
    X_tq[dst_c] = pd.to_numeric(match[src_c], errors='coerce').fillna(0).astype(float).values

candidates = list(X_tq.columns)

y = df['is_positive_outcome'].astype(int).values
tr_mask = (df['date'] <= pd.Timestamp('2023-12-31')).values
te_mask = (df['date'] >= pd.Timestamp('2025-01-01')).values
VAL = pd.Timestamp('2023-07-01')
tr_fs_tr = (df['date'] <= VAL).values
tr_fs_va = ((df['date'] > VAL) & (df['date'] <= pd.Timestamp('2023-12-31'))).values

for c in candidates:
    nz_tr = int((X_tq.loc[tr_mask, c] != 0).sum())
    print(f"  train nz {c:22s}: {nz_tr}/{tr_mask.sum()}")

C_R=0.2; XGB=dict(n_estimators=600,learning_rate=0.02,max_depth=3,reg_alpha=0.2,subsample=0.8,colsample_bytree=0.8,eval_metric='auc',use_label_encoder=False,verbosity=0)
LG=dict(n_estimators=400,learning_rate=0.03,num_leaves=15,reg_alpha=0.1,subsample=0.8,colsample_bytree=0.8,verbose=-1)
W_R, W_X, W_L = 0.70, 0.15, 0.15

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
print(f"\nv51b VAL baseline: AUC {va_auc:.4f}  Brier {va_bri:.4f}")

# Single-feat screen
print("\n=== Single-feat VAL screen ===")
screen = {}
for c in candidates:
    X_try = pd.concat([X_v51b, X_tq[[c]]], axis=1).values
    sc_, r_, x_, l_ = fit(X_try[tr_fs_tr], y[tr_fs_tr])
    a, b = scr(sc_, r_, x_, l_, X_try[tr_fs_va], y[tr_fs_va])
    screen[c] = {'val_auc': float(a), 'val_bri': float(b)}
    mark = '##' if a > va_auc and b < va_bri else '+ ' if a > va_auc else '  '
    print(f"  {mark} {c:22s}  val {a:.4f} (Δ{(a-va_auc)*10000:+6.1f}bp)  bri {b:.4f} (Δ{(b-va_bri)*10000:+6.1f}bp)")

# Greedy both-metric val FS
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
        if a > cur_va_auc and b < cur_va_bri and (a - cur_va_auc) > best_gain:
            best_gain = a - cur_va_auc; best=c; best_auc=a; best_bri=b
    if not best: break
    selected.append(best); X_cur = pd.concat([X_cur, X_tq[[best]]], axis=1)
    cur_va_auc=best_auc; cur_va_bri=best_bri; remaining.remove(best)
    print(f"  + {best}  val AUC {cur_va_auc:.4f}  val Bri {cur_va_bri:.4f}")

print(f"\nSelected: {selected}")
coverage_pct = 100*final_match.mean()

if not selected:
    print("KILL_FS — no candidate passes both-metric val gate")
    json.dump({'version':'v52c_tq_coverage','verdict':'KILL_FS','selected':[],
               'single_feature_screen':screen,
               'coverage':{'pct':coverage_pct,'matched':int(final_match.sum())}},
              open(f'{ROOT}/gungnir_v52c_results.json','w'), indent=2)
    raise SystemExit(0)

# TEST red team
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
print(f"  +TQc{len(selected)}:   AUC {a_p:.4f}  Brier {b_p:.4f}")
print(f"  dAUC {(a_p-a_b)*10000:+.1f}bp  dBri {(b_p-b_b)*10000:+.1f}bp")

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

out = {'version':'v52c_tq_coverage','base':'v51b','selected':selected,
       'coverage':{'pct':float(coverage_pct),'matched':int(final_match.sum()),'total':len(df)},
       'point':{'auc_b':float(a_b),'bri_b':float(b_b),'auc_p':float(a_p),'bri_p':float(b_p),
                'd_auc_bp':(a_p-a_b)*10000,'d_bri_bp':(b_p-b_b)*10000},
       'boot':{'n':40,'auc_w':au,'bri_w':br,'both_w':bo,'p_auc':float(pa),'p_bri':float(pb),
               'mean_d_auc':float(np.mean(d_a)),'mean_d_bri':float(np.mean(d_b))},
       'seed':{'n':20,'auc_w':sa,'bri_w':sb,'both_w':sbo},
       'single_feature_screen':screen,'verdict':verdict}
json.dump(out, open(f'{ROOT}/gungnir_v52c_results.json','w'), indent=2)
print(f"\nSaved gungnir_v52c_results.json")
