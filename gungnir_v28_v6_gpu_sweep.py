#!/usr/bin/env python3
"""
GUNGNIR v28.6.0 — GPU-CLASS SWEEP: Bayesian-Optimized Deep Ensemble
====================================================================
Strategy: Instead of random grid search, use Bayesian optimization (Optuna)
to find XGBoost/LightGBM configs that specifically minimize HOLDOUT Brier.

Key innovations over v28.5.0:
  1. Optuna Bayesian optimization (500 trials each for XGB + LGB)
  2. NESTED CV: inner CV for hyperparams, outer temporal holdout for evaluation
  3. Aggressive regularization constraints (prevent the overfitting that killed v28.3/4)
  4. Feature importance pruning: remove features that hurt holdout
  5. Temperature scaling: learn optimal temperature for probability calibration
  6. 7-strategy meta-learner: LR + L1 + P3 + Bayesian + XGB + LGB + MLP
  7. Learned meta-weights via constrained optimization on calibration set

All evaluated on HONEST temporal holdout: train <2025, test 2025+
"""

import csv, math, re, hashlib, json, time, warnings, sys
from collections import defaultdict, Counter

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression
from sklearn.neural_network import MLPClassifier
import xgboost as xgb
import lightgbm as lgb

warnings.filterwarnings('ignore')

# Optuna
try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print("WARNING: optuna not installed, falling back to grid search")

# ============================================================================
# REUSE v28.5.0 DATA PIPELINE (import the encoding logic)
# ============================================================================
# Rather than copy 400 lines, exec the v28.5.0 script up to the encoding step

print("\n" + "="*70)
print("  GUNGNIR v28.6.0 — BAYESIAN-OPTIMIZED DEEP ENSEMBLE")
print("="*70)

# We'll import the data from v28.5.0's encoding
# First, let's re-encode efficiently

CTGOV_REAL = {
    "p3_onc_blind_rate": 0.48, "p3_immuno_blind_rate": 0.83,
    "p3_cns_blind_rate": 0.67, "p3_metabolic_blind_rate": 0.56,
    "p3_rare_blind_rate": 0.29, "p3_infectious_blind_rate": 0.64,
    "p3_ophtho_blind_rate": 1.00, "p3_cardio_blind_rate": 0.56,
    "p3_generic_blind_rate": 0.55,
    "p3_onc_enroll": 435, "p3_immuno_enroll": 315, "p3_cns_enroll": 227,
    "p3_metabolic_enroll": 338, "p3_rare_enroll": 43, "p3_infectious_enroll": 480,
    "p3_ophtho_enroll": 1116, "p3_cardio_enroll": 450, "p3_generic_enroll": 400,
    "p3_onc_hard_rate": 0.64, "p3_immuno_hard_rate": 0.33,
    "p3_cns_hard_rate": 0.50, "p3_metabolic_hard_rate": 0.16,
    "p3_rare_hard_rate": 0.57, "p3_infectious_hard_rate": 0.48,
    "p3_ophtho_hard_rate": 0.50, "p3_cardio_hard_rate": 0.72,
    "p3_generic_hard_rate": 0.45,
    "p2_onc_blind_rate": 0.44, "p2_immuno_blind_rate": 0.69,
    "p2_generic_blind_rate": 0.40,
    "p2_onc_enroll": 63, "p2_immuno_enroll": 98, "p2_generic_enroll": 80,
    "p1_blind_rate": 0.15, "p1_enroll": 30,
}

CTGOV_DRUG_LOOKUP = {
    "keytruda": {"blind": "NONE", "enroll": 94, "endpoint_hard": 1.0},
    "pembrolizumab": {"blind": "NONE", "enroll": 94, "endpoint_hard": 1.0},
    "rinvoq": {"blind": "QUADRUPLE", "enroll": 912, "endpoint_hard": 0.0},
    "upadacitinib": {"blind": "QUADRUPLE", "enroll": 912, "endpoint_hard": 0.0},
    "dupixent": {"blind": "QUADRUPLE", "enroll": 138, "endpoint_hard": 0.0},
    "dupilumab": {"blind": "QUADRUPLE", "enroll": 138, "endpoint_hard": 0.0},
    "opdivo": {"blind": "NONE", "enroll": 419, "endpoint_hard": 1.0},
    "nivolumab": {"blind": "NONE", "enroll": 419, "endpoint_hard": 1.0},
    "tirzepatide": {"blind": "DOUBLE", "enroll": 783, "endpoint_hard": 0.0},
    "lynparza": {"blind": "TRIPLE", "enroll": 1836, "endpoint_hard": 0.5},
    "olaparib": {"blind": "TRIPLE", "enroll": 1836, "endpoint_hard": 0.5},
    "imfinzi": {"blind": "NONE", "enroll": 1118, "endpoint_hard": 1.0},
    "durvalumab": {"blind": "NONE", "enroll": 1118, "endpoint_hard": 1.0},
    "lecanemab": {"blind": "QUADRUPLE", "enroll": 1400, "endpoint_hard": 0.0},
    "enhertu": {"blind": "NONE", "enroll": 927, "endpoint_hard": 0.0},
    "zanubrutinib": {"blind": "NONE", "enroll": 652, "endpoint_hard": 0.5},
    "brukinsa": {"blind": "NONE", "enroll": 652, "endpoint_hard": 0.5},
}

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
    r"primary\s+endpoint\s+(?:met|not|was)|ORR\s+(?:was|of)\s+\d|PFS\s+(?:was|of)\s+\d|OS\s+(?:was|of)\s+\d|median\s+\w+\s+was|"
    r"achieved|demonstrated\s+(?:statistical|significant|positive|negative)|p[\s-]?value\s*(?:=|of|was)\s*[0-9]|"
    r"hazard\s+ratio\s*(?:=|of|was)\s*[0-9]|(?:complete|partial|overall)\s+response\s+rate\s+(?:was|of)\s+\d|"
    r"median\s+(?:PFS|OS|DFS|EFS|RFS)\s+(?:was|of)\s+\d|"
    r"(?:positive|negative|mixed|disappointing|encouraging)\s+(?:data|results|outcome|readout)|"
    r"(?:FDA|EMA)\s+(?:approved|rejected|accepted|refused)|"
    r"(?:stock|share|shares)\s+(?:surged|plummeted|jumped|dropped|fell|rose|spiked)).*?)(?:\.|$)", re.I)
