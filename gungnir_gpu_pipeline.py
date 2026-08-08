#!/usr/bin/env python3
"""
GUNGNIR v28 GPU BRIER CRUSHER — RTX 4070 Pipeline
====================================================
Goal: MINIMIZE Brier score using every tool available:
  1. XGBoost GPU with massive hyperparameter grid
  2. PyTorch MLP ensemble on CUDA
  3. Meta-learner stacking (LR + XGB + NN)
  4. Isotonic + Platt + Beta calibration
  5. Temperature scaling on GPU

Current: Brier=0.2279 (logistic regression)
Baseline: Brier=0.249 (constant predictor at 53.2%)
Target:  Brier≤0.16
"""

import csv, math, re, hashlib, json, time, sys, os
from collections import defaultdict, Counter
import numpy as np

# ============================================================================
# GPU CHECK
# ============================================================================
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    HAS_TORCH = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"PyTorch: {torch.__version__}, Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}, VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f}GB")
except ImportError:
    HAS_TORCH = False
    DEVICE = "cpu"
    print("PyTorch not available, using CPU-only pipeline")

try:
    import xgboost as xgb
    HAS_XGB = True
    print(f"XGBoost: {xgb.__version__}")
except ImportError:
    HAS_XGB = False
    print("XGBoost not available")

try:
    import lightgbm as lgb
    HAS_LGB = True
    print(f"LightGBM: {lgb.__version__}")
except ImportError:
    HAS_LGB = False
    print("LightGBM not available")

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression

# ============================================================================
# DATA PATHS (Windows)
# ============================================================================
BASE = r"C:\Users\dcmoo\gungnir_gpu"
BACKTEST_PATH = os.path.join(BASE, "BACKTEST.csv")
ODIN_PATH = os.path.join(BASE, "ODIN.csv")

# ============================================================================
# NLP + FEATURE ENCODING (same as v28.3.0 — integrity-fixed)
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
    "ta_cardiovascular": re.compile(r"cardiovasc|heart\s+fail|atrial|myocardial|coronary|hypertens|arrhyth|angina|cardiomyopath|thrombos|anticoagul|mace\b", re.I),
}
_G_COMPETITIVE_FULL = {
    "nsclc": 5, "non-small cell lung cancer": 5, "breast cancer": 4,
    "aml": 3, "acute myeloid leukemia": 3, "mdd": 4,
    "major depressive disorder": 4, "alzheimer": 3, "prostate cancer": 3,
    "type 2 diabetes": 5, "obesity": 4, "copd": 3, "asthma": 3,
    "chronic pain": 3, "als": 2, "multiple myeloma": 3,
    "non-hodgkin lymphoma": 2, "atopic dermatitis": 3, "psoriasis": 3,
    "rheumatoid arthritis": 3, "crohn": 2, "nash": 3, "mash": 3,
}
_G_COMPETITIVE = set(_G_COMPETITIVE_FULL.keys())
_G_MODALITY = {
    "gene_therapy": re.compile(r"gene\s*therap|aav|crispr|base\s*edit|lentivir", re.I),
    "adc": re.compile(r"antibody.drug\s+conjug|\badc\b|drug\s+conjugat", re.I),
    "small_molecule": re.compile(r"small\s+molecul|oral|tablet|capsule|inhibitor|antagonist|agonist", re.I),
    "antibody": re.compile(r"antibod|mab\b|-mab\b|bispecific", re.I),
}
_DESIGN_COMBO = re.compile(r"combination|combo|plus\s+\w+mab|with\s+\w+mab|\+\s+\w+mab", re.I)
_DESIGN_SURROGATE = re.compile(r"surrogate|biomarker|response\s+rate|tumor\s+(?:reduction|shrink)", re.I)
_POST_READOUT = re.compile(r"(data\s+(?:released|reported|showed|presented|announced|demonstrated|revealed|from\s+\w+\s+(?:reported|showed)).*)", re.I | re.DOTALL)
_RESULT_PHRASES = re.compile(
    r"((?:met|failed|missed|did\s+not\s+meet|statistically\s+significant|not\s+statistically|"
    r"primary\s+endpoint\s+(?:met|not|was)|ORR\s+(?:was|of)\s+\d|PFS\s+(?:was|of)\s+\d|OS\s+(?:was|of)\s+\d|"
    r"median\s+\w+\s+was|achieved|demonstrated\s+(?:statistical|significant|positive|negative)|"
    r"p[\s-]?value\s*(?:=|of|was)\s*[0-9]|hazard\s+ratio\s*(?:=|of|was)\s*[0-9]|"
    r"(?:positive|negative|mixed|disappointing|encouraging)\s+(?:data|results|outcome|readout)|"
    r"(?:FDA|EMA)\s+(?:approved|rejected|accepted|refused)|"
    r"(?:stock|share|shares)\s+(?:surged|plummeted|jumped|dropped|fell|rose|spiked)).*?)(?:\.|$)", re.I)

BIG_PHARMA = {"PFE","MRK","LLY","ABBV","BMY","JNJ","AZN","RHHBY","NVS","SNY","GSK","AMGN","GILD","REGN","BIIB","VRTX","MRNA","BNTX","TAK","NVO","TEVA"}

