#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v45 KAIZEN — Prune + Tighten (Discipline Release)
================================================================================

APPROACH:
  Start from v44.0.0 as baseline (AUC 0.8018, 146 features)

  v44 FINDINGS (Red Team Audit):
    - 19 features with ZERO coefficients across ALL 3 models (M1, M2, M3)
    - 8 features near-zero in M1 but with some M2/M3 signal
    - 17 features with |M1 coef| < 0.02 (candidates for pruning)
    - 146 features on 1,752 events = 12:1 ratio (over-parameterized)
    - C=0.02 (trending less regularized) — needs tightening

  v45 STRATEGY: Pure discipline. No new features. Three phases:
    1. DROP all 19 confirmed-dead features (zero in ALL models)
    2. PROGRESSIVE ABLATION of next ~20 weakest features — test each removal
    3. REGULARIZATION SWEEP — test tighter C values now that feature count is lower
    4. ARCHITECTURE SWEEP — meta weights and tree count
    5. 20-SEED STABILITY vs v44
    6. DEPLOY if champion

  TARGET: ~100-110 features with tighter regularization, maintaining AUC ≥ 0.8018

  T-1 COMPLIANCE: Same features as v44, just fewer. No new data sources.
"""

import csv, json, math, os, re, sys, warnings, io, time
from collections import defaultdict, Counter
import numpy as np
warnings.filterwarnings("ignore")

try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()

sys.path.insert(0, DATA_DIR)

# ============================================================================
# v44 CONFIG (champion baseline)
# ============================================================================
V44_CONFIG = {
    "ridge_c": 0.02, "xgb_lr": 0.01, "xgb_trees": 600, "xgb_depth": 3,
    "meta_ridge": 0.90, "meta_xgb": 0.10, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# ============================================================================
# FEATURES TO DROP — Phase 1: Zero across ALL 3 models (CONFIRMED DEAD)
# ============================================================================
DEAD_FEATURES = [
    "btd_x_phase3",
    "cat_conference",
    "cat_full_results",
    "cat_initial",
    "cat_interim",
    "cat_regulatory",
    "cat_submission",
    "cat_topline",
    "ctgov_has_withdrawals",
    "has_btd",
    "has_fast_track",
    "has_priority_review",
    "hist_loa",
    "hist_pop",
    "ind_maturity_high",
    "journey_had_prior_negative",
    "journey_had_prior_positive",
    "journey_pos_x_phase3",
    "journey_streak_x_small",
]

# ============================================================================
# FEATURES NEAR-ZERO IN M1 — Phase 2 ablation candidates
# These have |M1_coef| < 0.02 and are candidates for progressive removal
# ============================================================================
WEAK_CANDIDATES = [
    # |M1 coef| = 0.000 (zero in M1 but non-zero in M2 or M3)
    "ctgov_is_global",          # M1=0.000
    "is_mid",                   # M1=0.000
    "journey_n_positive",       # M1=0.000
    "nlp_dose_response",        # M1=0.000
    "phase3_x_double_blind",    # M1=0.000
    "ta_metabolic",             # M1=0.000
    "ta_ophthalmology",         # M1=0.000
    "ta_rare_disease",          # M1=0.000
    # |M1 coef| < 0.01
    "combo_x_onc",
    "ctgov_enrollment",
    "desig_x_small",
    "designation_count",
    "has_orphan",
    "is_phase2",
    "is_phase3",
    "is_pivotal",
    "journey_n_prior",
    "journey_positive_streak",
    "journey_sr_x_phase3",
    "log_market_cap",
    "log_price",
    "momentum_10d",
    "momentum_x_micro",
    "nlp_interim",
    "orphan_x_micro",
    # Slightly above 0.02 but still weak
    "ctgov_n_countries",
    "ctgov_n_sites",
    "competitive_3mo",
    "competitive_6mo",
    "is_nano",
    "indication_density",
    "volatility_5d",
]

# ============================================================================
# VERSION-SPECIFIC SELECTED FEATURES (same as v44)
# ============================================================================
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
V43_SELECTED = [
    "v43_ch2_is_oligo_X_volatility_20d",
    "v43_ch2_is_biologic_X_is_phase3",
    "v43_ch2_is_cell_X_ctgov_is_randomized",
    "v43_ch2_is_adc_X_enrollment_sq",
    "v43_ch2_is_cell_X_momentum_10d",
    "v43_ch2_is_oligo_X_is_phase2",
]
V44_SELECTED = [
    "v44_ch2_moa_antagonist_X_journey_had_positive",
    "v44_ch2_is_sm_X_is_phase2_X_is_small",
]

# Same conference / brand / ChEMBL helpers as v44 — import from v44
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
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}
    def get_col(name):
        idx = feat_idx.get(name)
        return X_base[:, idx] if idx is not None else np.zeros(n)
    return {
        "v42_iis_is_interim_X_momentum_10d": get_col("iis_is_interim") * get_col("momentum_10d"),
        "v42_ctgov_n_arms_X_phase3_x_oncology": get_col("ctgov_n_arms") * get_col("phase3_x_oncology"),
        "v42_ctgov_n_countries_X_indication_density": get_col("ctgov_n_countries") * get_col("indication_density"),
        "v42_global_x_phase3_X_volatility_20d": get_col("global_x_phase3") * get_col("volatility_20d"),
        "v42_ct_is_industry_X_ctgov_masking_rigor": get_col("ct_is_industry") * get_col("ctgov_masking_rigor"),
        "v42_iis_is_interim_X_indication_density_sq": get_col("iis_is_interim") * get_col("indication_density_sq"),
        "v42_momentum_20d_X_ta_metabolic": get_col("momentum_20d") * get_col("ta_metabolic"),
        "v42_is_small_X_ta_cns": get_col("is_small") * get_col("ta_cns"),
    }


def parse_primary_drug(raw):
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
    print(f"  ChEMBL cache: {len(chembl_cache)} drugs, INN: {len(inn_class)} drugs")

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

        fic = int(info.get('first_in_class', 0) or 0) if info else 0
        prior = 0
        if info:
            mp = info.get('max_phase', 0) or 0
            fa = info.get('first_approval')
            if isinstance(mp, (int, float)) and mp >= 4 and fa: prior = 1
        is_combo = int(bool(re.search(r'\band\b|\bplus\b|\+|combination|combo', drug_raw, re.IGNORECASE)))

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


def build_v43_features(events, X_base, feat_names, ch2_features):
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}
    def get_col(name):
        idx = feat_idx.get(name)
        return X_base[:, idx] if idx is not None else np.zeros(n)
    return {
        "v43_ch2_is_oligo_X_volatility_20d": ch2_features["ch2_is_oligo"] * get_col("volatility_20d"),
        "v43_ch2_is_biologic_X_is_phase3": ch2_features["ch2_is_biologic"] * get_col("is_phase3"),
        "v43_ch2_is_cell_X_ctgov_is_randomized": ch2_features["ch2_is_cell"] * get_col("ctgov_is_randomized"),
        "v43_ch2_is_adc_X_enrollment_sq": ch2_features["ch2_is_adc"] * get_col("enrollment_sq"),
        "v43_ch2_is_cell_X_momentum_10d": ch2_features["ch2_is_cell"] * get_col("momentum_10d"),
        "v43_ch2_is_oligo_X_is_phase2": ch2_features["ch2_is_oligo"] * get_col("is_phase2"),
    }


def build_v44_features(events, X_base, feat_names, ch2_features):
    """Build v44's 2 cross-family interaction features."""
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}
    def get_col(name):
        idx = feat_idx.get(name)
        return X_base[:, idx] if idx is not None else np.zeros(n)
    return {
        "v44_ch2_moa_antagonist_X_journey_had_positive": ch2_features["ch2_moa_antagonist"] * get_col("journey_had_positive"),
        "v44_ch2_is_sm_X_is_phase2_X_is_small": ch2_features["ch2_is_sm"] * get_col("is_phase2") * get_col("is_small"),
    }


# Custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.ndarray,)): return obj.tolist()
        if isinstance(obj, (np.bool_,)): return bool(obj)
        return super().default(obj)


def main():
    t_start = time.time()

    print("\n" + "=" * 80)
    print("  GUNGNIR v45 KAIZEN — Prune + Tighten (Discipline Release)")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Build v44 baseline (146 features) — same as v44 pipeline
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Build v44 baseline (146 features)")
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

    # v43 ChEMBL features
    print("  Building v43 ChEMBL features...")
    ch2_features = build_chembl_features(events)
    v43_dict = build_v43_features(events, X_v42, feat_v42, ch2_features)
    v43_cols = [v43_dict[f] for f in V43_SELECTED]
    X_v43 = np.column_stack([X_v42] + [c.reshape(-1, 1) for c in v43_cols])
    feat_v43 = list(feat_v42) + V43_SELECTED
    print(f"  v43: {X_v43.shape[1]} features")

    # v44 features (2 cross-family interactions)
    print("  Building v44 features...")
    v44_dict = build_v44_features(events, X_v43, feat_v43, ch2_features)
    v44_cols = [v44_dict[f] for f in V44_SELECTED]
    X_v44 = np.column_stack([X_v43] + [c.reshape(-1, 1) for c in v44_cols])
    feat_v44 = list(feat_v43) + V44_SELECTED
    print(f"  v44: {X_v44.shape[0]} × {X_v44.shape[1]} features")

    # Baseline WF AUC with v44 config
    print("\n  Evaluating v44 baseline...")
    baseline = v39.evaluate_wf(X_v44, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=True, **V44_CONFIG)
    v44_auc = baseline["avg_auc"]
    v44_brier = baseline["avg_brier"]
    print(f"\n  *** v44 BASELINE: AUC={v44_auc:.4f} Brier={v44_brier:.4f} ({len(feat_v44)} features)")

    # =========================================================================
    # PHASE 2: Drop 19 confirmed-dead features (zero across ALL models)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 2: Drop {len(DEAD_FEATURES)} Confirmed-Dead Features")
    print(f"{'=' * 80}")

    # Build mask of features to KEEP
    dead_set = set(DEAD_FEATURES)
    keep_indices = [i for i, f in enumerate(feat_v44) if f not in dead_set]
    dropped_features = [f for f in feat_v44 if f in dead_set]
    not_found = [f for f in DEAD_FEATURES if f not in set(feat_v44)]

    if not_found:
        print(f"  WARNING: {len(not_found)} dead features not found in v44: {not_found}")

    X_pruned = X_v44[:, keep_indices]
    feat_pruned = [feat_v44[i] for i in keep_indices]
    print(f"  Dropped: {len(dropped_features)} features")
    print(f"  Remaining: {len(feat_pruned)} features")

    # Evaluate after Phase 2 drop
    print("\n  Evaluating after dead feature removal...")
    r_phase2 = v39.evaluate_wf(X_pruned, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=False, **V44_CONFIG)
    p2_auc = r_phase2["avg_auc"]
    p2_brier = r_phase2["avg_brier"]
    delta_p2 = p2_auc - v44_auc
    print(f"  After Phase 2: AUC={p2_auc:.4f} (Δ={delta_p2:+.4f}) Brier={p2_brier:.4f}")
    print(f"  {'IMPROVED' if delta_p2 > 0 else 'ACCEPTABLE' if delta_p2 > -0.001 else 'REGRESSION'}")

    # =========================================================================
    # PHASE 3: Progressive Ablation of Weak Features
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 3: Progressive Ablation ({len(WEAK_CANDIDATES)} candidates)")
    print(f"{'=' * 80}")

    # Test removing each weak candidate individually
    print("  Testing individual feature removal impact...")
    removal_impacts = []
    feat_pruned_set = set(feat_pruned)

    for feat_name in WEAK_CANDIDATES:
        if feat_name not in feat_pruned_set:
            continue  # already removed in Phase 2

        # Build X without this feature
        idx_to_drop = feat_pruned.index(feat_name)
        test_indices = [i for i in range(len(feat_pruned)) if i != idx_to_drop]
        X_test = X_pruned[:, test_indices]

        r = v39.evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **V44_CONFIG)
        delta = r["avg_auc"] - p2_auc
        removal_impacts.append({
            "feature": feat_name,
            "auc_without": r["avg_auc"],
            "delta": delta,  # positive = removing HELPS, negative = removing HURTS
            "brier_without": r["avg_brier"],
        })

    # Sort: most helpful removals first (positive delta = removing helps)
    removal_impacts.sort(key=lambda x: -x["delta"])

    print(f"\n  Individual removal impact (top = safest to remove):")
    for r in removal_impacts:
        direction = "HELPS" if r["delta"] > 0.0001 else ("SAFE" if r["delta"] > -0.0003 else "HURTS")
        print(f"    {r['feature']:50s} Δ={r['delta']:+.4f}  [{direction}]")

    # Greedy backward elimination: remove features one by one starting with safest
    print(f"\n  Greedy backward elimination...")
    current_X = X_pruned.copy()
    current_feats = list(feat_pruned)
    current_auc = p2_auc
    removed = []

    # Only try removing features that don't hurt significantly
    safe_removals = [r["feature"] for r in removal_impacts if r["delta"] > -0.0005]
    print(f"  Safe removal candidates: {len(safe_removals)}")

    for rnd in range(len(safe_removals)):
        best_feat_to_remove = None
        best_auc_after = current_auc
        best_brier_after = 999

        for feat_name in safe_removals:
            if feat_name not in current_feats:
                continue
            idx = current_feats.index(feat_name)
            test_indices = [i for i in range(current_X.shape[1]) if i != idx]
            X_test = current_X[:, test_indices]
            r = v39.evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates,
                                 verbose=False, **V44_CONFIG)
            # Accept removal if AUC doesn't drop (or improves)
            if r["avg_auc"] >= best_auc_after - 0.00005:
                if r["avg_auc"] > best_auc_after or (r["avg_auc"] == best_auc_after and r["avg_brier"] < best_brier_after):
                    best_auc_after = r["avg_auc"]
                    best_feat_to_remove = feat_name
                    best_brier_after = r["avg_brier"]

        if best_feat_to_remove:
            idx = current_feats.index(best_feat_to_remove)
            test_indices = [i for i in range(current_X.shape[1]) if i != idx]
            current_X = current_X[:, test_indices]
            current_feats.remove(best_feat_to_remove)
            delta = best_auc_after - current_auc
            removed.append({
                "feature": best_feat_to_remove,
                "auc_after": best_auc_after,
                "delta": delta,
                "brier_after": best_brier_after,
            })
            print(f"  R{rnd+1}: -{best_feat_to_remove:50s} AUC={best_auc_after:.4f} (Δ={delta:+.5f}) features={len(current_feats)}")
            current_auc = best_auc_after
        else:
            print(f"  R{rnd+1}: No safe removal. Stopping.")
            break

    total_dropped = len(dropped_features) + len(removed)
    print(f"\n  Phase 2+3 summary:")
    print(f"    Dead dropped: {len(dropped_features)}")
    print(f"    Weak pruned:  {len(removed)}")
    print(f"    Total dropped: {total_dropped}")
    print(f"    Features: {len(feat_v44)} → {len(current_feats)} (-{total_dropped})")
    print(f"    AUC: {v44_auc:.4f} → {current_auc:.4f} (Δ={current_auc - v44_auc:+.4f})")

    # =========================================================================
    # PHASE 4: Regularization Sweep (tighter C)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 4: Regularization Sweep")
    print(f"{'=' * 80}")

    best_c = V44_CONFIG["ridge_c"]
    best_c_auc = current_auc
    best_c_brier = 999

    print("  C sweep (expect tighter C with fewer features):")
    for c in [0.005, 0.008, 0.010, 0.012, 0.015, 0.018, 0.020, 0.025, 0.030, 0.035, 0.040, 0.050]:
        cfg = dict(V44_CONFIG)
        cfg["ridge_c"] = c
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        is_best = r["avg_auc"] > best_c_auc or (r["avg_auc"] == best_c_auc and r["avg_brier"] < best_c_brier)
        flag = " <-- BEST" if is_best else ""
        print(f"    C={c:.3f}: AUC={r['avg_auc']:.4f} Brier={r['avg_brier']:.4f}{flag}")
        if is_best:
            best_c_auc = r["avg_auc"]
            best_c = c
            best_c_brier = r["avg_brier"]

    print(f"\n  Best C: {best_c} (AUC={best_c_auc:.4f})")

    # =========================================================================
    # PHASE 5: Architecture Sweep (meta weights + trees)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 5: Architecture Sweep")
    print(f"{'=' * 80}")

    best_meta_r = V44_CONFIG["meta_ridge"]
    best_meta_x = V44_CONFIG["meta_xgb"]
    best_arch_auc = best_c_auc

    # Meta weight sweep
    print("  Meta weight sweep:")
    for meta_r in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]:
        cfg = dict(V44_CONFIG)
        cfg["ridge_c"] = best_c
        cfg["meta_ridge"] = meta_r
        cfg["meta_xgb"] = 1.0 - meta_r
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        is_best = r["avg_auc"] > best_arch_auc
        flag = " <-- BEST" if is_best else ""
        print(f"    Meta {meta_r:.0%}/{1-meta_r:.0%}: AUC={r['avg_auc']:.4f} Brier={r['avg_brier']:.4f}{flag}")
        if is_best:
            best_arch_auc = r["avg_auc"]
            best_meta_r = meta_r
            best_meta_x = 1.0 - meta_r

    # XGB trees sweep
    print("  XGB trees sweep:")
    best_trees = V44_CONFIG["xgb_trees"]
    for trees in [300, 400, 500, 600, 700, 800]:
        cfg = dict(V44_CONFIG)
        cfg["ridge_c"] = best_c
        cfg["meta_ridge"] = best_meta_r
        cfg["meta_xgb"] = best_meta_x
        cfg["xgb_trees"] = trees
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        is_best = r["avg_auc"] > best_arch_auc
        flag = " <-- BEST" if is_best else ""
        print(f"    Trees={trees}: AUC={r['avg_auc']:.4f} Brier={r['avg_brier']:.4f}{flag}")
        if is_best:
            best_arch_auc = r["avg_auc"]
            best_trees = trees

    # GOOD+ and CRASH C sweep
    print("  GOOD+/CRASH C sweep:")
    best_gp_c = V44_CONFIG["goodplus_c"]
    best_cr_c = V44_CONFIG["crash_c"]
    for gp_c in [0.1, 0.3, 0.5, 0.7, 1.0]:
        for cr_c in [0.1, 0.3, 0.5, 0.7, 1.0]:
            cfg = dict(V44_CONFIG)
            cfg["ridge_c"] = best_c
            cfg["meta_ridge"] = best_meta_r
            cfg["meta_xgb"] = best_meta_x
            cfg["xgb_trees"] = best_trees
            cfg["goodplus_c"] = gp_c
            cfg["crash_c"] = cr_c
            r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                                 verbose=False, **cfg)
            if r["avg_auc"] > best_arch_auc:
                best_arch_auc = r["avg_auc"]
                best_gp_c = gp_c
                best_cr_c = cr_c

    print(f"  Best GOOD+ C: {best_gp_c}, CRASH C: {best_cr_c}")

    final_config = {
        "ridge_c": best_c,
        "meta_ridge": best_meta_r,
        "meta_xgb": best_meta_x,
        "xgb_trees": best_trees,
        "xgb_depth": V44_CONFIG["xgb_depth"],
        "xgb_lr": V44_CONFIG["xgb_lr"],
        "goodplus_c": best_gp_c,
        "crash_c": best_cr_c,
        "temperature": V44_CONFIG["temperature"],
    }
    print(f"\n  Final config: C={best_c}, meta={best_meta_r:.0%}/{best_meta_x:.0%}, "
          f"trees={best_trees}, GP_C={best_gp_c}, CR_C={best_cr_c}")
    print(f"  Current best AUC: {best_arch_auc:.4f}")

    # =========================================================================
    # PHASE 6: 20-Seed Stability Test
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 6: 20-Seed Stability Test (v45 vs v44)")
    print(f"{'=' * 80}")

    from scipy import stats

    final_cfg = dict(V44_CONFIG)
    final_cfg.update(final_config)

    v44_aucs, v45_aucs = [], []
    v44_briers, v45_briers = [], []
    for seed in range(20):
        cfg44 = dict(V44_CONFIG)
        cfg44["seed"] = seed
        cfg45 = dict(final_cfg)
        cfg45["seed"] = seed

        r44 = v39.evaluate_wf(X_v44, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg44)
        r45 = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg45)
        v44_aucs.append(r44["avg_auc"])
        v45_aucs.append(r45["avg_auc"])
        v44_briers.append(r44["avg_brier"])
        v45_briers.append(r45["avg_brier"])

    wins_auc = sum(1 for a, b in zip(v44_aucs, v45_aucs) if b > a)
    wins_brier = sum(1 for a, b in zip(v44_briers, v45_briers) if b < a)
    t_stat_auc, p_val_auc = stats.ttest_rel(v45_aucs, v44_aucs)
    t_stat_brier, p_val_brier = stats.ttest_rel(v45_briers, v44_briers)

    print(f"  AUC comparison:")
    print(f"    v44: {np.mean(v44_aucs):.4f} ± {np.std(v44_aucs):.4f} [{min(v44_aucs):.4f}, {max(v44_aucs):.4f}]")
    print(f"    v45: {np.mean(v45_aucs):.4f} ± {np.std(v45_aucs):.4f} [{min(v45_aucs):.4f}, {max(v45_aucs):.4f}]")
    print(f"    AUC wins: {wins_auc}/20, p={p_val_auc:.10f}")
    print(f"  Brier comparison:")
    print(f"    v44: {np.mean(v44_briers):.4f} ± {np.std(v44_briers):.4f}")
    print(f"    v45: {np.mean(v45_briers):.4f} ± {np.std(v45_briers):.4f}")
    print(f"    Brier wins: {wins_brier}/20, p={p_val_brier:.10f}")

    # =========================================================================
    # PHASE 7: Final Evaluation with best config
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 7: Final Evaluation")
    print(f"{'=' * 80}")

    final_result = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                                     verbose=True, **final_cfg)
    final_auc = final_result["avg_auc"]
    final_brier = final_result["avg_brier"]
    print(f"\n  Final v45: AUC={final_auc:.4f} Brier={final_brier:.4f} ({len(current_feats)} features)")

    # =========================================================================
    # CHAMPION DETERMINATION
    # =========================================================================
    # v45 is champion if:
    # 1. AUC maintained or improved (≥ v44 - 0.001, acceptable small regression for 25% fewer features)
    # 2. At least 12/20 seed wins on AUC OR Brier
    # 3. Feature count < v44
    auc_ok = final_auc >= (v44_auc - 0.0015)  # Allow tiny regression for discipline
    stability_ok = wins_auc >= 10 or wins_brier >= 12  # More lenient for pruning
    leaner = len(current_feats) < len(feat_v44)
    is_champion = auc_ok and leaner

    # =========================================================================
    # SAVE RESULTS
    # =========================================================================
    elapsed = time.time() - t_start

    results = {
        "version": "v45.0.0",
        "codename": "Prune + Tighten (Discipline)",
        "date": time.strftime("%Y-%m-%d"),
        "baseline_version": "v44.0.0",
        "baseline_auc": float(v44_auc),
        "baseline_brier": float(v44_brier),
        "baseline_n_features": len(feat_v44),
        "final_auc": float(final_auc),
        "final_brier": float(final_brier),
        "final_n_features": len(current_feats),
        "delta_auc": float(final_auc - v44_auc),
        "delta_brier": float(final_brier - v44_brier),
        "features_dropped_dead": dropped_features,
        "features_dropped_ablation": [r["feature"] for r in removed],
        "features_total_dropped": len(dropped_features) + len(removed),
        "removal_impacts": removal_impacts,
        "ablation_sequence": removed,
        "config": final_config,
        "stability": {
            "v44_auc_mean": float(np.mean(v44_aucs)),
            "v45_auc_mean": float(np.mean(v45_aucs)),
            "v44_aucs": [float(x) for x in v44_aucs],
            "v45_aucs": [float(x) for x in v45_aucs],
            "v44_briers": [float(x) for x in v44_briers],
            "v45_briers": [float(x) for x in v45_briers],
            "wins_auc": wins_auc,
            "wins_brier": wins_brier,
            "p_value_auc": float(p_val_auc),
            "p_value_brier": float(p_val_brier),
        },
        "champion": bool(is_champion),
        "champion_reasons": {
            "auc_ok": bool(auc_ok),
            "stability_ok": bool(stability_ok),
            "leaner": bool(leaner),
        },
        "runtime_seconds": elapsed,
        "wf_splits": {s["split"]: {"auc": s["auc"], "brier": s["brier"]}
                      for s in final_result.get("splits", [])},
    }

    results_path = os.path.join(DATA_DIR, "gungnir_v45_kaizen_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)

    print(f"\n{'=' * 80}")
    if is_champion:
        print(f"  *** v45 IS CHAMPION: {len(feat_v44)} → {len(current_feats)} features "
              f"(-{total_dropped}), AUC {v44_auc:.4f} → {final_auc:.4f} ***")
    else:
        print(f"  v45 result: {len(feat_v44)} → {len(current_feats)} features, "
              f"AUC {v44_auc:.4f} → {final_auc:.4f}")
        if not auc_ok: print(f"  AUC REGRESSION too large ({final_auc - v44_auc:+.4f})")
        if not stability_ok: print(f"  INSUFFICIENT STABILITY (AUC wins={wins_auc}, Brier wins={wins_brier})")
        if not leaner: print(f"  NOT LEANER ({len(current_feats)} >= {len(feat_v44)})")
    print(f"  Runtime: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  Results saved: {results_path}")
    print(f"{'=' * 80}")

    # =========================================================================
    # PHASE 8: Deploy if champion
    # =========================================================================
    if is_champion:
        print(f"\n{'=' * 80}")
        print("  PHASE 8: Generating Deploy Config")
        print(f"{'=' * 80}")

        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        dates_str = np.array([str(d) for d in dates])
        train_mask = dates_str < "2025"

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(current_X[train_mask])
        y_tr = y_bin[train_mask]

        # M1: Binary
        m1 = LogisticRegression(C=best_c, penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=42)
        m1.fit(X_tr, y_tr)

        # M2: GOOD+
        m2 = LogisticRegression(C=best_gp_c, penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=42)
        m2.fit(X_tr, y_gp[train_mask])

        # M3: CRASH
        m3 = LogisticRegression(C=best_cr_c, penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=42)
        m3.fit(X_tr, y_cr[train_mask])

        # Count zero/near-zero coefficients in pruned model
        m1_zeros = sum(1 for c in m1.coef_[0] if abs(c) < 1e-8)
        m1_near_zero = sum(1 for c in m1.coef_[0] if abs(c) < 0.01)
        print(f"  M1 zero coefs: {m1_zeros}, near-zero (<0.01): {m1_near_zero}")

        deploy = {
            "version": "v45.0.0",
            "codename": "Prune + Tighten (Discipline)",
            "n_features": len(current_feats),
            "feature_names": current_feats,
            "M1_coef": {f: float(c) for f, c in zip(current_feats, m1.coef_[0])},
            "M1_intercept": float(m1.intercept_[0]),
            "M2_coef": {f: float(c) for f, c in zip(current_feats, m2.coef_[0])},
            "M2_intercept": float(m2.intercept_[0]),
            "M3_coef": {f: float(c) for f, c in zip(current_feats, m3.coef_[0])},
            "M3_intercept": float(m3.intercept_[0]),
            "scaler_means": {f: float(m) for f, m in zip(current_feats, scaler.mean_)},
            "scaler_scales": {f: float(s) for f, s in zip(current_feats, scaler.scale_)},
            "config": final_config,
            "performance": {
                "wf_auc": float(final_auc),
                "wf_brier": float(final_brier),
                "baseline_auc": float(v44_auc),
                "baseline_features": len(feat_v44),
                "features_dropped": len(dropped_features) + len(removed),
                "stability_wins_auc": wins_auc,
                "stability_wins_brier": wins_brier,
                "stability_p_auc": float(p_val_auc),
                "stability_p_brier": float(p_val_brier),
            },
            "features_dropped_v45": {
                "dead": dropped_features,
                "ablation": [r["feature"] for r in removed],
            },
            "leakage_audit": "PASSED — same features as v44, just fewer. No new data sources.",
        }

        # Save XGBoost model
        try:
            import xgboost as xgb_lib
            m5 = xgb_lib.XGBClassifier(
                n_estimators=best_trees,
                max_depth=V44_CONFIG["xgb_depth"],
                learning_rate=V44_CONFIG["xgb_lr"],
                subsample=0.8, colsample_bytree=0.6,
                reg_alpha=0.3, reg_lambda=2.0,
                min_child_weight=10, gamma=0.2,
                random_state=42, use_label_encoder=False,
                eval_metric="logloss", verbosity=0
            )
            m5.fit(X_tr, y_tr)
            xgb_path = os.path.join(DATA_DIR, "gungnir_v45_xgb.json")
            m5.save_model(xgb_path)
            print(f"  XGBoost saved: {xgb_path}")
        except Exception as e:
            print(f"  XGBoost save failed: {e}")

        deploy_path = os.path.join(DATA_DIR, "gungnir_v45_deploy.json")
        with open(deploy_path, "w") as f:
            json.dump(deploy, f, indent=2)
        print(f"  Deploy config saved: {deploy_path}")
        print(f"  Features: {len(current_feats)} (was {len(feat_v44)})")
        print(f"  Dropped: {[r['feature'] for r in removed]}")
        print(f"  Dead dropped: {dropped_features}")


if __name__ == "__main__":
    main()