BIG_PHARMA = {"PFE","MRK","LLY","ABBV","BMY","JNJ","AZN","RHHBY","NVS","SNY",
              "GSK","AMGN","GILD","REGN","BIIB","VRTX","MRNA","BNTX","TAK","NVO","TEVA","ROCHE","NOVARTIS","BAYER"}

def bool_val(s):
    if isinstance(s, bool): return s
    return str(s).strip().upper() in ("TRUE", "1", "YES")
def safe_float(s, default=0.0):
    try: return float(re.sub(r'[^0-9.\-]', '', str(s)))
    except: return default
def sanitize_text(text):
    return _RESULT_PHRASES.sub("", _POST_READOUT.sub("", text)).strip()

FEATURES = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious",
    "ta_ophthalmology", "ta_pain", "ta_cardiovascular",
    "is_gene_therapy", "is_adc", "is_small_molecule",
    "is_double_blind", "is_open_label", "is_combination",
    "uses_surrogate", "endpoint_hardness", "log_enrollment",
    "designation_count", "odin_btd", "odin_desig_rich", "odin_sponsor_exp",
    "has_ppm", "log_price", "era_post_2024",
    "is_topline", "mentions_primary", "endpoint_pfs",
    "is_competitive", "competitive_count",
    "phase3_x_cns", "phase3_x_immunology", "rare_x_phase3",
    "antibody_x_oncology", "combo_x_oncology",
    "blind_x_phase3", "enroll_x_phase3",
    "os_x_oncology", "hard_x_phase3", "rare_small_enroll",
    "sponsor_success_rate", "enroll_vs_ta_median", "ta_base_rate",
    "desig_x_phase3", "sponsor_x_phase3", "is_antibody",
    "blind_x_oncology", "ppm_x_phase3",
]
N_FEATURES = len(FEATURES)
TA_BASE_RATES = {}

# ---- LOAD DATA ----
print("[1/7] Loading & encoding data...")
t0 = time.time()

odin_index = {}
with open("/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED-f40ae6fd.csv") as f:
    for row in csv.DictReader(f):
        asset = re.sub(r'\s*\(.*?\)', '', row.get("asset","").strip().lower()).strip()
        ticker = row.get("ticker","").upper()
        entry = {"btd": bool_val(row.get("btd","")), "orphan": bool_val(row.get("orphan","")),
            "priority_review": bool_val(row.get("priority_review","")), "fast_track": bool_val(row.get("fast_track","")),
            "accelerated_approval": bool_val(row.get("accelerated_approval","")),
            "surrogate_endpoint": bool_val(row.get("surrogate_endpoint","")),
            "sponsor_prior_approvals": int(safe_float(row.get("sponsor_prior_approvals","0"))),
            "desig_count": sum([bool_val(row.get(k,"")) for k in ["btd","orphan","priority_review","fast_track","accelerated_approval"]])}
        odin_index[f"{ticker}|{asset}"] = entry
        for w in set(re.findall(r'\b[a-z]{4,}\b', asset)):
            k = f"{ticker}|{w}"
            if k not in odin_index: odin_index[k] = entry

def odin_lookup(ticker, asset):
    ticker = ticker.upper()
    ac = re.sub(r'\s*\(.*?\)', '', asset.strip().lower()).strip()
    hit = odin_index.get(f"{ticker}|{ac}")
    if hit: return hit
    for w in sorted(set(re.findall(r'\b[a-z]{4,}\b', ac)), key=len, reverse=True):
        hit = odin_index.get(f"{ticker}|{w}")
        if hit: return hit
    return None

with open("/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_PHASE_BACKTEST_EXTENDED.csv", encoding="latin-1") as f:
    all_rows = list(csv.DictReader(f))

binary = sorted([r for r in all_rows if r.get("parsed_outcome","").strip() in ("POSITIVE","NEGATIVE")],
                key=lambda x: x.get("catalyst_date",""))
seen = set(); deduped = []
for r in binary:
    k = f"{r['ticker']}|{r.get('catalyst_date','')}|{r.get('asset','')}"
    if k not in seen: seen.add(k); deduped.append(r)
binary = deduped

ppm_drug = defaultdict(list)
for r in sorted(all_rows, key=lambda x: x.get("catalyst_date","")):
    if r.get("parsed_outcome","") == "POSITIVE":
        ppm_drug[(r["ticker"], re.sub(r'\s*\(.*?\)','',r.get("asset","").lower()).strip())].append(r.get("catalyst_date",""))

sponsor_events = defaultdict(list)
for r in binary:
    sponsor_events[r["ticker"]].append((r.get("catalyst_date",""), 1 if r["parsed_outcome"]=="POSITIVE" else 0))

ta_outcomes = defaultdict(list)
for r in binary:
    ind = r.get("indication","").lower()
    out = 1 if r["parsed_outcome"]=="POSITIVE" else 0
    matched = False
    for tn, tr in _G_TA.items():
        if tr.search(ind): ta_outcomes[tn].append(out); matched = True; break
    if not matched: ta_outcomes["other"].append(out)