CTGOV_REAL = {
    "p3_onc_blind_rate": 0.48, "p3_immuno_blind_rate": 0.83, "p3_cns_blind_rate": 0.67,
    "p3_metabolic_blind_rate": 0.56, "p3_rare_blind_rate": 0.29, "p3_infectious_blind_rate": 0.64,
    "p3_ophtho_blind_rate": 1.00, "p3_cardio_blind_rate": 0.56, "p3_generic_blind_rate": 0.55,
    "p3_onc_enroll": 435, "p3_immuno_enroll": 315, "p3_cns_enroll": 227,
    "p3_metabolic_enroll": 338, "p3_rare_enroll": 43, "p3_infectious_enroll": 480,
    "p3_ophtho_enroll": 1116, "p3_cardio_enroll": 450, "p3_generic_enroll": 400,
    "p3_onc_hard_rate": 0.64, "p3_immuno_hard_rate": 0.33, "p3_cns_hard_rate": 0.50,
    "p3_metabolic_hard_rate": 0.16, "p3_rare_hard_rate": 0.57, "p3_infectious_hard_rate": 0.48,
    "p3_cardio_hard_rate": 0.72, "p3_generic_hard_rate": 0.45,
    "p2_onc_blind_rate": 0.44, "p2_immuno_blind_rate": 0.69, "p2_generic_blind_rate": 0.40,
    "p2_onc_enroll": 63, "p2_immuno_enroll": 98, "p2_generic_enroll": 80,
    "p1_blind_rate": 0.15, "p1_enroll": 30,
}

def bool_val(s):
    if isinstance(s, bool): return s
    return str(s).strip().upper() in ("TRUE", "1", "YES")

def safe_float(s, default=0.0):
    try: return float(re.sub(r'[^0-9.\-]', '', str(s)))
    except: return default

def sanitize_text(text):
    clean = _POST_READOUT.sub("", text)
    clean = _RESULT_PHRASES.sub("", clean)
    return clean.strip()

def get_ta_key(indication):
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(indication):
            return ta_name.replace("ta_", "")
    return "generic"

# Extended feature set — 50+ features for tree models
FEATURES = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious",
    "ta_ophthalmology", "ta_pain", "ta_cardiovascular",
    "is_gene_therapy", "is_adc", "is_small_molecule", "is_antibody",
    "is_double_blind", "is_open_label", "is_combination", "uses_surrogate",
    "endpoint_hardness", "log_enrollment",
    "designation_count", "odin_btd", "odin_desig_rich", "odin_sponsor_exp",
    "has_ppm", "log_price", "era_post_2024",
    "is_topline", "mentions_primary", "endpoint_pfs",
    "is_competitive", "competitive_count",
    "phase3_x_cns", "phase3_x_immunology", "rare_x_phase3",
    "antibody_x_oncology", "combo_x_oncology",
    "blind_x_phase3", "enroll_x_phase3", "os_x_oncology",
    "hard_x_phase3", "rare_small_enroll",
    # NEW for tree models — more granular features
    "is_big_pharma",
    "ta_count",           # how many TAs match (multi-indication)
    "price_bucket_low",   # <$5
    "price_bucket_mid",   # $5-50
    "price_bucket_high",  # >$50
    "year_ordinal",       # year as ordinal
    "enrollment_bucket",  # categorical enrollment size
    "is_resubmission",    # from text
    "has_fast_track",     # from ODIN
    "has_orphan",         # from ODIN
]

print("\n" + "="*70)
print("  GUNGNIR v28 GPU BRIER CRUSHER")
print("="*70)

# ============================================================================
# LOAD AND ENCODE
# ============================================================================
print("\n[1/6] Loading and encoding data...")

# Build ODIN index
odin_index = {}
odin_by_ticker = defaultdict(list)
with open(ODIN_PATH, encoding="utf-8") as f:
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
            "desig_count": sum([bool_val(row.get(k,"")) for k in ["btd","orphan","priority_review","fast_track","accelerated_approval"]]),
        }
        odin_index[f"{ticker}|{asset_clean}"] = entry
        odin_by_ticker[ticker].append(entry)
        for w in asset_words:
            if f"{ticker}|{w}" not in odin_index:
                odin_index[f"{ticker}|{w}"] = entry

def odin_lookup(ticker, asset):
    ticker = ticker.upper()
    asset_clean = re.sub(r'\s*\(.*?\)', '', asset.strip().lower()).strip()
    hit = odin_index.get(f"{ticker}|{asset_clean}")
    if hit: return hit
    for w in sorted(set(re.findall(r'\b[a-z]{4,}\b', asset_clean)), key=len, reverse=True):
        hit = odin_index.get(f"{ticker}|{w}")
        if hit: return hit
    return None  # NO ticker-only fallback

# Load backtest
with open(BACKTEST_PATH, encoding="latin-1") as f:
    all_rows = list(csv.DictReader(f))

binary = [r for r in all_rows if r.get("parsed_outcome","").strip() in ("POSITIVE","NEGATIVE")]
binary_sorted = sorted(binary, key=lambda x: x.get("catalyst_date",""))

# Dedup
seen = set()
deduped = []
for row in binary_sorted:
    key = f"{row['ticker']}|{row.get('catalyst_date','')}|{row.get('asset','')}"
    if key not in seen:
        seen.add(key)
        deduped.append(row)
binary_sorted = deduped

# Build strict PPM
ppm_drug = defaultdict(list)
for row in sorted(all_rows, key=lambda x: x.get("catalyst_date","")):
    if row.get("parsed_outcome","") == "POSITIVE":
        ticker = row["ticker"]
        asset = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
        ppm_drug[(ticker, asset)].append(row.get("catalyst_date",""))

