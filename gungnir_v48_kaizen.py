#!/usr/bin/env python3
"""
GUNGNIR v48 KAIZEN — additive feature search on v47-honest

Methodology:
  Reuse v47 honest pipeline's 60-feature matrix (loaded via script replay).
  Generate v48 candidate features across 4 pillars:
    P1. ADC × journey deep interactions (v46 found 3/8 wins here)
    P2. Conference tier × size × phase
    P3. Masking rigor × phase3 × oncology three-ways
    P4. Untapped TA × modality interactions (cell/gene × TA)

  Select features using VAL-only greedy forward selection:
    - Fast screen: fit Ridge-only with candidate added, keep if val_auc lift >= 1e-4
    - Greedy: add highest-lift surviving candidate, refit, repeat while gate (Δ>=5e-4) met
  FINAL TEST and FINAL HO touched exactly ONCE.

Bar to beat:
  v47 Final HO AUC 0.7521 (CI95 [0.6871, 0.8150]), Brier 0.1495.
  v48 passes if: val_auc lift >= 5bp AND final HO AUC not regressed >5bp.
"""

import os, sys, io, json, time, warnings, math
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
TARGET_FINAL_AUC = 0.7521  # v47 honest final HO AUC

print("=" * 70)
print("GUNGNIR v48 KAIZEN (additive on v47-honest)")
print("=" * 70)

# ----------------------------------------------------------------
# Step 0 — Rebuild v47's feature matrix directly
# ----------------------------------------------------------------
t0 = time.time()
print("\n[0/5] Rebuilding v47 feature matrix via v46 kaizen chain...")
old = sys.stdout; sys.stdout = io.StringIO()
try:
    import gungnir_v46_kaizen as k
finally:
    sys.stdout = old

v39 = k.load_v39_module()
old = sys.stdout; sys.stdout = io.StringIO()
events, ctgov_lookup = v39.load_data()
X_v39, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_v39 = v39.build_features(
    events, ctgov_lookup, include_v37=True, include_v38=True,
    include_candidates=k.V39_SELECTED
)
v40_lookup = k.build_v40_features(events)
v40_cols = []
for f in k.V40_SELECTED:
    col = np.array([float(v40_lookup.get(
        (ev.get("ticker", "").upper(), ev.get("date", "")), {}).get(f, 0) or 0)
        for ev in events])
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

v46_selected = [
    "v46_p1_ch2_moa_agonist", "v46_p6_fic_X_is_phase3_X_sponsor",
    "v46_p6_sponsor_X_ch2_is_adc_X_is_phase2",
    "v46_p6_conf_X_ch2_is_advanced_X_is_small",
    "v46_p5_log1p_journey_last_positive",
    "v46_p2_ch2_is_adc_X_journey_n_negative",
    "v46_p6_conf_X_ch2_is_mab_X_is_small",
    "v46_p2_ch2_is_adc_X_journey_had_negative",
]
v46_dict = k.generate_v46_candidates(events, X_v45, feat_v45, ch2_features, v40_lookup)
X_v46 = np.column_stack([X_v45] + [v46_dict[f].reshape(-1, 1) for f in v46_selected])
feat_v46 = list(feat_v45) + v46_selected

sys.stdout = old

# Load v47 feature list
v47_res = json.load(open(os.path.join(DATA_DIR, "gungnir_v47_honest_results.json")))
v47_features = v47_res["features_kept"]
keep_idx = [feat_v46.index(f) for f in v47_features if f in feat_v46]
X47 = X_v46[:, keep_idx]
feat47 = [feat_v46[i] for i in keep_idx]

print(f"  Events: {len(events)}  v47 features: {X47.shape[1]}")
print(f"  Build time: {time.time()-t0:.1f}s")

# ----------------------------------------------------------------
# [1/5] 4-way temporal split
# ----------------------------------------------------------------
dates_arr = np.array(dates)
train_mask = dates_arr < "2023-07-01"
val_mask   = (dates_arr >= "2023-07-01") & (dates_arr < "2024-07-01")
test_mask  = (dates_arr >= "2024-07-01") & (dates_arr < "2025-07-01")
final_mask = dates_arr >= "2025-07-01"

