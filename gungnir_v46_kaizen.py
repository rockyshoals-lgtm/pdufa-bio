#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v46 KAIZEN — New Feature Mining Post-Prune
================================================================================

APPROACH:
  Start from v45.0.0 as baseline (AUC 0.8083, 118 features, 15:1 ratio)

  v45 PRUNE cleaned the model — 28 features removed, AUC IMPROVED.
  Now we have room to add carefully selected NEW features.

  v46 STRATEGY: Systematic feature mining across 6 pillars:
    PILLAR 1: ChEMBL base features (standalone modality/MOA/FIC)
    PILLAR 2: ChEMBL × journey interactions
    PILLAR 3: ChEMBL × trial design interactions
    PILLAR 4: TA × modality cross-family
    PILLAR 5: Non-linear transforms of strong features
    PILLAR 6: Three-way interactions (top features × top features × top features)

  PIPELINE:
    1. BUILD v45 baseline (reuse v45 pipeline)
    2. GENERATE all candidate features from 6 pillars
    3. FAST SCREEN — individual Ridge-only AUC on each candidate (filter >0.0000)
    4. FULL WF EVAL — top candidates through full 3-model ensemble
    5. GREEDY FORWARD SELECTION — add features one at a time if they help
    6. REGULARIZATION + ARCHITECTURE SWEEP
    7. 20-SEED STABILITY vs v45
    8. DEPLOY if champion

  TARGET: 118-135 features, AUC > 0.8083

  T-1 COMPLIANCE: All new features are products/transforms of existing
  pre-readout features. No new data sources.
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
# v45 CONFIG (champion baseline)
# ============================================================================
V45_CONFIG = {
    "ridge_c": 0.02, "xgb_lr": 0.01, "xgb_trees": 600, "xgb_depth": 3,
    "meta_ridge": 0.90, "meta_xgb": 0.10, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# ============================================================================
# v45 DEAD + ABLATION features to exclude
# ============================================================================
V45_DEAD = [
    "btd_x_phase3", "cat_conference", "cat_full_results", "cat_initial",
    "cat_interim", "cat_regulatory", "cat_submission", "cat_topline",
    "ctgov_has_withdrawals", "has_btd", "has_fast_track", "has_priority_review",
    "hist_loa", "hist_pop", "ind_maturity_high", "journey_had_prior_negative",
    "journey_had_prior_positive", "journey_pos_x_phase3", "journey_streak_x_small",
]
V45_ABLATION = [
    "ta_ophthalmology", "journey_n_positive", "combo_x_onc",
    "journey_n_prior", "nlp_dose_response", "indication_density",
    "momentum_x_micro", "journey_positive_streak", "desig_x_small",
]
V45_DROPPED = set(V45_DEAD + V45_ABLATION)

# ============================================================================
# VERSION-SPECIFIC SELECTED FEATURES (same as v45/v44)
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

# Conference helpers (same as v45)
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
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}
    def get_col(name):
        idx = feat_idx.get(name)
        return X_base[:, idx] if idx is not None else np.zeros(n)
    return {
        "v44_ch2_moa_antagonist_X_journey_had_positive": ch2_features["ch2_moa_antagonist"] * get_col("journey_had_positive"),
        "v44_ch2_is_sm_X_is_phase2_X_is_small": ch2_features["ch2_is_sm"] * get_col("is_phase2") * get_col("is_small"),
    }