def has_ppm(row):
    ticker = row["ticker"]
    asset = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
    date = row.get("catalyst_date","")
    for d in ppm_drug.get((ticker, asset), []):
        if d < date: return True
    return False

print(f"  Events: {len(binary_sorted)}")


def encode(row):
    raw = {f: 0.0 for f in FEATURES}
    stage = row.get("stage","").lower().strip()
    indication = row.get("indication","").lower()
    asset = row.get("asset","").lower()
    ticker = row.get("ticker","").upper()
    text = sanitize_text(row.get("raw_catalyst_text",""))

    # Phase
    if "3" in stage and "1" not in stage and "2" not in stage: raw["is_pivotal"] = 1.0
    elif stage in ("phase 2b","phase2b","p2b"): raw["is_P2B"] = 1.0
    elif "2" in stage and "1" not in stage: raw["is_P2"] = 1.0
    elif "1" in stage: raw["is_phase1_any"] = 1.0
    if "2/3" in stage: raw["is_pivotal"] = 1.0; raw["is_P2"] = 0.0
    is_p3 = raw["is_pivotal"]

    # TA
    ta_count = 0
    is_onc = is_cns = is_immuno = is_cardio = 0.0
    for ta_feat, ta_re in _G_TA.items():
        if ta_feat in raw and ta_re.search(indication):
            raw[ta_feat] = 1.0; ta_count += 1
        if ta_feat == "ta_oncology" and ta_re.search(indication): is_onc = 1.0
        if ta_feat == "ta_cns" and ta_re.search(indication): is_cns = 1.0
        if ta_feat == "ta_immunology" and ta_re.search(indication): is_immuno = 1.0
        if ta_feat == "ta_cardiovascular" and ta_re.search(indication): is_cardio = 1.0
    raw["ta_count"] = float(ta_count)

    # Modality
    is_antibody = 0.0
    for mod, pat in _G_MODALITY.items():
        if pat.search(asset) or pat.search(text):
            if mod == "antibody": is_antibody = 1.0
            if f"is_{mod}" in raw: raw[f"is_{mod}"] = 1.0
    raw["is_antibody"] = is_antibody

    # Competition
    raw["is_competitive"] = 1.0 if any(kw in indication for kw in _G_COMPETITIVE) else 0.0
    for kw, score in _G_COMPETITIVE_FULL.items():
        if kw in indication: raw["competitive_count"] = max(raw["competitive_count"], float(score))

    # Combo / surrogate
    if _DESIGN_COMBO.search(text) or _DESIGN_COMBO.search(asset): raw["is_combination"] = 1.0
    if _DESIGN_SURROGATE.search(text): raw["uses_surrogate"] = 1.0

    # CT.gov-calibrated features
    # DEPRECATED: Hash-based CT.gov simulation removed (2026-03-27)

    # All Gungnir models must use real CT.gov data or phase-average imputation.

    # Use gungnir_v32_train.py (CHAMPION) instead of this retired script.

    raise RuntimeError("DEPRECATED: This script contains hash-based simulated data. Use gungnir_v32_train.py instead.")
    ta_key = get_ta_key(indication)

    if re.search(r"double.?blind|placebo.?control|triple.?blind|quadruple.?blind", text, re.I):
        raw["is_double_blind"] = 1.0
    elif re.search(r"open.?label|single.?arm|unblinded", text, re.I):
        raw["is_double_blind"] = 0.0
    else:
        if is_p3: rate = CTGOV_REAL.get(f"p3_{ta_key}_blind_rate", CTGOV_REAL["p3_generic_blind_rate"])
        elif raw["is_P2"] or raw["is_P2B"]: rate = CTGOV_REAL.get(f"p2_{ta_key}_blind_rate", CTGOV_REAL["p2_generic_blind_rate"])
        else: rate = CTGOV_REAL["p1_blind_rate"]
        raw["is_double_blind"] = 1.0 if h < rate else 0.0
    raw["is_open_label"] = 1.0 - raw["is_double_blind"]

    if is_p3: med_enr = CTGOV_REAL.get(f"p3_{ta_key}_enroll", CTGOV_REAL["p3_generic_enroll"])
    elif raw["is_P2"] or raw["is_P2B"]: med_enr = CTGOV_REAL.get(f"p2_{ta_key}_enroll", CTGOV_REAL["p2_generic_enroll"])
    else: med_enr = CTGOV_REAL["p1_enroll"]
    enroll = max(int(med_enr * 0.5) + int(h * med_enr * 1.3), 10)
    raw["log_enrollment"] = math.log(enroll)
    raw["enrollment_bucket"] = 0 if enroll < 50 else (1 if enroll < 200 else (2 if enroll < 500 else 3))

    if re.search(r"overall.?survival|(?:^|\W)OS(?:\W|$).*(?:endpoint|primary)|mortality|MACE", text, re.I):
        raw["endpoint_hardness"] = 1.0
    elif re.search(r"\bPFS\b|progression.?free|disease.?free", text, re.I):
        raw["endpoint_hardness"] = 0.5
    elif re.search(r"\bORR\b|response.?rate|objective.?response", text, re.I):
        raw["endpoint_hardness"] = 0.0
    else:
        raw["endpoint_hardness"] = CTGOV_REAL.get(f"p3_{ta_key}_hard_rate", CTGOV_REAL["p3_generic_hard_rate"]) if is_p3 else 0.2

    # ODIN (strict)
    odin = odin_lookup(ticker, row.get("asset",""))
    desig_count = 0
    if odin:
        for k in ["btd","orphan","priority_review","fast_track","accelerated_approval"]:
            if odin.get(k): desig_count += 1
        raw["odin_btd"] = 1.0 if odin["btd"] else 0.0
        raw["odin_desig_rich"] = 1.0 if odin["desig_count"] >= 3 else 0.0
        raw["odin_sponsor_exp"] = 1.0 if odin["sponsor_prior_approvals"] >= 5 else 0.0
        raw["has_fast_track"] = 1.0 if odin["fast_track"] else 0.0
        raw["has_orphan"] = 1.0 if odin["orphan"] else 0.0
        if odin["surrogate_endpoint"]: raw["uses_surrogate"] = 1.0
    else:
        if bool_val(row.get("btd","")): desig_count += 1; raw["odin_btd"] = 1.0
        if bool_val(row.get("orphan","")): desig_count += 1; raw["has_orphan"] = 1.0
        if bool_val(row.get("fast_track","")): desig_count += 1; raw["has_fast_track"] = 1.0
        if bool_val(row.get("priority_review","")): desig_count += 1
        if bool_val(row.get("accelerated_approval","")): desig_count += 1
    raw["designation_count"] = float(desig_count)

    # PPM
    if has_ppm(row): raw["has_ppm"] = 1.0

    # Price
    price = safe_float(row.get("price_at_catalyst",""))
    if not price or price <= 0:
        price = 100 if ticker in BIG_PHARMA else 20
    raw["log_price"] = math.log(max(price, 1))
    raw["price_bucket_low"] = 1.0 if price < 5 else 0.0
    raw["price_bucket_mid"] = 1.0 if 5 <= price < 50 else 0.0
    raw["price_bucket_high"] = 1.0 if price >= 50 else 0.0
    raw["is_big_pharma"] = 1.0 if ticker in BIG_PHARMA else 0.0

    # Era
    try: year = int(row.get("catalyst_date","2026")[:4])
    except: year = 2026
    raw["era_post_2024"] = 1.0 if year >= 2025 else 0.0
    raw["year_ordinal"] = float(year - 2015)

    # NLP
    raw["is_topline"] = 1.0 if re.search(r"top[\s-]?line", text, re.I) else 0.0
    raw["mentions_primary"] = 1.0 if re.search(r"primary\s+endpoint|primary\s+outcome", text, re.I) else 0.0
    raw["endpoint_pfs"] = 1.0 if re.search(r"\bPFS\b|progression[\s-]free", text, re.I) else 0.0
    raw["is_resubmission"] = 1.0 if re.search(r"resubmi|re-submi|second\s+attempt|prior\s+(?:CRL|rejection)", text, re.I) else 0.0

    # Interactions
    raw["phase3_x_cns"] = is_p3 * is_cns
    raw["phase3_x_immunology"] = is_p3 * is_immuno
    raw["rare_x_phase3"] = raw["ta_rare"] * is_p3
    raw["antibody_x_oncology"] = is_antibody * raw["ta_oncology"]
    raw["combo_x_oncology"] = raw["is_combination"] * raw["ta_oncology"]
    raw["blind_x_phase3"] = raw["is_double_blind"] * is_p3
    raw["enroll_x_phase3"] = raw["log_enrollment"] * is_p3
    raw["os_x_oncology"] = raw["endpoint_hardness"] * raw["ta_oncology"]
    raw["hard_x_phase3"] = raw["endpoint_hardness"] * is_p3
    raw["rare_small_enroll"] = raw["ta_rare"] * (1.0 if raw["log_enrollment"] < math.log(100) else 0.0)

    return raw


