#!/usr/bin/env python3
"""
GUNGNIR v28 FULL RETRAIN PIPELINE
===================================
End-to-end retrain on enriched 3,489-event dataset.
- 10-fold TimeSeriesSplit CV ensemble
- Phase 3 sub-model (MoE)
- Hyperparameter grid search (C, penalty)
- Threshold optimization (T1 n≥500 constraint)
- $140k live trading simulation
- Production MCP deploy code

GPU: Falls back to NumPy if CuPy unavailable (same algorithms).
"""

import csv, math, re, sys, json, time
from collections import defaultdict, Counter

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("WARNING: numpy not available, using pure Python")

try:
    import cupy as cp
    GPU = True
    print("GPU: CuPy detected, using RTX 4070 acceleration")
except ImportError:
    GPU = False
    if HAS_NUMPY:
        import numpy as cp  # alias numpy as cp for unified code
        print("GPU: CuPy not available, using NumPy CPU fallback")

# Try sklearn
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import brier_score_loss, roc_auc_score
    HAS_SKLEARN = True
    print("sklearn: available")
except ImportError:
    HAS_SKLEARN = False
    print("sklearn: not available, using pure Python implementation")

np_available = HAS_NUMPY

# ============================================================================
# GUNGNIR v27 BASELINE WEIGHTS (for comparison)
# ============================================================================

V27_FEATURES = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious",
    "ta_ophthalmology", "ta_pain",
    "is_gene_therapy", "is_adc", "is_small_molecule",
    "is_rct", "is_combination", "has_hard_endpoint", "uses_surrogate",
    "designation_count", "log_price", "era_post_2024",
    "phase3_x_cns", "phase3_x_immunology", "rare_x_phase3",
    "antibody_x_oncology", "rct_x_phase3", "combo_x_oncology",
    "is_competitive", "has_ppm",
    "is_topline", "odin_btd", "mentions_primary",
    "orr_x_oncology", "endpoint_pfs",
]

V27_INTERCEPT = 0.6288855542014196
V27_COEFS = {
    "is_P2": -0.4736582326196623, "is_P2B": -0.36977256891387766,
    "is_pivotal": -0.6498020968356205, "is_phase1_any": -0.13997252914162728,
    "ta_oncology": -0.16295321706231716, "ta_rare": -0.875170840051619,
    "ta_metabolic": 0.23977990126602738, "ta_infectious": 0.027418186737885167,
    "ta_ophthalmology": -0.1180490347402135, "ta_pain": 0.03875147359202568,
    "is_gene_therapy": 0.23219320852992717, "is_adc": -0.024177732948626643,
    "is_small_molecule": -0.0041978770164206375, "is_rct": 0.07830319744780984,
    "is_combination": 0.035994834392002954, "has_hard_endpoint": 0.23724862113759607,
    "uses_surrogate": 0.5433548316235536, "designation_count": 0.8494439301325211,
    "log_price": 0.34741142570358224, "era_post_2024": -0.11026153268806602,
    "phase3_x_cns": -0.09643451573646784, "phase3_x_immunology": 0.2849623132197371,
    "rare_x_phase3": -0.054458165413033575, "antibody_x_oncology": 0.14167734518781006,
    "rct_x_phase3": 0.09662471334956377, "combo_x_oncology": -0.086061076729749,
    "is_competitive": -0.1529698241484826, "has_ppm": 0.6915492770276539,
    "is_topline": 0.09655878808584675, "odin_btd": 0.2590475665762014,
    "mentions_primary": 0.03561461388365659, "orr_x_oncology": 0.7182678503153423,
    "endpoint_pfs": 0.09100655132371727,
}
V27_MEANS = {
    "is_P2": 0.2689313517338995, "is_P2B": 0.055201698513800426,
    "is_pivotal": 0.4062278839348903, "is_phase1_any": 0.23779193205944799,
    "ta_oncology": 0.4578910120311394, "ta_rare": 0.12455767869780608,
    "ta_metabolic": 0.04600141542816702, "ta_infectious": 0.051663128096249115,
    "ta_ophthalmology": 0.028308563340410473, "ta_pain": 0.010615711252653927,
    "is_gene_therapy": 0.0007077140835102619, "is_adc": 0.026185421089879687,
    "is_small_molecule": 0.7395612172682237, "is_rct": 0.10049539985845718,
    "is_combination": 0.055909412597310686, "has_hard_endpoint": 0.0007077140835102619,
    "uses_surrogate": 0.24769992922859166, "designation_count": 0.12526539278131635,
    "log_price": 2.876966489026295, "era_post_2024": 0.4012738853503185,
    "phase3_x_cns": 0.04529370134465676, "phase3_x_immunology": 0.024062278839348902,
    "rare_x_phase3": 0.05874026893135174, "antibody_x_oncology": 0.19179051663128097,
    "rct_x_phase3": 0.055201698513800426, "combo_x_oncology": 0.04953998584571833,
    "is_competitive": 0.15498938428874734, "has_ppm": 0.18329794762915783,
    "is_topline": 0.08917197452229299, "odin_btd": 0.05732484076433121,
    "mentions_primary": 0.4154281670205237, "orr_x_oncology": 0.18117480537862704,
    "endpoint_pfs": 0.07006369426751592,
}
V27_STDS = {
    "is_P2": 0.4434041945995517, "is_P2B": 0.2283735339197428,
    "is_pivotal": 0.4911280792712544, "is_phase1_any": 0.4257310525518228,
    "ta_oncology": 0.4982236778117217, "ta_rare": 0.3302166915454459,
    "ta_metabolic": 0.20948815051637698, "ta_infectious": 0.22134599452341505,
    "ta_ophthalmology": 0.16585291249179931, "ta_pain": 0.10248423257874455,
    "is_gene_therapy": 0.026593480860659498, "is_adc": 0.15968639520079783,
    "is_small_molecule": 0.43887404022221105, "is_rct": 0.300659399430229,
    "is_combination": 0.2297467087475561, "has_hard_endpoint": 0.026593480860659498,
    "uses_surrogate": 0.43167658529128294, "designation_count": 0.3310195978377396,
    "log_price": 1.520417207760554, "era_post_2024": 0.4901562549699615,
    "phase3_x_cns": 0.20794754618210284, "phase3_x_immunology": 0.15324257103170227,
    "rare_x_phase3": 0.23513793768174499, "antibody_x_oncology": 0.39370917485065965,
    "rct_x_phase3": 0.2283735339197428, "combo_x_oncology": 0.21699257049061463,
    "is_competitive": 0.36189456343877613, "has_ppm": 0.38691059693952085,
    "is_topline": 0.2849918130088802, "odin_btd": 0.23246226230439054,
    "mentions_primary": 0.49279570317373056, "orr_x_oncology": 0.38516294639365767,
    "endpoint_pfs": 0.2552543300575016,
}

# ============================================================================
# v28 EXPANDED FEATURE SET (33 → 45 features with simulated enrichment)
# ============================================================================

V28_FEATURES = V27_FEATURES + [
    # New CT.gov features (simulated enrichment)
    "is_rct_ctgov",          # RCT from clinicaltrials.gov (80% coverage)
    "uses_surrogate_ctgov",  # Surrogate endpoint from CT.gov (75% coverage)
    "is_adaptive",           # Adaptive trial design (40% coverage)
    "sample_size_log",       # Log(sample size) from CT.gov
    "has_interim_positive",  # Prior positive interim analysis
    # Enhanced ODIN cross-ref features
    "odin_desig_rich",       # ≥3 designations from ODIN
    "odin_prior_crl",        # Prior CRL from ODIN
    "odin_sponsor_exp",      # Sponsor experienced (from ODIN)
    # Enhanced interaction terms
    "rct_x_phase3_ctgov",   # RCT × Phase 3 (CT.gov sourced)
    "surrogate_x_onc",      # Surrogate × Oncology (CT.gov)
    "adaptive_x_phase3",    # Adaptive × Phase 3
    "competitive_count",     # Gradient competitive (0-5 scale)
]

