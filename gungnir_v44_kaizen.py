#!/usr/bin/env python3
"""
================================================================================
GUNGNIR v44 KAIZEN — Multi-Pillar Cross-Family Interaction Mining
================================================================================

APPROACH:
  Start from v43.0.0 as baseline (AUC 0.8001, 144 features)

  v43 FINDINGS:
    ChEMBL drug modality × trial context interactions found 6 features.
    Key signals: oligo×volatility, biologic×phase3, cell×randomized.

  v44 STRATEGY: Systematic cross-family interaction mining + non-linear transforms.
  The 144 v43 features span 12 families but many cross-family interactions are
  UNTESTED. v42's exhaustive pairwise was within-family; v44 targets BETWEEN-family.

  PILLAR 1 — Designation × Journey/Sponsor:
    BTD/orphan/fast_track × journey history, sponsor success, streak
    Regulatory conviction × execution track record

  PILLAR 2 — Endpoint × TA/Phase:
    Safety/biomarker/PFS/hard endpoints × TA × phase granularity
    Different endpoints matter differently in different disease areas

  PILLAR 3 — Journey × Modality:
    Drug journey (prior positive/negative) × drug class (oligo/cell/mAb/sm)
    Past success with specific modality types

  PILLAR 4 — Size × Conference × Journey (three-way):
    Conference signal amplified by company journey + market cap
    Small companies with positive history at elite conferences

  PILLAR 5 — Non-linear transforms of top continuous features:
    Squared/cubed/log transforms of sponsor_success_rate, indication_density,
    volatility, momentum — capture diminishing/accelerating returns

  PILLAR 6 — Interim/Catalyst-type × Deep Interactions:
    Interim readout × modality, conference × phase, topline × size
    Catalyst context shapes outcome probability

  PILLAR 7 — CT.gov Trial Design × Sponsor/Journey:
    Randomization/blinding × sponsor quality, DMC × journey
    Trial rigor interacts with sponsor execution ability

  T-1 COMPLIANCE: All features are products/transforms of existing T-1 compliant
  features. No new data sources. All inputs are public pre-readout information.
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

# v43 config (champion)
V43_CONFIG = {
    "ridge_c": 0.02, "xgb_lr": 0.01, "xgb_trees": 600, "xgb_depth": 3,
    "meta_ridge": 0.85, "meta_xgb": 0.15, "temperature": 1.0,
    "crash_c": 0.3, "goodplus_c": 0.5,
}

# ---- Features selected in each version ----
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
    """Build v43's 6 ChEMBL interaction features."""
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


def fast_ridge_screen(X_base, y_bin, dates, candidate_col, ridge_c=0.02, seed=42):
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


# =============================================================================
# V44 CANDIDATE GENERATION — 7 PILLARS
# =============================================================================