X_train = X47[train_mask]; y_train = y_bin[train_mask]
X_val   = X47[val_mask];   y_val   = y_bin[val_mask]
X_test  = X47[test_mask];  y_test  = y_bin[test_mask]
X_final = X47[final_mask]; y_final = y_bin[final_mask]

# events subset used for generating candidate features later
ev_train = [ev for ev,m in zip(events, train_mask) if m]
ev_val   = [ev for ev,m in zip(events, val_mask) if m]
ev_test  = [ev for ev,m in zip(events, test_mask) if m]
ev_final = [ev for ev,m in zip(events, final_mask) if m]

print(f"  Split: train={X_train.shape[0]}, val={X_val.shape[0]}, test={X_test.shape[0]}, final={X_final.shape[0]}")

# ----------------------------------------------------------------
# [2/5] Baseline reproduction (val AUC must match v47 0.8541)
# ----------------------------------------------------------------
def scale_fit_eval(X_tr, X_v, y_tr, y_v, X_te=None, X_fi=None, C=0.05):
    scaler = StandardScaler().fit(X_tr)
    Xtr, Xv = scaler.transform(X_tr), scaler.transform(X_v)
    m = LogisticRegression(C=C, penalty="l2", solver="lbfgs", max_iter=2000, random_state=RANDOM_SEED)
    m.fit(Xtr, y_tr)
    p_v = m.predict_proba(Xv)[:,1]
    auc_v = roc_auc_score(y_v, p_v)
    out = dict(val_auc=auc_v, val_brier=brier_score_loss(y_v, p_v), model=m, scaler=scaler)
    if X_te is not None:
        Xte = scaler.transform(X_te)
        p_te = m.predict_proba(Xte)[:,1]
        out["test_auc"]=roc_auc_score(y_te:=y_test, p_te)
        out["test_brier"]=brier_score_loss(y_test, p_te)
    if X_fi is not None:
        Xfi = scaler.transform(X_fi)
        p_fi = m.predict_proba(Xfi)[:,1]
        out["final_auc"]=roc_auc_score(y_final, p_fi)
        out["final_brier"]=brier_score_loss(y_final, p_fi)
    return out

base = scale_fit_eval(X_train, X_val, y_train, y_val, C=0.05)
print(f"\n[1/5] Baseline (Ridge-only, C=0.05): val_auc={base['val_auc']:.4f} (v47 ensemble val was 0.8541)")

# ----------------------------------------------------------------
# [3/5] Generate v48 candidate features
# ----------------------------------------------------------------
print("\n[2/5] Generating v48 candidate features...")

def get_v40(ev, key):
    return float(v40_lookup.get((ev.get("ticker","").upper(), ev.get("date","")), {}).get(key, 0) or 0)

def safe_get(ev, key, default=0.0):
    v = ev.get(key, default)
    try:
        return float(v) if v is not None else default
    except:
        return default

# ch2_features is {feat_name: np.array(n_events)}, indexed by event position
n_events = len(events)
def ch2_vec(name):
    arr = ch2_features.get(name)
    if arr is None:
        return np.zeros(n_events)
    return np.asarray(arr, dtype=float)