# Encode all
t0 = time.time()
encoded_rows = []
for row in binary_sorted:
    feat = encode(row)
    actual = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    encoded_rows.append({"features": feat, "actual": actual, "date": row.get("catalyst_date",""),
                         "stage": row.get("stage","").lower()})

n_events = len(encoded_rows)
n_features = len(FEATURES)
X = np.zeros((n_events, n_features), dtype=np.float32)
y = np.zeros(n_events, dtype=np.float32)
for i, e in enumerate(encoded_rows):
    for j, fname in enumerate(FEATURES):
        X[i, j] = e["features"].get(fname, 0.0)
    y[i] = e["actual"]

base_rate = np.mean(y)
baseline_brier = base_rate * (1 - base_rate)
print(f"  Encoded: {n_events} × {n_features} in {time.time()-t0:.1f}s")
print(f"  Base rate: {base_rate:.4f}")
print(f"  Baseline Brier (constant): {baseline_brier:.4f}")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)


# ============================================================================
# [2/6] XGBOOST GPU GRID SEARCH
# ============================================================================
print(f"\n[2/6] XGBoost GPU hyperparameter grid search...")

if HAS_XGB:
    # Massive grid search on GPU
    xgb_grid = {
        "max_depth": [3, 4, 5, 6, 7, 8],
        "learning_rate": [0.005, 0.01, 0.02, 0.05, 0.1],
        "n_estimators": [200, 500, 1000, 2000],
        "subsample": [0.6, 0.7, 0.8, 0.9],
        "colsample_bytree": [0.5, 0.6, 0.7, 0.8, 1.0],
        "min_child_weight": [1, 3, 5, 10],
        "reg_alpha": [0, 0.01, 0.1, 1.0],
        "reg_lambda": [0.5, 1.0, 2.0, 5.0],
        "gamma": [0, 0.1, 0.5, 1.0],
        "scale_pos_weight": [1.0, base_rate/(1-base_rate), (1-base_rate)/base_rate],
    }

    # Use random search over the massive grid
    np.random.seed(42)
    n_random_configs = 300  # 300 random combos on GPU
    best_xgb_brier = 1.0
    best_xgb_config = {}
    best_xgb_oof = None

    # Check if GPU device is available for XGBoost
    try:
        test_dtrain = xgb.DMatrix(X_scaled[:10], label=y[:10])
        test_params = {"device": "cuda", "max_depth": 3, "objective": "binary:logistic", "eval_metric": "logloss"}
        xgb.train(test_params, test_dtrain, num_boost_round=2, verbose_eval=False)
        XGB_DEVICE = "cuda"
        print(f"  XGBoost GPU: CUDA active")
    except Exception as e:
        XGB_DEVICE = "cpu"
        print(f"  XGBoost GPU unavailable ({e}), using CPU")

    tscv = TimeSeriesSplit(n_splits=5)
    t_xgb = time.time()

    for config_i in range(n_random_configs):
        config = {k: np.random.choice(v) for k, v in xgb_grid.items()}

        params = {
            "device": XGB_DEVICE,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": int(config["max_depth"]),
            "learning_rate": float(config["learning_rate"]),
            "subsample": float(config["subsample"]),
            "colsample_bytree": float(config["colsample_bytree"]),
            "min_child_weight": int(config["min_child_weight"]),
            "reg_alpha": float(config["reg_alpha"]),
            "reg_lambda": float(config["reg_lambda"]),
            "gamma": float(config["gamma"]),
            "scale_pos_weight": float(config["scale_pos_weight"]),
            "verbosity": 0,
        }
        n_rounds = int(config["n_estimators"])

        fold_briers = []
        oof = np.zeros(n_events)
        oof_mask = np.zeros(n_events)

        try:
            for train_idx, val_idx in tscv.split(X):
                dtrain = xgb.DMatrix(X[train_idx], label=y[train_idx], feature_names=FEATURES)
                dval = xgb.DMatrix(X[val_idx], label=y[val_idx], feature_names=FEATURES)
                model = xgb.train(params, dtrain, num_boost_round=n_rounds,
                                  evals=[(dval, "val")], early_stopping_rounds=50,
                                  verbose_eval=False)
                preds = model.predict(dval)
                brier = np.mean((preds - y[val_idx])**2)
                fold_briers.append(brier)
                oof[val_idx] = preds
                oof_mask[val_idx] = 1

            mean_brier = np.mean(fold_briers)

            if mean_brier < best_xgb_brier:
                best_xgb_brier = mean_brier
                best_xgb_config = {**config, "n_rounds_actual": model.best_iteration if hasattr(model, 'best_iteration') else n_rounds}
                best_xgb_oof = oof.copy()
                if config_i % 20 == 0 or mean_brier < 0.22:
                    print(f"    [{config_i+1}/{n_random_configs}] NEW BEST: Brier={mean_brier:.6f}  "
                          f"depth={int(config['max_depth'])} lr={config['learning_rate']:.3f} "
                          f"n={n_rounds} ss={config['subsample']:.1f}")
        except Exception as e:
            continue

        if config_i % 50 == 0 and config_i > 0:
            elapsed = time.time() - t_xgb
            rate = config_i / elapsed
            print(f"    Progress: {config_i}/{n_random_configs} ({elapsed:.0f}s, {rate:.1f} configs/s), best={best_xgb_brier:.6f}")

    xgb_time = time.time() - t_xgb
    print(f"\n  XGBoost grid done: {n_random_configs} configs in {xgb_time:.0f}s")
    print(f"  Best XGBoost Brier: {best_xgb_brier:.6f}")
    print(f"  Config: {json.dumps({k: float(v) if isinstance(v, (np.floating, float)) else int(v) if isinstance(v, (np.integer, int)) else v for k, v in best_xgb_config.items()}, indent=4)}")

    # Retrain best XGBoost on full data
    best_params = {
        "device": XGB_DEVICE,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": int(best_xgb_config["max_depth"]),
        "learning_rate": float(best_xgb_config["learning_rate"]),
        "subsample": float(best_xgb_config["subsample"]),
        "colsample_bytree": float(best_xgb_config["colsample_bytree"]),
        "min_child_weight": int(best_xgb_config["min_child_weight"]),
        "reg_alpha": float(best_xgb_config["reg_alpha"]),
        "reg_lambda": float(best_xgb_config["reg_lambda"]),
        "gamma": float(best_xgb_config["gamma"]),
        "scale_pos_weight": float(best_xgb_config["scale_pos_weight"]),
        "verbosity": 0,
    }
    dtrain_full = xgb.DMatrix(X, label=y, feature_names=FEATURES)
    xgb_full = xgb.train(best_params, dtrain_full,
                          num_boost_round=int(best_xgb_config.get("n_rounds_actual", 500)))
    xgb_full_probs = xgb_full.predict(dtrain_full)
    xgb_full_auc = roc_auc_score(y, xgb_full_probs)
    xgb_full_brier = np.mean((xgb_full_probs - y)**2)
    print(f"  XGBoost full retrain: AUC={xgb_full_auc:.4f}, Brier={xgb_full_brier:.6f}")

    # Feature importance
    importance = xgb_full.get_score(importance_type='gain')
    top_imp = sorted(importance.items(), key=lambda x: -x[1])[:15]
    print(f"\n  XGBoost top features:")
    for fname, gain in top_imp:
        print(f"    {fname:30s}  gain={gain:.2f}")