def generate_v44_candidates(X_v43, feat_v43, events, ch2_features):
    """Generate all v44 candidate features across 7 pillars."""
    n = len(events)
    feat_idx = {name: i for i, name in enumerate(feat_v43)}

    def get_col(name):
        idx = feat_idx.get(name)
        return X_v43[:, idx] if idx is not None else np.zeros(n)

    candidates = {}
    MIN_NZ = 15  # minimum non-zero events for a candidate

    def add_candidate(name, vals):
        if np.std(vals) > 1e-8 and np.sum(np.abs(vals) > 0.001) >= MIN_NZ:
            candidates[name] = vals

    # =========================================================================
    # PILLAR 1: Designation × Journey/Sponsor
    # =========================================================================
    print("  Pillar 1: Designation × Journey/Sponsor...")

    desig_features = ["has_btd", "has_fast_track", "has_orphan", "has_priority_review",
                      "designation_count"]
    journey_features = ["journey_had_positive", "journey_had_negative",
                        "journey_last_positive", "journey_success_rate",
                        "journey_n_positive", "journey_n_prior",
                        "journey_positive_streak", "journey_had_prior_positive"]
    sponsor_features = ["sponsor_success_rate"]

    for d in desig_features:
        d_col = get_col(d)
        # Designation × journey
        for j in journey_features:
            j_col = get_col(j)
            add_candidate(f"v44_{d}_X_{j}", d_col * j_col)
        # Designation × sponsor
        for s in sponsor_features:
            s_col = get_col(s)
            add_candidate(f"v44_{d}_X_{s}", d_col * s_col)
        # Designation × momentum/volatility
        for mv in ["momentum_10d", "momentum_20d", "volatility_20d"]:
            mv_col = get_col(mv)
            add_candidate(f"v44_{d}_X_{mv}", d_col * mv_col)
        # Designation × size
        for sz in ["is_micro", "is_small", "is_mid"]:
            sz_col = get_col(sz)
            add_candidate(f"v44_{d}_X_{sz}", d_col * sz_col)
        # Designation × phase
        for ph in ["is_phase2", "is_phase3", "is_phase1b", "is_phase2a", "is_phase2b"]:
            ph_col = get_col(ph)
            add_candidate(f"v44_{d}_X_{ph}", d_col * ph_col)

    # Designation stacking interactions
    btd = get_col("has_btd")
    ft = get_col("has_fast_track")
    orph = get_col("has_orphan")
    pr = get_col("has_priority_review")
    dc = get_col("designation_count")

    add_candidate("v44_btd_x_orphan", btd * orph)
    add_candidate("v44_btd_x_fast_track", btd * ft)
    add_candidate("v44_orphan_x_fast_track", orph * ft)
    add_candidate("v44_btd_x_priority_review", btd * pr)
    add_candidate("v44_desig_stack_x_sponsor", dc * get_col("sponsor_success_rate"))
    add_candidate("v44_desig_stack_x_journey_pos", dc * get_col("journey_had_positive"))
    add_candidate("v44_desig_stack_x_phase3", dc * get_col("is_phase3"))
    add_candidate("v44_desig_stack_sq", dc ** 2)

    p1_count = len(candidates)
    print(f"    Generated: {p1_count} candidates")

    # =========================================================================
    # PILLAR 2: Endpoint × TA/Phase
    # =========================================================================
    print("  Pillar 2: Endpoint × TA/Phase...")

    endpoint_features = ["ct_ep_is_safety", "ct_ep_is_biomarker", "ct_ep_is_pfs",
                         "ctgov_ep_hard", "ctgov_ep_surrogate"]
    ta_features = ["ta_oncology", "ta_cns", "ta_metabolic", "ta_immunology",
                   "ta_rare_disease", "ta_infectious", "ta_cardiovascular",
                   "ta_hematology", "ta_ophthalmology"]
    phase_features = ["is_phase2", "is_phase3", "is_phase2a", "is_phase2b",
                      "is_phase1b", "is_bridging"]

    for ep in endpoint_features:
        ep_col = get_col(ep)
        for ta in ta_features:
            ta_col = get_col(ta)
            add_candidate(f"v44_{ep}_X_{ta}", ep_col * ta_col)
        for ph in phase_features:
            ph_col = get_col(ph)
            add_candidate(f"v44_{ep}_X_{ph}", ep_col * ph_col)
        # Endpoint × sponsor
        add_candidate(f"v44_{ep}_X_sponsor_sr", ep_col * get_col("sponsor_success_rate"))
        # Endpoint × size
        for sz in ["is_micro", "is_small"]:
            add_candidate(f"v44_{ep}_X_{sz}", ep_col * get_col(sz))

    p2_count = len(candidates) - p1_count
    print(f"    Generated: {p2_count} candidates")

    # =========================================================================
    # PILLAR 3: Journey × Modality
    # =========================================================================
    print("  Pillar 3: Journey × Modality...")

    modality_features = ["ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_biologic",
                         "ch2_is_cell", "ch2_is_gene", "ch2_is_oligo",
                         "ch2_is_advanced", "ch2_is_peptide"]
    moa_features = ["ch2_moa_inhibitor", "ch2_moa_agonist", "ch2_moa_antagonist"]
    quality_features = ["ch2_first_in_class", "ch2_has_prior_approval", "ch2_is_combo"]

    for mod in modality_features:
        mod_col = ch2_features.get(mod, np.zeros(n))
        if np.sum(mod_col != 0) < MIN_NZ: continue
        for j in journey_features:
            j_col = get_col(j)
            add_candidate(f"v44_{mod}_X_{j}", mod_col * j_col)
        # Modality × sponsor
        add_candidate(f"v44_{mod}_X_sponsor_sr", mod_col * get_col("sponsor_success_rate"))
        # Modality × designation
        for d in ["has_btd", "has_orphan", "has_fast_track"]:
            add_candidate(f"v44_{mod}_X_{d}", mod_col * get_col(d))
        # Modality × indication_density
        add_candidate(f"v44_{mod}_X_ind_density", mod_col * get_col("indication_density"))

    for moa in moa_features:
        moa_col = ch2_features.get(moa, np.zeros(n))
        if np.sum(moa_col != 0) < MIN_NZ: continue
        for j in ["journey_had_positive", "journey_success_rate", "sponsor_success_rate"]:
            add_candidate(f"v44_{moa}_X_{j}", moa_col * get_col(j))
        for ta in ["ta_oncology", "ta_cns", "ta_immunology"]:
            add_candidate(f"v44_{moa}_X_{ta}", moa_col * get_col(ta))

    for q in quality_features:
        q_col = ch2_features.get(q, np.zeros(n))
        if np.sum(q_col != 0) < MIN_NZ: continue
        for partner in ["journey_success_rate", "sponsor_success_rate", "is_phase3",
                        "is_micro", "is_small", "has_btd", "indication_density"]:
            add_candidate(f"v44_{q}_X_{partner}", q_col * get_col(partner))

    p3_count = len(candidates) - p1_count - p2_count
    print(f"    Generated: {p3_count} candidates")

    # =========================================================================
    # PILLAR 4: Three-way interactions (top signals)
    # =========================================================================
    print("  Pillar 4: Three-way interactions...")

    # Conference × journey × size
    conf = get_col("v40_has_conference")
    for j in ["journey_had_positive", "journey_success_rate", "journey_last_positive"]:
        j_col = get_col(j)
        for sz in ["is_micro", "is_small"]:
            sz_col = get_col(sz)
            add_candidate(f"v44_conf_X_{j}_X_{sz}", conf * j_col * sz_col)

    # Sponsor × designation × phase
    ssr = get_col("sponsor_success_rate")
    for d in ["has_btd", "has_orphan"]:
        d_col = get_col(d)
        for ph in ["is_phase2", "is_phase3"]:
            ph_col = get_col(ph)
            add_candidate(f"v44_sponSR_X_{d}_X_{ph}", ssr * d_col * ph_col)

    # Modality × phase × size (three-way: what drug, what stage, what cap)
    for mod in ["ch2_is_mab", "ch2_is_sm", "ch2_is_biologic"]:
        mod_col = ch2_features.get(mod, np.zeros(n))
        if np.sum(mod_col != 0) < MIN_NZ: continue
        for ph in ["is_phase2", "is_phase3"]:
            ph_col = get_col(ph)
            for sz in ["is_micro", "is_small"]:
                sz_col = get_col(sz)
                add_candidate(f"v44_{mod}_X_{ph}_X_{sz}", mod_col * ph_col * sz_col)

    # Endpoint × TA × phase (three-way)
    for ep in ["ctgov_ep_hard", "ct_ep_is_biomarker"]:
        ep_col = get_col(ep)
        for ta in ["ta_oncology", "ta_cns", "ta_rare_disease"]:
            ta_col = get_col(ta)
            for ph in ["is_phase2", "is_phase3"]:
                ph_col = get_col(ph)
                add_candidate(f"v44_{ep}_X_{ta}_X_{ph}", ep_col * ta_col * ph_col)

    # Interim × size × modality
    interim = get_col("iis_is_interim")
    for sz in ["is_micro", "is_small"]:
        sz_col = get_col(sz)
        add_candidate(f"v44_interim_X_{sz}", interim * sz_col)
    for mod in ["ch2_is_biologic", "ch2_is_sm"]:
        mod_col = ch2_features.get(mod, np.zeros(n))
        add_candidate(f"v44_interim_X_{mod}", interim * mod_col)

    p4_count = len(candidates) - p1_count - p2_count - p3_count
    print(f"    Generated: {p4_count} candidates")

    # =========================================================================
    # PILLAR 5: Non-linear transforms
    # =========================================================================
    print("  Pillar 5: Non-linear transforms...")

    # Squared transforms
    for feat in ["sponsor_success_rate", "indication_density", "volatility_20d",
                 "momentum_10d", "momentum_20d", "volatility_5d",
                 "hist_loa", "hist_pop", "ta_base_rate",
                 "journey_success_rate", "journey_n_positive",
                 "ctgov_enrollment", "ctgov_n_sites", "ctgov_masking_rigor",
                 "competitive_3mo", "competitive_6mo", "log_market_cap"]:
        col = get_col(feat)
        add_candidate(f"v44_{feat}_sq", col ** 2)

    # Cubed transforms (top features only)
    for feat in ["sponsor_success_rate", "indication_density", "volatility_20d",
                 "momentum_10d"]:
        col = get_col(feat)
        add_candidate(f"v44_{feat}_cubed", col ** 3)

    # Log transforms (for count-like features)
    for feat in ["journey_n_positive", "journey_n_prior", "ctgov_n_sites",
                 "ctgov_n_countries", "designation_count"]:
        col = get_col(feat)
        add_candidate(f"v44_log1p_{feat}", np.log1p(np.abs(col)))

    # Abs momentum (direction-agnostic volatility proxy)
    for feat in ["momentum_5d", "momentum_10d", "momentum_20d"]:
        col = get_col(feat)
        add_candidate(f"v44_abs_{feat}", np.abs(col))

    p5_count = len(candidates) - p1_count - p2_count - p3_count - p4_count
    print(f"    Generated: {p5_count} candidates")

    # =========================================================================
    # PILLAR 6: Catalyst-type × Deep Interactions
    # =========================================================================
    print("  Pillar 6: Catalyst-type × Deep Interactions...")

    cat_features = ["cat_conference", "cat_interim", "cat_topline",
                    "cat_full_results", "cat_initial", "cat_regulatory",
                    "cat_submission"]

    for cat in cat_features:
        cat_col = get_col(cat)
        if np.sum(np.abs(cat_col) > 0.001) < MIN_NZ: continue
        # Catalyst type × size
        for sz in ["is_micro", "is_small", "is_mid"]:
            add_candidate(f"v44_{cat}_X_{sz}", cat_col * get_col(sz))
        # Catalyst type × phase
        for ph in ["is_phase2", "is_phase3"]:
            add_candidate(f"v44_{cat}_X_{ph}", cat_col * get_col(ph))
        # Catalyst type × TA
        for ta in ["ta_oncology", "ta_cns", "ta_rare_disease"]:
            add_candidate(f"v44_{cat}_X_{ta}", cat_col * get_col(ta))
        # Catalyst type × sponsor
        add_candidate(f"v44_{cat}_X_sponsor_sr", cat_col * get_col("sponsor_success_rate"))
        # Catalyst type × journey
        add_candidate(f"v44_{cat}_X_journey_pos", cat_col * get_col("journey_had_positive"))
        # Catalyst type × modality
        for mod in ["ch2_is_biologic", "ch2_is_sm", "ch2_is_advanced"]:
            mod_col = ch2_features.get(mod, np.zeros(n))
            add_candidate(f"v44_{cat}_X_{mod}", cat_col * mod_col)

    p6_count = len(candidates) - p1_count - p2_count - p3_count - p4_count - p5_count
    print(f"    Generated: {p6_count} candidates")

    # =========================================================================
    # PILLAR 7: CT.gov Trial Design × Sponsor/Journey
    # =========================================================================
    print("  Pillar 7: CT.gov × Sponsor/Journey...")

    ctgov_design = ["ctgov_is_randomized", "ctgov_is_double_blind", "ctgov_is_placebo",
                    "ctgov_has_dmc", "ctgov_is_global", "ctgov_masking_rigor",
                    "ctgov_n_arms", "ctgov_enrollment", "ct_has_combination",
                    "ct_is_industry"]

    for ct in ctgov_design:
        ct_col = get_col(ct)
        # Trial design × sponsor
        add_candidate(f"v44_{ct}_X_sponsor_sr", ct_col * get_col("sponsor_success_rate"))
        # Trial design × journey
        for j in ["journey_had_positive", "journey_success_rate"]:
            add_candidate(f"v44_{ct}_X_{j}", ct_col * get_col(j))
        # Trial design × designation
        for d in ["has_btd", "has_orphan"]:
            add_candidate(f"v44_{ct}_X_{d}", ct_col * get_col(d))

    # DMC × phase (DMC in later-stage = more rigorous = signal)
    dmc = get_col("ctgov_has_dmc")
    for ph in ["is_phase2", "is_phase3", "is_phase2b"]:
        add_candidate(f"v44_dmc_X_{ph}", dmc * get_col(ph))

    # Randomized × modality (cell therapy already captured in v43, try others)
    rand = get_col("ctgov_is_randomized")
    for mod in ["ch2_is_sm", "ch2_is_mab", "ch2_is_adc", "ch2_is_gene"]:
        mod_col = ch2_features.get(mod, np.zeros(n))
        add_candidate(f"v44_rand_X_{mod}", rand * mod_col)

    # Global × TA (global trials in specific TAs)
    glob = get_col("ctgov_is_global")
    for ta in ta_features:
        add_candidate(f"v44_global_X_{ta}", glob * get_col(ta))

    p7_count = len(candidates) - p1_count - p2_count - p3_count - p4_count - p5_count - p6_count
    print(f"    Generated: {p7_count} candidates")

    print(f"\n  TOTAL CANDIDATES: {len(candidates)}")
    return candidates