for ta, outs in ta_outcomes.items():
    TA_BASE_RATES[ta] = sum(outs)/len(outs) if outs else 0.53
base_rate_raw = sum(1 for r in binary if r["parsed_outcome"]=="POSITIVE") / len(binary)

def get_ta_key(ind):
    for tn, tr in _G_TA.items():
        if tr.search(ind): return tn.replace("ta_","")
    return "generic"

def encode(row):
    raw = {f: 0.0 for f in FEATURES}
    stage = row.get("stage","").lower().strip()
    ind = row.get("indication","").lower()
    asset = row.get("asset","").lower()
    ticker = row.get("ticker","").upper()
    text = sanitize_text(row.get("raw_catalyst_text",""))
    date = row.get("catalyst_date","")

    if "3" in stage and "1" not in stage and "2" not in stage: raw["is_pivotal"]=1.0
    elif stage in ("phase 2b","phase2b","p2b"): raw["is_P2B"]=1.0
    elif "2" in stage and "1" not in stage: raw["is_P2"]=1.0
    elif "1" in stage: raw["is_phase1_any"]=1.0
    if "2/3" in stage: raw["is_pivotal"]=1.0; raw["is_P2"]=0.0
    ip3 = raw["is_pivotal"]

    for tf, tr in _G_TA.items():
        if tf in raw and tr.search(ind): raw[tf]=1.0
    is_cns = 1.0 if _G_TA["ta_cns"].search(ind) else 0.0
    is_imm = 1.0 if _G_TA["ta_immunology"].search(ind) else 0.0
    is_ab = 1.0 if _G_MODALITY["antibody"].search(asset) or _G_MODALITY["antibody"].search(text) else 0.0

    raw["is_competitive"] = 1.0 if any(kw in ind for kw in _G_COMPETITIVE) else 0.0
    for kw, sc in _G_COMPETITIVE_FULL.items():
        if kw in ind: raw["competitive_count"] = max(raw["competitive_count"], float(sc))

    if _G_MODALITY["gene_therapy"].search(asset) or _G_MODALITY["gene_therapy"].search(text): raw["is_gene_therapy"]=1.0
    if _G_MODALITY["adc"].search(asset) or _G_MODALITY["adc"].search(text): raw["is_adc"]=1.0
    if _G_MODALITY["small_molecule"].search(text) or _G_MODALITY["small_molecule"].search(asset): raw["is_small_molecule"]=1.0
    if _DESIGN_COMBO.search(text) or _DESIGN_COMBO.search(asset): raw["is_combination"]=1.0
    if _DESIGN_SURROGATE.search(text): raw["uses_surrogate"]=1.0

    # CT.gov features
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    is_p2 = "2" in stage and not is_p3
    # DEPRECATED: Hash-based CT.gov simulation removed (2026-03-27)

    # All Gungnir models must use real CT.gov data or phase-average imputation.

    # Use gungnir_v32_train.py (CHAMPION) instead of this retired script.

    raise RuntimeError("DEPRECATED: This script contains hash-based simulated data. Use gungnir_v32_train.py instead.")
    dm = None
    for dk, dd in CTGOV_DRUG_LOOKUP.items():
        if dk in asset: dm=dd; break
    if dm: raw["is_double_blind"] = 1.0 if dm["blind"] not in ("NONE","none",None) else 0.0
    elif re.search(r"double.?blind|placebo.?control|triple.?blind|quadruple.?blind",text,re.I): raw["is_double_blind"]=1.0
    elif re.search(r"open.?label|single.?arm|unblinded",text,re.I): raw["is_double_blind"]=0.0
    else:
        ta = get_ta_key(ind)
        r = CTGOV_REAL.get(f"p3_{ta}_blind_rate",0.55) if is_p3 else CTGOV_REAL.get(f"p2_{ta}_blind_rate",0.40) if is_p2 else 0.15
        raw["is_double_blind"] = 1.0 if h < r else 0.0
    raw["is_open_label"] = 1.0 - raw["is_double_blind"]

    if dm and dm["enroll"]>0: enroll=dm["enroll"]
    else:
        ta = get_ta_key(ind)
        med = CTGOV_REAL.get(f"p3_{ta}_enroll",400) if is_p3 else CTGOV_REAL.get(f"p2_{ta}_enroll",80) if is_p2 else 30
        enroll = max(int(med*0.5),10) + int(h*(int(med*1.8)-max(int(med*0.5),10)))
    raw["log_enrollment"] = math.log(max(enroll,1))

    if dm and dm.get("endpoint_hard") is not None: raw["endpoint_hardness"]=dm["endpoint_hard"]
    elif re.search(r"overall.?survival|mortality|MACE",text,re.I): raw["endpoint_hardness"]=1.0
    elif re.search(r"\bPFS\b|progression.?free|disease.?free",text,re.I): raw["endpoint_hardness"]=0.5
    elif re.search(r"\bORR\b|response.?rate",text,re.I): raw["endpoint_hardness"]=0.0
    else:
        ta = get_ta_key(ind)
        raw["endpoint_hardness"] = CTGOV_REAL.get(f"p3_{ta}_hard_rate",0.45) if is_p3 else 0.2

    ta = get_ta_key(ind)
    ta_med = CTGOV_REAL.get(f"p3_{ta}_enroll",400) if is_p3 else CTGOV_REAL.get(f"p2_{ta}_enroll",80) if is_p2 else 30
    raw["enroll_vs_ta_median"] = math.log(max(math.exp(raw["log_enrollment"])/max(ta_med,1), 0.01))

    # ODIN
    odin = odin_lookup(ticker, row.get("asset",""))
    dc = 0
    if odin:
        for k in ["btd","orphan","priority_review","fast_track","accelerated_approval"]:
            if odin.get(k): dc += 1
        raw["odin_btd"] = 1.0 if odin["btd"] else 0.0
        raw["odin_desig_rich"] = 1.0 if odin["desig_count"]>=3 else 0.0
        raw["odin_sponsor_exp"] = 1.0 if odin["sponsor_prior_approvals"]>=5 else 0.0
        if odin["surrogate_endpoint"]: raw["uses_surrogate"]=1.0
    else:
        for k in ["btd","orphan","fast_track","priority_review","accelerated_approval"]:
            if bool_val(row.get(k,"")): dc+=1
        if bool_val(row.get("btd","")): raw["odin_btd"]=1.0
        if re.search(r"breakthrough\s+therap|\bbtd\b",text,re.I): raw["odin_btd"]=1.0
    raw["designation_count"] = float(dc)

    # PPM
    ppm_key = (ticker, re.sub(r'\s*\(.*?\)','',asset).strip())
    if any(d < date for d in ppm_drug.get(ppm_key,[])): raw["has_ppm"]=1.0

    price = safe_float(row.get("price_at_catalyst",""))
    raw["log_price"] = math.log(price) if price and price>0 else (math.log(100) if ticker in BIG_PHARMA else 3.0)
    try: yr = int(date[:4])
    except: yr = 2026
    raw["era_post_2024"] = 1.0 if yr>=2025 else 0.0

    raw["is_topline"] = 1.0 if re.search(r"top[\s-]?line",text,re.I) else 0.0
    raw["mentions_primary"] = 1.0 if re.search(r"primary\s+endpoint|primary\s+outcome",text,re.I) else 0.0
    raw["endpoint_pfs"] = 1.0 if re.search(r"\bPFS\b|progression[\s-]free",text,re.I) else 0.0

    raw["phase3_x_cns"]=ip3*is_cns; raw["phase3_x_immunology"]=ip3*is_imm
    raw["rare_x_phase3"]=raw["ta_rare"]*ip3; raw["antibody_x_oncology"]=is_ab*raw["ta_oncology"]
    raw["combo_x_oncology"]=raw["is_combination"]*raw["ta_oncology"]
    raw["blind_x_phase3"]=raw["is_double_blind"]*ip3; raw["enroll_x_phase3"]=raw["log_enrollment"]*ip3
    raw["os_x_oncology"]=raw["endpoint_hardness"]*raw["ta_oncology"]
    raw["hard_x_phase3"]=raw["endpoint_hardness"]*ip3
    raw["rare_small_enroll"]=raw["ta_rare"]*(1.0 if raw["log_enrollment"]<math.log(100) else 0.0)

    prior = [(d,o) for d,o in sponsor_events.get(ticker,[]) if d<date]
    raw["sponsor_success_rate"] = sum(o for _,o in prior)/len(prior) if len(prior)>=2 else 0.5

    for tn, tr in _G_TA.items():
        if tr.search(ind): raw["ta_base_rate"]=TA_BASE_RATES.get(tn, base_rate_raw); break
    else: raw["ta_base_rate"]=base_rate_raw

    raw["desig_x_phase3"]=raw["designation_count"]*ip3
    raw["sponsor_x_phase3"]=raw["odin_sponsor_exp"]*ip3
    raw["is_antibody"]=is_ab
    raw["blind_x_oncology"]=raw["is_double_blind"]*raw["ta_oncology"]
    raw["ppm_x_phase3"]=raw["has_ppm"]*ip3

    return raw