else:
    print("  SKIPPED (no XGBoost)")
    best_xgb_brier = 1.0
    best_xgb_oof = np.full(n_events, base_rate)
    xgb_full_probs = np.full(n_events, base_rate)


# ============================================================================
# [3/6] PYTORCH MLP ENSEMBLE ON GPU
# ============================================================================
print(f"\n[3/6] PyTorch MLP ensemble on {DEVICE}...")

if HAS_TORCH and DEVICE.type == "cuda":
    class MLPClassifier(nn.Module):
        def __init__(self, input_dim, hidden_dims, dropout=0.3):
            super().__init__()
            layers = []
            prev_dim = input_dim
            for hd in hidden_dims:
                layers.extend([nn.Linear(prev_dim, hd), nn.BatchNorm1d(hd), nn.GELU(), nn.Dropout(dropout)])
                prev_dim = hd
            layers.append(nn.Linear(prev_dim, 1))
            self.net = nn.Sequential(*layers)

        def forward(self, x):
            return self.net(x).squeeze(-1)

    # MLP architectures to try
    MLP_CONFIGS = [
        {"hidden_dims": [128, 64, 32], "dropout": 0.3, "lr": 0.001, "epochs": 300, "wd": 1e-4},
        {"hidden_dims": [256, 128, 64], "dropout": 0.4, "lr": 0.0005, "epochs": 400, "wd": 1e-3},
        {"hidden_dims": [64, 32], "dropout": 0.2, "lr": 0.002, "epochs": 200, "wd": 1e-5},
        {"hidden_dims": [512, 256, 128, 64], "dropout": 0.5, "lr": 0.0003, "epochs": 500, "wd": 5e-4},
        {"hidden_dims": [128, 128, 64, 32], "dropout": 0.35, "lr": 0.001, "epochs": 350, "wd": 1e-4},
        {"hidden_dims": [256, 64], "dropout": 0.3, "lr": 0.001, "epochs": 300, "wd": 1e-4},
        {"hidden_dims": [128, 64, 32, 16], "dropout": 0.25, "lr": 0.0015, "epochs": 250, "wd": 5e-5},
        {"hidden_dims": [384, 192, 96], "dropout": 0.45, "lr": 0.0005, "epochs": 400, "wd": 1e-3},
    ]

    X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(DEVICE)
    y_tensor = torch.tensor(y, dtype=torch.float32).to(DEVICE)

    # Class weights for BCE
    pos_weight = torch.tensor([(1 - base_rate) / base_rate]).to(DEVICE)

    best_mlp_brier = 1.0
    best_mlp_oof = None
    mlp_models = []
    all_mlp_oofs = []

    tscv = TimeSeriesSplit(n_splits=5)

    for ci, cfg in enumerate(MLP_CONFIGS):
        oof_probs = np.zeros(n_events)
        oof_mask = np.zeros(n_events)
        fold_briers = []

        for fold_i, (train_idx, val_idx) in enumerate(tscv.split(X_scaled)):
            model = MLPClassifier(n_features, cfg["hidden_dims"], cfg["dropout"]).to(DEVICE)
            optimizer = optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["wd"])
            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg["epochs"])
            criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

            X_tr = X_tensor[train_idx]
            y_tr = y_tensor[train_idx]
            X_va = X_tensor[val_idx]
            y_va = y_tensor[val_idx]

            best_val_brier = 1.0
            best_val_probs = None
            patience = 30
            no_improve = 0

            model.train()
            for epoch in range(cfg["epochs"]):
                # Mini-batch training
                perm = torch.randperm(len(train_idx), device=DEVICE)
                batch_size = 256
                epoch_loss = 0
                for bi in range(0, len(train_idx), batch_size):
                    idx = perm[bi:bi+batch_size]
                    optimizer.zero_grad()
                    logits = model(X_tr[idx])
                    loss = criterion(logits, y_tr[idx])
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    epoch_loss += loss.item()
                scheduler.step()

                # Validate every 10 epochs
                if (epoch + 1) % 10 == 0:
                    model.eval()
                    with torch.no_grad():
                        val_logits = model(X_va)
                        val_probs_t = torch.sigmoid(val_logits).cpu().numpy()
                    val_brier = np.mean((val_probs_t - y[val_idx])**2)
                    if val_brier < best_val_brier:
                        best_val_brier = val_brier
                        best_val_probs = val_probs_t
                        no_improve = 0
                    else:
                        no_improve += 1
                    if no_improve >= patience // 10:
                        break
                    model.train()

            if best_val_probs is not None:
                oof_probs[val_idx] = best_val_probs
                oof_mask[val_idx] = 1
                fold_briers.append(best_val_brier)

        mean_brier = np.mean(fold_briers) if fold_briers else 1.0
        all_mlp_oofs.append(oof_probs.copy())
        print(f"    MLP config {ci}: dims={cfg['hidden_dims']} dr={cfg['dropout']} lr={cfg['lr']} → Brier={mean_brier:.6f}")

        if mean_brier < best_mlp_brier:
            best_mlp_brier = mean_brier
            best_mlp_oof = oof_probs.copy()

    # Average all MLP OOFs for diversity
    mlp_ensemble_oof = np.mean(all_mlp_oofs, axis=0)
    mlp_ens_brier = np.mean((mlp_ensemble_oof[mlp_ensemble_oof > 0] - y[mlp_ensemble_oof > 0])**2) if np.any(mlp_ensemble_oof > 0) else 1.0
    print(f"\n  Best single MLP Brier: {best_mlp_brier:.6f}")
    print(f"  MLP ensemble avg Brier: {mlp_ens_brier:.6f}")
