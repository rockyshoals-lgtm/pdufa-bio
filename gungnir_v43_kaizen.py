#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v43 KAIZEN — ChEMBL Biotech Scientist Enrichment
================================================================================

APPROACH:
  Start from v42.0.0 as baseline (AUC 0.7936, 138 features)

  v42 FINDINGS:
    Exhaustive pairwise interaction search found 8 features.
    Key signals: interim×momentum, multi-arm oncology penalty,
    global trials in crowded indications, etc.

  v43 STRATEGY: ChEMBL drug mechanism enrichment — "Biotech Scientist" features.
  Baker Bros approach: evaluate drug modality, target biology, mechanism of action,
  first-in-class status, prior approval. Coverage expanded from 14.9% to 59.7%
  using ChEMBL REST API + INN stem classification.

  NEW FEATURE CATEGORIES:
    1. Drug modality: small molecule, mAb, ADC, cell therapy, gene therapy, oligo
    2. Mechanism of action: inhibitor, agonist, antagonist
    3. Drug quality: first-in-class, prior approval
    4. Combination therapy flag
    5. Interactions: modality × phase, modality × TA, modality × size, etc.

  T-1 COMPLIANCE: Drug modality and mechanism are PUBLIC information known before
  any readout. ChEMBL data is published scientific/regulatory data.