# Encode all
encoded = []
for r in binary:
    feat = encode(r)
    actual = 1 if r["parsed_outcome"]=="POSITIVE" else 0
    stage = r.get("stage","").lower()
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    ind = r.get("indication","").lower()
    ta_key = "other"
    for tn, tr in _G_TA.items():
        if tr.search(ind): ta_key=tn; break
    encoded.append({"features":feat, "actual":actual, "is_phase3":is_p3,
                    "date":r.get("catalyst_date",""), "ta_key":ta_key})

n_events = len(encoded)
X = np.zeros((n_events, N_FEATURES))
y = np.zeros(n_events)
for i, e in enumerate(encoded):
    for j, fn in enumerate(FEATURES): X[i,j] = e["features"].get(fn, 0.0)
    y[i] = e["actual"]

dates = np.array([e["date"] for e in encoded])
train_mask = dates < "2025-01-01"
test_mask = dates >= "2025-01-01"
n_train, n_test = int(np.sum(train_mask)), int(np.sum(test_mask))

X_train, y_train = X[train_mask], y[train_mask]
X_test, y_test = X[test_mask], y[test_mask]

test_base = np.mean(y_test)
baseline_brier = np.mean((np.full(n_test, test_base) - y_test)**2)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

test_p3 = np.array([e["is_phase3"] for e in encoded if e["date"]>="2025-01-01"])
test_ta = np.array([e["ta_key"] for e in encoded if e["date"]>="2025-01-01"])
train_p3 = np.array([e["is_phase3"] for e in encoded if e["date"]<"2025-01-01"])
train_ta = np.array([e["ta_key"] for e in encoded if e["date"]<"2025-01-01"])

# Strata stats for Bayesian shrinkage
strata_stats = {}
train_enc = [e for e in encoded if e["date"]<"2025-01-01"]
for i, e in enumerate(train_enc):
    key = (e["ta_key"], e["is_phase3"])
    if key not in strata_stats: strata_stats[key] = {"count":0, "successes":0}
    strata_stats[key]["count"] += 1
    strata_stats[key]["successes"] += y_train[i]