else:
    print("  SKIPPED (no CUDA)")
    best_mlp_brier = 1.0
    best_mlp_oof = np.full(n_events, base_rate)
    mlp_ensemble_oof = np.full(n_events, base_rate)
    all_mlp_oofs = []


# ============================================================================
# [4/6] LOGISTIC REGRESSION BASELINE (for stacking)
# ============================================================================
print(f"\n[4/6] Logistic regression baseline for stacking...")

lr_oof = np.zeros(n_events)
lr_mask = np.zeros(n_events)
tscv = TimeSeriesSplit(n_splits=10)
lr_models = []

for fold_i, (train_idx, val_idx) in enumerate(tscv.split(X_scaled)):
    model = LogisticRegression(C=0.005, penalty='l2', solver='lbfgs',
                              class_weight='balanced', max_iter=2000)
    model.fit(X_scaled[train_idx], y[train_idx])
    lr_models.append(model)
    probs = model.predict_proba(X_scaled[val_idx])[:, 1]
    lr_oof[val_idx] = probs
    lr_mask[val_idx] = 1

lr_oof_brier = np.mean((lr_oof[lr_mask > 0] - y[lr_mask > 0])**2)
print(f"  LR OOF Brier: {lr_oof_brier:.6f}")

# LR ensemble
lr_ensemble = np.zeros(n_events)
for m in lr_models:
    lr_ensemble += m.predict_proba(X_scaled)[:, 1]