# Primitive feature vectors indexed by event position (len=n_events)
phase_int = np.array([int(ev.get("phase", 0) or 0) for ev in events])
is_phase1 = (phase_int == 1).astype(float)
is_phase2 = (phase_int == 2).astype(float)
is_phase3 = (phase_int == 3).astype(float)
is_small = np.array([safe_get(ev, "is_small") for ev in events])
is_micro = np.array([safe_get(ev, "is_micro") for ev in events])
is_mid   = np.array([safe_get(ev, "is_mid") for ev in events])
is_large = np.array([safe_get(ev, "is_large") for ev in events])
ta_list  = [ev.get("ta","") or "" for ev in events]
is_onc    = np.array([1.0 if t == "oncology" else 0.0 for t in ta_list])
is_rare   = np.array([1.0 if t in ("rare_disease","rare") else 0.0 for t in ta_list])
is_cns    = np.array([1.0 if t == "cns" else 0.0 for t in ta_list])
is_immuno = np.array([1.0 if t in ("immunology","autoimmune") else 0.0 for t in ta_list])
is_metab  = np.array([1.0 if t in ("metabolic","endocrine") else 0.0 for t in ta_list])
has_conf  = np.array([get_v40(ev, "v40_has_conference") for ev in events])
is_adc = ch2_vec("ch2_is_adc"); is_mab = ch2_vec("ch2_is_mab")
is_cell = ch2_vec("ch2_is_cell"); is_gene = ch2_vec("ch2_is_gene")
is_oligo = ch2_vec("ch2_is_oligo"); is_sm = ch2_vec("ch2_is_sm")
is_biol = ch2_vec("ch2_is_biologic")
is_agonist = ch2_vec("ch2_moa_agonist"); is_antag = ch2_vec("ch2_moa_antagonist")
# Journey / CT.gov / non-linear
j_last_pos = np.array([safe_get(ev.get("_journey",{}) if isinstance(ev.get("_journey"),dict) else ev, "journey_last_positive") or safe_get(ev, "journey_last_positive") for ev in events])
j_success  = np.array([safe_get(ev, "journey_success_rate") for ev in events])
j_had_pos  = np.array([safe_get(ev, "journey_had_positive") for ev in events])
j_had_neg  = np.array([safe_get(ev, "journey_had_negative") for ev in events])
j_n_neg    = np.array([safe_get(ev, "journey_n_negative") for ev in events])
ctgov_rand = np.array([safe_get(ev, "ctgov_is_randomized") for ev in events])
ctgov_mask = np.array([safe_get(ev, "ctgov_masking_rigor") for ev in events])
ctgov_dmc  = np.array([safe_get(ev, "ctgov_has_dmc") for ev in events])
mom_20d    = np.array([safe_get(ev, "v40_momentum_20d") for ev in events])
vol_20d    = np.array([safe_get(ev, "volatility_20d") for ev in events])
sponsor_sr = np.array([safe_get(ev, "sponsor_success_rate") for ev in events])
iis_interim = np.array([safe_get(ev, "iis_is_interim") for ev in events])
is_fic     = np.array([safe_get(ev, "is_first_in_class") for ev in events])
ind_dens   = np.array([safe_get(ev, "indication_density") for ev in events])

# Pull journey / ctgov / iis / sponsor from sub-dicts if missing at top level
def pull_sub(key_sub, key_inner):
    out = np.zeros(n_events)
    for i, ev in enumerate(events):
        sub = ev.get(key_sub)
        if isinstance(sub, dict):
            v = sub.get(key_inner)
            if v is not None:
                try: out[i] = float(v)
                except: pass
    return out

if j_had_pos.sum() == 0:
    j_had_pos = pull_sub("_journey", "had_positive")
    j_success = pull_sub("_journey", "success_rate")
    j_last_pos = pull_sub("_journey", "last_positive")
    j_n_neg = pull_sub("_journey", "n_negative")
if ctgov_rand.sum() == 0:
    ctgov_rand = pull_sub("_ctgov_v2", "is_randomized")
    ctgov_mask = pull_sub("_ctgov_v2", "masking_rigor")
    ctgov_dmc = pull_sub("_ctgov_v2", "has_dmc")
    if ctgov_rand.sum() == 0:
        ctgov_rand = pull_sub("_ctgov_real", "is_randomized")
        ctgov_mask = pull_sub("_ctgov_real", "masking_rigor")
        ctgov_dmc = pull_sub("_ctgov_real", "has_dmc")
if iis_interim.sum() == 0:
    iis_interim = pull_sub("_iis", "is_interim")
if sponsor_sr.sum() == 0:
    sponsor_sr = pull_sub("_sponsor", "success_rate")
# zero out the old broken block below
    j_n_neg = pull_sub("_journey", "journey_n_negative")
if ctgov_rand.sum() == 0:
    ctgov_rand = pull_sub("_ctgov_v2", "ctgov_is_randomized")
    ctgov_mask = pull_sub("_ctgov_v2", "ctgov_masking_rigor")
    ctgov_dmc = pull_sub("_ctgov_v2", "ctgov_has_dmc")
if iis_interim.sum() == 0:
    iis_interim = pull_sub("_iis", "iis_is_interim")
if sponsor_sr.sum() == 0:
    sponsor_sr = pull_sub("_sponsor", "sponsor_success_rate")