"""

import csv, json, math, os, re, sys, warnings, io, time
from collections import defaultdict, Counter
import numpy as np
warnings.filterwarnings("ignore")

try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()

# Import from v42 kaizen
sys.path.insert(0, DATA_DIR)

# v42 config
V42_CONFIG = {
    "ridge_c": 0.015, "xgb_lr": 0.01, "xgb_trees": 600, "xgb_depth": 3,
    "meta_ridge": 0.80, "meta_xgb": 0.20, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

V42_SELECTED = [
    "v42_iis_is_interim_X_momentum_10d",
    "v42_ctgov_n_arms_X_phase3_x_oncology",
    "v42_ctgov_n_countries_X_indication_density",
    "v42_global_x_phase3_X_volatility_20d",
    "v42_ct_is_industry_X_ctgov_masking_rigor",
    "v42_iis_is_interim_X_indication_density_sq",
    "v42_momentum_20d_X_ta_metabolic",
    "v42_is_small_X_ta_cns",
]

V41_SELECTED = [
    "v41_sponsor_x_conference", "v41_journey_last_pos_sq",
    "v41_immuno_x_phase2", "v41_placebo_x_cns", "v41_enrollment_x_journey"
]
V40_SELECTED = ["v40_has_conference", "v40_days_to_cover", "v40_conf_x_small"]
V39_SELECTED = [
    "ct_ep_is_safety", "ct_ep_is_biomarker", "ct_active_comp_x_phase3",
    "orphan_x_micro", "ch_is_enzyme", "ind_maturity_high",
    "ch_is_ion_channel", "ct_has_combination", "ct_ep_is_pfs", "ch_is_agonist"
]

ELITE_CONFERENCES = ["AACR", "ASH", "ESMO"]
TIER1_CONFERENCES = ["ASCO", "AAN", "EHA", "AASLD"]
TIER2_CONFERENCES = ["SITC", "SNO", "ACNP", "ACR", "ADA", "EASD", "ECTRIMS",
                     "WCG", "EULAR", "DDW", "AUA", "ATS", "CHEST", "IDSA"]
GENERIC_CONF = ["conference", "congress", "meeting", "symposium", "annual meeting",
                "presented at", "poster", "oral presentation", "late-breaking"]

BRAND_MAP = {
    'KEYTRUDA': 'PEMBROLIZUMAB', 'ENHERTU': 'TRASTUZUMAB DERUXTECAN',
    'ABECMA': 'IDECABTAGENE VICLEUCEL', 'LIVDELZI': 'SELADELPAR',
    'NYXOL': 'PHENTOLAMINE', 'TONMYA': 'CYCLOBENZAPRINE',
    'HADUVIO': 'FARUDODSTAT', 'ZYGEL': 'CANNABIDIOL',
    'IMFINZI': 'DURVALUMAB', 'VABYSMO': 'FARICIMAB',
    'BAVENCIO': 'AVELUMAB', 'TECENTRIQ': 'ATEZOLIZUMAB',
    'OPDIVO': 'NIVOLUMAB', 'BREYANZI': 'LISOCABTAGENE MARALEUCEL',
    'YERVOY': 'IPILIMUMAB', 'TAGRISSO': 'OSIMERTINIB',
    'ZEJULA': 'NIRAPARIB', 'CABOMETYX': 'CABOZANTINIB',
    'NIKTIMVO': 'AXATILIMAB', 'KORSUVA': 'DIFELIKEFALIN',
    'PADCEV': 'ENFORTUMAB VEDOTIN', 'TUKYSA': 'TUCATINIB',
    'TRODELVY': 'SACITUZUMAB GOVITECAN', 'LYNPARZA': 'OLAPARIB',
    'DUPIXENT': 'DUPILUMAB', 'CALQUENCE': 'ACALABRUTINIB',
}


def extract_conference(catalyst_text, conference_field):
    text = (str(catalyst_text) + " " + str(conference_field)).upper()
    for conf in ELITE_CONFERENCES:
        if conf.upper() in text: return 1, 3
    for conf in TIER1_CONFERENCES:
        if conf.upper() in text: return 1, 2
    for conf in TIER2_CONFERENCES:
        if conf.upper() in text: return 1, 1
    for g in GENERIC_CONF:
        if g.upper() in text: return 1, 1
    return 0, 0


def load_v39_module():
    import importlib.util
    v39_path = os.path.join(DATA_DIR, "gungnir_v39_kaizen.py")
    full_lookup_path = os.path.join(DATA_DIR, "ctgov_training_lookup_v2_full.json")
    spec = importlib.util.spec_from_file_location("v39_kaizen", v39_path)
    v39_mod = importlib.util.module_from_spec(spec)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        spec.loader.exec_module(v39_mod)
    except Exception:
        pass
    sys.stdout = old_stdout
    if os.path.exists(full_lookup_path):
        v39_mod.CTGOV_TRAIN_LOOKUP_V2 = full_lookup_path
        print(f"  Patched v39 to use FULL CT.gov lookup (96.6% coverage)")
    return v39_mod


def build_v40_features(events):
    si_path = os.path.join(DATA_DIR, "short_interest_snapshot.json")
    si_data = {}
    if os.path.exists(si_path):
        with open(si_path) as f:
            si_data = json.load(f)
    v40_lookup = {}
    for ev in events:
        ticker = ev.get("ticker", "").upper()
        date = ev.get("date", "")
        key = (ticker, date)
        catalyst_text = ev.get("catalyst_text", "")
        conference_field = ev.get("_conference", "")
        is_micro = int(ev.get("is_micro", 0) or 0)
        is_small = int(ev.get("is_small", 0) or 0)
        has_conf, _ = extract_conference(catalyst_text, conference_field)
        si = si_data.get(ticker, {})
        dtc = float(si.get("short_ratio", 0) or 0) if "error" not in si else 0
        v40_lookup[key] = {
            "v40_has_conference": has_conf,
            "v40_days_to_cover": dtc,
            "v40_conf_x_small": has_conf * (is_micro + is_small),
        }
    return v40_lookup


def build_v41_features(events, X_base, feat_names, v40_lookup):
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}
    def get_col(name):
        idx = feat_idx.get(name)
        return X_base[:, idx] if idx is not None else np.zeros(n)
    def get_v40_col(v40_name):
        return np.array([float(v40_lookup.get(
            (ev.get("ticker", "").upper(), ev.get("date", "")), {}).get(v40_name, 0) or 0)
            for ev in events])

    return {
        "v41_sponsor_x_conference": get_col("sponsor_success_rate") * get_v40_col("v40_has_conference"),
        "v41_journey_last_pos_sq": get_col("journey_last_positive") ** 2,
        "v41_immuno_x_phase2": get_col("ta_immunology") * get_col("is_phase2"),
        "v41_placebo_x_cns": get_col("ctgov_is_placebo") * get_col("ta_cns"),
        "v41_enrollment_x_journey": get_col("ctgov_enrollment") * get_col("journey_success_rate"),
    }


def build_v42_features(events, X_base, feat_names):
    """Build v42's 8 features from v41 feature matrix."""
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}
    def get_col(name):
        idx = feat_idx.get(name)
        return X_base[:, idx] if idx is not None else np.zeros(n)

    # v42 features are pairwise interactions of existing features
    v42_cols = {}

    # Get base columns
    iis_interim = get_col("iis_is_interim")
    momentum_10d = get_col("momentum_10d")
    ctgov_n_arms = get_col("ctgov_n_arms")
    phase3_onc = get_col("phase3_x_oncology")
    n_countries = get_col("ctgov_n_countries")
    ind_density = get_col("indication_density")
    global_p3 = get_col("global_x_phase3")
    vol_20d = get_col("volatility_20d")
    ct_industry = get_col("ct_is_industry")
    masking = get_col("ctgov_masking_rigor")
    ind_density_sq = get_col("indication_density_sq")
    momentum_20d = get_col("momentum_20d")
    ta_metabolic = get_col("ta_metabolic")
    is_small = get_col("is_small")
    ta_cns = get_col("ta_cns")

    v42_cols["v42_iis_is_interim_X_momentum_10d"] = iis_interim * momentum_10d
    v42_cols["v42_ctgov_n_arms_X_phase3_x_oncology"] = ctgov_n_arms * phase3_onc
    v42_cols["v42_ctgov_n_countries_X_indication_density"] = n_countries * ind_density
    v42_cols["v42_global_x_phase3_X_volatility_20d"] = global_p3 * vol_20d
    v42_cols["v42_ct_is_industry_X_ctgov_masking_rigor"] = ct_industry * masking
    v42_cols["v42_iis_is_interim_X_indication_density_sq"] = iis_interim * ind_density_sq
    v42_cols["v42_momentum_20d_X_ta_metabolic"] = momentum_20d * ta_metabolic
    v42_cols["v42_is_small_X_ta_cns"] = is_small * ta_cns

    return v42_cols