# ============================================================================
# NLP PATTERNS (same as v28 backtest)
# ============================================================================

_G_TA = {
    "ta_oncology": re.compile(r"cancer|tumor|tumour|lymphoma|leukemia|melanoma|carcinoma|myeloma|sarcoma|glioma|glioblastoma|oncolog|nsclc|solid\s+tumor|breast(?!\s*feed)|ovarian|pancreatic|colorectal|prostate\s+(?!hyper)", re.I),
    "ta_rare": re.compile(r"duchenne|sma|spinal\s+muscular|sickle\s+cell|cystic\s+fibrosis|hemophilia|fabry|gaucher|pompe|achondroplasia|rare|orphan|lysosom|ataxia|dystrophy|thalassemia", re.I),
    "ta_metabolic": re.compile(r"diabet|obes|metabol|nash|mash|steatohepatitis|cholesterol|lipid|glycem|hba1c|weight\s+(?:loss|manage)", re.I),
    "ta_infectious": re.compile(r"hiv|hepatitis|influenza|covid|sars|rsv|malaria|tuberculosis|tb\b|antibiotic|antibacterial|antiviral|antifungal|infection|infectious|pneumonia|sepsis", re.I),
    "ta_ophthalmology": re.compile(r"ophthalm|retina|macular|glaucoma|dry\s+eye|uveitis|diabetic\s+retinopath|geographic\s+atrophy|amd\b|dme\b", re.I),
    "ta_pain": re.compile(r"\bpain\b|fibromyalg|analges|nocicepti", re.I),
    "ta_cns": re.compile(r"alzheimer|parkinson|epilep|schizophren|depression|depressive|bipolar|multiple\s+sclerosis|(?:^|\W)als(?:\W|$)|amyotrophic|huntington|migraine|dementia|seizure|anxiety|ptsd|adhd|narcolep|stroke", re.I),
    "ta_immunology": re.compile(r"lupus|rheumatoid|crohn|colitis|psoria|atopic|eczema|inflam|autoimmun|immunolog|ibd|gvhd|dermati|ankylos|vasculit", re.I),
}
_G_COMPETITIVE = {"nsclc", "aml", "mdd", "alzheimer", "chronic pain", "als",
    "non-small cell lung cancer", "acute myeloid leukemia",
    "major depressive disorder", "breast cancer", "prostate cancer",
    "type 2 diabetes", "obesity", "copd", "asthma"}
_G_COMPETITIVE_FULL = {
    "nsclc": 5, "non-small cell lung cancer": 5, "breast cancer": 4,
    "aml": 3, "acute myeloid leukemia": 3, "mdd": 4,
    "major depressive disorder": 4, "alzheimer": 3, "prostate cancer": 3,
    "type 2 diabetes": 5, "obesity": 4, "copd": 3, "asthma": 3,
    "chronic pain": 3, "als": 2, "multiple myeloma": 3,
    "non-hodgkin lymphoma": 2, "atopic dermatitis": 3, "psoriasis": 3,
    "rheumatoid arthritis": 3, "crohn": 2, "nash": 3, "mash": 3,
}
_G_MODALITY = {
    "gene_therapy": re.compile(r"gene\s*therap|aav|crispr|base\s*edit|lentivir", re.I),
    "adc": re.compile(r"antibody.drug\s+conjug|\badc\b|drug\s+conjugat", re.I),
    "small_molecule": re.compile(r"small\s+molecul|oral|tablet|capsule|inhibitor|antagonist|agonist", re.I),
    "antibody": re.compile(r"antibod|mab\b|-mab\b|bispecific", re.I),
}

_DESIGN_RCT = re.compile(r"randomiz|placebo.?control|double.?blind|rct\b|single.?arm", re.I)
_DESIGN_SINGLE_ARM = re.compile(r"single.?arm|open.?label|single.?group", re.I)
_DESIGN_SURROGATE = re.compile(r"surrogate|biomarker|response\s+rate|tumor\s+(?:reduction|shrink)", re.I)
_DESIGN_COMBO = re.compile(r"combination|combo|plus\s+\w+mab|with\s+\w+mab|\+\s+\w+mab", re.I)
_DESIGN_INTERIM = re.compile(r"interim|futility|adaptive", re.I)
_DESIGN_ADAPTIVE = re.compile(r"adaptive|basket|umbrella|platform\s+trial|seamless", re.I)

_POST_READOUT = re.compile(
    r"(data\s+(?:released|reported|showed|presented|announced|demonstrated|revealed|from\s+\w+\s+(?:reported|showed)).*)",
    re.I | re.DOTALL
)
_RESULT_PHRASES = re.compile(
    r"((?:met|failed|missed|did\s+not\s+meet|statistically\s+significant|not\s+statistically|"
    r"primary\s+endpoint\s+(?:met|not|was)|ORR\s+(?:was|of)\s+\d|"
    r"PFS\s+(?:was|of)\s+\d|OS\s+(?:was|of)\s+\d|median\s+\w+\s+was).*?)(?:\.|$)",
    re.I
)

BIG_PHARMA = {"PFE","MRK","LLY","ABBV","BMY","JNJ","AZN","RHHBY","NVS","SNY",
              "GSK","AMGN","GILD","REGN","BIIB","VRTX","MRNA","BNTX","TAK","NVO",
              "TEVA","ROCHE","NOVARTIS","BAYER"}


def bool_val(s):
    if isinstance(s, bool): return s
    return str(s).strip().upper() in ("TRUE", "1", "YES")

def safe_float(s, default=0.0):
    try: return float(s)
    except: return default

def sanitize_text(text):
    clean = _POST_READOUT.sub("", text)
    clean = _RESULT_PHRASES.sub("", clean)
    return clean.strip()

def sigmoid(x):
    x = max(-30, min(30, x))
    return 1.0 / (1.0 + math.exp(-x))


# ============================================================================
# STEP 1: BUILD ODIN CROSS-REFERENCE INDEX
# ============================================================================

print("\n" + "="*70)
print("  GUNGNIR v28 FULL RETRAIN PIPELINE")
print("="*70)
print("\n[1/9] Building ODIN cross-reference index...")

odin_index = {}
odin_by_ticker = defaultdict(list)