lr_ensemble /= len(lr_models)
lr_ens_brier = np.mean((lr_ensemble - y)**2)
print(f"  LR Ensemble Brier: {lr_ens_brier:.6f}")


# ============================================================================
# [5/6] META-LEARNER STACKING
# ============================================================================
print(f"\n[5/6] Meta-learner stacking...")

# Stack: LR OOF + XGB OOF + MLP ensemble OOF → meta-learner
# Use OOF predictions to avoid leakage
stack_valid = (lr_mask > 0)
if HAS_XGB and best_xgb_oof is not None:
    stack_valid &= (best_xgb_oof > 0)

X_stack = np.column_stack([
    lr_oof,
    best_xgb_oof if HAS_XGB else np.full(n_events, base_rate),
    mlp_ensemble_oof if HAS_TORCH else np.full(n_events, base_rate),
])

# Also add raw features to the stack
X_meta = np.column_stack([X_stack, X_scaled])
y_meta = y

# Train meta-learner (calibrated logistic regression)
meta_tscv = TimeSeriesSplit(n_splits=5)
meta_oof = np.zeros(n_events)
meta_mask = np.zeros(n_events)

for train_idx, val_idx in meta_tscv.split(X_meta):
    meta_model = LogisticRegression(C=0.1, solver='lbfgs', max_iter=5000)
    meta_model.fit(X_meta[train_idx], y[train_idx])
    meta_oof[val_idx] = meta_model.predict_proba(X_meta[val_idx])[:, 1]
    meta_mask[val_idx] = 1

valid_meta = meta_mask > 0
meta_brier = np.mean((meta_oof[valid_meta] - y[valid_meta])**2)
meta_auc = roc_auc_score(y[valid_meta], meta_oof[valid_meta])
print(f"  Meta-learner OOF Brier: {meta_brier:.6f}")
print(f"  Meta-learner OOF AUC: {meta_auc:.4f}")

# Simple weighted blend search
print(f"\n  Weighted blend optimization...")
best_blend_brier = 1.0
best_weights = (1.0, 0.0, 0.0)

for w_lr in np.linspace(0, 1, 21):
    for w_xgb in np.linspace(0, 1 - w_lr, 21):
        w_mlp = 1.0 - w_lr - w_xgb
        if w_mlp < 0: continue
        blend = w_lr * lr_oof + w_xgb * best_xgb_oof + w_mlp * mlp_ensemble_oof
        valid = (lr_mask > 0)
        brier = np.mean((blend[valid] - y[valid])**2)
        if brier < best_blend_brier:
            best_blend_brier = brier
            best_weights = (w_lr, w_xgb, w_mlp)

print(f"  Best blend: LR={best_weights[0]:.2f} XGB={best_weights[1]:.2f} MLP={best_weights[2]:.2f}")
print(f"  Blend Brier: {best_blend_brier:.6f}")


# ============================================================================
# [6/6] CALIBRATION + FINAL RESULTS
# ============================================================================
print(f"\n[6/6] Calibration and final results...")

# Use best available predictions
candidates = {
    "LR OOF": (lr_oof, lr_mask),
    "LR Ensemble": (lr_ensemble, np.ones(n_events)),
}
if HAS_XGB:
    candidates["XGB Full"] = (xgb_full_probs, np.ones(n_events))
if HAS_TORCH:
    candidates["MLP Ensemble"] = (mlp_ensemble_oof, np.ones(n_events) if np.all(mlp_ensemble_oof > 0) else (mlp_ensemble_oof > 0).astype(float))

# Best blend
blend_probs = best_weights[0] * lr_ensemble + best_weights[1] * xgb_full_probs + best_weights[2] * mlp_ensemble_oof
candidates["Best Blend"] = (blend_probs, np.ones(n_events))