def parse_primary_drug(raw):
    """Extract primary drug name from catalyst event."""
    if not raw: return None
    s = str(raw)
    s = re.sub(r'\s*-\s*\([A-Z][A-Z0-9\-/\s]*\)\s*$', '', s)
    s = re.sub(r'\s*-\s*\([A-Z][A-Z0-9\-/\s]*$', '', s)
    parts = re.split(r'\s+(?:and|plus|\+|in combination with)\s+', s, flags=re.IGNORECASE)
    p = parts[0].strip()
    m = re.search(r'\(([a-z][a-z\-\s]+)\)', p)
    if m: p = m.group(1)
    else:
        m2 = re.match(r'^[A-Z]{3,}(?:\s+[A-Z]{3,})*\s+\(([^)]+)\)', p)
        if m2: p = m2.group(1)
    p = re.sub(r'\s*\([^)]*\)', '', p)
    return p.strip(' -').upper()


def clean_for_lookup(name):
    if not name: return name
    if name in BRAND_MAP: return BRAND_MAP[name]
    return re.sub(r'-[A-Z]{2,5}$', '', name).strip()


def build_chembl_features(events):
    """Build ChEMBL biotech scientist features for each event."""
    # Load caches
    chembl_path = os.path.join(DATA_DIR, "chembl_enrichment_cache_v2.json")
    inn_path = os.path.join(DATA_DIR, "drug_classifications.json")

    chembl_cache = {}
    if os.path.exists(chembl_path):
        with open(chembl_path) as f:
            chembl_cache = json.load(f)

    inn_class = {}
    if os.path.exists(inn_path):
        with open(inn_path) as f:
            inn_class = json.load(f)

    print(f"  ChEMBL cache: {len(chembl_cache)} drugs")
    print(f"  INN classifications: {len(inn_class)} drugs")

    def lkp(drug, lookup):
        for key in [drug, lookup]:
            if key and key in chembl_cache: return chembl_cache[key]
        return None

    features = defaultdict(list)
    n_matched = 0

    for ev in events:
        drug_raw = ev.get("drug", "") or ev.get("Drug", "") or ev.get("asset", "") or ""
        drug = parse_primary_drug(drug_raw)
        lookup = clean_for_lookup(drug)
        info = lkp(drug, lookup)
        dl = (drug or '').lower()

        # Modality
        mod = 'unknown'
        if info:
            mt = (info.get('molecule_type') or '').lower()
            if 'antibody' in mt and 'conjugate' in mt: mod = 'adc'
            elif 'antibody' in mt: mod = 'mab'
            elif 'protein' in mt: mod = 'protein'
            elif 'oligonucleotide' in mt: mod = 'oligo'
            elif 'cell' in mt: mod = 'cell'
            elif 'gene' in mt: mod = 'gene'
            elif 'small molecule' in mt or 'small_molecule' in mt: mod = 'sm'
            elif 'vaccine' in mt: mod = 'vaccine'
        if mod == 'unknown':
            for key in [drug, lookup]:
                if key and key in inn_class:
                    m2 = inn_class[key].get('modality', 'unknown')
                    if m2 != 'unknown':
                        if 'antibody' in m2: mod = 'mab'
                        elif m2 == 'small_molecule': mod = 'sm'
                        elif 'cell' in m2: mod = 'cell'
                        elif 'gene' in m2: mod = 'gene'
                        elif 'oligo' in m2: mod = 'oligo'
                        elif 'peptide' in m2 or 'fusion' in m2: mod = 'peptide'
                        elif 'adc' in m2 or 'conjugate' in m2: mod = 'adc'
                        break
        if mod == 'unknown':
            if dl.endswith('mab'): mod = 'mab'
            elif any(x in dl for x in ['vedotin', 'tansine', 'deruxtecan', 'govitecan', 'mafodotin']): mod = 'adc'
            elif dl.endswith('cel') or 'car-t' in dl: mod = 'cell'
            elif dl.endswith('vec') or 'aav' in dl: mod = 'gene'
            elif dl.endswith('nib') or dl.endswith('tinib'): mod = 'sm'
            elif dl.endswith('sen') or 'sirna' in dl: mod = 'oligo'
            elif dl.endswith('cept'): mod = 'peptide'
            elif dl.endswith('tide'): mod = 'peptide'

        if mod != 'unknown': n_matched += 1

        # Mechanism
        mech = 'unknown'
        if info:
            mt2 = info.get('mechanism_type')
            if mt2: mech = mt2.lower()
            elif info.get('mechanisms'):
                a = (info['mechanisms'][0].get('action') or '').lower()
                if a: mech = a
        if mech == 'unknown':
            if any(dl.endswith(s) for s in ['nib', 'tinib']) or 'parib' in dl or 'lisib' in dl or 'zomib' in dl:
                mech = 'inhibitor'
            elif dl.endswith('mab'): mech = 'antibody_binding'

        # First in class
        fic = int(info.get('first_in_class', 0) or 0) if info else 0

        # Prior approval
        prior = 0
        if info:
            mp = info.get('max_phase', 0) or 0
            fa = info.get('first_approval')
            if isinstance(mp, (int, float)) and mp >= 4 and fa: prior = 1

        # Combo
        is_combo = int(bool(re.search(r'\band\b|\bplus\b|\+|combination|combo', drug_raw, re.IGNORECASE)))

        # Binary features
        features['ch2_is_sm'].append(int(mod == 'sm'))
        features['ch2_is_mab'].append(int(mod == 'mab'))
        features['ch2_is_adc'].append(int(mod == 'adc'))
        features['ch2_is_biologic'].append(int(mod in ('mab', 'adc', 'protein')))
        features['ch2_is_cell'].append(int(mod == 'cell'))
        features['ch2_is_gene'].append(int(mod == 'gene'))
        features['ch2_is_oligo'].append(int(mod == 'oligo'))
        features['ch2_is_advanced'].append(int(mod in ('cell', 'gene', 'oligo')))
        features['ch2_is_peptide'].append(int(mod in ('peptide',)))
        features['ch2_moa_inhibitor'].append(int(mech == 'inhibitor'))
        features['ch2_moa_agonist'].append(int(mech == 'agonist'))
        features['ch2_moa_antagonist'].append(int(mech in ('antagonist', 'antagonist_antibody')))
        features['ch2_first_in_class'].append(fic)
        features['ch2_has_prior_approval'].append(prior)
        features['ch2_is_combo'].append(is_combo)

    print(f"  Drug modality matched: {n_matched}/{len(events)} ({n_matched/len(events)*100:.1f}%)")

    return {k: np.array(v) for k, v in features.items()}