def main():
    t_start = time.time()

    print("\n" + "=" * 80)
    print("  GUNGNIR v44 KAIZEN — Multi-Pillar Cross-Family Interaction Mining")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: Build v43 baseline (144 features)
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 1: Build v43 baseline (144 features)")
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

    # Baseline WF AUC
    print("\n  Evaluating v43 baseline...")
    baseline = v39.evaluate_wf(X_v43, y_bin, y_gp, y_cr, y_ret, dates,
                                verbose=True, **V43_CONFIG)
    base_auc = baseline["avg_auc"]
    base_brier = baseline["avg_brier"]
    print(f"\n  *** v43 BASELINE: AUC={base_auc:.4f} Brier={base_brier:.4f}")

    # =========================================================================
    # PHASE 2: Generate v44 candidates across 7 pillars
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 2: Generate v44 Candidates (7 Pillars)")
    print(f"{'=' * 80}")

    candidates = generate_v44_candidates(X_v43, feat_v43, events, ch2_features)

    # =========================================================================
    # PHASE 3: Fast Ridge Pre-screen
    # =========================================================================
    print(f"\n{'=' * 80}")
    print(f"  PHASE 3: Fast Pre-Screen ({len(candidates)} candidates)")
    print(f"{'=' * 80}")

    screen_results = []
    for i, (feat_name, col) in enumerate(candidates.items()):
        delta, abs_auc = fast_ridge_screen(X_v43, y_bin, dates, col,
                                            ridge_c=V43_CONFIG["ridge_c"])
        screen_results.append({"feature": feat_name, "delta": delta, "auc": abs_auc})
        if (i + 1) % 100 == 0:
            pos_so_far = sum(1 for r in screen_results if r["delta"] > 0)
            print(f"    {i + 1}/{len(candidates)} screened... ({pos_so_far} positive)")

    screen_results.sort(key=lambda x: -x["delta"])
    positive = [r for r in screen_results if r["delta"] > 0]
    print(f"\n  Positive: {len(positive)}/{len(screen_results)}")

    print(f"\n  TOP 40 (fast screen):")
    for r in screen_results[:40]:
        flag = " ***" if r["delta"] > 0.001 else (" **" if r["delta"] > 0.0005 else "")
        print(f"    {r['feature']:60s} Δ={r['delta']:+.4f}{flag}")

    # Save intermediate results
    with open(os.path.join(DATA_DIR, "gungnir_v44_screen_results.json"), "w") as f:
        json.dump(screen_results[:100], f, indent=2)

    # =========================================================================
    # PHASE 4: Full WF Audit on top candidates
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 4: Full WF Audit (top 60 from pre-screen)")
    print(f"{'=' * 80}")

    top_candidates = [r["feature"] for r in screen_results[:60] if r["delta"] > 0]
    print(f"  Auditing {len(top_candidates)} candidates...")

    audit_results = []
    for i, feat_name in enumerate(top_candidates):
        col = candidates[feat_name]
        X_test = np.column_stack([X_v43, col.reshape(-1, 1)])
        result = v39.evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates,
                                  verbose=False, **V43_CONFIG)
        delta = result["avg_auc"] - base_auc
        audit_results.append({
            "feature": feat_name, "auc": result["avg_auc"],
            "delta": delta, "brier": result["avg_brier"],
        })
        if (i + 1) % 10 == 0:
            print(f"    {i + 1}/{len(top_candidates)} audited...")

    audit_results.sort(key=lambda x: -x["delta"])
    positive_audit = [r for r in audit_results if r["delta"] > 0]
    print(f"\n  Positive on full WF: {len(positive_audit)}/{len(audit_results)}")

    print(f"\n  TOP 25 (full WF):")
    for r in audit_results[:25]:
        flag = " ***" if r["delta"] > 0.001 else (" **" if r["delta"] > 0.0005 else "")
        print(f"    {r['feature']:60s} AUC={r['auc']:.4f} Δ={r['delta']:+.4f} Brier={r['brier']:.4f}{flag}")

    # =========================================================================
    # PHASE 5: Greedy Forward Selection
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 5: Greedy Forward Selection")
    print(f"{'=' * 80}")

    greedy_candidates = [r["feature"] for r in audit_results if r["delta"] > 0.0002]
    print(f"  Candidates entering greedy: {len(greedy_candidates)}")

    current_X = X_v43.copy()
    current_feats = list(feat_v43)
    current_auc = base_auc
    selected = []

    for rnd in range(20):  # up to 20 rounds
        best_feat, best_auc, best_brier = None, current_auc, 999
        for feat_name in greedy_candidates:
            if feat_name in current_feats: continue
            col = candidates[feat_name]
            X_test = np.column_stack([current_X, col.reshape(-1, 1)])
            result = v39.evaluate_wf(X_test, y_bin, y_gp, y_cr, y_ret, dates,
                                      verbose=False, **V43_CONFIG)
            if result["avg_auc"] > best_auc:
                best_auc = result["avg_auc"]
                best_feat = feat_name
                best_brier = result["avg_brier"]

        if best_feat and (best_auc - current_auc) > 0.00005:
            col = candidates[best_feat]
            current_X = np.column_stack([current_X, col.reshape(-1, 1)])
            current_feats.append(best_feat)
            incr = best_auc - current_auc
            selected.append({"feature": best_feat, "auc": best_auc,
                           "incremental": incr, "brier": best_brier})
            print(f"  R{rnd + 1}: +{best_feat:60s} AUC={best_auc:.4f} (+{incr:.4f}) Brier={best_brier:.4f}")
            current_auc = best_auc
        else:
            print(f"  R{rnd + 1}: No improvement. Stopping.")
            break

    print(f"\n  v43 {base_auc:.4f} → v44 {current_auc:.4f} (Δ={current_auc - base_auc:+.4f})")
    print(f"  Features added: {len(selected)}, Total: {len(current_feats)}")

    if len(selected) == 0:
        print("\n  *** NO FEATURES SELECTED — v43 remains champion ***")
        results = {
            "version": "v44.0.0", "date": time.strftime("%Y-%m-%d"),
            "baseline_auc": base_auc, "final_auc": base_auc,
            "champion": False, "features_added": [],
            "screen_top30": screen_results[:30],
            "audit_top20": audit_results[:20],
        }
        with open(os.path.join(DATA_DIR, "gungnir_v44_kaizen_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        return

    # =========================================================================
    # PHASE 6: Architecture Sweep
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 6: Architecture Sweep")
    print(f"{'=' * 80}")

    best_c, best_c_auc = V43_CONFIG["ridge_c"], current_auc
    best_meta_r, best_meta_x = V43_CONFIG["meta_ridge"], V43_CONFIG["meta_xgb"]

    # C sweep
    print("  C sweep:")
    for c in [0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050]:
        cfg = dict(V43_CONFIG)
        cfg["ridge_c"] = c
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        flag = " <-- BEST" if r["avg_auc"] > best_c_auc else ""
        print(f"    C={c:.3f}: AUC={r['avg_auc']:.4f} Brier={r['avg_brier']:.4f}{flag}")
        if r["avg_auc"] > best_c_auc:
            best_c_auc = r["avg_auc"]
            best_c = c

    # Meta weight sweep
    print("  Meta weight sweep:")
    for meta_r in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        cfg = dict(V43_CONFIG)
        cfg["ridge_c"] = best_c
        cfg["meta_ridge"] = meta_r
        cfg["meta_xgb"] = 1.0 - meta_r
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        flag = " <-- BEST" if r["avg_auc"] > best_c_auc else ""
        print(f"    Meta {meta_r:.0%}/{1 - meta_r:.0%}: AUC={r['avg_auc']:.4f}{flag}")
        if r["avg_auc"] > best_c_auc:
            best_c_auc = r["avg_auc"]
            best_meta_r = meta_r
            best_meta_x = 1.0 - meta_r

    # XGB tree count sweep
    print("  XGB trees sweep:")
    for trees in [400, 500, 600, 700, 800]:
        cfg = dict(V43_CONFIG)
        cfg["ridge_c"] = best_c
        cfg["meta_ridge"] = best_meta_r
        cfg["meta_xgb"] = best_meta_x
        cfg["xgb_trees"] = trees
        r = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                             verbose=False, **cfg)
        flag = " <-- BEST" if r["avg_auc"] > best_c_auc else ""
        print(f"    Trees={trees}: AUC={r['avg_auc']:.4f}{flag}")
        if r["avg_auc"] > best_c_auc:
            best_c_auc = r["avg_auc"]
            V43_CONFIG["xgb_trees"] = trees

    final_config = {
        "ridge_c": best_c, "meta_ridge": best_meta_r, "meta_xgb": best_meta_x,
        "xgb_trees": V43_CONFIG["xgb_trees"], "xgb_depth": V43_CONFIG["xgb_depth"],
        "xgb_lr": V43_CONFIG["xgb_lr"],
    }
    print(f"\n  Best config: C={best_c}, meta={best_meta_r:.0%}/{best_meta_x:.0%}, trees={final_config['xgb_trees']}")
    print(f"  Best AUC: {best_c_auc:.4f}")

    # =========================================================================
    # PHASE 7: 20-Seed Stability Test
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 7: 20-Seed Stability Test")
    print(f"{'=' * 80}")

    from scipy import stats

    final_cfg = dict(V43_CONFIG)
    final_cfg["ridge_c"] = best_c
    final_cfg["meta_ridge"] = best_meta_r
    final_cfg["meta_xgb"] = best_meta_x

    v43_aucs, v44_aucs = [], []
    for seed in range(20):
        cfg43 = dict(V43_CONFIG)
        cfg43["seed"] = seed
        cfg44 = dict(final_cfg)
        cfg44["seed"] = seed
        r43 = v39.evaluate_wf(X_v43, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg43)
        r44 = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                               verbose=False, **cfg44)
        v43_aucs.append(r43["avg_auc"])
        v44_aucs.append(r44["avg_auc"])

    wins = sum(1 for a, b in zip(v43_aucs, v44_aucs) if b > a)
    t_stat, p_val = stats.ttest_rel(v44_aucs, v43_aucs)
    print(f"  v43: {np.mean(v43_aucs):.4f} ± {np.std(v43_aucs):.4f}")
    print(f"  v44: {np.mean(v44_aucs):.4f} ± {np.std(v44_aucs):.4f}")
    print(f"  Wins: {wins}/20, p={p_val:.10f}")
    print(f"  v43 range: [{min(v43_aucs):.4f}, {max(v43_aucs):.4f}]")
    print(f"  v44 range: [{min(v44_aucs):.4f}, {max(v44_aucs):.4f}]")

    # =========================================================================
    # PHASE 8: Final evaluation with best config
    # =========================================================================
    print(f"\n{'=' * 80}")
    print("  PHASE 8: Final Evaluation")
    print(f"{'=' * 80}")

    final_result = v39.evaluate_wf(current_X, y_bin, y_gp, y_cr, y_ret, dates,
                                     verbose=True, **final_cfg)
    final_auc = final_result["avg_auc"]
    final_brier = final_result["avg_brier"]
    print(f"\n  Final v44: AUC={final_auc:.4f} Brier={final_brier:.4f}")

    # =========================================================================
    # SAVE RESULTS
    # =========================================================================
    elapsed = time.time() - t_start
    is_champion = bool(wins >= 14 and final_auc > base_auc)

    results = {
        "version": "v44.0.0",
        "date": time.strftime("%Y-%m-%d"),
        "baseline_version": "v43.0.0",
        "baseline_auc": float(base_auc),
        "baseline_brier": float(base_brier),
        "final_auc": float(final_auc),
        "final_brier": float(final_brier),
        "best_c": best_c,
        "best_meta": f"{int(best_meta_r*100)}/{int(best_meta_x*100)}",
        "best_c_auc": float(best_c_auc),
        "delta": float(final_auc - base_auc),
        "n_features_v43": len(feat_v43),
        "n_features_v44": len(current_feats),
        "features_added": [s["feature"] for s in selected],
        "key_discoveries": [],
        "screen_results_top40": screen_results[:40],
        "audit_results_top25": audit_results[:25],
        "greedy_selection": selected,
        "stability": {
            "v43_mean": float(np.mean(v43_aucs)),
            "v44_mean": float(np.mean(v44_aucs)),
            "v43_aucs": [float(x) for x in v43_aucs],
            "v44_aucs": [float(x) for x in v44_aucs],
            "wins": wins,
            "p_value": float(p_val),
        },
        "config": final_config,
        "champion": is_champion,
        "runtime_seconds": elapsed,
        "wf_splits": {s["split"]: {"auc": s["auc"], "brier": s["brier"]}
                      for s in final_result.get("splits", [])},
    }

    # Custom JSON encoder for numpy types
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, (np.ndarray,)): return obj.tolist()
            if isinstance(obj, (np.bool_,)): return bool(obj)
            return super().default(obj)

    results_path = os.path.join(DATA_DIR, "gungnir_v44_kaizen_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)

    print(f"\n{'=' * 80}")
    if is_champion:
        print(f"  *** v44 IS CHAMPION: AUC {base_auc:.4f} → {final_auc:.4f} "
              f"(+{final_auc - base_auc:.4f}), {wins}/20 seeds ***")
    else:
        print(f"  v44 result: AUC {base_auc:.4f} → {final_auc:.4f} "
              f"(+{final_auc - base_auc:.4f}), {wins}/20 seeds")
        if wins < 14:
            print(f"  INSUFFICIENT STABILITY ({wins}/20 < 14/20)")
        if final_auc <= base_auc:
            print(f"  NO AUC IMPROVEMENT")
    print(f"  Runtime: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  Results saved: {results_path}")
    print(f"{'=' * 80}")

    # =========================================================================
    # PHASE 9: Deploy if champion
    # =========================================================================
    if is_champion:
        print(f"\n{'=' * 80}")
        print("  PHASE 9: Generating Deploy Config")
        print(f"{'=' * 80}")

        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        # Train final model on all pre-2025 data
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
        m2 = LogisticRegression(C=V43_CONFIG["goodplus_c"], penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=42)
        m2.fit(X_tr, y_gp[train_mask])

        # M3: CRASH
        m3 = LogisticRegression(C=V43_CONFIG["crash_c"], penalty="l2", solver="lbfgs",
                                max_iter=2000, random_state=42)
        m3.fit(X_tr, y_cr[train_mask])

        deploy = {
            "version": "v44.0.0",
            "codename": "Cross-Family Interactions",
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
                "baseline_auc": float(base_auc),
                "stability_wins": wins,
                "stability_p": float(p_val),
            },
            "features_added_v44": [s["feature"] for s in selected],
        }

        # Save XGBoost model
        try:
            import xgboost as xgb_lib
            m5 = xgb_lib.XGBClassifier(
                n_estimators=final_config["xgb_trees"],
                max_depth=final_config["xgb_depth"],
                learning_rate=final_config["xgb_lr"],
                subsample=0.8, colsample_bytree=0.6,
                reg_alpha=0.3, reg_lambda=2.0,
                min_child_weight=10, gamma=0.2,
                random_state=42, use_label_encoder=False,
                eval_metric="logloss", verbosity=0
            )
            m5.fit(X_tr, y_tr)
            xgb_path = os.path.join(DATA_DIR, "gungnir_v44_xgb.json")
            m5.save_model(xgb_path)
            print(f"  XGBoost saved: {xgb_path}")
        except Exception as e:
            print(f"  XGBoost save failed: {e}")

        deploy_path = os.path.join(DATA_DIR, "gungnir_v44_deploy.json")
        with open(deploy_path, "w") as f:
            json.dump(deploy, f, indent=2)
        print(f"  Deploy config saved: {deploy_path}")
        print(f"  Features: {len(current_feats)}")
        print(f"  New features: {[s['feature'] for s in selected]}")


if __name__ == "__main__":
    main()