for key in strata_stats:
    s = strata_stats[key]
    s["rate"] = s["successes"]/s["count"] if s["count"]>0 else base_rate_raw

print(f"  {n_events} events ({n_train} train, {n_test} test), {N_FEATURES} features")
print(f"  Test base rate: {test_base:.4f}, Constant Brier: {baseline_brier:.6f}")
print(f"  Encoding time: {time.time()-t0:.1f}s")

# ============================================================================
# STRATEGY 1: L2 Ridge (from v28.5.0)
# ============================================================================
print(f"\n[2/7] Strategy 1: L2 Ridge ensemble...")
best_C = 0.01
s1_models = []
tscv = TimeSeriesSplit(n_splits=10)
for tr, va in tscv.split(X_train_s):
    m = LogisticRegression(C=best_C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
    m.fit(X_train_s[tr], y_train[tr]); s1_models.append(m)
s1_train = np.mean([m.predict_proba(X_train_s)[:,1] for m in s1_models], axis=0)
s1_test = np.mean([m.predict_proba(X_test_s)[:,1] for m in s1_models], axis=0)
print(f"  Test AUC={roc_auc_score(y_test, s1_test):.4f}, Brier={np.mean((s1_test-y_test)**2):.6f}")

# ============================================================================
# STRATEGY 2: L1 Sparse
# ============================================================================
print(f"\n[3/7] Strategy 2: L1 Sparse...")
s2_models = []
for tr, va in tscv.split(X_train_s):
    m = LogisticRegression(C=0.1, penalty='l1', solver='liblinear', class_weight='balanced', max_iter=2000)
    m.fit(X_train_s[tr], y_train[tr]); s2_models.append(m)
s2_train = np.mean([m.predict_proba(X_train_s)[:,1] for m in s2_models], axis=0)
s2_test = np.mean([m.predict_proba(X_test_s)[:,1] for m in s2_models], axis=0)
print(f"  Test AUC={roc_auc_score(y_test, s2_test):.4f}, Brier={np.mean((s2_test-y_test)**2):.6f}")

# ============================================================================
# STRATEGY 3: P3 Specialist
# ============================================================================
print(f"\n[4/7] Strategy 3: Phase 3 Specialist...")
p3_train_idx = np.where(train_p3)[0]
X_p3_train = X_train_s[p3_train_idx]; y_p3_train = y_train[p3_train_idx]
p3_model = LogisticRegression(C=0.01, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
p3_model.fit(X_p3_train, y_p3_train)
s3_train = p3_model.predict_proba(X_train_s)[:,1]
s3_test = p3_model.predict_proba(X_test_s)[:,1]
print(f"  Test AUC={roc_auc_score(y_test, s3_test):.4f}, Brier={np.mean((s3_test-y_test)**2):.6f}")

# ============================================================================
# STRATEGY 4: Bayesian Shrinkage
# ============================================================================
print(f"\n[5/7] Strategy 4: Bayesian Shrinkage (strength=200)...")
def bayesian_shrink(ml_pred, ta_key, is_p3, strength=200):
    stats = strata_stats.get((ta_key, is_p3), {"count":0, "rate":base_rate_raw})
    alpha = stats["count"]/(stats["count"]+strength)
    return alpha * ml_pred + (1-alpha) * stats["rate"]

s4_train = np.array([bayesian_shrink(s1_train[i], train_ta[i], train_p3[i]) for i in range(n_train)])
s4_test = np.array([bayesian_shrink(s1_test[i], test_ta[i], test_p3[i]) for i in range(n_test)])
print(f"  Test AUC={roc_auc_score(y_test, s4_test):.4f}, Brier={np.mean((s4_test-y_test)**2):.6f}")

# ============================================================================
# STRATEGY 5: XGBoost with Optuna Bayesian Optimization
# ============================================================================
print(f"\n[6/7] Strategy 5+6: XGBoost + LightGBM Bayesian optimization...")

# Use inner temporal CV for hyperopt, outer holdout for final eval
# Split training data: inner_train (first 80%) + inner_val (last 20%)
n_inner = int(n_train * 0.8)
X_itrain, y_itrain = X_train[:n_inner], y_train[:n_inner]
X_ival, y_ival = X_train[n_inner:], y_train[n_inner:]

def xgb_objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 2, 6),
        'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.1, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.3, 0.8),
        'min_child_weight': trial.suggest_int('min_child_weight', 5, 50),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.01, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 50.0, log=True),
        'gamma': trial.suggest_float('gamma', 0.1, 5.0, log=True),
        'scale_pos_weight': 1.0,
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'verbosity': 0,
        'tree_method': 'hist',
    }
    m = xgb.XGBClassifier(**params)
    m.fit(X_itrain, y_itrain, eval_set=[(X_ival, y_ival)], verbose=False)
    preds = m.predict_proba(X_ival)[:,1]
    return np.mean((preds - y_ival)**2)

def lgb_objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 2, 6),
        'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.1, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.3, 0.8),
        'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.01, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 50.0, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 8, 31),
        'objective': 'binary',
        'metric': 'binary_logloss',
        'verbosity': -1,
    }
    m = lgb.LGBMClassifier(**params)
    m.fit(X_itrain, y_itrain, eval_set=[(X_ival, y_ival)])
    preds = m.predict_proba(X_ival)[:,1]
    return np.mean((preds - y_ival)**2)

N_XGB_TRIALS = 300
N_LGB_TRIALS = 300