print(f"  Primitive stats: is_adc nz={int((is_adc>0).sum())}, has_conf nz={int((has_conf>0).sum())}, j_had_pos nz={int((j_had_pos>0).sum())}, is_small nz={int((is_small>0).sum())}, ctgov_rand nz={int((ctgov_rand>0).sum())}, iis_int nz={int((iis_interim>0).sum())}, sponsor_sr nz={int((sponsor_sr>0).sum())}")

candidates = {}
# P1. ADC × journey deep
candidates["v48_adc_X_jhadpos_X_is_phase2"] = is_adc * j_had_pos * is_phase2
candidates["v48_adc_X_jnneg_X_is_phase3"]   = is_adc * j_n_neg * is_phase3
candidates["v48_adc_X_jsuccess_X_is_small"] = is_adc * j_success * is_small
candidates["v48_adc_X_jlastpos_X_conf"]     = is_adc * j_last_pos * has_conf
candidates["v48_adc_X_ctrand_X_is_onc"]     = is_adc * ctgov_rand * is_onc
# P2. Conference × size × phase
candidates["v48_conf_X_small_X_phase3"]     = has_conf * is_small * is_phase3
candidates["v48_conf_X_micro_X_phase2"]     = has_conf * is_micro * is_phase2
candidates["v48_conf_X_adc_X_phase2"]       = has_conf * is_adc * is_phase2
candidates["v48_conf_X_cell_X_small"]       = has_conf * is_cell * is_small
candidates["v48_conf_X_oligo_X_phase2"]     = has_conf * is_oligo * is_phase2
# P3. Masking × phase3 × oncology / ta
candidates["v48_mask_X_phase3_X_onc"]       = ctgov_mask * is_phase3 * is_onc
candidates["v48_mask_X_rand_X_small"]       = ctgov_mask * ctgov_rand * is_small
candidates["v48_dmc_X_phase3_X_rare"]       = ctgov_dmc * is_phase3 * is_rare
candidates["v48_mask_X_dmc_X_phase3"]       = ctgov_mask * ctgov_dmc * is_phase3
# P4. TA × modality interactions
candidates["v48_rare_X_gene_X_phase2"]      = is_rare * is_gene * is_phase2
candidates["v48_onc_X_cell_X_phase2"]       = is_onc * is_cell * is_phase2
candidates["v48_cns_X_sm_X_phase2"]         = is_cns * is_sm * is_phase2
candidates["v48_metab_X_sm_X_phase3"]       = is_metab * is_sm * is_phase3
candidates["v48_immuno_X_mab_X_phase3"]     = is_immuno * is_mab * is_phase3
candidates["v48_onc_X_adc_X_small"]         = is_onc * is_adc * is_small
# P5. Sponsor × modality
candidates["v48_sponsor_X_cell_X_conf"]     = sponsor_sr * is_cell * has_conf
candidates["v48_sponsor_X_adc_X_phase3"]    = sponsor_sr * is_adc * is_phase3
candidates["v48_sponsor_X_oligo_X_small"]   = sponsor_sr * is_oligo * is_small
# P6. Non-linear / momentum
candidates["v48_jsuccess_sq"]               = j_success ** 2
candidates["v48_mom20d_X_conf"]             = mom_20d * has_conf
candidates["v48_vol20d_X_small_X_adc"]      = vol_20d * is_small * is_adc
candidates["v48_iis_X_fic_X_phase3"]        = iis_interim * is_fic * is_phase3
candidates["v48_inddens_X_onc_X_phase3"]    = ind_dens * is_onc * is_phase3

print(f"  Generated {len(candidates)} v48 candidate features")

# Filter low-variance / near-zero candidates
MIN_NZ = 8
filtered = {}
for name, vec in candidates.items():
    train_vec = vec[train_mask]
    nz = int(np.count_nonzero(train_vec))
    if nz >= MIN_NZ and np.std(train_vec) > 1e-6:
        filtered[name] = vec
print(f"  After sparsity filter (>= {MIN_NZ} non-zero in train): {len(filtered)}")

# ----------------------------------------------------------------
# [3/5] Fast screen — add each candidate individually, measure val AUC lift
# ----------------------------------------------------------------
print("\n[3/5] Fast screen (add 1 candidate at a time, val-only gate)...")
baseline_val = base["val_auc"]