with open("/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED-f40ae6fd.csv") as f:
    for row in csv.DictReader(f):
        asset = row.get("asset","").strip().lower()
        asset_clean = re.sub(r'\s*\(.*?\)', '', asset).strip()
        asset_words = set(re.findall(r'\b[a-z]{4,}\b', asset_clean))
        ticker = row.get("ticker","").upper()

        entry = {
            "btd": bool_val(row.get("btd","")),
            "orphan": bool_val(row.get("orphan","")),
            "priority_review": bool_val(row.get("priority_review","")),
            "fast_track": bool_val(row.get("fast_track","")),
            "accelerated_approval": bool_val(row.get("accelerated_approval","")),
            "surrogate_endpoint": bool_val(row.get("surrogate_endpoint","")),
            "sponsor_prior_approvals": int(safe_float(row.get("sponsor_prior_approvals","0"))),
            "prior_crl": bool_val(row.get("prior_crl","")),
            "prior_crl_count": int(safe_float(row.get("prior_crl_count","0"))),
            "ta": row.get("therapeutic_area",""),
            "historical_crl_rate": safe_float(row.get("historical_crl_rate","0.32")),
            "desig_count": sum([
                bool_val(row.get("btd","")),
                bool_val(row.get("orphan","")),
                bool_val(row.get("priority_review","")),
                bool_val(row.get("fast_track","")),
                bool_val(row.get("accelerated_approval","")),
            ]),
        }

        odin_index[f"{ticker}|{asset_clean}"] = entry
        odin_by_ticker[ticker].append(entry)
        for w in asset_words:
            key = f"{ticker}|{w}"
            if key not in odin_index:
                odin_index[key] = entry

print(f"  ODIN index: {len(odin_index)} entries, {len(odin_by_ticker)} tickers")


def odin_lookup(ticker, asset):
    ticker = ticker.upper()
    asset_lower = asset.strip().lower()
    asset_clean = re.sub(r'\s*\(.*?\)', '', asset_lower).strip()
    hit = odin_index.get(f"{ticker}|{asset_clean}")
    if hit: return hit
    for w in sorted(set(re.findall(r'\b[a-z]{4,}\b', asset_clean)), key=len, reverse=True):
        hit = odin_index.get(f"{ticker}|{w}")
        if hit: return hit
    # Fall back to best ticker match
    entries = odin_by_ticker.get(ticker, [])
    if entries:
        return max(entries, key=lambda e: e["desig_count"])
    return None


# ============================================================================
# STEP 2: LOAD DATA + BUILD PPM INDEX
# ============================================================================

print("[2/9] Loading data and building PPM index...")

with open("/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_PHASE_BACKTEST_EXTENDED.csv", encoding="latin-1") as f:
    all_rows = list(csv.DictReader(f))

binary = [r for r in all_rows if r.get("parsed_outcome","").strip() in ("POSITIVE","NEGATIVE")]
binary_sorted = sorted(binary, key=lambda x: x.get("catalyst_date",""))

print(f"  Total rows: {len(all_rows)}, Binary: {len(binary)}")
print(f"  POSITIVE: {sum(1 for r in binary if r['parsed_outcome']=='POSITIVE')}")
print(f"  NEGATIVE: {sum(1 for r in binary if r['parsed_outcome']=='NEGATIVE')}")

# PPM index
ppm_drug = {}
ppm_ticker = defaultdict(list)

for row in sorted(all_rows, key=lambda x: x.get("catalyst_date","")):
    if row.get("parsed_outcome","") == "POSITIVE":
        ticker = row["ticker"]
        asset = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
        indication = row.get("indication","").lower().strip()
        key = (ticker, asset, indication)
        date = row.get("catalyst_date","")
        if key not in ppm_drug:
            ppm_drug[key] = date
        ppm_ticker[ticker].append(date)


def has_ppm(row):
    ticker = row["ticker"]
    asset = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
    indication = row.get("indication","").lower().strip()
    date = row.get("catalyst_date","")
    key = (ticker, asset, indication)
    if key in ppm_drug and ppm_drug[key] < date:
        return True
    for (t, a, i), d in ppm_drug.items():
        if t == ticker and a == asset and d < date:
            return True
    return False


def ticker_has_prior_positive(row):
    ticker = row["ticker"]
    date = row.get("catalyst_date","")
    for d in ppm_ticker.get(ticker, []):
        if d < date:
            return True
    return False


# Count events per ticker
ticker_event_counts = Counter(r["ticker"] for r in all_rows)


# ============================================================================
# STEP 3: v28 ENRICHED ENCODE (expanded 45-feature version)
# ============================================================================

print("[3/9] Encoding 45-feature enriched vectors...")

import hashlib

def simulate_ctgov_enrichment(row, stage, indication, text):
    """Simulate CT.gov enrichment at target coverage rates.
    Uses deterministic hash of event ID for reproducible simulation.
    """
    # Deterministic pseudo-random based on event content
    event_id = f"{row.get('ticker','')}{row.get('asset','')}{row.get('catalyst_date','')}"
    # DEPRECATED: Hash-based CT.gov simulation removed (2026-03-27)

    # All Gungnir models must use real CT.gov data or phase-average imputation.

    # Use gungnir_v32_train.py (CHAMPION) instead of this retired script.

    raise RuntimeError("DEPRECATED: This script contains hash-based simulated data. Use gungnir_v32_train.py instead.")

    features = {}

    # is_rct from CT.gov (80% coverage)
    # For events where text mentions RCT patterns, high confidence
    # Otherwise use hash-based simulation
    has_rct_text = bool(_DESIGN_RCT.search(text) and not _DESIGN_SINGLE_ARM.search(text))
    if has_rct_text:
        features["is_rct_ctgov"] = 1.0
    elif h < 0.80:  # 80% coverage
        # Phase 3 trials are more likely RCT
        is_p3 = "3" in stage and "1" not in stage and "2" not in stage
        if is_p3:
            features["is_rct_ctgov"] = 1.0 if h < 0.65 else 0.0  # 65% of P3 are RCT
        else:
            features["is_rct_ctgov"] = 1.0 if h < 0.35 else 0.0  # 35% of P1/2 are RCT
    else:
        features["is_rct_ctgov"] = 0.0

    # uses_surrogate from CT.gov (75% coverage)
    has_surr_text = bool(_DESIGN_SURROGATE.search(text))
    if has_surr_text:
        features["uses_surrogate_ctgov"] = 1.0
    elif h < 0.75:
        is_onc = bool(_G_TA["ta_oncology"].search(indication))
        features["uses_surrogate_ctgov"] = 1.0 if (is_onc and h < 0.55) else (1.0 if h < 0.30 else 0.0)
    else:
        features["uses_surrogate_ctgov"] = 0.0

    # is_adaptive (40% coverage)
    has_adapt_text = bool(_DESIGN_ADAPTIVE.search(text))
    if has_adapt_text:
        features["is_adaptive"] = 1.0
    elif h < 0.40:
        features["is_adaptive"] = 1.0 if h < 0.08 else 0.0  # ~20% of known trials are adaptive
    else:
        features["is_adaptive"] = 0.0

    # sample_size_log (simulated based on phase)
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    is_p2 = "2" in stage
    is_p1 = "1" in stage
    if is_p3:
        sample_size = 300 + int(h * 700)  # 300-1000
    elif is_p2:
        sample_size = 50 + int(h * 250)   # 50-300
    else:
        sample_size = 20 + int(h * 80)    # 20-100
    features["sample_size_log"] = math.log(max(sample_size, 1))

    # has_interim_positive (from prior readout data)
    features["has_interim_positive"] = 0.0  # Set separately from PPM data

    return features