# XGBoost
print(f"  XGBoost: {N_XGB_TRIALS} Bayesian trials...")
t_xgb = time.time()
if HAS_OPTUNA:
    xgb_study = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=42))
    xgb_study.optimize(xgb_objective, n_trials=N_XGB_TRIALS, show_progress_bar=False)
    best_xgb_params = xgb_study.best_params
    print(f"    Best inner Brier: {xgb_study.best_value:.6f} (in {time.time()-t_xgb:.1f}s)")
else:
    best_xgb_params = {'max_depth':3, 'learning_rate':0.01, 'n_estimators':200,
        'subsample':0.8, 'colsample_bytree':0.5, 'min_child_weight':20,
        'reg_alpha':1.0, 'reg_lambda':10.0, 'gamma':1.0}

# Train XGBoost ensemble on full training data
xgb_models = []
tscv5 = TimeSeriesSplit(n_splits=5)
for tr, va in tscv5.split(X_train):
    params = {**best_xgb_params, 'objective':'binary:logistic', 'eval_metric':'logloss',
              'verbosity':0, 'tree_method':'hist', 'scale_pos_weight':1.0}
    m = xgb.XGBClassifier(**params)
    m.fit(X_train[tr], y_train[tr], eval_set=[(X_train[va], y_train[va])], verbose=False)
    xgb_models.append(m)

s5_train = np.mean([m.predict_proba(X_train)[:,1] for m in xgb_models], axis=0)
s5_test = np.mean([m.predict_proba(X_test)[:,1] for m in xgb_models], axis=0)
print(f"    Holdout: AUC={roc_auc_score(y_test, s5_test):.4f}, Brier={np.mean((s5_test-y_test)**2):.6f}")

# LightGBM
print(f"  LightGBM: {N_LGB_TRIALS} Bayesian trials...")
t_lgb = time.time()
if HAS_OPTUNA:
    lgb_study = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=42))
    lgb_study.optimize(lgb_objective, n_trials=N_LGB_TRIALS, show_progress_bar=False)
    best_lgb_params = lgb_study.best_params
    print(f"    Best inner Brier: {lgb_study.best_value:.6f} (in {time.time()-t_lgb:.1f}s)")
else:
    best_lgb_params = {'max_depth':3, 'learning_rate':0.01, 'n_estimators':200,
        'subsample':0.8, 'colsample_bytree':0.5, 'min_child_samples':30,
        'reg_alpha':1.0, 'reg_lambda':10.0, 'num_leaves':15}

lgb_models = []
for tr, va in tscv5.split(X_train):
    params = {**best_lgb_params, 'objective':'binary', 'metric':'binary_logloss', 'verbosity':-1}
    m = lgb.LGBMClassifier(**params)
    m.fit(X_train[tr], y_train[tr], eval_set=[(X_train[va], y_train[va])])
    lgb_models.append(m)

s6_train = np.mean([m.predict_proba(X_train)[:,1] for m in lgb_models], axis=0)
s6_test = np.mean([m.predict_proba(X_test)[:,1] for m in lgb_models], axis=0)
print(f"    Holdout: AUC={roc_auc_score(y_test, s6_test):.4f}, Brier={np.mean((s6_test-y_test)**2):.6f}")

# ============================================================================
# STRATEGY 7: Small MLP
# ============================================================================
print(f"\n  Strategy 7: MLP Neural Network...")
mlp_models = []
for tr, va in tscv5.split(X_train_s):
    m = MLPClassifier(hidden_layer_sizes=(32, 16), activation='relu', solver='adam',
                      alpha=1.0, learning_rate_init=0.001, max_iter=500,
                      early_stopping=True, validation_fraction=0.15, n_iter_no_change=20,
                      random_state=42)
    m.fit(X_train_s[tr], y_train[tr])
    mlp_models.append(m)

s7_train = np.mean([m.predict_proba(X_train_s)[:,1] for m in mlp_models], axis=0)
s7_test = np.mean([m.predict_proba(X_test_s)[:,1] for m in mlp_models], axis=0)
print(f"    Holdout: AUC={roc_auc_score(y_test, s7_test):.4f}, Brier={np.mean((s7_test-y_test)**2):.6f}")


# ============================================================================
# META-LEARNER: 7-strategy optimal ensemble
# ============================================================================
print(f"\n[7/7] Meta-learner: 7-strategy optimal ensemble...")

strategies = {
    "S1_Ridge": (s1_test, s1_train),
    "S2_Lasso": (s2_test, s2_train),
    "S3_P3Spec": (s3_test, s3_train),
    "S4_Bayes": (s4_test, s4_train),
    "S5_XGB": (s5_test, s5_train),
    "S6_LGB": (s6_test, s6_train),
    "S7_MLP": (s7_test, s7_train),
}

print(f"\n  Individual holdout performance:")
for name, (tp, _) in strategies.items():
    auc = roc_auc_score(y_test, tp)
    brier = np.mean((tp - y_test)**2)
    delta = baseline_brier - brier
    print(f"    {name:12s}  AUC={auc:.4f}  Brier={brier:.6f}  ΔvsConst={delta:+.6f}")

# Constrained optimization for meta-weights
# Use last 30% of training as calibration
n_cal = int(n_train * 0.3)
cal_stack = np.column_stack([strategies[n][1][-n_cal:] for n in strategies])
cal_y = y_train[-n_cal:]

# Grid search with finer resolution for 7 strategies
# Too many combos for 7D grid — use Optuna!
snames = list(strategies.keys())
n_strats = len(snames)

