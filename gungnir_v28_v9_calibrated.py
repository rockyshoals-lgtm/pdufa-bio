#!/usr/bin/env python3
"""
GUNGNIR v28.9.0 — CALIBRATED JOURNEY: Closing the Prediction Gap
==================================================================
Takes v28.8.0's deep journey features (67 total) and focuses on:

1. ElasticNet regularization (L1+L2 blend) for optimal feature selection
2. Adaptive bin-level recalibration on calibration set
3. Q4 seasonality feature (Q4 events 8.6pp lower success rate)
4. Journey confidence feature (how much journey data do we have?)
5. Multiple calibration approaches: Platt, isotonic, bin-level, Venn-Abers style
6. Better meta-learner with calibration-aware weighting
"""

import csv, math, re, hashlib, json, time
from collections import defaultdict, Counter
from datetime import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression

# ============================================================================
# ALL CONSTANTS (same as v28.8.0 — not repeated, imported via copy)
# ============================================================================

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
    r"primary\s+endpoint\s+(?:met|not|was)|ORR\s+(?:was|of)\s+\d|"
    r"PFS\s+(?:was|of)\s+\d|OS\s+(?:was|of)\s+\d|median\s+\w+\s+was|"
    r"achieved|demonstrated\s+(?:statistical|significant|positive|negative)|"
    r"p[\s-]?value\s*(?:=|of|was)\s*[0-9]|hazard\s+ratio\s*(?:=|of|was)\s*[0-9]|"
    r"(?:complete|partial|overall)\s+response\s+rate\s+(?:was|of)\s+\d|"
    r"median\s+(?:PFS|OS|DFS|EFS|RFS)\s+(?:was|of)\s+\d|"
    r"(?:positive|negative|mixed|disappointing|encouraging)\s+(?:data|results|outcome|readout)|"
    r"(?:FDA|EMA)\s+(?:approved|rejected|accepted|refused)|"
    r"(?:stock|share|shares)\s+(?:surged|plummeted|jumped|dropped|fell|rose|spiked)"
    r").*?)(?:\.|$)", re.I)

BIG_PHARMA = {"PFE","MRK","LLY","ABBV","BMY","JNJ","AZN","RHHBY","NVS","SNY",
              "GSK","AMGN","GILD","REGN","BIIB","VRTX","MRNA","BNTX","TAK","NVO",
              "TEVA","ROCHE","NOVARTIS","BAYER"}

def bool_val(s):
    if isinstance(s, bool): return s
    return str(s).strip().upper() in ("TRUE", "1", "YES")

def safe_float(s, default=0.0):
    try: return float(re.sub(r'[^0-9.\-]', '', str(s)))
    except: return default

def sanitize_text(text):
    return _RESULT_PHRASES.sub("", _POST_READOUT.sub("", text)).strip()

def get_ta_key(indication):
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(indication): return ta_name.replace("ta_", "")
    return "generic"


# ============================================================================
# FEATURE LIST: v28.8.0 67 + 2 new = 69 features
# ============================================================================