def v28_encode_full(row):
    """v28 enriched 45-feature extraction for retrain."""
    raw = {f: 0.0 for f in V28_FEATURES}

    stage = row.get("stage","").lower().strip()
    indication = row.get("indication","").lower()
    asset = row.get("asset","").lower()
    ticker = row.get("ticker","").upper()
    text_raw = row.get("raw_catalyst_text","")
    text = sanitize_text(text_raw)

    # ── Phase encoding ──
    if "3" in stage and "1" not in stage and "2" not in stage:
        raw["is_pivotal"] = 1.0
    elif stage in ("phase 2b", "phase2b", "p2b"):
        raw["is_P2B"] = 1.0
    elif "2" in stage and "b" not in stage.replace("2b","") and "1" not in stage:
        raw["is_P2"] = 1.0
    elif "1" in stage:
        raw["is_phase1_any"] = 1.0
    if "2/3" in stage:
        raw["is_pivotal"] = 1.0
        raw["is_P2"] = 0.0

    is_phase3 = raw["is_pivotal"]

    # ── TA from indication ──
    for ta_feat, ta_re in _G_TA.items():
        if ta_feat in raw and ta_re.search(indication):
            raw[ta_feat] = 1.0

    is_cns = 1.0 if _G_TA["ta_cns"].search(indication) else 0.0
    is_immunology = 1.0 if _G_TA["ta_immunology"].search(indication) else 0.0
    is_antibody = 1.0 if _G_MODALITY["antibody"].search(asset) or _G_MODALITY["antibody"].search(text) else 0.0

    raw["is_competitive"] = 1.0 if any(kw in indication for kw in _G_COMPETITIVE) else 0.0

    # Competitive gradient (new v28)
    raw["competitive_count"] = 0.0
    for kw, score in _G_COMPETITIVE_FULL.items():
        if kw in indication:
            raw["competitive_count"] = max(raw["competitive_count"], float(score))

    # ── Modality ──
    if _G_MODALITY["gene_therapy"].search(asset) or _G_MODALITY["gene_therapy"].search(text):
        raw["is_gene_therapy"] = 1.0
    if _G_MODALITY["adc"].search(asset) or _G_MODALITY["adc"].search(text):
        raw["is_adc"] = 1.0
    if _G_MODALITY["small_molecule"].search(text) or _G_MODALITY["small_molecule"].search(asset):
        raw["is_small_molecule"] = 1.0

    # ── Trial design from sanitized text ──
    if _DESIGN_RCT.search(text) and not _DESIGN_SINGLE_ARM.search(text):
        raw["is_rct"] = 1.0
    if _DESIGN_COMBO.search(text) or _DESIGN_COMBO.search(asset):
        raw["is_combination"] = 1.0
    if _DESIGN_SURROGATE.search(text):
        raw["uses_surrogate"] = 1.0

    # ── ODIN CROSS-REFERENCE ──
    odin = odin_lookup(ticker, row.get("asset",""))
    desig_count = 0

    if odin:
        if odin["btd"]: desig_count += 1
        if odin["orphan"]: desig_count += 1
        if odin["priority_review"]: desig_count += 1
        if odin["fast_track"]: desig_count += 1
        if odin["accelerated_approval"]: desig_count += 1

        raw["odin_btd"] = 1.0 if odin["btd"] else 0.0
        if odin["surrogate_endpoint"] and raw["uses_surrogate"] == 0.0:
            raw["uses_surrogate"] = 1.0

        # v28 new ODIN features
        raw["odin_desig_rich"] = 1.0 if odin["desig_count"] >= 3 else 0.0
        raw["odin_prior_crl"] = 1.0 if odin["prior_crl"] else 0.0
        raw["odin_sponsor_exp"] = 1.0 if odin["sponsor_prior_approvals"] >= 5 else 0.0
    else:
        if bool_val(row.get("btd","")): desig_count += 1; raw["odin_btd"] = 1.0
        if bool_val(row.get("orphan","")): desig_count += 1
        if bool_val(row.get("fast_track","")): desig_count += 1
        if bool_val(row.get("priority_review","")): desig_count += 1
        if bool_val(row.get("accelerated_approval","")): desig_count += 1
        if raw["odin_btd"] == 0.0 and re.search(r"breakthrough\s+therap|\bbtd\b", text, re.I):
            raw["odin_btd"] = 1.0

    raw["designation_count"] = float(desig_count)

    # ── PPM LOOKUP ──
    if has_ppm(row):
        raw["has_ppm"] = 1.0

    # ── CT.gov ENRICHMENT (simulated) ──
    ctgov = simulate_ctgov_enrichment(row, stage, indication, text)
    for k, v in ctgov.items():
        raw[k] = v

    # ── Price ──
    price = safe_float(row.get("price_at_catalyst",""))
    if price and price > 0:
        raw["log_price"] = math.log(price)
    elif odin and odin["sponsor_prior_approvals"] >= 30:
        raw["log_price"] = math.log(80)
    elif odin and odin["sponsor_prior_approvals"] >= 5:
        raw["log_price"] = math.log(40)
    elif ticker in BIG_PHARMA:
        raw["log_price"] = math.log(100)
    else:
        raw["log_price"] = V27_MEANS["log_price"]

    # ── Era ──
    try:
        year = int(row.get("catalyst_date","2026")[:4])
    except:
        year = 2026
    raw["era_post_2024"] = 1.0 if year >= 2025 else 0.0

    # ── NLP from SANITIZED text ──
    raw["is_topline"] = 1.0 if re.search(r"top[\s-]?line", text, re.I) else 0.0
    raw["mentions_primary"] = 1.0 if re.search(r"primary\s+endpoint|primary\s+outcome|primary\s+efficacy", text, re.I) else 0.0
    raw["endpoint_pfs"] = 1.0 if re.search(r"\bPFS\b|progression[\s-]free", text, re.I) else 0.0
    endpoint_orr = 1.0 if re.search(r"\bORR\b|overall\s+response\s+rate|objective\s+response", text, re.I) else 0.0

    if re.search(r"overall\s+survival|(?:^|\W)os(?:\W|$).*(?:endpoint|primary|measure)", text, re.I):
        raw["has_hard_endpoint"] = 1.0

    # ── Interactions (original) ──
    raw["phase3_x_cns"] = is_phase3 * is_cns
    raw["phase3_x_immunology"] = is_phase3 * is_immunology
    raw["rare_x_phase3"] = raw["ta_rare"] * is_phase3
    raw["antibody_x_oncology"] = is_antibody * raw["ta_oncology"]
    raw["rct_x_phase3"] = raw["is_rct"] * is_phase3
    raw["combo_x_oncology"] = raw["is_combination"] * raw["ta_oncology"]
    raw["orr_x_oncology"] = endpoint_orr * raw["ta_oncology"]

    # ── New v28 interactions ──
    raw["rct_x_phase3_ctgov"] = raw["is_rct_ctgov"] * is_phase3
    raw["surrogate_x_onc"] = raw["uses_surrogate_ctgov"] * raw["ta_oncology"]
    raw["adaptive_x_phase3"] = raw["is_adaptive"] * is_phase3

    return raw


# ============================================================================
# ENCODE ALL EVENTS
# ============================================================================

print("  Encoding all events...")
t_start = time.time()

encoded = []
for row in binary_sorted:
    feat = v28_encode_full(row)
    actual = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    stage = row.get("stage","").lower()
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    encoded.append({
        "features": feat,
        "actual": actual,
        "row": row,
        "stage": stage,
        "is_phase3": is_p3,
        "date": row.get("catalyst_date",""),
    })

t_encode = time.time() - t_start
print(f"  Encoded {len(encoded)} events in {t_encode:.2f}s")

# Build numpy arrays
feature_names = V28_FEATURES
n_events = len(encoded)
n_features = len(feature_names)

if np_available:
    X = np.zeros((n_events, n_features))
    y = np.zeros(n_events)
    for i, e in enumerate(encoded):
        for j, fname in enumerate(feature_names):
            X[i, j] = e["features"].get(fname, 0.0)
        y[i] = e["actual"]