# Meta-learner
if np.any(valid_meta):
    # Retrain meta on all data
    meta_final = LogisticRegression(C=0.1, solver='lbfgs', max_iter=5000)
    meta_final.fit(X_meta, y)
    meta_probs = meta_final.predict_proba(X_meta)[:, 1]
    candidates["Meta-learner"] = (meta_probs, np.ones(n_events))

print(f"\n  {'Model':20s}  {'Raw Brier':>10s}  {'Iso Brier':>10s}  {'Platt Brier':>11s}  {'AUC':>6s}")
print(f"  {'-'*20}  {'-'*10}  {'-'*10}  {'-'*11}  {'-'*6}")

best_overall_brier = 1.0
best_overall_name = ""
best_overall_probs = None

for name, (probs, mask) in candidates.items():
    valid = mask > 0
    if np.sum(valid) < 100: continue

    raw_brier = np.mean((probs[valid] - y[valid])**2)

    try:
        auc = roc_auc_score(y[valid], probs[valid])
    except:
        auc = 0.5

    # Isotonic calibration (temporal split)
    n_cal = int(np.sum(valid) * 0.2)
    cal_idx = np.where(valid)[0][-n_cal:]
    train_idx = np.where(valid)[0][:-n_cal]

    try:
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(probs[train_idx], y[train_idx])
        iso_probs = iso.predict(probs[valid])
        iso_brier = np.mean((iso_probs - y[valid])**2)
    except:
        iso_brier = raw_brier

    # Platt
    try:
        platt = LogisticRegression(C=1e10, solver='lbfgs', max_iter=5000)
        platt.fit(probs[cal_idx].reshape(-1,1), y[cal_idx])
        platt_probs = platt.predict_proba(probs[valid].reshape(-1,1))[:, 1]
        platt_brier = np.mean((platt_probs - y[valid])**2)
    except:
        platt_brier = raw_brier

    best_cal = min(raw_brier, iso_brier, platt_brier)

    print(f"  {name:20s}  {raw_brier:10.6f}  {iso_brier:10.6f}  {platt_brier:11.6f}  {auc:6.4f}")

    if best_cal < best_overall_brier:
        best_overall_brier = best_cal
        best_overall_name = name
        if best_cal == iso_brier:
            best_overall_probs = iso.predict(probs) if hasattr(iso, 'predict') else probs
        elif best_cal == platt_brier:
            best_overall_probs = platt.predict_proba(probs.reshape(-1,1))[:, 1] if hasattr(platt, 'predict_proba') else probs
        else:
            best_overall_probs = probs

print(f"\n  BASELINE Brier (constant): {baseline_brier:.6f}")
print(f"  BEST MODEL: {best_overall_name}")
print(f"  BEST Brier: {best_overall_brier:.6f}")
print(f"  Improvement over baseline: {(baseline_brier - best_overall_brier):.6f} ({(baseline_brier - best_overall_brier)/baseline_brier*100:.1f}%)")
print(f"  Improvement over v28.3 LR: {(0.2279 - best_overall_brier):.6f}")

# Tier analysis on best model
if best_overall_probs is not None:
    use_probs = best_overall_probs

    # Threshold search
    best_score = -1
    best_t1_th = 0.55
    best_t4_th = 0.45

    for th1 in np.linspace(0.50, 0.80, 61):
        for th4 in np.linspace(0.25, 0.50, 51):
            if th4 >= th1: continue
            t1_m = use_probs >= th1
            t4_m = use_probs < th4
            n1 = np.sum(t1_m); n4 = np.sum(t4_m)
            if n1 < 200 or n4 < 200: continue
            r1 = np.mean(y[t1_m]) * 100
            r4 = np.mean(y[t4_m]) * 100
            spread = r1 - r4
            score = spread * math.sqrt(n1) * math.sqrt(n4)
            if score > best_score:
                best_score = score
                best_t1_th = th1
                best_t4_th = th4

    t1_mask = use_probs >= best_t1_th
    t4_mask = use_probs < best_t4_th
    t1_rate = np.mean(y[t1_mask]) * 100
    t4_rate = np.mean(y[t4_mask]) * 100
    n_t1 = int(np.sum(t1_mask))
    n_t4 = int(np.sum(t4_mask))
    spread = t1_rate - t4_rate

    print(f"\n  TIER PERFORMANCE ({best_overall_name}):")
    print(f"    T1 ≥ {best_t1_th:.3f}: {t1_rate:.1f}% success (n={n_t1})")
    print(f"    T4 < {best_t4_th:.3f}: {t4_rate:.1f}% success (n={n_t4})")
    print(f"    Spread: {spread:.1f}pp")

# Save results
results = {
    "best_model": best_overall_name,
    "best_brier": float(best_overall_brier),
    "baseline_brier": float(baseline_brier),
    "improvement_pct": float((baseline_brier - best_overall_brier)/baseline_brier*100),
    "v28_3_lr_brier": 0.2279,
    "blend_weights": {"lr": float(best_weights[0]), "xgb": float(best_weights[1]), "mlp": float(best_weights[2])},
    "n_events": n_events,
    "base_rate": float(base_rate),
    "device": str(DEVICE),
}
if best_overall_probs is not None:
    results["t1_threshold"] = float(best_t1_th)
    results["t4_threshold"] = float(best_t4_th)
    results["t1_success"] = float(t1_rate)
    results["t4_success"] = float(t4_rate)
    results["spread"] = float(spread)

with open(os.path.join(BASE, "gpu_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*70}")
print(f"  GPU PIPELINE COMPLETE")
print(f"{'='*70}")