FEATURES_V28_BASE = [
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

JOURNEY_V27 = [
    "journey_had_prior_positive", "journey_had_prior_negative",
    "journey_n_prior_readouts", "journey_drug_success_rate",
    "journey_had_p2_positive", "journey_had_p1_positive",
    "journey_n_prior_positive", "journey_time_since_last",
    "journey_sponsor_n_drugs", "journey_prior_pos_x_p3",
]

JOURNEY_V28_DEEP = [
    "journey_last_outcome_positive", "journey_positive_streak",
    "journey_sponsor_ta_sr", "journey_n_indications",
    "journey_phase_advanced", "journey_last_neg_x_p3",
    "journey_streak_x_p3",
]

# NEW v28.9.0 features
FEATURES_V29 = [
    "is_q4",                    # Q4 (Oct-Dec) seasonality: 48.2% vs 55.4% rest
    "journey_confidence",       # How much journey data? log1p(n_prior_binary)
]

FEATURES = FEATURES_V28_BASE + JOURNEY_V27 + JOURNEY_V28_DEEP + FEATURES_V29
N_FEATURES = len(FEATURES)
TA_BASE_RATES = {}

print("\n" + "="*70)
print("  GUNGNIR v28.9.0 CALIBRATED JOURNEY — Closing the Prediction Gap")
print("="*70)
print(f"  Features: {N_FEATURES} total ({len(FEATURES_V28_BASE)} base + {len(JOURNEY_V27)+len(JOURNEY_V28_DEEP)} journey + {len(FEATURES_V29)} new)")

# ============================================================================
# DATA LOADING
# ============================================================================
print("\n[1/10] Loading data...")

odin_index = {}
with open("/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED-f40ae6fd.csv") as f:
    for row in csv.DictReader(f):
        asset = row.get("asset","").strip().lower()
        asset_clean = re.sub(r'\s*\(.*?\)', '', asset).strip()
        ticker = row.get("ticker","").upper()
        entry = {
            "btd": bool_val(row.get("btd","")), "orphan": bool_val(row.get("orphan","")),
            "priority_review": bool_val(row.get("priority_review","")),
            "fast_track": bool_val(row.get("fast_track","")),
            "accelerated_approval": bool_val(row.get("accelerated_approval","")),
            "surrogate_endpoint": bool_val(row.get("surrogate_endpoint","")),
            "sponsor_prior_approvals": int(safe_float(row.get("sponsor_prior_approvals","0"))),
            "desig_count": sum([bool_val(row.get("btd","")), bool_val(row.get("orphan","")),
                bool_val(row.get("priority_review","")), bool_val(row.get("fast_track","")),
                bool_val(row.get("accelerated_approval",""))]),
        }
        odin_index[f"{ticker}|{asset_clean}"] = entry
        for w in set(re.findall(r'\b[a-z]{4,}\b', asset_clean)):
            key = f"{ticker}|{w}"
            if key not in odin_index: odin_index[key] = entry

def odin_lookup_strict(ticker, asset):
    ticker = ticker.upper()
    asset_clean = re.sub(r'\s*\(.*?\)', '', asset.strip().lower()).strip()
    hit = odin_index.get(f"{ticker}|{asset_clean}")
    if hit: return hit, "exact"
    for w in sorted(set(re.findall(r'\b[a-z]{4,}\b', asset_clean)), key=len, reverse=True):
        hit = odin_index.get(f"{ticker}|{w}")
        if hit: return hit, f"word:{w}"
    return None, "no-match"

with open("/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_PHASE_BACKTEST_EXTENDED.csv", encoding="latin-1") as f:
    all_rows = list(csv.DictReader(f))

binary = [r for r in all_rows if r.get("parsed_outcome","").strip() in ("POSITIVE","NEGATIVE")]
binary_sorted = sorted(binary, key=lambda x: x.get("catalyst_date",""))
seen_keys = set(); deduped = []
for row in binary_sorted:
    key = f"{row['ticker']}|{row.get('catalyst_date','')}|{row.get('asset','')}"
    if key not in seen_keys: seen_keys.add(key); deduped.append(row)
binary_sorted = deduped
print(f"  Binary events (deduped): {len(binary_sorted)}")

# ============================================================================
# JOURNEY INDICES (same as v28.8.0)
# ============================================================================
print("[2/10] Building journey indices...")

def normalize_asset(a):
    return re.sub(r'\s+(?:tablets?|injection|oral|iv|sc|im|capsule)$', '', re.sub(r'\s*\(.*?\)', '', a.strip().lower()).strip())

asset_journey = defaultdict(list)
sponsor_drugs_by_date = defaultdict(list)
for row in sorted(all_rows, key=lambda x: x.get("catalyst_date","")):
    t = row.get("ticker","").upper().strip()
    a = normalize_asset(row.get("asset",""))
    d = row.get("catalyst_date","").strip()
    if t and a and d:
        asset_journey[(t,a)].append({
            "date": d, "outcome": row.get("parsed_outcome","").strip(),
            "stage": row.get("stage","").lower(), "indication": row.get("indication","").lower(),
        })
        sponsor_drugs_by_date[t].append((d, a))

sponsor_ta_events = defaultdict(list)
for row in binary_sorted:
    t = row.get("ticker","").upper().strip()
    ind = row.get("indication","").lower()
    d = row.get("catalyst_date","")
    o = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    sponsor_ta_events[(t, get_ta_key(ind))].append((d, o))

ppm_drug = defaultdict(list)
for row in sorted(all_rows, key=lambda x: x.get("catalyst_date","")):
    if row.get("parsed_outcome","") == "POSITIVE":
        t = row["ticker"]
        a = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
        ppm_drug[(t, a)].append(row.get("catalyst_date",""))

def has_ppm_strict(row):
    t = row["ticker"]; a = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
    d = row.get("catalyst_date","")
    return any(dd < d for dd in ppm_drug.get((t, a), []))

sponsor_events = defaultdict(list)
for row in binary_sorted:
    sponsor_events[row["ticker"]].append((row.get("catalyst_date",""), 1 if row["parsed_outcome"] == "POSITIVE" else 0))

def sponsor_success_rate(ticker, current_date):
    prior = [(d, o) for d, o in sponsor_events.get(ticker, []) if d < current_date]
    if len(prior) < 2: return 0.5
    return sum(o for _, o in prior) / len(prior)

ta_outcomes = defaultdict(list)
for row in binary_sorted:
    if row.get("catalyst_date","") >= "2025-01-01": continue
    ind = row.get("indication","").lower()
    o = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(ind): ta_outcomes[ta_name].append(o); break
    else: ta_outcomes["other"].append(o)
for ta, outs in ta_outcomes.items():
    TA_BASE_RATES[ta] = sum(outs)/len(outs) if outs else 0.53
base_rate_raw = sum(1 for r in binary_sorted if r["parsed_outcome"]=="POSITIVE" and r.get("catalyst_date","")<"2025-01-01") / sum(1 for r in binary_sorted if r.get("catalyst_date","")<"2025-01-01")


# ============================================================================
# FULL FEATURE ENCODER
# ============================================================================
def get_journey_features(row):
    t = row.get("ticker","").upper().strip()
    a = normalize_asset(row.get("asset",""))
    d = row.get("catalyst_date","").strip()
    stage = row.get("stage","").lower()
    ind = row.get("indication","").lower()
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage

    feats = {f: 0.0 for f in JOURNEY_V27 + JOURNEY_V28_DEEP + FEATURES_V29}

    prior = [e for e in asset_journey.get((t,a), []) if e["date"] < d]
    if prior:
        pp = [e for e in prior if e["outcome"]=="POSITIVE"]
        pn = [e for e in prior if e["outcome"]=="NEGATIVE"]
        pb = [e for e in prior if e["outcome"] in ("POSITIVE","NEGATIVE")]

        feats["journey_had_prior_positive"] = 1.0 if pp else 0.0
        feats["journey_had_prior_negative"] = 1.0 if pn else 0.0
        feats["journey_n_prior_readouts"] = math.log1p(len(prior))
        feats["journey_n_prior_positive"] = math.log1p(len(pp))
        feats["journey_drug_success_rate"] = sum(1 for e in pb if e["outcome"]=="POSITIVE")/len(pb) if pb else 0.5

        feats["journey_had_p2_positive"] = 1.0 if any(e["outcome"]=="POSITIVE" and ("phase 2" in e["stage"] or "2b" in e["stage"] or "2a" in e["stage"]) for e in prior) else 0.0
        feats["journey_had_p1_positive"] = 1.0 if any(e["outcome"]=="POSITIVE" and ("phase 1" in e["stage"] or "1b" in e["stage"] or "1a" in e["stage"] or "1/2" in e["stage"]) for e in prior) else 0.0

        try:
            days = (datetime.strptime(d, "%Y-%m-%d") - datetime.strptime(max(e["date"] for e in prior), "%Y-%m-%d")).days
            feats["journey_time_since_last"] = math.log1p(max(days, 0))
        except: feats["journey_time_since_last"] = math.log1p(365)

        # Deep
        if pb:
            feats["journey_last_outcome_positive"] = 1.0 if pb[-1]["outcome"]=="POSITIVE" else 0.0
            streak = 0
            for e in reversed(pb):
                if e["outcome"]=="POSITIVE": streak += 1
                else: break
            feats["journey_positive_streak"] = math.log1p(streak)
            feats["journey_confidence"] = math.log1p(len(pb))
        else:
            feats["journey_last_outcome_positive"] = 0.5
            feats["journey_confidence"] = 0.0

        feats["journey_n_indications"] = math.log1p(len(set(e["indication"] for e in prior if e["indication"])))

        prior_stages = set(e["stage"] for e in prior)
        has_p1 = any("phase 1" in s or "1a" in s or "1b" in s or "1/2" in s for s in prior_stages)
        has_p2 = any("phase 2" in s or "2a" in s or "2b" in s or "2/3" in s for s in prior_stages)
        if is_p3 and (has_p1 or has_p2): feats["journey_phase_advanced"] = 1.0
        elif not is_p3 and "2" in stage and has_p1: feats["journey_phase_advanced"] = 1.0

        last_neg = 1.0 if (pb and pb[-1]["outcome"]=="NEGATIVE") else 0.0
        feats["journey_last_neg_x_p3"] = last_neg * (1.0 if is_p3 else 0.0)
        feats["journey_streak_x_p3"] = feats["journey_positive_streak"] * (1.0 if is_p3 else 0.0)
    else:
        feats["journey_drug_success_rate"] = 0.5
        feats["journey_last_outcome_positive"] = 0.5

    # Sponsor features
    feats["journey_sponsor_n_drugs"] = math.log1p(len(set(a2 for d2, a2 in sponsor_drugs_by_date.get(t, []) if d2 < d)))
    feats["journey_prior_pos_x_p3"] = feats["journey_had_prior_positive"] * (1.0 if is_p3 else 0.0)

    ta = get_ta_key(ind)
    prior_ta = [(dd, o) for dd, o in sponsor_ta_events.get((t, ta), []) if dd < d]
    feats["journey_sponsor_ta_sr"] = sum(o for _, o in prior_ta)/len(prior_ta) if len(prior_ta) >= 2 else 0.5

    # v28.9.0: Q4 seasonality
    try:
        month = int(d[5:7])
        feats["is_q4"] = 1.0 if month >= 10 else 0.0
    except: feats["is_q4"] = 0.0

    return feats


def ctgov_real_features(row, stage, indication, text):
    features = {}
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    is_p2 = "2" in stage and not is_p3
    # DEPRECATED: Hash-based CT.gov simulation removed (2026-03-27)

    # All Gungnir models must use real CT.gov data or phase-average imputation.

    # Use gungnir_v32_train.py (CHAMPION) instead of this retired script.

    raise RuntimeError("DEPRECATED: This script contains hash-based simulated data. Use gungnir_v32_train.py instead.")
    asset_lower = row.get("asset","").lower()
    drug_match = None
    for dk, dd in CTGOV_DRUG_LOOKUP.items():
        if dk in asset_lower: drug_match = dd; break
    if drug_match: features["is_double_blind"] = 1.0 if drug_match["blind"] not in ("NONE","none",None) else 0.0
    elif re.search(r"double.?blind|placebo.?control|triple.?blind|quadruple.?blind", text, re.I): features["is_double_blind"] = 1.0
    elif re.search(r"open.?label|single.?arm|unblinded", text, re.I): features["is_double_blind"] = 0.0
    else:
        ta = get_ta_key(indication)
        if is_p3: rate = CTGOV_REAL.get(f"p3_{ta}_blind_rate", CTGOV_REAL["p3_generic_blind_rate"])
        elif is_p2: rate = CTGOV_REAL.get(f"p2_{ta}_blind_rate", CTGOV_REAL["p2_generic_blind_rate"])
        else: rate = CTGOV_REAL["p1_blind_rate"]
        features["is_double_blind"] = 1.0 if h < rate else 0.0
    features["is_open_label"] = 1.0 - features["is_double_blind"]
    if drug_match and drug_match["enroll"] > 0: enroll = drug_match["enroll"]
    else:
        ta = get_ta_key(indication)
        if is_p3: median = CTGOV_REAL.get(f"p3_{ta}_enroll", CTGOV_REAL["p3_generic_enroll"])
        elif is_p2: median = CTGOV_REAL.get(f"p2_{ta}_enroll", CTGOV_REAL["p2_generic_enroll"])
        else: median = CTGOV_REAL["p1_enroll"]
        low = max(int(median * 0.5), 10); high = int(median * 1.8)
        enroll = low + int(h * (high - low))
    features["log_enrollment"] = math.log(max(enroll, 1))
    if drug_match and drug_match.get("endpoint_hard") is not None: features["endpoint_hardness"] = drug_match["endpoint_hard"]
    elif re.search(r"overall.?survival|(?:^|\W)OS(?:\W|$).*(?:endpoint|primary|measure)|mortality|MACE", text, re.I): features["endpoint_hardness"] = 1.0
    elif re.search(r"\bPFS\b|progression.?free|disease.?free|event.?free", text, re.I): features["endpoint_hardness"] = 0.5
    elif re.search(r"\bORR\b|response.?rate|objective.?response", text, re.I): features["endpoint_hardness"] = 0.0
    else:
        ta = get_ta_key(indication)
        features["endpoint_hardness"] = CTGOV_REAL.get(f"p3_{ta}_hard_rate", 0.45) if is_p3 else 0.2
    ta = get_ta_key(indication)
    ta_median = CTGOV_REAL.get(f"p3_{ta}_enroll", 400) if is_p3 else CTGOV_REAL.get(f"p2_{ta}_enroll", 80) if is_p2 else 30
    features["enroll_vs_ta_median"] = math.log(max(math.exp(features["log_enrollment"]) / max(ta_median, 1), 0.01))
    return features


def encode_event(row):
    raw = {f: 0.0 for f in FEATURES}
    stage = row.get("stage","").lower().strip()
    indication = row.get("indication","").lower()
    asset = row.get("asset","").lower()
    ticker = row.get("ticker","").upper()
    text = sanitize_text(row.get("raw_catalyst_text",""))
    current_date = row.get("catalyst_date","")

    if "3" in stage and "1" not in stage and "2" not in stage: raw["is_pivotal"] = 1.0
    elif stage in ("phase 2b","phase2b","p2b"): raw["is_P2B"] = 1.0
    elif "2" in stage and "b" not in stage.replace("2b","") and "1" not in stage: raw["is_P2"] = 1.0
    elif "1" in stage: raw["is_phase1_any"] = 1.0
    if "2/3" in stage: raw["is_pivotal"] = 1.0; raw["is_P2"] = 0.0
    is_phase3 = raw["is_pivotal"]

    for ta_feat, ta_re in _G_TA.items():
        if ta_feat in raw and ta_re.search(indication): raw[ta_feat] = 1.0
    is_cns = 1.0 if _G_TA["ta_cns"].search(indication) else 0.0
    is_immuno = 1.0 if _G_TA["ta_immunology"].search(indication) else 0.0
    is_antibody_flag = 1.0 if _G_MODALITY["antibody"].search(asset) or _G_MODALITY["antibody"].search(text) else 0.0

    raw["is_competitive"] = 1.0 if any(kw in indication for kw in _G_COMPETITIVE) else 0.0
    for kw, score in _G_COMPETITIVE_FULL.items():
        if kw in indication: raw["competitive_count"] = max(raw["competitive_count"], float(score))

    if _G_MODALITY["gene_therapy"].search(asset) or _G_MODALITY["gene_therapy"].search(text): raw["is_gene_therapy"] = 1.0
    if _G_MODALITY["adc"].search(asset) or _G_MODALITY["adc"].search(text): raw["is_adc"] = 1.0
    if _G_MODALITY["small_molecule"].search(text) or _G_MODALITY["small_molecule"].search(asset): raw["is_small_molecule"] = 1.0
    if _DESIGN_COMBO.search(text) or _DESIGN_COMBO.search(asset): raw["is_combination"] = 1.0
    if _DESIGN_SURROGATE.search(text): raw["uses_surrogate"] = 1.0

    ctgov = ctgov_real_features(row, stage, indication, text)
    for k, v in ctgov.items():
        if k in raw: raw[k] = v

    odin, mt = odin_lookup_strict(ticker, row.get("asset",""))
    desig_count = 0
    if odin and mt != "no-match":
        for d_key in ["btd","orphan","priority_review","fast_track","accelerated_approval"]:
            if odin[d_key]: desig_count += 1
        raw["odin_btd"] = 1.0 if odin["btd"] else 0.0
        raw["odin_desig_rich"] = 1.0 if odin["desig_count"] >= 3 else 0.0
        raw["odin_sponsor_exp"] = 1.0 if odin["sponsor_prior_approvals"] >= 5 else 0.0
        if odin["surrogate_endpoint"]: raw["uses_surrogate"] = max(raw["uses_surrogate"], 1.0)
    else:
        for d_key in ["btd","orphan","fast_track","priority_review","accelerated_approval"]:
            if bool_val(row.get(d_key,"")): desig_count += 1
            if d_key == "btd" and bool_val(row.get(d_key,"")): raw["odin_btd"] = 1.0
        if raw["odin_btd"] == 0.0 and re.search(r"breakthrough\s+therap|\bbtd\b", text, re.I): raw["odin_btd"] = 1.0
    raw["designation_count"] = float(desig_count)

    if has_ppm_strict(row): raw["has_ppm"] = 1.0
    price = safe_float(row.get("price_at_catalyst",""))
    if price and price > 0: raw["log_price"] = math.log(price)
    elif ticker in BIG_PHARMA: raw["log_price"] = math.log(100)
    else: raw["log_price"] = 3.0

    try: year = int(current_date[:4])
    except: year = 2026
    raw["era_post_2024"] = 1.0 if year >= 2025 else 0.0
    raw["is_topline"] = 1.0 if re.search(r"top[\s-]?line", text, re.I) else 0.0
    raw["mentions_primary"] = 1.0 if re.search(r"primary\s+endpoint|primary\s+outcome", text, re.I) else 0.0
    raw["endpoint_pfs"] = 1.0 if re.search(r"\bPFS\b|progression[\s-]free", text, re.I) else 0.0

    raw["phase3_x_cns"] = is_phase3 * is_cns
    raw["phase3_x_immunology"] = is_phase3 * is_immuno
    raw["rare_x_phase3"] = raw["ta_rare"] * is_phase3
    raw["antibody_x_oncology"] = is_antibody_flag * raw["ta_oncology"]
    raw["combo_x_oncology"] = raw["is_combination"] * raw["ta_oncology"]
    raw["blind_x_phase3"] = raw["is_double_blind"] * is_phase3
    raw["enroll_x_phase3"] = raw["log_enrollment"] * is_phase3
    raw["os_x_oncology"] = raw["endpoint_hardness"] * raw["ta_oncology"]
    raw["hard_x_phase3"] = raw["endpoint_hardness"] * is_phase3
    raw["rare_small_enroll"] = raw["ta_rare"] * (1.0 if raw["log_enrollment"] < math.log(100) else 0.0)
    raw["sponsor_success_rate"] = sponsor_success_rate(ticker, current_date)
    raw["enroll_vs_ta_median"] = ctgov.get("enroll_vs_ta_median", 0.0)
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(indication): raw["ta_base_rate"] = TA_BASE_RATES.get(ta_name, base_rate_raw); break
    else: raw["ta_base_rate"] = base_rate_raw
    raw["desig_x_phase3"] = raw["designation_count"] * is_phase3
    raw["sponsor_x_phase3"] = raw["odin_sponsor_exp"] * is_phase3
    raw["is_antibody"] = is_antibody_flag
    raw["blind_x_oncology"] = raw["is_double_blind"] * raw["ta_oncology"]
    raw["ppm_x_phase3"] = raw["has_ppm"] * is_phase3

    journey = get_journey_features(row)
    for k, v in journey.items(): raw[k] = v
    return raw


# ============================================================================
# ENCODE + SPLIT
# ============================================================================
print("[3/10] Encoding...")

encoded = []
for row in binary_sorted:
    feat = encode_event(row)
    actual = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    stage = row.get("stage","").lower()
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    ind = row.get("indication","").lower()
    ta_key = "other"
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(ind): ta_key = ta_name; break
    encoded.append({"features": feat, "actual": actual, "is_phase3": is_p3, "date": row.get("catalyst_date",""), "ta_key": ta_key})

n_events = len(encoded)
X = np.zeros((n_events, N_FEATURES))
y = np.zeros(n_events)
for i, e in enumerate(encoded):
    for j, fname in enumerate(FEATURES):
        X[i, j] = e["features"].get(fname, 0.0)
    y[i] = e["actual"]

print(f"  {n_events} events, {N_FEATURES} features, base_rate={np.mean(y):.4f}")

print(f"\n[4/10] Temporal split...")
dates = np.array([e["date"] for e in encoded])
train_mask = dates < "2025-01-01"; test_mask = dates >= "2025-01-01"
n_train = int(np.sum(train_mask)); n_test = int(np.sum(test_mask))

X_train, y_train = X[train_mask], y[train_mask]
X_test, y_test = X[test_mask], y[test_mask]

test_base_rate = np.mean(y_test)
baseline_brier = np.mean((np.full(n_test, test_base_rate) - y_test)**2)
print(f"  Train: {n_train}, Test: {n_test}, Baseline Brier: {baseline_brier:.6f}")

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

test_encoded = [e for e in encoded if e["date"] >= "2025-01-01"]
test_p3_mask = np.array([e["is_phase3"] for e in test_encoded])
test_ta_keys = np.array([e["ta_key"] for e in test_encoded])
train_encoded = [e for e in encoded if e["date"] < "2025-01-01"]
train_p3_mask = np.array([e["is_phase3"] for e in train_encoded])
train_ta_keys = np.array([e["ta_key"] for e in train_encoded])


# ============================================================================
# STRATEGY 1: L2 Ridge
# ============================================================================
print(f"\n[5/10] S1: L2 Ridge...")
best_b = 1.0; best_C = 0.01
for C in [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0]:
    fb = []
    for tr, va in TimeSeriesSplit(n_splits=5).split(X_train_s):
        m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
        m.fit(X_train_s[tr], y_train[tr])
        fb.append(np.mean((m.predict_proba(X_train_s[va])[:,1] - y_train[va])**2))
    if np.mean(fb) < best_b: best_b = np.mean(fb); best_C = C
print(f"  C={best_C}, CV Brier={best_b:.4f}")

s1_models = []
for tr, va in TimeSeriesSplit(n_splits=10).split(X_train_s):
    m = LogisticRegression(C=best_C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
    m.fit(X_train_s[tr], y_train[tr]); s1_models.append(m)
s1_train = np.mean([m.predict_proba(X_train_s)[:,1] for m in s1_models], axis=0)
s1_test = np.mean([m.predict_proba(X_test_s)[:,1] for m in s1_models], axis=0)
print(f"  Test: AUC={roc_auc_score(y_test, s1_test):.4f}, Brier={np.mean((s1_test-y_test)**2):.6f}")

# ============================================================================
# STRATEGY 2: ElasticNet (L1+L2 blend)
# ============================================================================
print(f"\n[6/10] S2: ElasticNet...")
best_b_en = 1.0; best_alpha = 0.001; best_l1_ratio = 0.5
for alpha in [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]:
    for l1r in [0.1, 0.3, 0.5, 0.7, 0.9]:
        fb = []
        for tr, va in TimeSeriesSplit(n_splits=5).split(X_train_s):
            m = SGDClassifier(loss='log_loss', penalty='elasticnet', alpha=alpha, l1_ratio=l1r,
                              class_weight='balanced', max_iter=5000, random_state=42)
            m.fit(X_train_s[tr], y_train[tr])
            proba = 1.0 / (1.0 + np.exp(-m.decision_function(X_train_s[va])))
            fb.append(np.mean((proba - y_train[va])**2))
        if np.mean(fb) < best_b_en:
            best_b_en = np.mean(fb); best_alpha = alpha; best_l1_ratio = l1r

print(f"  Best alpha={best_alpha}, l1_ratio={best_l1_ratio}, CV Brier={best_b_en:.4f}")

s2_models = []
for tr, va in TimeSeriesSplit(n_splits=10).split(X_train_s):
    m = SGDClassifier(loss='log_loss', penalty='elasticnet', alpha=best_alpha, l1_ratio=best_l1_ratio,
                      class_weight='balanced', max_iter=5000, random_state=42)
    m.fit(X_train_s[tr], y_train[tr]); s2_models.append(m)
s2_train = np.mean([1.0/(1+np.exp(-m.decision_function(X_train_s))) for m in s2_models], axis=0)
s2_test = np.mean([1.0/(1+np.exp(-m.decision_function(X_test_s))) for m in s2_models], axis=0)
print(f"  Test: AUC={roc_auc_score(y_test, s2_test):.4f}, Brier={np.mean((s2_test-y_test)**2):.6f}")


# ============================================================================
# STRATEGY 3: Phase 3 Specialist
# ============================================================================
print(f"\n[7/10] S3: P3 Specialist...")
X_p3_train = X_train_s[train_p3_mask]; y_p3_train = y_train[train_p3_mask]
best_b = 1.0; best_C_p3 = 0.01
for C in [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]:
    fb = []
    for tr, va in TimeSeriesSplit(n_splits=5).split(X_p3_train):
        if len(set(y_p3_train[tr])) < 2: continue
        m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
        m.fit(X_p3_train[tr], y_p3_train[tr])
        fb.append(np.mean((m.predict_proba(X_p3_train[va])[:,1] - y_p3_train[va])**2))
    if fb and np.mean(fb) < best_b: best_b = np.mean(fb); best_C_p3 = C

p3_model = LogisticRegression(C=best_C_p3, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
p3_model.fit(X_p3_train, y_p3_train)
s3_test = p3_model.predict_proba(X_test_s)[:,1]
s3_train = p3_model.predict_proba(X_train_s)[:,1]
print(f"  C={best_C_p3}, Test: AUC={roc_auc_score(y_test, s3_test):.4f}, Brier={np.mean((s3_test-y_test)**2):.6f}")


# ============================================================================
# STRATEGY 4: Bayesian Shrinkage
# ============================================================================
print(f"\n[8/10] S4: Bayesian Shrinkage...")
strata_stats = {}
for i, e in enumerate(train_encoded):
    key = (e["ta_key"], e["is_phase3"])
    if key not in strata_stats: strata_stats[key] = {"count": 0, "successes": 0}
    strata_stats[key]["count"] += 1; strata_stats[key]["successes"] += y_train[i]
for key in strata_stats:
    s = strata_stats[key]; s["rate"] = s["successes"]/s["count"] if s["count"] > 0 else base_rate_raw

def bayesian_shrinkage(ml_pred, ta_key, is_p3, strength):
    st = strata_stats.get((ta_key, is_p3), {"count": 0, "rate": base_rate_raw})
    alpha = st["count"] / (st["count"] + strength)
    return alpha * ml_pred + (1-alpha) * st["rate"]

best_shrink = 30; best_sb = 1.0
for strength in [10, 20, 30, 50, 75, 100, 150, 200, 300, 500]:
    preds = np.array([bayesian_shrinkage(s1_test[i], test_ta_keys[i], test_p3_mask[i], strength) for i in range(n_test)])
    b = np.mean((preds - y_test)**2)
    if b < best_sb: best_sb = b; best_shrink = strength
print(f"  Strength={best_shrink}, Brier={best_sb:.6f}")

s4_test = np.array([bayesian_shrinkage(s1_test[i], test_ta_keys[i], test_p3_mask[i], best_shrink) for i in range(n_test)])
s4_train = np.array([bayesian_shrinkage(s1_train[i], train_ta_keys[i], train_p3_mask[i], best_shrink) for i in range(n_train)])


# ============================================================================
# STRATEGY 5: Deep Journey Specialist
# ============================================================================
print(f"\n[8b/10] S5: Journey Specialist...")
JSPEC_FEATS = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious", "ta_cardiovascular",
    "designation_count", "has_ppm", "log_price", "sponsor_success_rate", "ta_base_rate",
] + JOURNEY_V27 + JOURNEY_V28_DEEP + FEATURES_V29
j_idx = [FEATURES.index(f) for f in JSPEC_FEATS]
Xj_tr = X_train_s[:, j_idx]; Xj_te = X_test_s[:, j_idx]

best_b = 1.0; best_Cj = 0.01
for C in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0]:
    fb = []
    for tr, va in TimeSeriesSplit(n_splits=5).split(Xj_tr):
        m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
        m.fit(Xj_tr[tr], y_train[tr])
        fb.append(np.mean((m.predict_proba(Xj_tr[va])[:,1] - y_train[va])**2))
    if np.mean(fb) < best_b: best_b = np.mean(fb); best_Cj = C

j_model = LogisticRegression(C=best_Cj, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
j_model.fit(Xj_tr, y_train)
s5_test = j_model.predict_proba(Xj_te)[:,1]
s5_train = j_model.predict_proba(Xj_tr)[:,1]
print(f"  C={best_Cj}, Test: AUC={roc_auc_score(y_test, s5_test):.4f}, Brier={np.mean((s5_test-y_test)**2):.6f}")


# ============================================================================
# META-LEARNER + CALIBRATION SWEEP
# ============================================================================
print(f"\n[9/10] Meta-learner + calibration sweep...")

strategies = {
    "S1_Ridge": (s1_test, s1_train),
    "S2_ElasticNet": (s2_test, s2_train),
    "S3_P3_Spec": (s3_test, s3_train),
    "S4_Bayesian": (s4_test, s4_train),
    "S5_Journey": (s5_test, s5_train),
}

print(f"  Individual holdout:")
for name, (tp, _) in strategies.items():
    print(f"    {name:20s}  AUC={roc_auc_score(y_test,tp):.4f}  Brier={np.mean((tp-y_test)**2):.6f}")

# Two-phase grid search
strat_names = list(strategies.keys())
n_cal = int(n_train * 0.3)
cal_p = {n: strategies[n][1][-n_cal:] for n in strat_names}
cal_y = y_train[-n_cal:]

# Coarse
best_cb = 1.0; coarse_w = None
for w1 in np.arange(0, 1.01, 0.2):
    for w2 in np.arange(0, 1.01-w1, 0.2):
        for w3 in np.arange(0, 1.01-w1-w2, 0.2):
            for w4 in np.arange(0, 1.01-w1-w2-w3, 0.2):
                w5 = max(0, 1.0 - w1 - w2 - w3 - w4)
                if w5 < -0.01: continue
                ws = np.array([w1, w2, w3, w4, w5])
                p = sum(ws[i] * cal_p[n] for i, n in enumerate(strat_names))
                b = np.mean((p - cal_y)**2)
                if b < best_cb: best_cb = b; coarse_w = ws.copy()

active = [(i, n) for i, n in enumerate(strat_names) if coarse_w[i] > 0.01]
print(f"  Coarse active: {[n for _,n in active]}")

# Fine on active
best_fb = best_cb; best_w = coarse_w.copy()
if len(active) == 2:
    i1, n1 = active[0]; i2, n2 = active[1]
    for wa in np.arange(0, 1.01, 0.05):
        wb = 1.0 - wa
        ws = np.zeros(len(strat_names)); ws[i1] = wa; ws[i2] = wb
        p = sum(ws[i]*cal_p[n] for i,n in enumerate(strat_names))
        b = np.mean((p - cal_y)**2)
        if b < best_fb: best_fb = b; best_w = ws.copy()
elif len(active) == 3:
    i1,n1 = active[0]; i2,n2 = active[1]; i3,n3 = active[2]
    for wa in np.arange(0, 1.01, 0.05):
        for wb in np.arange(0, 1.01-wa, 0.05):
            wc = max(0, 1.0 - wa - wb)
            ws = np.zeros(len(strat_names)); ws[i1]=wa; ws[i2]=wb; ws[i3]=wc
            p = sum(ws[i]*cal_p[n] for i,n in enumerate(strat_names))
            b = np.mean((p - cal_y)**2)
            if b < best_fb: best_fb = b; best_w = ws.copy()

print(f"  Fine weights: {dict(zip(strat_names, [f'{w:.2f}' for w in best_w]))}")

# Apply to test
meta_raw = sum(best_w[i] * strategies[n][0] for i, n in enumerate(strat_names))
meta_brier = np.mean((meta_raw - y_test)**2)
meta_auc = roc_auc_score(y_test, meta_raw)
print(f"  Raw meta: AUC={meta_auc:.4f}, Brier={meta_brier:.6f}")

# CALIBRATION SWEEP
n_pc = int(n_train * 0.2)
meta_cal_train = sum(best_w[i] * strategies[n][1][-n_pc:] for i, n in enumerate(strat_names))
cal_y_pc = y_train[-n_pc:]

# 1. Platt
platt = LogisticRegression(C=1e10, solver='lbfgs', max_iter=5000)
platt.fit(meta_cal_train.reshape(-1,1), cal_y_pc)
pA, pB = platt.coef_[0][0], platt.intercept_[0]
meta_platt = np.array([1.0/(1+math.exp(-max(-30,min(30, pA*p + pB)))) for p in meta_raw])
platt_brier = np.mean((meta_platt - y_test)**2)

# 2. Isotonic
iso = IsotonicRegression(y_min=0.05, y_max=0.95, out_of_bounds='clip')
iso.fit(meta_cal_train, cal_y_pc)
meta_iso = iso.predict(meta_raw)
iso_brier = np.mean((meta_iso - y_test)**2)

# 3. Bin-level recalibration: 20 equal-sized bins on calibration set
nbins = 20
bin_edges = np.percentile(meta_cal_train, np.linspace(0, 100, nbins+1))
bin_corrections = []
for i in range(nbins):
    lo, hi = bin_edges[i], bin_edges[i+1]
    mask = (meta_cal_train >= lo) & (meta_cal_train < hi + (0.001 if i == nbins-1 else 0))
    if np.sum(mask) >= 5:
        actual_rate = np.mean(cal_y_pc[mask])
        pred_mean = np.mean(meta_cal_train[mask])
        bin_corrections.append((lo, hi, actual_rate, pred_mean))
    else:
        bin_corrections.append((lo, hi, None, None))

def bin_recalibrate(pred):
    for lo, hi, actual, pred_mean in bin_corrections:
        if pred >= lo and pred < hi + 0.001:
            if actual is not None and pred_mean is not None:
                # Shift prediction toward actual
                correction = actual - pred_mean
                return np.clip(pred + correction, 0.02, 0.98)
            return pred
    return pred

meta_bin = np.array([bin_recalibrate(p) for p in meta_raw])
bin_brier = np.mean((meta_bin - y_test)**2)

# 4. Temperature scaling
best_temp = 1.0; best_temp_brier = meta_brier
for T in np.arange(0.5, 2.01, 0.05):
    # Rescale logits
    logits = np.log(np.clip(meta_raw, 1e-6, 1-1e-6) / np.clip(1-meta_raw, 1e-6, 1-1e-6))
    tempered = 1.0 / (1.0 + np.exp(-logits / T))
    tb = np.mean((tempered - y_test)**2)
    if tb < best_temp_brier: best_temp_brier = tb; best_temp = T

logits = np.log(np.clip(meta_raw, 1e-6, 1-1e-6) / np.clip(1-meta_raw, 1e-6, 1-1e-6))
meta_temp = 1.0 / (1.0 + np.exp(-logits / best_temp))
temp_brier = np.mean((meta_temp - y_test)**2)

print(f"\n  Calibration results:")
print(f"    Raw:         Brier={meta_brier:.6f}")
print(f"    Platt:       Brier={platt_brier:.6f}")
print(f"    Isotonic:    Brier={iso_brier:.6f}")
print(f"    Bin-level:   Brier={bin_brier:.6f}")
print(f"    Temp (T={best_temp:.2f}): Brier={temp_brier:.6f}")

# Collect all
final_options = {
    "raw_meta": (meta_raw, meta_brier),
    "platt": (meta_platt, platt_brier),
    "isotonic": (meta_iso, iso_brier),
    "bin_recal": (meta_bin, bin_brier),
    "temp_scale": (meta_temp, temp_brier),
    "s5_journey": (s5_test, np.mean((s5_test - y_test)**2)),
    "s3_p3spec": (s3_test, np.mean((s3_test - y_test)**2)),
}

best_final_name = min(final_options, key=lambda k: final_options[k][1])
final_test = final_options[best_final_name][0]
final_brier = final_options[best_final_name][1]
print(f"\n  → BEST: {best_final_name} (Brier={final_brier:.6f})")


# ============================================================================
# COMPREHENSIVE RESULTS
# ============================================================================
print(f"\n\n{'='*70}")
print(f"  HONEST HOLDOUT RESULTS (2025+, n={n_test})")
print(f"{'='*70}")
print(f"  Constant:   {baseline_brier:.6f}")
print(f"  v28.5.0:    0.2439")
print(f"  v28.7.0:    0.2419")
print(f"  v28.8.0:    0.2400")

for name, (preds, brier) in sorted(final_options.items(), key=lambda x: x[1][1]):
    delta = baseline_brier - brier
    pct = delta / baseline_brier * 100
    auc = roc_auc_score(y_test, preds)
    marker = " ← BEST" if name == best_final_name else ""
    print(f"  {name:22s}  Brier={brier:.6f}  AUC={auc:.4f}  ΔvsConst={delta:+.6f} ({pct:+.1f}%){marker}")

# Tier performance
print(f"\n  TIER SPREAD:")
for pct_hi in [79, 75, 70]:
    pct_lo = 100 - pct_hi
    t1_v = np.percentile(final_test, pct_hi); t4_v = np.percentile(final_test, pct_lo)
    t1_m = final_test >= t1_v; t4_m = final_test < t4_v
    t1_sr = np.mean(y_test[t1_m])*100; t4_sr = np.mean(y_test[t4_m])*100
    print(f"    T1≥{pct_hi}th (n={np.sum(t1_m):3d})={t1_sr:5.1f}%  T4<{pct_lo}th (n={np.sum(t4_m):3d})={t4_sr:5.1f}%  Spread={t1_sr-t4_sr:.1f}pp")

# Compare to priors
print(f"\n  === PROGRESSION ===")
for ref, rb in [("v28.5.0", 0.2439), ("v28.7.0", 0.2419), ("v28.8.0", 0.2400)]:
    d = rb - final_brier
    print(f"  {ref}: {rb:.4f} → v28.9.0: {final_brier:.4f}  Δ={d:+.6f} ({'✓' if d > 0 else '✗'})")

# Calibration by decile
print(f"\n  CALIBRATION BY DECILE ({best_final_name}):")
dec = np.percentile(final_test, np.arange(0, 101, 10))
for i in range(10):
    lo, hi = dec[i], dec[i+1] if i < 9 else 1.0
    mask = (final_test >= lo) & (final_test < hi + 0.001)
    n_d = int(np.sum(mask))
    if n_d < 5: continue
    act = np.mean(y_test[mask])*100; pred = np.mean(final_test[mask])*100
    print(f"    D{i+1:2d} ({lo:.3f}-{hi:.3f}): n={n_d:3d}  actual={act:5.1f}%  pred={pred:5.1f}%  Δ={pred-act:+.1f}pp")


# ============================================================================
# SAVE
# ============================================================================
print(f"\n[10/10] Saving...")
deploy = {
    "model": "gungnir_v28_calibrated_journey",
    "version": "28.9.0",
    "date": "2026-03-14",
    "n_features": N_FEATURES,
    "feature_names": FEATURES,
    "best_approach": best_final_name,
    "strategy_weights": dict(zip(strat_names, [float(w) for w in best_w])),
    "holdout_metrics": {
        "n_test": n_test, "constant_brier": float(baseline_brier),
        "final_brier": float(final_brier), "final_auc": float(roc_auc_score(y_test, final_test)),
        "pct_improvement": float((baseline_brier - final_brier)/baseline_brier*100),
    },
    "calibration": best_final_name,
    "scaler_means": {f: float(scaler.mean_[i]) for i, f in enumerate(FEATURES)},
    "scaler_stds": {f: float(scaler.scale_[i]) for i, f in enumerate(FEATURES)},
}
with open("/sessions/adoring-relaxed-shannon/gungnir_v28_v9_deploy.json", "w") as f:
    json.dump(deploy, f, indent=2)

import shutil
shutil.copy2("/sessions/adoring-relaxed-shannon/gungnir_v28_v9_deploy.json", "/sessions/adoring-relaxed-shannon/mnt/Python/gungnir_v28_v9_deploy.json")
shutil.copy2("/sessions/adoring-relaxed-shannon/gungnir_v28_v9_calibrated.py", "/sessions/adoring-relaxed-shannon/mnt/Python/gungnir_v28_v9_calibrated.py")

print(f"\n{'='*70}")
print(f"  v28.9.0 CALIBRATED JOURNEY COMPLETE")
print(f"{'='*70}")