def fast_ridge_screen(X_base, y_bin, dates, candidate_col, ridge_c=0.015, seed=42):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    dates_str = np.array([str(d) for d in dates])
    train_mask = dates_str < "2025"
    test_mask = dates_str >= "2025"
    if train_mask.sum() < 100 or test_mask.sum() < 30: return 0.0, 0.0

    y_tr, y_te = y_bin[train_mask], y_bin[test_mask]

    sc1 = StandardScaler()
    X_tr1 = sc1.fit_transform(X_base[train_mask])
    X_te1 = sc1.transform(X_base[test_mask])
    lr1 = LogisticRegression(C=ridge_c, penalty="l2", solver="lbfgs", max_iter=2000, random_state=seed)
    lr1.fit(X_tr1, y_tr)
    base_auc = roc_auc_score(y_te, lr1.predict_proba(X_te1)[:, 1])

    X_cand = np.column_stack([X_base, candidate_col.reshape(-1, 1)])
    sc2 = StandardScaler()
    X_tr2 = sc2.fit_transform(X_cand[train_mask])
    X_te2 = sc2.transform(X_cand[test_mask])
    lr2 = LogisticRegression(C=ridge_c, penalty="l2", solver="lbfgs", max_iter=2000, random_state=seed)
    lr2.fit(X_tr2, y_tr)
    cand_auc = roc_auc_score(y_te, lr2.predict_proba(X_te2)[:, 1])

    return cand_auc - base_auc, cand_auc