# ============================================================================
# v46 NEW: Candidate Feature Generation
# ============================================================================
def generate_v46_candidates(events, X_base, feat_names, ch2_features, v40_lookup):
    """Generate ALL candidate features across 6 pillars."""
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_names)}

    def get_col(name):
        idx = feat_idx.get(name)
        return X_base[:, idx] if idx is not None else np.zeros(n)

    def get_v40_col(v40_name):
        return np.array([float(v40_lookup.get(
            (ev.get("ticker", "").upper(), ev.get("date", "")), {}).get(v40_name, 0) or 0)
            for ev in events])

    candidates = {}

    # ==== PILLAR 1: ChEMBL base features (standalone) ====
    # These were built but never tested individually
    p1_bases = [
        "ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_biologic",
        "ch2_is_cell", "ch2_is_gene", "ch2_is_oligo", "ch2_is_advanced",
        "ch2_is_peptide", "ch2_moa_inhibitor", "ch2_moa_agonist",
        "ch2_moa_antagonist", "ch2_first_in_class", "ch2_has_prior_approval",
        "ch2_is_combo",
    ]
    for fname in p1_bases:
        arr = ch2_features.get(fname, np.zeros(n))
        nonzero = np.count_nonzero(arr)
        if nonzero >= 15:  # min sparsity threshold
            candidates[f"v46_p1_{fname}"] = arr

    # ==== PILLAR 2: ChEMBL × journey interactions ====
    journey_cols = [
        "journey_success_rate", "journey_had_positive", "journey_had_negative",
        "journey_last_positive", "journey_n_negative",
    ]
    modality_cols = [
        "ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_biologic",
        "ch2_is_cell", "ch2_is_gene", "ch2_is_oligo", "ch2_is_advanced",
        "ch2_moa_inhibitor",
    ]
    for mod in modality_cols:
        mod_arr = ch2_features.get(mod, np.zeros(n))
        if np.count_nonzero(mod_arr) < 15:
            continue
        for jcol in journey_cols:
            j_arr = get_col(jcol)
            prod = mod_arr * j_arr
            if np.count_nonzero(prod) >= 10:
                name = f"v46_p2_{mod}_X_{jcol}"
                # Skip if already in v44
                if name not in ["v44_ch2_moa_antagonist_X_journey_had_positive"]:
                    candidates[name] = prod

    # ==== PILLAR 3: ChEMBL × trial design interactions ====
    trial_design_cols = [
        "ctgov_is_randomized", "ctgov_is_placebo", "ctgov_is_double_blind",
        "ctgov_has_dmc", "ctgov_enrollment", "ctgov_masking_rigor",
        "ct_ep_is_safety", "ct_ep_is_biomarker", "ct_has_combination",
        "ct_active_comp_x_phase3",
    ]
    for mod in ["ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_advanced",
                "ch2_moa_inhibitor", "ch2_first_in_class", "ch2_is_combo"]:
        mod_arr = ch2_features.get(mod, np.zeros(n))
        if np.count_nonzero(mod_arr) < 15:
            continue
        for tcol in trial_design_cols:
            t_arr = get_col(tcol)
            prod = mod_arr * t_arr
            if np.count_nonzero(prod) >= 10:
                # Skip if already in v43
                name = f"v46_p3_{mod}_X_{tcol}"
                candidates[name] = prod

    # ==== PILLAR 4: TA × modality cross-family ====
    ta_cols = [
        "ta_oncology", "ta_cns", "ta_immunology", "ta_rare_disease",
        "ta_hematology", "ta_metabolic", "ta_infectious", "ta_cardiovascular",
    ]
    for ta in ta_cols:
        ta_arr = get_col(ta)
        if np.count_nonzero(ta_arr) < 15:
            continue
        for mod in ["ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_biologic",
                    "ch2_is_advanced", "ch2_moa_inhibitor"]:
            mod_arr = ch2_features.get(mod, np.zeros(n))
            if np.count_nonzero(mod_arr) < 15:
                continue
            prod = ta_arr * mod_arr
            if np.count_nonzero(prod) >= 10:
                candidates[f"v46_p4_{ta}_X_{mod}"] = prod

    # ==== PILLAR 5: Non-linear transforms of strong features ====
    # Transform strong continuous features
    strong_continuous = [
        "sponsor_success_rate", "journey_success_rate", "journey_last_positive",
        "ctgov_enrollment", "ctgov_n_countries", "ctgov_n_sites",
        "volatility_20d", "momentum_20d", "indication_density_sq",
        "v40_days_to_cover", "competitive_3mo",
    ]
    for feat in strong_continuous:
        arr = get_col(feat) if feat not in ["v40_days_to_cover"] else get_v40_col(feat)
        # Squared
        sq = arr ** 2
        if np.any(sq != 0) and np.any(sq != arr):  # not all 0 or 1
            candidates[f"v46_p5_{feat}_sq"] = sq
        # Log(1+x) for positive features
        if np.all(arr >= 0) and np.any(arr > 0):
            lg = np.log1p(arr)
            if np.std(lg) > 0.01:
                candidates[f"v46_p5_log1p_{feat}"] = lg
        # Cubed for features with known non-linear effects
        if feat in ["sponsor_success_rate", "journey_success_rate", "volatility_20d"]:
            cube = arr ** 3
            if np.any(cube != 0):
                candidates[f"v46_p5_{feat}_cubed"] = cube

    # ==== PILLAR 6: Three-way interactions (top features) ====
    # Conference × modality × size
    conf_arr = get_v40_col("v40_has_conference")
    for mod in ["ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_advanced"]:
        mod_arr = ch2_features.get(mod, np.zeros(n))
        for sz in ["is_micro", "is_small"]:
            sz_arr = get_col(sz)
            prod = conf_arr * mod_arr * sz_arr
            if np.count_nonzero(prod) >= 5:
                candidates[f"v46_p6_conf_X_{mod}_X_{sz}"] = prod

    # Phase × modality × sponsor
    spon_arr = get_col("sponsor_success_rate")
    for mod in ["ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_advanced"]:
        mod_arr = ch2_features.get(mod, np.zeros(n))
        for ph in ["is_phase2", "is_phase3"]:
            ph_arr = get_col(ph)
            prod = spon_arr * mod_arr * ph_arr
            if np.count_nonzero(prod) >= 10:
                candidates[f"v46_p6_sponsor_X_{mod}_X_{ph}"] = prod

    # Journey × modality × phase
    jsr_arr = get_col("journey_success_rate")
    for mod in ["ch2_is_sm", "ch2_is_mab", "ch2_is_biologic"]:
        mod_arr = ch2_features.get(mod, np.zeros(n))
        for ph in ["is_phase2", "is_phase3"]:
            ph_arr = get_col(ph)
            prod = jsr_arr * mod_arr * ph_arr
            if np.count_nonzero(prod) >= 10:
                candidates[f"v46_p6_journey_X_{mod}_X_{ph}"] = prod

    # Interim × modality
    interim_arr = get_col("iis_is_interim")
    for mod in ["ch2_is_sm", "ch2_is_mab", "ch2_is_biologic", "ch2_is_advanced"]:
        mod_arr = ch2_features.get(mod, np.zeros(n))
        prod = interim_arr * mod_arr
        if np.count_nonzero(prod) >= 5:
            candidates[f"v46_p6_interim_X_{mod}"] = prod

    # First-in-class × phase × sponsor
    fic_arr = ch2_features.get("ch2_first_in_class", np.zeros(n))
    for ph in ["is_phase2", "is_phase3"]:
        ph_arr = get_col(ph)
        prod = fic_arr * ph_arr * spon_arr
        if np.count_nonzero(prod) >= 5:
            candidates[f"v46_p6_fic_X_{ph}_X_sponsor"] = prod
        # FIC × phase × journey
        prod2 = fic_arr * ph_arr * jsr_arr
        if np.count_nonzero(prod2) >= 5:
            candidates[f"v46_p6_fic_X_{ph}_X_journey"] = prod2

    return candidates


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
    print("  GUNGNIR v46 KAIZEN — New Feature Mining Post-Prune")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Build v45 baseline (118 features)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Build v45 baseline (118 features)")
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
    print(f"  v39.1: {X_v39.shape[0]} x {X_v39.shape[1]}")

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

    # v41
    print("  Building v41 features...")
    v41_dict = build_v41_features(events, X_v40, feat_v40, v40_lookup)
    v41_cols = [v41_dict[f] for f in V41_SELECTED]
    X_v41 = np.column_stack([X_v40] + [c.reshape(-1, 1) for c in v41_cols])
    feat_v41 = list(feat_v40) + V41_SELECTED

    # v42
    print("  Building v42 features...")
    v42_dict = build_v42_features(events, X_v41, feat_v41)
    v42_cols = [v42_dict[f] for f in V42_SELECTED]
    X_v42 = np.column_stack([X_v41] + [c.reshape(-1, 1) for c in v42_cols])
    feat_v42 = list(feat_v41) + V42_SELECTED

    # v43
    print("  Building v43 ChEMBL features...")
    ch2_features = build_chembl_features(events)
    v43_dict = build_v43_features(events, X_v42, feat_v42, ch2_features)
    v43_cols = [v43_dict[f] for f in V43_SELECTED]
    X_v43 = np.column_stack([X_v42] + [c.reshape(-1, 1) for c in v43_cols])
    feat_v43 = list(feat_v42) + V43_SELECTED

    # v44
    print("  Building v44 features...")
    v44_dict = build_v44_features(events, X_v43, feat_v43, ch2_features)
    v44_cols = [v44_dict[f] for f in V44_SELECTED]
    X_v44 = np.column_stack([X_v43] + [c.reshape(-1, 1) for c in v44_cols])
    feat_v44 = list(feat_v43) + V44_SELECTED
    print(f"  v44: {X_v44.shape[0]} x {X_v44.shape[1]} features")

    # Apply v45 pruning (remove 28 features)
    print("  Applying v45 pruning (removing 28 features)...")
    keep_indices = [i for i, f in enumerate(feat_v44) if f not in V45_DROPPED]
    X_v45 = X_v44[:, keep_indices]
    feat_v45 = [feat_v44[i] for i in keep_indices]
    print(f"  v45: {X_v45.shape[0]} x {X_v45.shape[1]} features")

    # v45 baseline
    print("\n  Evaluating v45 baseline...")
    baseline = v39.evaluate_wf(X_v45, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=True, **V45_CONFIG)
    v45_auc = baseline["avg_auc"]
    v45_brier = baseline["avg_brier"]
    print(f"\n  *** v45 BASELINE: AUC={v45_auc:.4f} Brier={v45_brier:.4f} ({len(feat_v45)} features)")

    # =========================================================================
    # PHASE 2: Generate candidate features (6 pillars)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 2: Generate Candidate Features (6 Pillars)")
    print(f"{'=' * 80}")

    candidates = generate_v46_candidates(events, X_v45, feat_v45, ch2_features, v40_lookup)

    # Count per pillar
    pillar_counts = defaultdict(int)
    for name in candidates:
        pillar = name.split("_")[1]  # v46_p1, v46_p2, etc.
        pillar_counts[pillar] += 1
    print(f"\n  Total candidates: {len(candidates)}")
    for p, c in sorted(pillar_counts.items()):
        pnames = {"p1": "ChEMBL Base", "p2": "ChEMBL×Journey", "p3": "ChEMBL×Trial",
                  "p4": "TA×Modality", "p5": "Non-linear", "p6": "Three-way"}
        print(f"    {pnames.get(p, p)}: {c}")

    # =========================================================================
    # PHASE 3: Fast Screen — Ridge-only individual AUC lift
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 3: Fast Screen (Ridge-only individual AUC)")
    print(f"{'=' * 80}")

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    # Simple temporal split for fast screening
    dates_arr = np.array(dates)
    train_mask = dates_arr < "2024-07-01"
    test_mask = dates_arr >= "2024-07-01"
    X_train_base = X_v45[train_mask]
    X_test_base = X_v45[test_mask]
    y_train = y_bin[train_mask]
    y_test = y_bin[test_mask]

    # Baseline ridge
    scaler_base = StandardScaler()
    X_tr_s = scaler_base.fit_transform(X_train_base)
    X_te_s = scaler_base.transform(X_test_base)
    lr_base = LogisticRegression(C=V45_CONFIG["ridge_c"], penalty='l2', solver='lbfgs', max_iter=2000)
    lr_base.fit(X_tr_s, y_train)
    base_fast_auc = roc_auc_score(y_test, lr_base.predict_proba(X_te_s)[:, 1])
    print(f"  Fast baseline AUC: {base_fast_auc:.4f}")

    # Screen each candidate
    screen_results = []
    for i, (name, col) in enumerate(candidates.items()):
        if i % 50 == 0 and i > 0:
            print(f"  ...screened {i}/{len(candidates)}")

        # Add candidate column to base
        X_train_aug = np.column_stack([X_train_base, col[train_mask].reshape(-1, 1)])
        X_test_aug = np.column_stack([X_test_base, col[test_mask].reshape(-1, 1)])

        scaler = StandardScaler()
        X_tr_s2 = scaler.fit_transform(X_train_aug)
        X_te_s2 = scaler.transform(X_test_aug)

        lr = LogisticRegression(C=V45_CONFIG["ridge_c"], penalty='l2', solver='lbfgs', max_iter=2000)
        lr.fit(X_tr_s2, y_train)
        fast_auc = roc_auc_score(y_test, lr.predict_proba(X_te_s2)[:, 1])
        delta = fast_auc - base_fast_auc

        screen_results.append({
            "name": name,
            "fast_auc": fast_auc,
            "delta": delta,
            "nonzero": int(np.count_nonzero(col)),
        })

    # Sort by delta descending
    screen_results.sort(key=lambda x: -x["delta"])

    n_positive = sum(1 for r in screen_results if r["delta"] > 0)
    n_strong = sum(1 for r in screen_results if r["delta"] > 0.001)
    print(f"\n  Screen complete: {n_positive}/{len(screen_results)} positive, {n_strong} strong (>0.001)")
    print(f"\n  Top 30 candidates:")
    for r in screen_results[:30]:
        flag = "STRONG" if r["delta"] > 0.001 else ("PASS" if r["delta"] > 0 else "FAIL")
        print(f"    {r['name']:60s} Δ={r['delta']:+.4f} nz={r['nonzero']:4d} [{flag}]")

    # =========================================================================
    # PHASE 4: Full WF Eval on top candidates + Greedy Forward Selection
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 4: Full WF Eval + Greedy Forward Selection")
    print(f"{'=' * 80}")

    # Take top N candidates (positive delta on fast screen)
    TOP_N = min(40, n_positive)
    top_candidates = [(r["name"], candidates[r["name"]]) for r in screen_results[:TOP_N] if r["delta"] > 0]
    print(f"  Testing {len(top_candidates)} candidates through full WF pipeline")

    # Full WF eval on each individually
    full_results = []
    for i, (name, col) in enumerate(top_candidates):
        X_aug = np.column_stack([X_v45, col.reshape(-1, 1)])
        feat_aug = list(feat_v45) + [name]
        r = v39.evaluate_wf(X_aug, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **V45_CONFIG)
        delta = r["avg_auc"] - v45_auc
        full_results.append({
            "name": name,
            "wf_auc": r["avg_auc"],
            "wf_brier": r["avg_brier"],
            "delta": delta,
        })
        flag = "PASS" if delta > 0 else "FLAT" if delta > -0.0005 else "HURT"
        print(f"    [{i+1:2d}/{len(top_candidates)}] {name:60s} AUC={r['avg_auc']:.4f} Δ={delta:+.4f} [{flag}]")

    full_results.sort(key=lambda x: -x["delta"])
    n_pass = sum(1 for r in full_results if r["delta"] > 0)
    print(f"\n  Full WF: {n_pass}/{len(full_results)} positive")

    if n_pass == 0:
        print("\n  NO candidates pass full WF eval. v45 remains champion.")
        results = {
            "version": "v46.0.0",
            "codename": "New Feature Mining Post-Prune",
            "date": "2026-04-09",
            "baseline_version": "v45.0.0",
            "baseline_auc": v45_auc,
            "baseline_brier": v45_brier,
            "final_auc": v45_auc,
            "champion": False,
            "reason": "No candidates passed full WF eval",
            "candidates_screened": len(candidates),
            "candidates_fast_positive": n_positive,
            "candidates_full_positive": 0,
            "runtime_seconds": time.time() - t_start,
        }
        out_path = os.path.join(DATA_DIR, "gungnir_v46_kaizen_results.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, cls=NumpyEncoder)
        print(f"  Results saved to {out_path}")
        return

    # Greedy forward selection
    print(f"\n  Greedy forward selection from {n_pass} positive candidates...")
    passing = [r for r in full_results if r["delta"] > 0]
    current_X = X_v45.copy()
    current_feats = list(feat_v45)
    current_auc = v45_auc
    current_brier = v45_brier
    selected = []

    for rnd in range(len(passing)):
        best_name = None
        best_auc = current_auc
        best_brier = 999
        best_col = None

        for r in passing:
            name = r["name"]
            if name in [s["name"] for s in selected]:
                continue
            col = candidates[name]
            X_aug = np.column_stack([current_X, col.reshape(-1, 1)])
            feat_aug = current_feats + [name]
            ev = v39.evaluate_wf(X_aug, y_bin, y_gp, y_cr, y_ret, dates,
                                  verbose=False, **V45_CONFIG)
            if ev["avg_auc"] > best_auc or (ev["avg_auc"] == best_auc and ev["avg_brier"] < best_brier):
                best_auc = ev["avg_auc"]
                best_brier = ev["avg_brier"]
                best_name = name
                best_col = col

        if best_name and best_auc > current_auc - 0.00005:
            current_X = np.column_stack([current_X, best_col.reshape(-1, 1)])
            current_feats.append(best_name)
            delta = best_auc - current_auc
            selected.append({"name": best_name, "auc_after": best_auc, "delta": delta, "brier_after": best_brier})
            print(f"  G{rnd+1}: +{best_name:60s} AUC={best_auc:.4f} (Δ={delta:+.5f}) features={len(current_feats)}")
            current_auc = best_auc
            current_brier = best_brier
        else:
            print(f"  G{rnd+1}: No improvement. Stopping.")
            break

    total_new = len(selected)
    print(f"\n  Greedy selection added {total_new} features")
    print(f"  Features: {len(feat_v45)} → {len(current_feats)} (+{total_new})")
    print(f"  AUC: {v45_auc:.4f} → {current_auc:.4f} (Δ={current_auc - v45_auc:+.4f})")

    # =========================================================================
    # PHASE 5: Regularization + Architecture Sweep
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 5: Regularization + Architecture Sweep")
    print(f"{'=' * 80}")

    best_c = V45_CONFIG["ridge_c"]
    best_c_auc = current_auc

    print("  C sweep:")
    for c in [0.008, 0.010, 0.012, 0.015, 0.018, 0.020, 0.025, 0.030, 0.035, 0.040, 0.050]:
        cfg = dict(V45_CONFIG)
        cfg["ridge_c"] = c
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        is_best = r["avg_auc"] > best_c_auc
        flag = " <-- BEST" if is_best else ""
        print(f"    C={c:.3f}: AUC={r['avg_auc']:.4f} Brier={r['avg_brier']:.4f}{flag}")
        if is_best:
            best_c_auc = r["avg_auc"]
            best_c = c

    print(f"  Best C: {best_c} (AUC={best_c_auc:.4f})")

    # Meta weight sweep
    best_meta_r = V45_CONFIG["meta_ridge"]
    best_meta_x = V45_CONFIG["meta_xgb"]
    best_arch_auc = best_c_auc

    print("  Meta weight sweep:")
    for meta_r in [0.80, 0.85, 0.90, 0.95, 1.00]:
        cfg = dict(V45_CONFIG)
        cfg["ridge_c"] = best_c
        cfg["meta_ridge"] = meta_r
        cfg["meta_xgb"] = round(1.0 - meta_r, 2)
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        is_best = r["avg_auc"] > best_arch_auc
        flag = " <-- BEST" if is_best else ""
        print(f"    Meta {meta_r:.0%}/{1-meta_r:.0%}: AUC={r['avg_auc']:.4f} Brier={r['avg_brier']:.4f}{flag}")
        if is_best:
            best_arch_auc = r["avg_auc"]
            best_meta_r = meta_r
            best_meta_x = round(1.0 - meta_r, 2)

    # XGB trees sweep
    best_trees = V45_CONFIG["xgb_trees"]
    print("  XGB trees sweep:")
    for trees in [400, 500, 600, 700, 800]:
        cfg = dict(V45_CONFIG)
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

    # GOODPLUS/CRASH C sweep
    best_gp_c = V45_CONFIG["goodplus_c"]
    best_cr_c = V45_CONFIG["crash_c"]
    print("  GOODPLUS/CRASH C sweep:")
    for gp_c, cr_c in [(0.3, 0.2), (0.5, 0.3), (0.5, 0.5), (0.7, 0.3), (1.0, 0.5)]:
        cfg = dict(V45_CONFIG)
        cfg["ridge_c"] = best_c
        cfg["meta_ridge"] = best_meta_r
        cfg["meta_xgb"] = best_meta_x
        cfg["xgb_trees"] = best_trees
        cfg["goodplus_c"] = gp_c
        cfg["crash_c"] = cr_c
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        is_best = r["avg_auc"] > best_arch_auc
        flag = " <-- BEST" if is_best else ""
        print(f"    GP_C={gp_c} CR_C={cr_c}: AUC={r['avg_auc']:.4f} Brier={r['avg_brier']:.4f}{flag}")
        if is_best:
            best_arch_auc = r["avg_auc"]
            best_gp_c = gp_c
            best_cr_c = cr_c

    final_config = dict(V45_CONFIG)
    final_config["ridge_c"] = best_c
    final_config["meta_ridge"] = best_meta_r
    final_config["meta_xgb"] = best_meta_x
    final_config["xgb_trees"] = best_trees
    final_config["goodplus_c"] = best_gp_c
    final_config["crash_c"] = best_cr_c

    print(f"\n  Final config: C={best_c}, meta {best_meta_r:.0%}/{best_meta_x:.0%}, "
          f"trees={best_trees}, GP_C={best_gp_c}, CR_C={best_cr_c}")

    # Final evaluation with best config
    print("\n  Final evaluation with best config...")
    final_eval = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                                  verbose=True, **final_config)
    final_auc = final_eval["avg_auc"]
    final_brier = final_eval["avg_brier"]
    print(f"\n  *** v46 FINAL: AUC={final_auc:.4f} Brier={final_brier:.4f} ({len(current_feats)} features)")
    print(f"  *** vs v45:    AUC Δ={final_auc - v45_auc:+.4f} Brier Δ={final_brier - v45_brier:+.4f}")

    # =========================================================================
    # PHASE 6: 20-Seed Stability Test
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 6: 20-Seed Stability Test")
    print(f"{'=' * 80}")

    v45_aucs = []
    v46_aucs = []
    v45_briers = []
    v46_briers = []

    for seed in range(20):
        cfg45 = dict(V45_CONFIG)
        cfg45["seed"] = seed + 100
        r45 = v39.evaluate_wf(X_v45, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg45)
        v45_aucs.append(r45["avg_auc"])
        v45_briers.append(r45["avg_brier"])

        cfg46 = dict(final_config)
        cfg46["seed"] = seed + 100
        r46 = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg46)
        v46_aucs.append(r46["avg_auc"])
        v46_briers.append(r46["avg_brier"])

        auc_win = "v46" if r46["avg_auc"] > r45["avg_auc"] else "v45"
        brier_win = "v46" if r46["avg_brier"] < r45["avg_brier"] else "v45"
        print(f"  Seed {seed+100}: v45 AUC={r45['avg_auc']:.4f} vs v46 AUC={r46['avg_auc']:.4f} [{auc_win}] "
              f"| v45 Brier={r45['avg_brier']:.4f} vs v46 Brier={r46['avg_brier']:.4f} [{brier_win}]")

    wins_auc = sum(1 for a45, a46 in zip(v45_aucs, v46_aucs) if a46 > a45)
    wins_brier = sum(1 for b45, b46 in zip(v45_briers, v46_briers) if b46 < b45)

    # Paired t-test
    from scipy import stats
    t_auc, p_auc = stats.ttest_rel(v46_aucs, v45_aucs)
    t_brier, p_brier = stats.ttest_rel(v46_briers, v45_briers)

    print(f"\n  AUC:   v45 mean={np.mean(v45_aucs):.4f} vs v46 mean={np.mean(v46_aucs):.4f}")
    print(f"         v46 wins {wins_auc}/20, p={p_auc:.10f}")
    print(f"  Brier: v45 mean={np.mean(v45_briers):.4f} vs v46 mean={np.mean(v46_briers):.4f}")
    print(f"         v46 wins {wins_brier}/20, p={p_brier:.10f}")

    # =========================================================================
    # PHASE 7: Champion Decision + Deploy
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 7: Champion Decision")
    print(f"{'=' * 80}")

    auc_ok = final_auc >= v45_auc - 0.0015
    stability_ok = wins_auc >= 10 or wins_brier >= 12
    improvement = final_auc > v45_auc
    is_champion = auc_ok and stability_ok and improvement

    print(f"  AUC improvement: {final_auc:.4f} vs {v45_auc:.4f} (Δ={final_auc - v45_auc:+.4f}) {'PASS' if improvement else 'FAIL'}")
    print(f"  Stability: AUC wins={wins_auc}/20, Brier wins={wins_brier}/20 {'PASS' if stability_ok else 'FAIL'}")
    print(f"  CHAMPION: {'YES' if is_champion else 'NO'}")

    # Save results
    results = {
        "version": "v46.0.0",
        "codename": "New Feature Mining Post-Prune",
        "date": "2026-04-09",
        "baseline_version": "v45.0.0",
        "baseline_auc": v45_auc,
        "baseline_brier": v45_brier,
        "baseline_n_features": len(feat_v45),
        "final_auc": final_auc,
        "final_brier": final_brier,
        "final_n_features": len(current_feats),
        "delta_auc": final_auc - v45_auc,
        "delta_brier": final_brier - v45_brier,
        "candidates_generated": len(candidates),
        "candidates_fast_positive": n_positive,
        "candidates_full_positive": n_pass,
        "features_selected": [s["name"] for s in selected],
        "selection_sequence": selected,
        "config": final_config,
        "stability": {
            "v45_auc_mean": float(np.mean(v45_aucs)),
            "v46_auc_mean": float(np.mean(v46_aucs)),
            "v45_aucs": v45_aucs,
            "v46_aucs": v46_aucs,
            "v45_briers": v45_briers,
            "v46_briers": v46_briers,
            "wins_auc": wins_auc,
            "wins_brier": wins_brier,
            "p_value_auc": float(p_auc),
            "p_value_brier": float(p_brier),
        },
        "champion": is_champion,
        "runtime_seconds": time.time() - t_start,
        "screen_top20": screen_results[:20],
        "full_wf_results": full_results[:20],
    }

    out_path = os.path.join(DATA_DIR, "gungnir_v46_kaizen_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)
    print(f"\n  Results saved to {out_path}")

    # Deploy if champion
    if is_champion:
        print(f"\n  *** v46 IS CHAMPION — Generating deploy config ***")
        # Train final model for deploy
        deploy_eval = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                                       verbose=False, return_model=True, **final_config)

        deploy = {
            "version": "v46.0.0",
            "codename": "New Feature Mining Post-Prune",
            "n_features": len(current_feats),
            "feature_names": current_feats,
        }

        if "model" in deploy_eval:
            m = deploy_eval["model"]
            deploy["M1_coef"] = dict(zip(current_feats, m["m1_coef"].tolist()))
            deploy["M1_intercept"] = float(m["m1_intercept"])
            deploy["M2_coef"] = dict(zip(current_feats, m["m2_coef"].tolist()))
            deploy["M2_intercept"] = float(m["m2_intercept"])
            deploy["M3_coef"] = dict(zip(current_feats, m["m3_coef"].tolist()))
            deploy["M3_intercept"] = float(m["m3_intercept"])
            deploy["scaler_mean"] = dict(zip(current_feats, m["scaler_mean"].tolist()))
            deploy["scaler_scale"] = dict(zip(current_feats, m["scaler_scale"].tolist()))
            deploy["config"] = final_config

        deploy_path = os.path.join(DATA_DIR, "gungnir_v46_deploy.json")
        with open(deploy_path, "w") as f:
            json.dump(deploy, f, indent=2, cls=NumpyEncoder)
        print(f"  Deploy config saved to {deploy_path}")

        # Save XGB model if available
        if "model" in deploy_eval and "xgb_model" in deploy_eval["model"]:
            xgb_path = os.path.join(DATA_DIR, "gungnir_v46_xgb.json")
            deploy_eval["model"]["xgb_model"].save_model(xgb_path)
            print(f"  XGB model saved to {xgb_path}")
    else:
        print(f"\n  v45 remains CHAMPION. v46 did not beat it.")

    print(f"\n  Total runtime: {time.time() - t_start:.1f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