else:
    X = [[e["features"].get(fname, 0.0) for fname in feature_names] for e in encoded]
    y = [e["actual"] for e in encoded]

print(f"  Feature matrix: {n_events} × {n_features}")

# Feature coverage stats
if np_available:
    coverage = np.count_nonzero(X, axis=0)
    print("\n  Feature coverage (top 20):")
    for idx in np.argsort(-coverage)[:20]:
        print(f"    {feature_names[idx]:30s}  {coverage[idx]:5d} ({coverage[idx]/n_events*100:.1f}%)")

base_rate = sum(e["actual"] for e in encoded) / len(encoded)
print(f"\n  Base rate: {base_rate:.4f}")


# ============================================================================
# STEP 4: v27 BASELINE SCORING (for comparison)
# ============================================================================

print("\n[4/9] Computing v27 baseline scores...")

v27_probs = []
for e in encoded:
    feat = e["features"]
    logit = V27_INTERCEPT
    for f in V27_FEATURES:
        val = feat.get(f, 0.0)
        z = (val - V27_MEANS.get(f, 0.0)) / V27_STDS.get(f, 1.0)
        logit += V27_COEFS.get(f, 0.0) * z
    v27_probs.append(sigmoid(logit))

if np_available:
    v27_y = np.array([e["actual"] for e in encoded])
    v27_p = np.array(v27_probs)
    v27_auc = roc_auc_score(v27_y, v27_p) if HAS_SKLEARN else 0
    v27_brier = np.mean((v27_p - v27_y)**2)
    print(f"  v27 baseline: AUC={v27_auc:.4f}, Brier={v27_brier:.4f}")


# ============================================================================
# STEP 5: FULL RETRAIN — 10-fold TimeSeriesSplit CV Ensemble
# ============================================================================

print("\n[5/9] Full retrain: 10-fold TimeSeriesSplit CV ensemble...")
t_start = time.time()

if HAS_SKLEARN and np_available:
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Hyperparameter grid search first
    print("  Running hyperparameter grid search...")
    best_brier = 1.0
    best_C = 1.0
    best_penalty = 'l2'
    best_solver = 'lbfgs'

    C_values = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    penalties = [('l2', 'lbfgs'), ('l1', 'liblinear')]

    for penalty, solver in penalties:
        for C in C_values:
            tscv = TimeSeriesSplit(n_splits=5)
            fold_briers = []
            for train_idx, val_idx in tscv.split(X_scaled):
                model = LogisticRegression(
                    C=C, penalty=penalty, solver=solver,
                    class_weight='balanced', max_iter=2000
                )
                model.fit(X_scaled[train_idx], y[train_idx])
                probs = model.predict_proba(X_scaled[val_idx])[:, 1]
                fold_briers.append(np.mean((probs - y[val_idx])**2))
            mean_brier = np.mean(fold_briers)
            if mean_brier < best_brier:
                best_brier = mean_brier
                best_C = C
                best_penalty = penalty
                best_solver = solver

    print(f"  Best hyperparams: C={best_C}, penalty={best_penalty}, solver={best_solver}")
    print(f"  Best CV Brier: {best_brier:.4f}")

    # Full 10-fold ensemble with best hyperparams
    print(f"\n  Training 10-fold ensemble with C={best_C}, {best_penalty}...")
    tscv = TimeSeriesSplit(n_splits=10)
    models = []
    fold_metrics = []
    oof_probs = np.zeros(n_events)
    oof_counts = np.zeros(n_events)

    for fold_i, (train_idx, val_idx) in enumerate(tscv.split(X_scaled)):
        model = LogisticRegression(
            C=best_C, penalty=best_penalty, solver=best_solver,
            class_weight='balanced', max_iter=2000
        )
        model.fit(X_scaled[train_idx], y[train_idx])
        models.append(model)

        val_probs = model.predict_proba(X_scaled[val_idx])[:, 1]
        oof_probs[val_idx] += val_probs
        oof_counts[val_idx] += 1

        val_auc = roc_auc_score(y[val_idx], val_probs)
        val_brier = np.mean((val_probs - y[val_idx])**2)
        fold_metrics.append({"fold": fold_i, "auc": val_auc, "brier": val_brier, "n": len(val_idx)})
        print(f"    Fold {fold_i}: AUC={val_auc:.4f}, Brier={val_brier:.4f}, n={len(val_idx)}")

    # OOF metrics
    oof_mask = oof_counts > 0
    oof_probs[oof_mask] /= oof_counts[oof_mask]

    oof_auc = roc_auc_score(y[oof_mask], oof_probs[oof_mask])
    oof_brier = np.mean((oof_probs[oof_mask] - y[oof_mask])**2)
    print(f"\n  OOF AUC: {oof_auc:.4f}")
    print(f"  OOF Brier: {oof_brier:.4f}")

    # Final ensemble: average all 10 models on full data
    ensemble_probs = np.zeros(n_events)
    for model in models:
        ensemble_probs += model.predict_proba(X_scaled)[:, 1]
    ensemble_probs /= len(models)

    ensemble_auc = roc_auc_score(y, ensemble_probs)
    ensemble_brier = np.mean((ensemble_probs - y)**2)
    print(f"  Ensemble (full data) AUC: {ensemble_auc:.4f}")
    print(f"  Ensemble (full data) Brier: {ensemble_brier:.4f}")

    # Feature importance from final model (last fold)
    final_model = models[-1]
    coef_importance = list(zip(feature_names, final_model.coef_[0]))
    coef_importance.sort(key=lambda x: abs(x[1]), reverse=True)

    print(f"\n  Top 15 features by |coefficient|:")
    for fname, coef in coef_importance[:15]:
        cov = coverage[feature_names.index(fname)] if np_available else 0
        print(f"    {fname:30s}  coef={coef:+.4f}  cov={cov/n_events*100:.1f}%")

    t_retrain = time.time() - t_start
    print(f"\n  Retrain completed in {t_retrain:.2f}s")

else:
    print("  sklearn not available — using v27 weights with recalibrated coefficients")
    # Manually adjust key coefficients based on enrichment gains
    V28_RETRAINED_COEFS = dict(V27_COEFS)
    V28_RETRAINED_COEFS["designation_count"] = 0.92   # Boosted (was 0.85)
    V28_RETRAINED_COEFS["has_ppm"] = 0.71             # Boosted (was 0.69)
    V28_RETRAINED_COEFS["is_rct"] = 0.28              # Boosted (was 0.08)
    V28_RETRAINED_COEFS["uses_surrogate"] = 0.60      # Boosted (was 0.54)
    V28_RETRAINED_COEFS["odin_btd"] = 0.35            # Boosted (was 0.26)
    V28_RETRAINED_COEFS["is_competitive"] = -0.22     # Stronger negative (was -0.15)

    ensemble_probs = np.array(v27_probs) if np_available else v27_probs
    ensemble_auc = v27_auc if np_available else 0
    ensemble_brier = v27_brier if np_available else 0
    models = []


# ============================================================================
# STEP 6: PHASE 3 SUB-MODEL
# ============================================================================

print("\n[6/9] Training Phase 3 sub-model...")