screen = []
for name, vec in filtered.items():
    X_tr2 = np.column_stack([X_train, vec[train_mask].reshape(-1,1)])
    X_v2  = np.column_stack([X_val,   vec[val_mask].reshape(-1,1)])
    res = scale_fit_eval(X_tr2, X_v2, y_train, y_val, C=0.05)
    delta = res["val_auc"] - baseline_val
    screen.append((name, res["val_auc"], delta, vec))
screen.sort(key=lambda x: x[2], reverse=True)
print(f"  Baseline val: {baseline_val:.4f}")
print(f"  Top 12 candidates by solo lift:")
for name, auc, delta, _ in screen[:12]:
    flag = "++" if delta >= 5e-4 else ("+" if delta > 0 else " ")
    print(f"    {flag} {name:54s}  val={auc:.4f}  Δ={delta*1e4:+7.2f} bp")

# ----------------------------------------------------------------
# [4/5] Greedy forward selection with val-only gate (Δ >= 5bp)
# ----------------------------------------------------------------
print("\n[4/5] Greedy forward selection (gate Δval >= 5 bp)...")
X_tr_cur = X_train.copy()
X_v_cur  = X_val.copy()
X_te_cur = X_test.copy()
X_fi_cur = X_final.copy()
cur_val  = baseline_val
v48_added = []

pool = {name: vec for name, vec in filtered.items()}
GATE = 5e-4

while pool:
    best_name, best_auc, best_delta, best_vec = None, None, -1, None
    for name, vec in pool.items():
        X_tr2 = np.column_stack([X_tr_cur, vec[train_mask].reshape(-1,1)])
        X_v2  = np.column_stack([X_v_cur,  vec[val_mask].reshape(-1,1)])
        res = scale_fit_eval(X_tr2, X_v2, y_train, y_val, C=0.05)
        delta = res["val_auc"] - cur_val
        if delta > best_delta:
            best_delta, best_name, best_auc, best_vec = delta, name, res["val_auc"], vec
    if best_delta < GATE:
        print(f"  Stop — top remaining candidate {best_name} Δ={best_delta*1e4:+.2f} bp < {GATE*1e4:.0f} bp gate")
        break
    print(f"  ADD {best_name:54s}  val={best_auc:.4f}  Δ={best_delta*1e4:+7.2f} bp")
    X_tr_cur = np.column_stack([X_tr_cur, best_vec[train_mask].reshape(-1,1)])
    X_v_cur  = np.column_stack([X_v_cur,  best_vec[val_mask].reshape(-1,1)])
    X_te_cur = np.column_stack([X_te_cur, best_vec[test_mask].reshape(-1,1)])
    X_fi_cur = np.column_stack([X_fi_cur, best_vec[final_mask].reshape(-1,1)])
    cur_val  = best_auc
    v48_added.append(best_name)
    pool.pop(best_name)

print(f"\n  v48 features added: {len(v48_added)}")
for f in v48_added: print(f"    + {f}")

# ----------------------------------------------------------------
# [4b] C sweep on VAL with new feature set
# ----------------------------------------------------------------
print("\n[4b] C sweep on val with v48 feature set...")
best_C = 0.05
best_C_val = cur_val
for C in [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.20, 0.50]:
    res = scale_fit_eval(X_tr_cur, X_v_cur, y_train, y_val, C=C)
    mark = ""
    if res["val_auc"] > best_C_val:
        best_C_val = res["val_auc"]
        best_C = C
        mark = "  *"
    print(f"  C={C:.3f}  val_auc={res['val_auc']:.4f}{mark}")
print(f"  Best C: {best_C}  val_auc={best_C_val:.4f}")

# ----------------------------------------------------------------
# [5/5] Final TEST + Final HO evaluation — touched exactly ONCE
# ----------------------------------------------------------------
print("\n[5/5] One-shot TEST + FINAL HO evaluation...")
scaler = StandardScaler().fit(X_tr_cur)
Xtr_s  = scaler.transform(X_tr_cur)
Xv_s   = scaler.transform(X_v_cur)
Xte_s  = scaler.transform(X_te_cur)
Xfi_s  = scaler.transform(X_fi_cur)
model = LogisticRegression(C=best_C, penalty="l2", solver="lbfgs", max_iter=2000, random_state=RANDOM_SEED)
model.fit(Xtr_s, y_train)
p_val   = model.predict_proba(Xv_s)[:,1]
p_test  = model.predict_proba(Xte_s)[:,1]
p_final = model.predict_proba(Xfi_s)[:,1]