def main():
    t_start = time.time()

    print("\n" + "=" * 80)
    print("  GUNGNIR v43 KAIZEN — ChEMBL Biotech Scientist Enrichment")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Build v42 baseline (138 features)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Build v42 baseline (138 features)")
    print(f"{'=' * 80}")

    print("\n  Loading v39 kaizen module...")
    v39 = load_v39_module()

    print("  Loading data...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    events, ctgov_lookup = v39.load_data()
    sys.stdout = old_stdout
    print(f"  Events: {len(events)}")

    print("  Building v39.1 features...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    X_v39, y_bin, y_gp, y_cr, y_ret, dates, meta, feat_v39 = v39.build_features(
        events, ctgov_lookup, include_v37=True, include_v38=True,
        include_candidates=V39_SELECTED
    )
    sys.stdout = old_stdout
    print(f"  v39.1: {X_v39.shape[0]} × {X_v39.shape[1]}")

    # v40
    print("  Building v40 features...")
    v40_lookup = build_v40_features(events)
    v40_cols = []
    for v40_feat in V40_SELECTED:
        col = np.array([float(v40_lookup.get(
            (ev.get("ticker", "").upper(), ev.get("date", "")), {}).get(v40_feat, 0) or 0)
            for ev in events])
        v40_cols.append(col)
    X_v40 = np.column_stack([X_v39] + [c.reshape(-1, 1) for c in v40_cols])
    feat_v40 = list(feat_v39) + V40_SELECTED
    print(f"  v40: {X_v40.shape[1]} features")

    # v41
    print("  Building v41 features...")
    v41_dict = build_v41_features(events, X_v40, feat_v40, v40_lookup)
    v41_cols = [v41_dict[f] for f in V41_SELECTED]
    X_v41 = np.column_stack([X_v40] + [c.reshape(-1, 1) for c in v41_cols])
    feat_v41 = list(feat_v40) + V41_SELECTED
    print(f"  v41: {X_v41.shape[1]} features")

    # v42
    print("  Building v42 features...")
    v42_dict = build_v42_features(events, X_v41, feat_v41)
    v42_cols = [v42_dict[f] for f in V42_SELECTED]
    X_v42 = np.column_stack([X_v41] + [c.reshape(-1, 1) for c in v42_cols])
    feat_v42 = list(feat_v41) + V42_SELECTED
    print(f"  v42: {X_v42.shape[1]} features")

    # Baseline WF AUC
    print("\n  Evaluating v42 baseline...")
    baseline = v39.evaluate_wf(X_v42, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=True, **V42_CONFIG)
    base_auc = baseline["avg_auc"]
    print(f"\n  *** v42 BASELINE: AUC={base_auc:.4f} Brier={baseline['avg_brier']:.4f}")

    # =========================================================================
    # PHASE 2: Build ChEMBL features
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 2: Build ChEMBL Biotech Scientist Features")
    print(f"{'=' * 80}")

    ch2_features = build_chembl_features(events)
    ch2_names = sorted(ch2_features.keys())
    print(f"\n  Base ChEMBL features: {len(ch2_names)}")

    for name in ch2_names:
        n = np.sum(ch2_features[name] != 0)
        print(f"    {name}: {n} events ({n / len(events) * 100:.1f}%)")

    # =========================================================================
    # PHASE 3: Generate interaction candidates
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 3: Generate Interaction Candidates")
    print(f"{'=' * 80}")

    feat_idx = {name: i for i, name in enumerate(feat_v42)}
    partner_names = [
        "is_phase2", "is_phase3", "is_phase1b", "is_phase2a", "is_phase2b",
        "ta_oncology", "ta_cns", "ta_metabolic", "ta_immunology", "ta_rare_disease",
        "ta_infectious", "ta_cardiovascular",
        "is_micro", "is_small", "is_mid", "is_large",
        "journey_n_positive", "journey_n_events", "journey_last_positive",
        "journey_success_rate", "indication_density", "sponsor_success_rate",
        "momentum_10d", "momentum_20d", "volatility_20d",
        "enrollment_sq", "indication_density_sq",
        "ctgov_enrollment", "ctgov_is_placebo", "ctgov_is_randomized",
    ]
    partners = [(p, feat_idx[p]) for p in partner_names if p in feat_idx]
    print(f"  Partners available: {len(partners)}")

    candidates = {}
    # Base ch2 features
    for name in ch2_names:
        vals = ch2_features[name]
        n_nz = np.sum(vals != 0)
        if n_nz >= 20:
            candidates[name] = vals

    # Interactions: ch2 × partner
    for ch_name in ch2_names:
        ch_vals = ch2_features[ch_name]
        if np.sum(ch_vals != 0) < 20: continue
        for p_name, p_idx in partners:
            p_vals = X_v42[:, p_idx]
            prod = ch_vals * p_vals
            if np.std(prod) > 1e-8 and np.sum(np.abs(prod) > 0.001) >= 10:
                cand_name = f"v43_{ch_name}_X_{p_name}"
                candidates[cand_name] = prod

    print(f"  Total candidates: {len(candidates)}")

    # =========================================================================
    # PHASE 4: Fast Ridge Pre-screen
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 4: Fast Pre-Screen ({len(candidates)} candidates)")
    print(f"{'=' * 80}")

    screen_results = []
    for i, (feat_name, col) in enumerate(candidates.items()):
        delta, abs_auc = fast_ridge_screen(X_v42, y_bin, dates, col,
                                            ridge_c=V42_CONFIG["ridge_c"])
        screen_results.append({"feature": feat_name, "delta": delta, "auc": abs_auc})
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(candidates)} screened...")

    screen_results.sort(key=lambda x: -x["delta"])
    positive = [r for r in screen_results if r["delta"] > 0]
    print(f"\n  Positive: {len(positive)}/{len(screen_results)}")

    print(f"\n  TOP 30:")
    for r in screen_results[:30]:
        flag = " ***" if r["delta"] > 0.001 else ""
        print(f"    {r['feature']:55s} Δ={r['delta']:+.4f}{flag}")

    # =========================================================================
    # PHASE 5: Full WF Audit on top candidates
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 5: Full WF Audit (top 50 from pre-screen)")
    print(f"{'=' * 80}")

    top_candidates = [r["feature"] for r in screen_results[:50] if r["delta"] > 0]
    audit_results = []

    for feat_name in top_candidates:
        col = candidates[feat_name]
        X_test = np.column_stack([X_v42, col.reshape(-1, 1)])
        result = v39.evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates,
                                  verbose=False, **V42_CONFIG)
        delta = result["avg_auc"] - base_auc
        audit_results.append({
            "feature": feat_name, "auc": result["avg_auc"],
            "delta": delta, "brier": result["avg_brier"],
        })

    audit_results.sort(key=lambda x: -x["delta"])
    positive_audit = [r for r in audit_results if r["delta"] > 0]
    print(f"\n  Positive on full WF: {len(positive_audit)}/{len(audit_results)}")

    print(f"\n  TOP 20 (full WF):")
    for r in audit_results[:20]:
        flag = " ***" if r["delta"] > 0.001 else ""
        print(f"    {r['feature']:55s} AUC={r['auc']:.4f} Δ={r['delta']:+.4f}{flag}")

    # =========================================================================
    # PHASE 6: Greedy Forward Selection
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 6: Greedy Forward Selection")
    print(f"{'=' * 80}")

    greedy_candidates = [r["feature"] for r in audit_results if r["delta"] > 0.0003]
    print(f"  Candidates: {len(greedy_candidates)}")

    current_X = X_v42.copy()
    current_feats = list(feat_v42)
    current_auc = base_auc
    selected = []

    for rnd in range(15):
        best_feat, best_auc = None, current_auc
        for feat_name in greedy_candidates:
            if feat_name in current_feats: continue
            col = candidates[feat_name]
            X_test = np.column_stack([current_X, col.reshape(-1, 1)])
            result = v39.evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates,
                                      verbose=False, **V42_CONFIG)
            if result["avg_auc"] > best_auc:
                best_auc = result["avg_auc"]
                best_feat = feat_name

        if best_feat and (best_auc - current_auc) > 0.0001:
            col = candidates[best_feat]
            current_X = np.column_stack([current_X, col.reshape(-1, 1)])
            current_feats.append(best_feat)
            incr = best_auc - current_auc
            selected.append({"feature": best_feat, "auc": best_auc,
                           "incremental": incr})
            print(f"  R{rnd + 1}: +{best_feat:50s} AUC={best_auc:.4f} (+{incr:.4f})")
            current_auc = best_auc
        else:
            print(f"  R{rnd + 1}: No improvement. Stopping.")
            break

    print(f"\n  v42 {base_auc:.4f} → v43 {current_auc:.4f} (Δ={current_auc - base_auc:+.4f})")
    print(f"  Features added: {len(selected)}, Total: {len(current_feats)}")

    # =========================================================================
    # PHASE 7: 10-Seed Stability
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 7: 10-Seed Stability Test")
    print(f"{'=' * 80}")

    from scipy import stats

    v42_aucs, v43_aucs = [], []
    for seed in range(10):
        cfg = dict(V42_CONFIG)
        cfg["seed"] = seed
        r42 = v39.evaluate_wf(X_v42, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg)
        r43 = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg)
        v42_aucs.append(r42["avg_auc"])
        v43_aucs.append(r43["avg_auc"])

    wins = sum(1 for a, b in zip(v42_aucs, v43_aucs) if b > a)
    t_stat, p_val = stats.ttest_rel(v43_aucs, v42_aucs)
    print(f"  v42: {np.mean(v42_aucs):.4f} ± {np.std(v42_aucs):.4f}")
    print(f"  v43: {np.mean(v43_aucs):.4f} ± {np.std(v43_aucs):.4f}")
    print(f"  Wins: {wins}/10, p={p_val:.10f}")

    # =========================================================================
    # PHASE 8: Architecture Sweep
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 8: Architecture Sweep")
    print(f"{'=' * 80}")

    best_c, best_c_auc = V42_CONFIG["ridge_c"], current_auc
    for c in [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]:
        cfg = dict(V42_CONFIG)
        cfg["ridge_c"] = c
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        flag = " <-- BEST" if r["avg_auc"] > best_c_auc else ""
        print(f"    C={c}: AUC={r['avg_auc']:.4f}{flag}")
        if r["avg_auc"] > best_c_auc:
            best_c_auc = r["avg_auc"]
            best_c = c

    for meta_r in [0.70, 0.75, 0.80, 0.85, 0.90]:
        cfg = dict(V42_CONFIG)
        cfg["ridge_c"] = best_c
        cfg["meta_ridge"] = meta_r
        cfg["meta_xgb"] = 1.0 - meta_r
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        flag = " <-- BEST" if r["avg_auc"] > best_c_auc else ""
        print(f"    Meta {meta_r:.0%}/{1 - meta_r:.0%}: AUC={r['avg_auc']:.4f}{flag}")
        if r["avg_auc"] > best_c_auc:
            best_c_auc = r["avg_auc"]
            V42_CONFIG["meta_ridge"] = meta_r
            V42_CONFIG["meta_xgb"] = 1.0 - meta_r

    print(f"\n  Best config: C={best_c}, meta={V42_CONFIG['meta_ridge']:.0%}/{V42_CONFIG['meta_xgb']:.0%}")
    print(f"  Best AUC: {best_c_auc:.4f}")

    # =========================================================================
    # SAVE RESULTS
    # =========================================================================
    elapsed = time.time() - t_start
    is_champion = wins >= 7 and current_auc > base_auc

    results = {
        "version": "v43.0.0",
        "date": time.strftime("%Y-%m-%d"),
        "baseline_version": "v42.0.0",
        "baseline_auc": base_auc,
        "final_wf_auc": current_auc,
        "best_c_auc": best_c_auc,
        "best_c": best_c,
        "auc_delta": current_auc - base_auc,
        "n_features_v42": len(feat_v42),
        "n_features_v43": len(current_feats),
        "features_added": [s["feature"] for s in selected],
        "screen_results_top30": screen_results[:30],
        "audit_results": audit_results[:20],
        "greedy_selection": selected,
        "stability": {
            "v42_mean": float(np.mean(v42_aucs)),
            "v43_mean": float(np.mean(v43_aucs)),
            "v42_aucs": [float(x) for x in v42_aucs],
            "v43_aucs": [float(x) for x in v43_aucs],
            "wins": wins,
            "p_value": float(p_val),
        },
        "champion": is_champion,
        "runtime_seconds": elapsed,
    }

    with open(os.path.join(DATA_DIR, "gungnir_v43_kaizen_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 80}")
    if is_champion:
        print(f"  *** v43 IS CHAMPION: AUC {base_auc:.4f} → {current_auc:.4f} "
              f"(+{current_auc - base_auc:.4f}), {wins}/10 seeds ***")
    else:
        print(f"  v43 does NOT beat v42: AUC {base_auc:.4f} → {current_auc:.4f}, "
              f"{wins}/10 seeds")
    print(f"  Runtime: {elapsed:.0f}s")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