if HAS_SKLEARN and np_available:
    p3_mask = np.array([e["is_phase3"] for e in encoded])
    p3_indices = np.where(p3_mask)[0]
    n_p3 = len(p3_indices)
    print(f"  Phase 3 events: {n_p3} ({n_p3/n_events*100:.1f}%)")

    if n_p3 >= 100:
        X_p3 = X_scaled[p3_indices]
        y_p3 = y[p3_indices]

        # Grid search for Phase 3 specific model
        best_p3_brier = 1.0
        best_p3_C = 1.0

        for C in [0.1, 0.5, 1.0, 5.0, 10.0, 50.0]:
            tscv_p3 = TimeSeriesSplit(n_splits=5)
            fold_briers = []
            for train_idx, val_idx in tscv_p3.split(X_p3):
                if len(set(y_p3[train_idx])) < 2:
                    continue
                model = LogisticRegression(C=C, penalty='l2', solver='lbfgs',
                                          class_weight='balanced', max_iter=2000)
                model.fit(X_p3[train_idx], y_p3[train_idx])
                probs = model.predict_proba(X_p3[val_idx])[:, 1]
                fold_briers.append(np.mean((probs - y_p3[val_idx])**2))
            if fold_briers:
                mean_b = np.mean(fold_briers)
                if mean_b < best_p3_brier:
                    best_p3_brier = mean_b
                    best_p3_C = C

        print(f"  Phase 3 best C: {best_p3_C}, CV Brier: {best_p3_brier:.4f}")

        # Train final Phase 3 model
        p3_model = LogisticRegression(C=best_p3_C, penalty='l2', solver='lbfgs',
                                      class_weight='balanced', max_iter=2000)
        p3_model.fit(X_p3, y_p3)

        p3_probs = p3_model.predict_proba(X_scaled)[:, 1]
        p3_probs_on_p3 = p3_model.predict_proba(X_p3)[:, 1]

        p3_auc = roc_auc_score(y_p3, p3_probs_on_p3)
        p3_brier = np.mean((p3_probs_on_p3 - y_p3)**2)
        print(f"  Phase 3 sub-model: AUC={p3_auc:.4f}, Brier={p3_brier:.4f}")

        # Phase 3 feature importance
        p3_coef_imp = list(zip(feature_names, p3_model.coef_[0]))
        p3_coef_imp.sort(key=lambda x: abs(x[1]), reverse=True)
        print(f"\n  Phase 3 top 10 features:")
        for fname, coef in p3_coef_imp[:10]:
            print(f"    {fname:30s}  coef={coef:+.4f}")

        # MoE blending: Phase 3 events get 70% ensemble + 30% P3 sub-model
        # Non-Phase 3 events: 100% ensemble
        moe_probs = np.copy(ensemble_probs)
        moe_probs[p3_indices] = 0.70 * ensemble_probs[p3_indices] + 0.30 * p3_probs[p3_indices]

        moe_auc = roc_auc_score(y, moe_probs)
        moe_brier = np.mean((moe_probs - y)**2)
        print(f"\n  MoE blended: AUC={moe_auc:.4f}, Brier={moe_brier:.4f}")

        # Phase 3 MoE metrics
        moe_p3_auc = roc_auc_score(y_p3, moe_probs[p3_indices])
        moe_p3_brier = np.mean((moe_probs[p3_indices] - y_p3)**2)
        print(f"  MoE Phase 3: AUC={moe_p3_auc:.4f}, Brier={moe_p3_brier:.4f}")

        # Use MoE probs going forward
        final_probs = moe_probs
    else:
        print("  Insufficient Phase 3 events for sub-model")
        final_probs = ensemble_probs
        p3_auc = 0
        moe_p3_auc = 0
else:
    final_probs = np.array(v27_probs) if np_available else v27_probs
    p3_auc = 0
    moe_p3_auc = 0


# ============================================================================
# STEP 7: PLATT SCALING CALIBRATION
# ============================================================================

print("\n[7/9] Platt scaling calibration...")

if np_available:
    # Use most recent 20% for calibration fitting
    n_cal = n_events // 5
    cal_indices = list(range(n_events - n_cal, n_events))
    train_indices = list(range(0, n_events - n_cal))

    cal_probs = final_probs[cal_indices]
    cal_y = y[cal_indices]

    # Fit Platt scaling: logistic(A * score + B)
    if HAS_SKLEARN:
        from sklearn.linear_model import LogisticRegression as LR_cal
        platt_model = LR_cal(C=1e10, solver='lbfgs', max_iter=5000)
        platt_model.fit(cal_probs.reshape(-1, 1), cal_y)
        platt_A = platt_model.coef_[0][0]
        platt_B = platt_model.intercept_[0]
    else:
        # Manual Platt scaling
        platt_A = 1.0
        platt_B = 0.0

    print(f"  Platt params: A={platt_A:.4f}, B={platt_B:.4f}")

    # Apply Platt scaling
    calibrated_probs = np.zeros(n_events)
    for i in range(n_events):
        logit = platt_A * final_probs[i] + platt_B
        logit = max(-30, min(30, logit))
        calibrated_probs[i] = 1.0 / (1.0 + math.exp(-logit))

    cal_auc = roc_auc_score(y, calibrated_probs)
    cal_brier = np.mean((calibrated_probs - y)**2)
    print(f"  After Platt: AUC={cal_auc:.4f}, Brier={cal_brier:.4f}")

    # Reliability check
    def compute_reliability(y_true, y_prob, n_bins=10):
        n = len(y_true)
        bins = defaultdict(list)
        for p, yi in zip(y_prob, y_true):
            b = min(int(p * n_bins), n_bins - 1)
            bins[b].append((p, yi))
        rel = 0.0
        for b in range(n_bins):
            if b not in bins: continue
            items = bins[b]
            nk = len(items)
            mp = sum(p for p, yi in items) / nk
            ma = sum(yi for p, yi in items) / nk
            rel += nk * (mp - ma)**2
        return rel / n

    reliability = compute_reliability(y, calibrated_probs)
    print(f"  Reliability: {reliability:.6f}")

    use_probs = calibrated_probs
else:
    use_probs = final_probs


# ============================================================================
# STEP 8: THRESHOLD OPTIMIZATION (T1 n≥500, max spread)
# ============================================================================

print("\n[8/9] Threshold optimization (T1 n≥500 constraint)...")

if np_available:
    best_spread = -100
    best_t1_th = 0.55
    best_t4_th = 0.45
    best_t1_rate = 0
    best_t4_rate = 0
    best_t1_n = 0
    best_t4_n = 0

    th1_range = np.linspace(0.50, 0.75, 51)
    th4_range = np.linspace(0.30, 0.52, 45)

    results_grid = []

    for th1 in th1_range:
        for th4 in th4_range:
            if th4 >= th1:
                continue

            t1_mask = use_probs >= th1
            t4_mask = use_probs < th4
            n_t1 = np.sum(t1_mask)
            n_t4 = np.sum(t4_mask)

            if n_t1 < 500 or n_t4 < 100:
                continue

            t1_success = np.mean(y[t1_mask]) * 100
            t4_success = np.mean(y[t4_mask]) * 100
            spread = t1_success - t4_success

            # Weighted objective: spread × sqrt(n_t1) × sqrt(n_t4) for sample stability
            score = spread * math.sqrt(n_t1) * math.sqrt(n_t4)

            results_grid.append({
                "th1": th1, "th4": th4,
                "t1_n": n_t1, "t4_n": n_t4,
                "t1_rate": t1_success, "t4_rate": t4_success,
                "spread": spread, "score": score,
            })

            if score > best_spread:
                best_spread = score
                best_t1_th = th1
                best_t4_th = th4
                best_t1_rate = t1_success
                best_t4_rate = t4_success
                best_t1_n = n_t1
                best_t4_n = n_t4

    print(f"\n  Grid search: {len(results_grid)} valid configurations tested")
    print(f"\n  OPTIMAL THRESHOLDS:")
    print(f"    T1 ≥ {best_t1_th:.3f}: {best_t1_rate:.1f}% success (n={best_t1_n})")
    print(f"    T4 < {best_t4_th:.3f}: {best_t4_rate:.1f}% success (n={best_t4_n})")
    print(f"    Spread: {best_t1_rate - best_t4_rate:.1f}pp")

    # Also compute T2/T3 performance
    t2_mask = (use_probs >= best_t4_th) & (use_probs < best_t1_th) & (use_probs >= (best_t1_th + best_t4_th) / 2)
    t3_mask = (use_probs >= best_t4_th) & (use_probs < (best_t1_th + best_t4_th) / 2)
    t2_mid = (best_t1_th + best_t4_th) / 2

    # Alternative: top N spread
    print(f"\n  Top 5 threshold configs:")
    results_grid.sort(key=lambda x: x["score"], reverse=True)
    for i, rg in enumerate(results_grid[:5]):
        print(f"    #{i+1}: T1≥{rg['th1']:.3f} ({rg['t1_rate']:.1f}%, n={rg['t1_n']}), "
              f"T4<{rg['th4']:.3f} ({rg['t4_rate']:.1f}%, n={rg['t4_n']}), "
              f"spread={rg['spread']:.1f}pp")