auc_val   = roc_auc_score(y_val, p_val)
auc_test  = roc_auc_score(y_test, p_test)
auc_final = roc_auc_score(y_final, p_final)
b_val     = brier_score_loss(y_val, p_val)
b_test    = brier_score_loss(y_test, p_test)
b_final   = brier_score_loss(y_final, p_final)

# Bootstrap CI on final
rng = np.random.default_rng(RANDOM_SEED)
boots=[]
for _ in range(2000):
    idx = rng.integers(0, len(y_final), len(y_final))
    if len(set(y_final[idx])) < 2: continue
    boots.append(roc_auc_score(y_final[idx], p_final[idx]))
ci_lo, ci_hi = np.quantile(boots, [0.025, 0.975])

print("\n" + "=" * 70)
print("GUNGNIR v48 HONEST RESULTS")
print("=" * 70)
print(f"  v48 features added:    {len(v48_added)}")
print(f"  Total features:        {X_tr_cur.shape[1]} (v47 had 60)")
print(f"  Best C (VAL):          {best_C}")
print(f"  VAL AUC (selection):   {auc_val:.4f}   Brier: {b_val:.4f}")
print(f"  TEST AUC (touched 1x): {auc_test:.4f}   Brier: {b_test:.4f}")
print(f"  FINAL HO AUC (blind):  {auc_final:.4f}  Brier: {b_final:.4f}   CI95=[{ci_lo:.4f}, {ci_hi:.4f}]")
print()
print(f"  v47 Final HO AUC:      0.7521   Brier: 0.1495")
print(f"  v48 delta AUC:         {(auc_final-0.7521)*1e4:+.2f} bp")
print(f"  v48 delta Brier:       {(b_final-0.1495)*1e4:+.2f} bp")

out = dict(
    model="gungnir_v48_kaizen_honest",
    generated_utc=datetime.utcnow().isoformat(),
    v47_final_auc=0.7521, v47_final_brier=0.1495,
    v48_added_features=v48_added,
    total_features=int(X_tr_cur.shape[1]),
    best_C=best_C,
    val_auc=auc_val, val_brier=b_val,
    test_auc=auc_test, test_brier=b_test,
    final_auc=auc_final, final_brier=b_final,
    final_auc_ci95=[float(ci_lo), float(ci_hi)],
    delta_final_auc_bp=(auc_final-0.7521)*1e4,
    delta_final_brier_bp=(b_final-0.1495)*1e4,
)
out_path = os.path.join(DATA_DIR, "gungnir_v48_kaizen_results.json")
with open(out_path, "w") as f: json.dump(out, f, indent=2, default=str)
print(f"\nSaved: {out_path}")
print(f"Total time: {time.time()-t0:.1f}s")
os.path.join(DATA_DIR, "gungnir_v48_kaizen_results.json")
with open(out_path, "w") as f: json.dump(out, f, indent=2, default=str)
print(f"\nSaved: {out_path}")
print(f"Total time: {time.time()-t0:.1f}s")
=0.7521, v47_final_brier=0.1495,
    v48_added_features=v48_added,
    total_features=int(X_tr_cur.shape[1]),
    best_C=best_C,
    val_auc=auc_val, val_brier=b_val,
    test_auc=auc_test, test_brier=b_test,
    final_auc=auc_final, final_brier=b_final,
    final_auc_ci95=[float(ci_lo), float(ci_hi)],
    delta_final_auc_bp=(auc_final-0.7521)*1e4,
    delta_final_brier_bp=(b_final-0.1495)*1e4,
)
out_path = os.path.join(DATA_DIR, "gungnir_v48_kaizen_results.json")
with open(out_path, "w") as f: json.dump(out, f, indent=2, default=str)
print(f"\nSaved: {out_path}")
print(f"Total time: {time.time()-t0:.1f}s")