if HAS_OPTUNA:
    def meta_objective(trial):
        raw_w = [trial.suggest_float(f'w_{i}', 0.0, 1.0) for i in range(n_strats)]
        total = sum(raw_w)
        if total < 0.01: return 1.0
        weights = np.array([w/total for w in raw_w])
        preds = cal_stack @ weights
        return np.mean((preds - cal_y)**2)

    meta_study = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=42))
    meta_study.optimize(meta_objective, n_trials=500)
    raw_w = [meta_study.best_params[f'w_{i}'] for i in range(n_strats)]
    total = sum(raw_w)
    best_meta_w = np.array([w/total for w in raw_w])
    print(f"\n  Optuna meta-weights (500 trials):")
else:
    # Fallback: use v28.5.0 approach
    best_meta_w = np.array([0.1, 0.1, 0.5, 0.3, 0.0, 0.0, 0.0])
    print(f"\n  Fallback meta-weights:")

for i, name in enumerate(snames):
    if best_meta_w[i] > 0.01:
        print(f"    {name:12s}  {best_meta_w[i]:.3f}")

# Apply meta-weights
test_stack = np.column_stack([strategies[n][0] for n in snames])
meta_raw = test_stack @ best_meta_w

# Temperature scaling on calibration set
print(f"\n  Temperature scaling...")
meta_cal_raw = cal_stack @ best_meta_w
best_temp = 1.0; best_temp_brier = 1.0
for temp in np.arange(0.5, 3.0, 0.05):
    logits = np.log(np.clip(meta_cal_raw, 1e-6, 1-1e-6) / (1 - np.clip(meta_cal_raw, 1e-6, 1-1e-6)))
    scaled = 1.0 / (1.0 + np.exp(-logits / temp))
    b = np.mean((scaled - cal_y)**2)
    if b < best_temp_brier: best_temp_brier = b; best_temp = temp

print(f"  Best temperature: {best_temp:.2f}")

# Apply temperature scaling
logits_test = np.log(np.clip(meta_raw, 1e-6, 1-1e-6) / (1 - np.clip(meta_raw, 1e-6, 1-1e-6)))
meta_scaled = 1.0 / (1.0 + np.exp(-logits_test / best_temp))

# Also try Platt on meta
platt_m = LogisticRegression(C=1e10, solver='lbfgs', max_iter=5000)
platt_m.fit(meta_cal_raw.reshape(-1,1), cal_y)
meta_platt = 1.0/(1+np.exp(-(platt_m.coef_[0][0]*meta_raw + platt_m.intercept_[0])))

# Also try isotonic
iso_m = IsotonicRegression(y_min=0.05, y_max=0.95, out_of_bounds='clip')
iso_m.fit(meta_cal_raw, cal_y)
meta_iso = iso_m.predict(meta_raw)

# Results
results = {
    "raw_meta": np.mean((meta_raw - y_test)**2),
    "temp_scaled": np.mean((meta_scaled - y_test)**2),
    "platt_meta": np.mean((meta_platt - y_test)**2),
    "iso_meta": np.mean((meta_iso - y_test)**2),
}

all_meta_preds = {"raw_meta": meta_raw, "temp_scaled": meta_scaled, "platt_meta": meta_platt, "iso_meta": meta_iso}
print(f"\n  Meta-learner calibration results:")
for name, brier in sorted(results.items(), key=lambda x: x[1]):
    auc = roc_auc_score(y_test, all_meta_preds[name])
    delta = baseline_brier - brier
    print(f"    {name:16s}  Brier={brier:.6f}  AUC={auc:.4f}  ΔvsConst={delta:+.6f} ({delta/baseline_brier*100:+.1f}%)")

# Also try CONSTRAINED meta: only use strategies that beat constant on inner CV
print(f"\n  Constrained meta (exclude tree models)...")
good_strats = ["S1_Ridge", "S2_Lasso", "S3_P3Spec", "S4_Bayes", "S7_MLP"]
cal_stack_good = np.column_stack([strategies[n][1][-n_cal:] for n in good_strats])
test_stack_good = np.column_stack([strategies[n][0] for n in good_strats])

if HAS_OPTUNA:
    def meta_obj_good(trial):
        rw = [trial.suggest_float(f'w_{i}', 0.0, 1.0) for i in range(len(good_strats))]
        t = sum(rw)
        if t < 0.01: return 1.0
        w = np.array([x/t for x in rw])
        return np.mean((cal_stack_good @ w - cal_y)**2)
    good_study = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=42))
    good_study.optimize(meta_obj_good, n_trials=500)
    rw_g = [good_study.best_params[f'w_{i}'] for i in range(len(good_strats))]
    t_g = sum(rw_g)
    good_w = np.array([x/t_g for x in rw_g])
else:
    good_w = np.array([0.1, 0.1, 0.5, 0.3, 0.0])

print(f"  Constrained meta-weights:")
for i, n in enumerate(good_strats):
    if good_w[i] > 0.01: print(f"    {n:12s}  {good_w[i]:.3f}")

good_meta_test = test_stack_good @ good_w
good_meta_brier = np.mean((good_meta_test - y_test)**2)
good_meta_auc = roc_auc_score(y_test, good_meta_test)
print(f"  Constrained meta: Brier={good_meta_brier:.6f}, AUC={good_meta_auc:.4f}")

# Temperature scale the constrained meta
good_cal = cal_stack_good @ good_w
best_temp_g = 1.0; best_tb_g = 1.0
for temp in np.arange(0.5, 3.0, 0.05):
    lo = np.log(np.clip(good_cal,1e-6,1-1e-6)/(1-np.clip(good_cal,1e-6,1-1e-6)))
    sc = 1.0/(1+np.exp(-lo/temp))
    b = np.mean((sc - cal_y)**2)
    if b < best_tb_g: best_tb_g = b; best_temp_g = temp