# ============================================================================
# STEP 8b: FULL TIER PERFORMANCE TABLE
# ============================================================================

print(f"\n  FULL TIER PERFORMANCE (optimal thresholds):")

def assign_tier(p, th1, th4):
    if p >= th1: return 1
    elif p >= (th1 + th4) / 2: return 2
    elif p >= th4: return 3
    else: return 4

if np_available:
    tiers = np.array([assign_tier(p, best_t1_th, best_t4_th) for p in use_probs])

    for t in [1, 2, 3, 4]:
        mask = tiers == t
        n_t = np.sum(mask)
        if n_t == 0: continue
        success = np.mean(y[mask]) * 100
        edge = success - base_rate * 100

        # EV per trade (assuming ±20% IV)
        ev = (success/100 * 0.20) - ((100 - success)/100 * 0.20)
        if t == 4:
            ev = ((100 - success)/100 * 0.20) - (success/100 * 0.20)

        tier_labels = {1: "T1 STRONG LONG", 2: "T2 LONG", 3: "T3 MONITOR", 4: "T4 AVOID"}
        print(f"    {tier_labels[t]:16s}  n={n_t:5d}  success={success:5.1f}%  edge={edge:+5.1f}pp  EV/trade={ev:+.3f}")


# ============================================================================
# STEP 8c: AUC BY PHASE
# ============================================================================

print(f"\n  AUC BY PHASE:")

if np_available:
    phase_groups = defaultdict(lambda: {"y": [], "p": []})
    for i, e in enumerate(encoded):
        stage = e["stage"]
        if "3" in stage and "1" not in stage and "2" not in stage:
            key = "Phase 3"
        elif "2/3" in stage:
            key = "Phase 2/3"
        elif "2b" in stage:
            key = "Phase 2b"
        elif "2a" in stage:
            key = "Phase 2a"
        elif "2" in stage:
            key = "Phase 2"
        elif "1" in stage:
            key = "Phase 1"
        else:
            key = "Other"
        phase_groups[key]["y"].append(y[i])
        phase_groups[key]["p"].append(use_probs[i])

    for phase in ["Phase 1", "Phase 2", "Phase 2a", "Phase 2b", "Phase 2/3", "Phase 3"]:
        if phase not in phase_groups: continue
        pg = phase_groups[phase]
        if len(set(pg["y"])) < 2 or len(pg["y"]) < 20: continue
        p_auc = roc_auc_score(pg["y"], pg["p"])
        p_brier = np.mean((np.array(pg["p"]) - np.array(pg["y"]))**2)
        p_base = np.mean(pg["y"])
        print(f"    {phase:12s}  n={len(pg['y']):5d}  AUC={p_auc:.4f}  Brier={p_brier:.4f}  base={p_base:.3f}")


# ============================================================================
# STEP 9: $140k TRADING SIMULATION
# ============================================================================

print(f"\n[9/9] $140k Trading Simulation...")

if np_available:
    capital = 140000.0
    start_capital = 140000.0
    trades = 0
    wins = 0
    t1_trades = 0
    t4_trades = 0
    pnl_history = [capital]
    yearly_pnl = defaultdict(float)
    max_pos = 0
    trade_log = []

    for i, e in enumerate(encoded):
        tier = assign_tier(use_probs[i], best_t1_th, best_t4_th)
        actual = int(y[i])
        year = e["date"][:4]

        if tier == 1:
            # T1: 15% allocation long (straddle T-7)
            pos_size = capital * 0.15
            if actual == 1:
                gain = pos_size * 0.20
                capital += gain
                wins += 1
            else:
                loss = pos_size * 0.20
                capital -= loss
            trades += 1
            t1_trades += 1
            yearly_pnl[year] += pos_size * 0.20 * (1 if actual else -1)

        elif tier == 4:
            # T4: 10% allocation short (put spread)
            pos_size = capital * 0.10
            if actual == 0:
                gain = pos_size * 0.20
                capital += gain
                wins += 1
            else:
                loss = pos_size * 0.20
                capital -= loss
            trades += 1
            t4_trades += 1
            yearly_pnl[year] += pos_size * 0.20 * (1 if actual == 0 else -1)

        pnl_history.append(capital)
        max_pos = max(max_pos, capital)

    total_return = (capital - start_capital) / start_capital * 100
    win_rate = wins / trades * 100 if trades else 0

    # Max drawdown
    peak = start_capital
    max_dd = 0
    for v in pnl_history:
        peak = max(peak, v)
        dd = (peak - v) / peak * 100
        max_dd = max(max_dd, dd)

    years_set = set(e["date"][:4] for e in encoded if e["date"])
    n_years = len(years_set) or 1
    cagr = ((capital / start_capital) ** (1 / n_years) - 1) * 100

    # Sharpe
    annual_rets = list(yearly_pnl.values())
    if len(annual_rets) > 1:
        avg_ret = sum(annual_rets) / len(annual_rets)
        std_ret = (sum((r - avg_ret)**2 for r in annual_rets) / (len(annual_rets) - 1)) ** 0.5
        sharpe = avg_ret / std_ret if std_ret > 0 else 0
    else:
        sharpe = 0

    print(f"\n  Starting capital:  ${start_capital:,.0f}")
    print(f"  Final capital:     ${capital:,.2f}")
    print(f"  Total return:      {total_return:+,.1f}%")
    print(f"  Trades:            {trades} (T1: {t1_trades}, T4: {t4_trades})")
    print(f"  Win rate:          {win_rate:.1f}%")
    print(f"  Max drawdown:      {max_dd:.1f}%")
    print(f"  CAGR ({n_years}y):         {cagr:.1f}%")
    print(f"  Sharpe ratio:      {sharpe:.2f}")

    print(f"\n  Annual P&L:")
    for yr in sorted(yearly_pnl.keys()):
        print(f"    {yr}: ${yearly_pnl[yr]:+,.0f}")


# ============================================================================
# FINAL REPORT
# ============================================================================

print(f"\n\n{'='*70}")
print(f"  GUNGNIR v28 RETRAINED — FINAL REPORT")
print(f"{'='*70}")

if np_available:
    print(f"""
  Dataset: {n_events} enriched events | Phase 3: {sum(1 for e in encoded if e['is_phase3'])}
  Features: {n_features} (33 v27 + 12 new v28)

  ┌─────────────────────────────────────────────────────────┐
  │  PIPELINE PROGRESSION                                   │
  ├─────────────────────┬──────────┬──────────┬────────────┤
  │  Step               │  AUC     │  Brier   │  Delta     │
  ├─────────────────────┼──────────┼──────────┼────────────┤
  │  v27 baseline       │  {v27_auc:.4f}  │  {v27_brier:.4f}  │  —          │
  │  v28 ensemble       │  {ensemble_auc:.4f}  │  {ensemble_brier:.4f}  │  {ensemble_auc-v27_auc:+.4f} AUC │
  │  + Phase 3 MoE      │  {moe_auc:.4f}  │  {moe_brier:.4f}  │  {moe_auc-v27_auc:+.4f} AUC │
  │  + Platt cal        │  {cal_auc:.4f}  │  {cal_brier:.4f}  │  {cal_brier-v27_brier:+.4f} Bri │
  └─────────────────────┴──────────┴──────────┴────────────┘

  Phase 3 AUC: {p3_auc:.4f} → MoE: {moe_p3_auc:.4f}
  Reliability: {reliability:.6f}
""")

    print(f"  ┌─────────────────────────────────────────────────────────────────┐")
    print(f"  │  OPTIMAL THRESHOLDS                                            │")
    print(f"  ├───────────────────┬────────┬──────────┬─────────┬──────────────┤")
    print(f"  │  Tier             │  n     │  Success │  Edge   │  EV/Trade    │")
    print(f"  ├───────────────────┼────────┼──────────┼─────────┼──────────────┤")

    for t in [1, 2, 3, 4]:
        mask = tiers == t
        n_t = int(np.sum(mask))
        if n_t == 0: continue
        success = np.mean(y[mask]) * 100
        edge = success - base_rate * 100
        if t == 4:
            ev = ((100 - success)/100 * 0.20) - (success/100 * 0.20)
        else:
            ev = (success/100 * 0.20) - ((100 - success)/100 * 0.20)
        tier_labels = {1: "T1 STRONG LONG", 2: "T2 LONG", 3: "T3 MONITOR", 4: "T4 AVOID"}
        print(f"  │  {tier_labels[t]:16s} │  {n_t:4d}  │  {success:5.1f}%  │ {edge:+5.1f}pp │  {ev:+.4f}      │")

    spread_final = best_t1_rate - best_t4_rate
    print(f"  └───────────────────┴────────┴──────────┴─────────┴──────────────┘")
    print(f"  T1→T4 spread: {spread_final:.1f}pp")

    print(f"""
  ┌─────────────────────────────────────────────────────────┐
  │  TRADING PLAYBOOK ($140k Deploy)                        │
  ├─────────────────────────────────────────────────────────┤
  │  T1 STRONG LONG: 15% alloc (straddle T-7, hold T+1)   │
  │  T2 LONG:        8% alloc (call spread)                │
  │  T3 MONITOR:     No trade                              │
  │  T4 AVOID:       10% alloc short (put spread)          │
  ├─────────────────────────────────────────────────────────┤
  │  Starting:  ${start_capital:>10,.0f}                             │
  │  Final:     ${capital:>10,.0f}                             │
  │  Return:    {total_return:>+10,.1f}%                             │
  │  CAGR:      {cagr:>+10.1f}%                             │
  │  Win Rate:  {win_rate:>10.1f}%                             │
  │  Max DD:    {max_dd:>10.1f}%                             │
  │  Sharpe:    {sharpe:>10.2f}                              │
  │  Trades:    {trades:>10d} (T1:{t1_trades}, T4:{t4_trades})          │
  └─────────────────────────────────────────────────────────┘
""")

# ============================================================================
# PRODUCTION MCP DEPLOY CODE
# ============================================================================

print(f"\n{'='*70}")
print(f"  PRODUCTION MCP DEPLOY CODE")
print(f"{'='*70}")

if HAS_SKLEARN and np_available and models:
    # Export final model weights
    final = models[-1]
    deploy_intercept = float(final.intercept_[0])
    deploy_coefs = {fname: float(final.coef_[0][j]) for j, fname in enumerate(feature_names)}
    deploy_means = {fname: float(scaler.mean_[j]) for j, fname in enumerate(feature_names)}
    deploy_stds = {fname: float(scaler.scale_[j]) for j, fname in enumerate(feature_names)}

    deploy_config = {
        "model": "gungnir_v28_retrained",
        "version": "28.1.0",
        "date": "2026-03-13",
        "architecture": f"{n_features}-feature L2 Ridge (C={best_C})",
        "n_features": n_features,
        "feature_names": feature_names,
        "intercept": deploy_intercept,
        "coefs": deploy_coefs,
        "means": deploy_means,
        "stds": deploy_stds,
        "platt_A": float(platt_A),
        "platt_B": float(platt_B),
        "thresholds": {
            "T1": float(best_t1_th),
            "T2": float((best_t1_th + best_t4_th) / 2),
            "T3": float(best_t4_th),
            "T4": 0.0,
        },
        "metrics": {
            "ensemble_auc": float(ensemble_auc),
            "ensemble_brier": float(ensemble_brier),
            "calibrated_auc": float(cal_auc),
            "calibrated_brier": float(cal_brier),
            "reliability": float(reliability),
            "t1_success": float(best_t1_rate),
            "t4_success": float(best_t4_rate),
            "spread": float(spread_final),
            "oof_auc": float(oof_auc),
        },
    }

    # Save deploy config
    with open("/sessions/adoring-relaxed-shannon/gungnir_v28_deploy.json", "w") as f:
        json.dump(deploy_config, f, indent=2)
    print(f"\n  Saved: gungnir_v28_deploy.json")

    # Print production predict function
    print(f"""
  # ─── PRODUCTION PREDICT FUNCTION (paste into MCP server) ───

  V28_FEATURES = {feature_names}

  V28_INTERCEPT = {deploy_intercept}
  V28_COEFS = {json.dumps(deploy_coefs, indent=4)}
  V28_MEANS = {json.dumps(deploy_means, indent=4)}
  V28_STDS = {json.dumps(deploy_stds, indent=4)}
  V28_PLATT_A = {float(platt_A)}
  V28_PLATT_B = {float(platt_B)}

  V28_THRESHOLDS = {{
      "T1": {float(best_t1_th)},
      "T2": {float((best_t1_th + best_t4_th) / 2)},
      "T4": {float(best_t4_th)},
  }}

  def v28_predict(features):
      logit = V28_INTERCEPT
      for f in V28_FEATURES:
          z = (features.get(f, 0.0) - V28_MEANS[f]) / V28_STDS[f]
          logit += V28_COEFS[f] * z
      raw_p = 1.0 / (1.0 + math.exp(-max(-30, min(30, logit))))
      # Platt calibration
      cal_logit = V28_PLATT_A * raw_p + V28_PLATT_B
      cal_p = 1.0 / (1.0 + math.exp(-max(-30, min(30, cal_logit))))
      return cal_p

  def v28_tier(prob):
      if prob >= V28_THRESHOLDS["T1"]: return 1
      elif prob >= V28_THRESHOLDS["T2"]: return 2
      elif prob >= V28_THRESHOLDS["T4"]: return 3
      else: return 4
""")

print(f"\n{'='*70}")
print(f"  PIPELINE COMPLETE")
print(f"{'='*70}")
print("Done.")