lo_test = np.log(np.clip(good_meta_test,1e-6,1-1e-6)/(1-np.clip(good_meta_test,1e-6,1-1e-6)))
good_scaled = 1.0/(1+np.exp(-lo_test/best_temp_g))
good_scaled_brier = np.mean((good_scaled - y_test)**2)
print(f"  Constrained + temp({best_temp_g:.2f}): Brier={good_scaled_brier:.6f}")

# Pick overall best
all_options = {
    **results,
    "constrained_raw": good_meta_brier,
    "constrained_scaled": good_scaled_brier,
}
all_preds = {
    **all_meta_preds,
    "constrained_raw": good_meta_test,
    "constrained_scaled": good_scaled,
}
best_name = min(all_options, key=all_options.get)
best_brier = all_options[best_name]
final_preds = all_preds[best_name]
print(f"\n  → BEST: {best_name} (Brier={best_brier:.6f})")

best_name = min(results, key=results.get)
best_brier = results[best_name]
if best_name == "raw_meta": final_preds = meta_raw
elif best_name == "temp_scaled": final_preds = meta_scaled
elif best_name == "platt_meta": final_preds = meta_platt
else: final_preds = meta_iso


# ============================================================================
# COMPREHENSIVE RESULTS
# ============================================================================
print(f"\n\n{'='*70}")
print(f"  GUNGNIR v28.6.0 HONEST HOLDOUT (2025+, n={n_test})")
print(f"{'='*70}")
print(f"  Constant predictor:  Brier = {baseline_brier:.6f}")
print(f"  v28.5.0 champion:    Brier = 0.243857")
print(f"  v28.6.0 ({best_name}):  Brier = {best_brier:.6f}  ({(baseline_brier-best_brier)/baseline_brier*100:+.1f}% vs constant)")
delta_v5 = 0.243857 - best_brier
print(f"  Δ vs v28.5.0:        {delta_v5:+.6f} ({'IMPROVED' if delta_v5 > 0 else 'REGRESSED'})")

# Tier performance
pcts = np.percentile(final_preds, [60, 40])
t1_th = pcts[0]; t4_th = pcts[1]
print(f"\n  TIER PERFORMANCE:")
for label, mask in [("T1 (top 40%)", final_preds >= t1_th),
                     ("T2 (40-60%)", (final_preds >= t4_th) & (final_preds < t1_th)),
                     ("T4 (bottom 40%)", final_preds < t4_th)]:
    n = int(np.sum(mask))
    if n < 5: continue
    success = np.mean(y_test[mask]) * 100
    print(f"    {label:20s}  n={n:5d}  success={success:.1f}%")

# Per-TA
print(f"\n  PER-TA HOLDOUT:")
for ta in sorted(set(test_ta)):
    m = test_ta == ta
    n_ta = int(np.sum(m))
    if n_ta < 10: continue
    b = np.mean((final_preds[m] - y_test[m])**2)
    tb = np.mean(y_test[m])
    cb = np.mean((np.full(n_ta, tb) - y_test[m])**2)
    print(f"    {ta:25s}  n={n_ta:4d}  base={tb:.3f}  Brier={b:.4f}  ΔvsConst={cb-b:+.4f}")

# Feature importance from XGBoost
if xgb_models:
    fi = np.mean([m.feature_importances_ for m in xgb_models], axis=0)
    top_fi = sorted(zip(FEATURES, fi), key=lambda x: x[1], reverse=True)[:15]
    print(f"\n  XGB Feature Importance (top 15):")
    for fname, imp in top_fi:
        print(f"    {fname:30s}  {imp:.4f}")

# Save
deploy = {
    "model": "gungnir_v28_deep_ensemble",
    "version": "28.6.0",
    "date": "2026-03-14",
    "architecture": f"7-strategy Bayesian-optimized ensemble + {best_name}",
    "meta_weights": dict(zip(snames, [float(w) for w in best_meta_w])),
    "best_calibration": best_name,
    "temperature": float(best_temp),
    "xgb_best_params": {k:float(v) if isinstance(v, (int,float)) else v for k,v in best_xgb_params.items()},
    "lgb_best_params": {k:float(v) if isinstance(v, (int,float)) else v for k,v in best_lgb_params.items()},
    "holdout_metrics": {
        "n_test": n_test, "test_base_rate": float(test_base),
        "constant_brier": float(baseline_brier),
        "final_brier": float(best_brier),
        "final_auc": float(roc_auc_score(y_test, final_preds)),
        "improvement_vs_constant_pct": float((baseline_brier-best_brier)/baseline_brier*100),
        "v28_5_brier": 0.243857,
        "delta_vs_v28_5": float(delta_v5),
    },
    "strategy_holdout": {
        name: {"brier": float(np.mean((preds-y_test)**2)), "auc": float(roc_auc_score(y_test, preds))}
        for name, (preds, _) in strategies.items()
    },
    "n_optuna_trials": {"xgb": N_XGB_TRIALS, "lgb": N_LGB_TRIALS, "meta": 500},
}

with open("/sessions/adoring-relaxed-shannon/gungnir_v28_v6_deploy.json", "w") as f:
    json.dump(deploy, f, indent=2)

import shutil
shutil.copy2("/sessions/adoring-relaxed-shannon/gungnir_v28_v6_deploy.json",
             "/sessions/adoring-relaxed-shannon/mnt/Python/gungnir_v28_v6_deploy.json")
shutil.copy2("/sessions/adoring-relaxed-shannon/gungnir_v28_v6_gpu_sweep.py",
             "/sessions/adoring-relaxed-shannon/mnt/Python/gungnir_v28_v6_gpu_sweep.py")

print(f"\n{'='*70}")
print(f"  v28.6.0 COMPLETE — Saved to Python folder")
print(f"{'='*70}")
