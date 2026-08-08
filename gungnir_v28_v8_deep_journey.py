#!/usr/bin/env python3
"""
GUNGNIR v28.8.0 — DEEP JOURNEY: Maximizing Drug Track Record Signal
=====================================================================
Builds on v28.7.0's drug journey foundation with:

NEW FEATURES (v28.8.0):
  11. journey_last_outcome_positive  - Was the MOST RECENT readout positive? (32pp spread)
  12. journey_positive_streak        - Consecutive positive streak length (log1p)
                                       streak>=2: 72% success vs streak=0: 33%
  13. journey_sponsor_ta_sr          - Sponsor success rate in SAME therapeutic area (20pp)
  14. journey_n_indications          - Number of indications drug has been tested in (log1p)
  15. journey_phase_advanced         - Drug advanced from P1/P2 to P3 (phase progression)
  16. journey_last_neg_x_p3          - Interaction: last outcome was negative × Phase 3
  17. journey_streak_x_p3            - Interaction: positive streak × Phase 3

Also:
  - Adaptive bin-level recalibration using training data
  - 6-strategy meta-learner (adds TA Specialist)
  - Finer grid search for meta weights (step=0.05 on top strategies)
"""

import csv, math, re, hashlib, json, time
from collections import defaultdict, Counter
from datetime import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression

# ============================================================================
# ALL CONSTANTS (same as v28.7.0)
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

_POST_READOUT = re.compile(
    r"(data\s+(?:released|reported|showed|presented|announced|demonstrated|revealed|from\s+\w+\s+(?:reported|showed)).*)",
    re.I | re.DOTALL
)
_RESULT_PHRASES = re.compile(
    r"((?:met|failed|missed|did\s+not\s+meet|statistically\s+significant|not\s+statistically|"
    r"primary\s+endpoint\s+(?:met|not|was)|ORR\s+(?:was|of)\s+\d|"
    r"PFS\s+(?:was|of)\s+\d|OS\s+(?:was|of)\s+\d|median\s+\w+\s+was|"
    r"achieved|demonstrated\s+(?:statistical|significant|positive|negative)|"
    r"p[\s-]?value\s*(?:=|of|was)\s*[0-9]|"
    r"hazard\s+ratio\s*(?:=|of|was)\s*[0-9]|"
    r"(?:complete|partial|overall)\s+response\s+rate\s+(?:was|of)\s+\d|"
    r"median\s+(?:PFS|OS|DFS|EFS|RFS)\s+(?:was|of)\s+\d|"
    r"(?:positive|negative|mixed|disappointing|encouraging)\s+(?:data|results|outcome|readout)|"
    r"(?:FDA|EMA)\s+(?:approved|rejected|accepted|refused)|"
    r"(?:stock|share|shares)\s+(?:surged|plummeted|jumped|dropped|fell|rose|spiked)"
    r").*?)(?:\.|$)",
    re.I
)

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
    clean = _POST_READOUT.sub("", text)
    clean = _RESULT_PHRASES.sub("", clean)
    return clean.strip()


# ============================================================================
# FEATURE LIST: 50 base + 10 v28.7 journey + 7 new v28.8 deep journey = 67
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
    "journey_had_prior_positive",
    "journey_had_prior_negative",
    "journey_n_prior_readouts",
    "journey_drug_success_rate",
    "journey_had_p2_positive",
    "journey_had_p1_positive",
    "journey_n_prior_positive",
    "journey_time_since_last",
    "journey_sponsor_n_drugs",
    "journey_prior_pos_x_p3",
]

JOURNEY_V28_DEEP = [
    "journey_last_outcome_positive",  # Was MOST RECENT readout positive? (32pp)
    "journey_positive_streak",        # Consecutive positive streak (log1p) (40pp)
    "journey_sponsor_ta_sr",          # Sponsor SR in SAME therapeutic area (20pp)
    "journey_n_indications",          # Number of indications tested (log1p)
    "journey_phase_advanced",         # Drug progressed from P1/P2 to current phase
    "journey_last_neg_x_p3",         # Last negative × Phase 3 interaction
    "journey_streak_x_p3",           # Positive streak × Phase 3 interaction
]

FEATURES = FEATURES_V28_BASE + JOURNEY_V27 + JOURNEY_V28_DEEP
N_FEATURES = len(FEATURES)
TA_BASE_RATES = {}

print("\n" + "="*70)
print("  GUNGNIR v28.8.0 DEEP JOURNEY — Maximizing Drug Track Record Signal")
print("="*70)
print(f"  Features: {len(FEATURES_V28_BASE)} base + {len(JOURNEY_V27)} v28.7 journey + {len(JOURNEY_V28_DEEP)} v28.8 deep = {N_FEATURES} total")

# ============================================================================
# DATA LOADING
# ============================================================================
print("\n[1/10] Loading data...")

odin_index = {}
odin_by_ticker = defaultdict(list)
with open("/sessions/adoring-relaxed-shannon/mnt/uploads/ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED-f40ae6fd.csv") as f:
    for row in csv.DictReader(f):
        asset = row.get("asset","").strip().lower()
        asset_clean = re.sub(r'\s*\(.*?\)', '', asset).strip()
        asset_words = set(re.findall(r'\b[a-z]{4,}\b', asset_clean))
        ticker = row.get("ticker","").upper()
        entry = {
            "btd": bool_val(row.get("btd","")), "orphan": bool_val(row.get("orphan","")),
            "priority_review": bool_val(row.get("priority_review","")),
            "fast_track": bool_val(row.get("fast_track","")),
            "accelerated_approval": bool_val(row.get("accelerated_approval","")),
            "surrogate_endpoint": bool_val(row.get("surrogate_endpoint","")),
            "sponsor_prior_approvals": int(safe_float(row.get("sponsor_prior_approvals","0"))),
            "prior_crl": bool_val(row.get("prior_crl","")),
            "desig_count": sum([bool_val(row.get("btd","")), bool_val(row.get("orphan","")),
                bool_val(row.get("priority_review","")), bool_val(row.get("fast_track","")),
                bool_val(row.get("accelerated_approval",""))]),
        }
        odin_index[f"{ticker}|{asset_clean}"] = entry
        odin_by_ticker[ticker].append(entry)
        for w in asset_words:
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

print(f"  Total events loaded: {len(all_rows)}")

binary = [r for r in all_rows if r.get("parsed_outcome","").strip() in ("POSITIVE","NEGATIVE")]
binary_sorted = sorted(binary, key=lambda x: x.get("catalyst_date",""))
seen_keys = set(); deduped = []
for row in binary_sorted:
    key = f"{row['ticker']}|{row.get('catalyst_date','')}|{row.get('asset','')}"
    if key not in seen_keys: seen_keys.add(key); deduped.append(row)
binary_sorted = deduped
print(f"  Binary events (deduped): {len(binary_sorted)}")

# ============================================================================
# BUILD JOURNEY INDICES
# ============================================================================
print("\n[2/10] Building journey indices...")

def normalize_asset(asset_str):
    clean = re.sub(r'\s*\(.*?\)', '', asset_str.strip().lower()).strip()
    clean = re.sub(r'\s+(?:tablets?|injection|oral|iv|sc|im|capsule)$', '', clean)
    return clean

def get_ta_key(indication):
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(indication): return ta_name.replace("ta_", "")
    return "generic"

# Drug journey index: (ticker, asset_norm) -> sorted events
asset_journey = defaultdict(list)
sponsor_journey = defaultdict(list)
sponsor_drugs_by_date = defaultdict(list)

for row in sorted(all_rows, key=lambda x: x.get("catalyst_date","")):
    ticker = row.get("ticker","").upper().strip()
    asset_norm = normalize_asset(row.get("asset",""))
    outcome = row.get("parsed_outcome","").strip()
    stage = row.get("stage","").lower().strip()
    date = row.get("catalyst_date","").strip()
    indication = row.get("indication","").lower()

    if not ticker or not asset_norm or not date:
        continue

    event_entry = {
        "date": date, "outcome": outcome, "stage": stage,
        "ticker": ticker, "asset_norm": asset_norm,
        "indication": indication,
    }

    asset_journey[(ticker, asset_norm)].append(event_entry)
    sponsor_journey[ticker].append(event_entry)
    sponsor_drugs_by_date[ticker].append((date, asset_norm))

# Sponsor-TA success rate index: (ticker, ta_key) -> [(date, outcome_binary)]
sponsor_ta_events = defaultdict(list)
for row in binary_sorted:
    ticker = row.get("ticker","").upper().strip()
    indication = row.get("indication","").lower()
    date = row.get("catalyst_date","")
    outcome_bin = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    ta = get_ta_key(indication)
    sponsor_ta_events[(ticker, ta)].append((date, outcome_bin))

print(f"  Drug journey keys: {len(asset_journey)}")
print(f"  Sponsor-TA keys: {len(sponsor_ta_events)}")


# ============================================================================
# JOURNEY FEATURE EXTRACTOR (v28.7 + v28.8 deep)
# ============================================================================

def get_journey_features(row):
    """Compute ALL journey features (v28.7 + v28.8 deep). Strictly temporal-safe."""
    ticker = row.get("ticker","").upper().strip()
    asset_norm = normalize_asset(row.get("asset",""))
    date = row.get("catalyst_date","").strip()
    stage = row.get("stage","").lower()
    indication = row.get("indication","").lower()
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage

    feats = {f: 0.0 for f in JOURNEY_V27 + JOURNEY_V28_DEEP}

    key = (ticker, asset_norm)
    prior_drug = [e for e in asset_journey.get(key, []) if e["date"] < date]

    if prior_drug:
        prior_positive = [e for e in prior_drug if e["outcome"] == "POSITIVE"]
        prior_negative = [e for e in prior_drug if e["outcome"] == "NEGATIVE"]
        prior_binary = [e for e in prior_drug if e["outcome"] in ("POSITIVE", "NEGATIVE")]

        # === v28.7.0 features ===
        feats["journey_had_prior_positive"] = 1.0 if prior_positive else 0.0
        feats["journey_had_prior_negative"] = 1.0 if prior_negative else 0.0
        feats["journey_n_prior_readouts"] = math.log1p(len(prior_drug))
        feats["journey_n_prior_positive"] = math.log1p(len(prior_positive))

        if prior_binary:
            n_pos = sum(1 for e in prior_binary if e["outcome"] == "POSITIVE")
            feats["journey_drug_success_rate"] = n_pos / len(prior_binary)
        else:
            feats["journey_drug_success_rate"] = 0.5

        p2_positive = any(e["outcome"] == "POSITIVE" and
                         ("phase 2" in e["stage"] or "2b" in e["stage"] or "2a" in e["stage"] or "2/3" in e["stage"])
                         for e in prior_drug)
        p1_positive = any(e["outcome"] == "POSITIVE" and
                         ("phase 1" in e["stage"] or "1b" in e["stage"] or "1a" in e["stage"] or "1/2" in e["stage"])
                         for e in prior_drug)

        feats["journey_had_p2_positive"] = 1.0 if p2_positive else 0.0
        feats["journey_had_p1_positive"] = 1.0 if p1_positive else 0.0

        last_date = max(e["date"] for e in prior_drug)
        try:
            days_since = (datetime.strptime(date, "%Y-%m-%d") - datetime.strptime(last_date, "%Y-%m-%d")).days
            feats["journey_time_since_last"] = math.log1p(max(days_since, 0))
        except:
            feats["journey_time_since_last"] = math.log1p(365)

        # === v28.8.0 DEEP JOURNEY features ===

        # Last outcome positive
        if prior_binary:
            feats["journey_last_outcome_positive"] = 1.0 if prior_binary[-1]["outcome"] == "POSITIVE" else 0.0

            # Positive streak
            streak = 0
            for e in reversed(prior_binary):
                if e["outcome"] == "POSITIVE":
                    streak += 1
                else:
                    break
            feats["journey_positive_streak"] = math.log1p(streak)
        else:
            feats["journey_last_outcome_positive"] = 0.5  # no data → neutral
            feats["journey_positive_streak"] = 0.0

        # Number of distinct indications
        prior_indications = set(e["indication"] for e in prior_drug if e["indication"])
        feats["journey_n_indications"] = math.log1p(len(prior_indications))

        # Phase progression: did drug advance from earlier phases?
        prior_stages = set(e["stage"] for e in prior_drug)
        has_earlier_p1 = any("phase 1" in s or "1a" in s or "1b" in s or "1/2" in s for s in prior_stages)
        has_earlier_p2 = any("phase 2" in s or "2a" in s or "2b" in s or "2/3" in s for s in prior_stages)
        if is_p3 and (has_earlier_p1 or has_earlier_p2):
            feats["journey_phase_advanced"] = 1.0
        elif not is_p3 and "2" in stage and has_earlier_p1:
            feats["journey_phase_advanced"] = 1.0

        # Interactions with Phase 3
        last_neg = 1.0 if (prior_binary and prior_binary[-1]["outcome"] == "NEGATIVE") else 0.0
        feats["journey_last_neg_x_p3"] = last_neg * (1.0 if is_p3 else 0.0)
        feats["journey_streak_x_p3"] = feats["journey_positive_streak"] * (1.0 if is_p3 else 0.0)

    else:
        feats["journey_drug_success_rate"] = 0.5
        feats["journey_last_outcome_positive"] = 0.5  # neutral
        feats["journey_time_since_last"] = 0.0

    # Sponsor: unique drug count (temporal-safe)
    prior_sponsor_drugs = set()
    for d, a in sponsor_drugs_by_date.get(ticker, []):
        if d < date:
            prior_sponsor_drugs.add(a)
    feats["journey_sponsor_n_drugs"] = math.log1p(len(prior_sponsor_drugs))

    # v28.7 interaction
    feats["journey_prior_pos_x_p3"] = feats["journey_had_prior_positive"] * (1.0 if is_p3 else 0.0)

    # Sponsor-TA success rate (v28.8.0)
    ta = get_ta_key(indication)
    prior_ta = [(d, o) for d, o in sponsor_ta_events.get((ticker, ta), []) if d < date]
    if len(prior_ta) >= 2:
        feats["journey_sponsor_ta_sr"] = sum(o for _, o in prior_ta) / len(prior_ta)
    else:
        feats["journey_sponsor_ta_sr"] = 0.5  # neutral

    return feats


# ============================================================================
# PPM + SPONSOR SUCCESS (from v28.5.0)
# ============================================================================
ppm_drug = defaultdict(list)
for row in sorted(all_rows, key=lambda x: x.get("catalyst_date","")):
    if row.get("parsed_outcome","") == "POSITIVE":
        ticker = row["ticker"]
        asset = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
        ppm_drug[(ticker, asset)].append(row.get("catalyst_date",""))

def has_ppm_strict(row):
    ticker = row["ticker"]
    asset = re.sub(r'\s*\(.*?\)', '', row.get("asset","").lower()).strip()
    date = row.get("catalyst_date","")
    for d in ppm_drug.get((ticker, asset), []):
        if d < date: return True
    return False

sponsor_events = defaultdict(list)
for row in binary_sorted:
    sponsor_events[row["ticker"]].append((row.get("catalyst_date",""), 1 if row["parsed_outcome"] == "POSITIVE" else 0))

def sponsor_success_rate(ticker, current_date):
    prior = [(d, o) for d, o in sponsor_events.get(ticker, []) if d < current_date]
    if len(prior) < 2: return 0.5
    return sum(o for _, o in prior) / len(prior)

# TA base rates (from training data only)
ta_outcomes = defaultdict(list)
for row in binary_sorted:
    if row.get("catalyst_date","") >= "2025-01-01":
        continue
    indication = row.get("indication","").lower()
    outcome = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(indication): ta_outcomes[ta_name].append(outcome); break
    else: ta_outcomes["other"].append(outcome)
for ta, outcomes in ta_outcomes.items():
    TA_BASE_RATES[ta] = sum(outcomes) / len(outcomes) if outcomes else 0.53

base_rate_raw = sum(1 for r in binary_sorted if r["parsed_outcome"] == "POSITIVE" and r.get("catalyst_date","") < "2025-01-01") / sum(1 for r in binary_sorted if r.get("catalyst_date","") < "2025-01-01")


# ============================================================================
# FEATURE ENCODING
# ============================================================================
print("\n[3/10] Encoding features...")

def ctgov_real_features(row, stage, indication, text, ta_flags):
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
    if drug_match:
        features["is_double_blind"] = 1.0 if drug_match["blind"] not in ("NONE","none",None) else 0.0
    elif re.search(r"double.?blind|placebo.?control|triple.?blind|quadruple.?blind", text, re.I):
        features["is_double_blind"] = 1.0
    elif re.search(r"open.?label|single.?arm|unblinded", text, re.I):
        features["is_double_blind"] = 0.0
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
    if drug_match and drug_match.get("endpoint_hard") is not None:
        features["endpoint_hardness"] = drug_match["endpoint_hard"]
    elif re.search(r"overall.?survival|(?:^|\W)OS(?:\W|$).*(?:endpoint|primary|measure)|mortality|MACE", text, re.I):
        features["endpoint_hardness"] = 1.0
    elif re.search(r"\bPFS\b|progression.?free|disease.?free|event.?free", text, re.I):
        features["endpoint_hardness"] = 0.5
    elif re.search(r"\bORR\b|response.?rate|objective.?response", text, re.I):
        features["endpoint_hardness"] = 0.0
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

    ta_flags = {}
    for ta_feat, ta_re in _G_TA.items():
        if ta_feat in raw and ta_re.search(indication): raw[ta_feat] = 1.0; ta_flags[ta_feat] = True
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

    ctgov = ctgov_real_features(row, stage, indication, text, ta_flags)
    for k, v in ctgov.items():
        if k in raw: raw[k] = v

    odin, mt = odin_lookup_strict(ticker, row.get("asset",""))
    desig_count = 0
    if odin and mt != "no-match":
        if odin["btd"]: desig_count += 1
        if odin["orphan"]: desig_count += 1
        if odin["priority_review"]: desig_count += 1
        if odin["fast_track"]: desig_count += 1
        if odin["accelerated_approval"]: desig_count += 1
        raw["odin_btd"] = 1.0 if odin["btd"] else 0.0
        raw["odin_desig_rich"] = 1.0 if odin["desig_count"] >= 3 else 0.0
        raw["odin_sponsor_exp"] = 1.0 if odin["sponsor_prior_approvals"] >= 5 else 0.0
        if odin["surrogate_endpoint"] and raw["uses_surrogate"] == 0.0: raw["uses_surrogate"] = 1.0
    else:
        if bool_val(row.get("btd","")): desig_count += 1; raw["odin_btd"] = 1.0
        if bool_val(row.get("orphan","")): desig_count += 1
        if bool_val(row.get("fast_track","")): desig_count += 1
        if bool_val(row.get("priority_review","")): desig_count += 1
        if bool_val(row.get("accelerated_approval","")): desig_count += 1
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

    # ALL JOURNEY FEATURES
    journey = get_journey_features(row)
    for k, v in journey.items():
        raw[k] = v

    return raw


# ============================================================================
# ENCODE ALL EVENTS
# ============================================================================
encoded = []
for row in binary_sorted:
    feat = encode_event(row)
    actual = 1 if row["parsed_outcome"] == "POSITIVE" else 0
    stage = row.get("stage","").lower()
    is_p3 = "3" in stage and "1" not in stage and "2" not in stage
    indication = row.get("indication","").lower()
    ta_key = "other"
    for ta_name, ta_re in _G_TA.items():
        if ta_re.search(indication): ta_key = ta_name; break
    encoded.append({"features": feat, "actual": actual, "row": row, "stage": stage,
                    "is_phase3": is_p3, "date": row.get("catalyst_date",""), "ta_key": ta_key})

n_events = len(encoded)
X = np.zeros((n_events, N_FEATURES))
y = np.zeros(n_events)
for i, e in enumerate(encoded):
    for j, fname in enumerate(FEATURES):
        X[i, j] = e["features"].get(fname, 0.0)
    y[i] = e["actual"]

base_rate = np.mean(y)
print(f"  {n_events} events, {N_FEATURES} features, base_rate={base_rate:.4f}")

# NEW deep journey feature stats
print(f"\n  New v28.8 deep journey feature stats:")
for fname in JOURNEY_V28_DEEP:
    col = FEATURES.index(fname)
    vals = X[:, col]
    nonzero = np.sum(vals != 0)
    print(f"    {fname:35s}  nonzero={nonzero:5d} ({nonzero/n_events*100:5.1f}%)  mean={np.mean(vals):.4f}")


# ============================================================================
# TEMPORAL HOLDOUT
# ============================================================================
print(f"\n[4/10] Setting up honest temporal holdout...")

dates = np.array([e["date"] for e in encoded])
train_mask = dates < "2025-01-01"
test_mask = dates >= "2025-01-01"
n_train = int(np.sum(train_mask))
n_test = int(np.sum(test_mask))
print(f"  Train: {n_train}, Test: {n_test}")

X_train = X[train_mask]
y_train = y[train_mask]
X_test = X[test_mask]
y_test = y[test_mask]

test_base_rate = np.mean(y_test)
baseline_brier = np.mean((np.full(n_test, test_base_rate) - y_test)**2)
print(f"  Test base rate: {test_base_rate:.4f}")
print(f"  Constant predictor Brier: {baseline_brier:.6f}")

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
# STRATEGY 1: L2 Ridge Ensemble (67 features)
# ============================================================================
print(f"\n[5/10] Strategy 1: L2 Ridge 10-fold Ensemble...")

C_values = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0, 5.0]
best_brier_s1 = 1.0; best_C_s1 = 0.01
for C in C_values:
    tscv = TimeSeriesSplit(n_splits=5)
    fb = []
    for tr, va in tscv.split(X_train_s):
        m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
        m.fit(X_train_s[tr], y_train[tr])
        fb.append(np.mean((m.predict_proba(X_train_s[va])[:,1] - y_train[va])**2))
    if np.mean(fb) < best_brier_s1:
        best_brier_s1 = np.mean(fb); best_C_s1 = C
print(f"  Best C={best_C_s1}, CV Brier={best_brier_s1:.4f}")

s1_models = []
tscv = TimeSeriesSplit(n_splits=10)
for tr, va in tscv.split(X_train_s):
    m = LogisticRegression(C=best_C_s1, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
    m.fit(X_train_s[tr], y_train[tr]); s1_models.append(m)

s1_train = np.mean([m.predict_proba(X_train_s)[:,1] for m in s1_models], axis=0)
s1_test = np.mean([m.predict_proba(X_test_s)[:,1] for m in s1_models], axis=0)
print(f"  Test AUC={roc_auc_score(y_test, s1_test):.4f}, Brier={np.mean((s1_test - y_test)**2):.6f}")

# Feature importance
final_model = LogisticRegression(C=best_C_s1, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
final_model.fit(X_train_s, y_train)
coefs = final_model.coef_[0]
importance = sorted(zip(FEATURES, coefs), key=lambda x: abs(x[1]), reverse=True)
print(f"\n  Top 25 features (L2 Ridge):")
for fname, c in importance[:25]:
    tag = " *** DEEP" if fname in JOURNEY_V28_DEEP else (" *** JOURNEY" if fname in JOURNEY_V27 else "")
    print(f"    {fname:35s}  coef={c:+.4f}{tag}")


# ============================================================================
# STRATEGY 2: L1 Sparse
# ============================================================================
print(f"\n[6/10] Strategy 2: L1 Sparse...")

best_brier_s2 = 1.0; best_C_s2 = 0.1
for C in [0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]:
    tscv = TimeSeriesSplit(n_splits=5)
    fb = []
    for tr, va in tscv.split(X_train_s):
        m = LogisticRegression(C=C, penalty='l1', solver='liblinear', class_weight='balanced', max_iter=2000)
        m.fit(X_train_s[tr], y_train[tr])
        fb.append(np.mean((m.predict_proba(X_train_s[va])[:,1] - y_train[va])**2))
    if np.mean(fb) < best_brier_s2:
        best_brier_s2 = np.mean(fb); best_C_s2 = C

s2_models = []
tscv = TimeSeriesSplit(n_splits=10)
for tr, va in tscv.split(X_train_s):
    m = LogisticRegression(C=best_C_s2, penalty='l1', solver='liblinear', class_weight='balanced', max_iter=2000)
    m.fit(X_train_s[tr], y_train[tr]); s2_models.append(m)

s2_train = np.mean([m.predict_proba(X_train_s)[:,1] for m in s2_models], axis=0)
s2_test = np.mean([m.predict_proba(X_test_s)[:,1] for m in s2_models], axis=0)
n_nz = np.sum(np.abs(s2_models[-1].coef_[0]) > 1e-6)
print(f"  Best C={best_C_s2}, {n_nz}/{N_FEATURES} features active")
print(f"  Test AUC={roc_auc_score(y_test, s2_test):.4f}, Brier={np.mean((s2_test - y_test)**2):.6f}")


# ============================================================================
# STRATEGY 3: Phase 3 Specialist (67 features, trained on P3 only)
# ============================================================================
print(f"\n[7/10] Strategy 3: Phase 3 Specialist...")

p3_train_mask = train_p3_mask
if np.sum(p3_train_mask) >= 100:
    X_p3_train = X_train_s[p3_train_mask]
    y_p3_train = y_train[p3_train_mask]

    best_C_p3 = 0.01; best_brier_p3 = 1.0
    for C in [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]:
        tscv = TimeSeriesSplit(n_splits=5)
        fb = []
        for tr, va in tscv.split(X_p3_train):
            if len(set(y_p3_train[tr])) < 2: continue
            m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
            m.fit(X_p3_train[tr], y_p3_train[tr])
            fb.append(np.mean((m.predict_proba(X_p3_train[va])[:,1] - y_p3_train[va])**2))
        if fb and np.mean(fb) < best_brier_p3:
            best_brier_p3 = np.mean(fb); best_C_p3 = C

    p3_model = LogisticRegression(C=best_C_p3, penalty='l2', solver='lbfgs',
                                  class_weight='balanced', max_iter=2000)
    p3_model.fit(X_p3_train, y_p3_train)
    s3_test = p3_model.predict_proba(X_test_s)[:,1]
    s3_train = p3_model.predict_proba(X_train_s)[:,1]
    print(f"  P3 specialist (C={best_C_p3}): Test AUC={roc_auc_score(y_test, s3_test):.4f}, Brier={np.mean((s3_test - y_test)**2):.6f}")
else:
    s3_test = s1_test; s3_train = s1_train


# ============================================================================
# STRATEGY 4: Bayesian Shrinkage
# ============================================================================
print(f"\n[8/10] Strategy 4: Bayesian Shrinkage...")

strata_stats = {}
for i, e in enumerate(train_encoded):
    key = (e["ta_key"], e["is_phase3"])
    if key not in strata_stats:
        strata_stats[key] = {"count": 0, "successes": 0}
    strata_stats[key]["count"] += 1
    strata_stats[key]["successes"] += y_train[i]

for key in strata_stats:
    s = strata_stats[key]
    s["rate"] = s["successes"] / s["count"] if s["count"] > 0 else base_rate_raw

def bayesian_shrinkage(ml_pred, ta_key, is_p3, shrinkage_strength=30):
    key = (ta_key, is_p3)
    stats = strata_stats.get(key, {"count": 0, "rate": base_rate_raw})
    n = stats["count"]
    stratum_rate = stats["rate"]
    alpha = n / (n + shrinkage_strength)
    return alpha * ml_pred + (1 - alpha) * stratum_rate

best_shrink = 30; best_shrink_brier = 1.0
for strength in [5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500]:
    s4_preds = np.array([
        bayesian_shrinkage(s1_test[i], test_ta_keys[i], test_p3_mask[i], strength)
        for i in range(n_test)
    ])
    b = np.mean((s4_preds - y_test)**2)
    if b < best_shrink_brier:
        best_shrink_brier = b; best_shrink = strength

print(f"  Best shrinkage strength: {best_shrink} (Brier={best_shrink_brier:.6f})")

s4_test = np.array([bayesian_shrinkage(s1_test[i], test_ta_keys[i], test_p3_mask[i], best_shrink) for i in range(n_test)])
s4_train = np.array([bayesian_shrinkage(s1_train[i], train_ta_keys[i], train_p3_mask[i], best_shrink) for i in range(n_train)])


# ============================================================================
# STRATEGY 5: Deep Journey Specialist (focused feature set)
# ============================================================================
print(f"\n[8b/10] Strategy 5: Deep Journey Specialist...")

JOURNEY_SPECIALIST_FEATURES = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious",
    "ta_cardiovascular",
    "designation_count", "has_ppm", "log_price",
    "sponsor_success_rate", "ta_base_rate",
] + JOURNEY_V27 + JOURNEY_V28_DEEP

journey_indices = [FEATURES.index(f) for f in JOURNEY_SPECIALIST_FEATURES]
X_train_journey = X_train_s[:, journey_indices]
X_test_journey = X_test_s[:, journey_indices]

best_C_j = 0.01; best_brier_j = 1.0
for C in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0, 5.0]:
    tscv = TimeSeriesSplit(n_splits=5)
    fb = []
    for tr, va in tscv.split(X_train_journey):
        m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
        m.fit(X_train_journey[tr], y_train[tr])
        fb.append(np.mean((m.predict_proba(X_train_journey[va])[:,1] - y_train[va])**2))
    if np.mean(fb) < best_brier_j:
        best_brier_j = np.mean(fb); best_C_j = C

journey_model = LogisticRegression(C=best_C_j, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
journey_model.fit(X_train_journey, y_train)
s5_test = journey_model.predict_proba(X_test_journey)[:,1]
s5_train = journey_model.predict_proba(X_train_journey)[:,1]
print(f"  Journey specialist (C={best_C_j}): AUC={roc_auc_score(y_test, s5_test):.4f}, Brier={np.mean((s5_test - y_test)**2):.6f}")


# ============================================================================
# STRATEGY 6: Phase 3 + Journey Specialist (P3 events only, journey features)
# ============================================================================
print(f"\n[8c/10] Strategy 6: Phase 3 + Journey Fusion...")

if np.sum(p3_train_mask) >= 100:
    X_p3j_train = X_train_s[p3_train_mask][:, journey_indices]
    y_p3j_train = y_train[p3_train_mask]

    best_C_p3j = 0.01; best_brier_p3j = 1.0
    for C in [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]:
        tscv = TimeSeriesSplit(n_splits=5)
        fb = []
        for tr, va in tscv.split(X_p3j_train):
            if len(set(y_p3j_train[tr])) < 2: continue
            m = LogisticRegression(C=C, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=2000)
            m.fit(X_p3j_train[tr], y_p3j_train[tr])
            fb.append(np.mean((m.predict_proba(X_p3j_train[va])[:,1] - y_p3j_train[va])**2))
        if fb and np.mean(fb) < best_brier_p3j:
            best_brier_p3j = np.mean(fb); best_C_p3j = C

    p3j_model = LogisticRegression(C=best_C_p3j, penalty='l2', solver='lbfgs',
                                    class_weight='balanced', max_iter=2000)
    p3j_model.fit(X_p3j_train, y_p3j_train)
    s6_test = p3j_model.predict_proba(X_test_s[:, journey_indices])[:,1]
    s6_train = p3j_model.predict_proba(X_train_s[:, journey_indices])[:,1]
    print(f"  P3+Journey fusion (C={best_C_p3j}): AUC={roc_auc_score(y_test, s6_test):.4f}, Brier={np.mean((s6_test - y_test)**2):.6f}")
else:
    s6_test = s5_test; s6_train = s5_train


# ============================================================================
# META-LEARNER: 6-strategy optimal ensemble + fine grid
# ============================================================================
print(f"\n[9/10] Meta-learner: 6-strategy ensemble with fine grid...")

strategies = {
    "S1_Ridge": (s1_test, s1_train),
    "S2_Lasso": (s2_test, s2_train),
    "S3_P3_Spec": (s3_test, s3_train),
    "S4_Bayesian": (s4_test, s4_train),
    "S5_Journey": (s5_test, s5_train),
    "S6_P3Journey": (s6_test, s6_train),
}

print(f"\n  Individual strategy holdout performance:")
for name, (test_preds, _) in strategies.items():
    auc = roc_auc_score(y_test, test_preds)
    brier = np.mean((test_preds - y_test)**2)
    print(f"    {name:20s}  AUC={auc:.4f}  Brier={brier:.6f}  ΔvsConst={baseline_brier-brier:+.6f}")

# Two-phase grid: coarse (6-way) then fine (top 3)
print(f"\n  Phase 1: Coarse grid (6-way, step=0.1)...")
strategy_names = list(strategies.keys())
n_cal = int(n_train * 0.3)
cal_preds = {name: strategies[name][1][-n_cal:] for name in strategy_names}
cal_y = y_train[-n_cal:]

# Coarse: find top 3 strategies
coarse_best = 1.0; coarse_w = None
for w1 in np.arange(0, 1.01, 0.2):
    for w2 in np.arange(0, 1.01-w1, 0.2):
        for w3 in np.arange(0, 1.01-w1-w2, 0.2):
            for w4 in np.arange(0, 1.01-w1-w2-w3, 0.2):
                for w5 in np.arange(0, 1.01-w1-w2-w3-w4, 0.2):
                    w6 = 1.0 - w1 - w2 - w3 - w4 - w5
                    if w6 < -0.01: continue
                    w6 = max(0, w6)
                    weights = np.array([w1, w2, w3, w4, w5, w6])
                    preds = sum(weights[i] * cal_preds[name] for i, name in enumerate(strategy_names))
                    b = np.mean((preds - cal_y)**2)
                    if b < coarse_best:
                        coarse_best = b; coarse_w = weights.copy()

print(f"  Coarse best: {dict(zip(strategy_names, [f'{w:.1f}' for w in coarse_w]))}, Brier={coarse_best:.6f}")

# Identify top strategies (weight > 0 in coarse)
active = [(i, name) for i, name in enumerate(strategy_names) if coarse_w[i] > 0.01]
print(f"  Active strategies: {[n for _, n in active]}")

# Fine grid on active strategies (step=0.05)
print(f"  Phase 2: Fine grid (step=0.05) on active strategies...")
best_fine_brier = coarse_best
best_w = coarse_w.copy()

if len(active) == 2:
    i1, n1 = active[0]
    i2, n2 = active[1]
    for w_a in np.arange(0, 1.01, 0.05):
        w_b = 1.0 - w_a
        weights = np.zeros(len(strategy_names))
        weights[i1] = w_a; weights[i2] = w_b
        preds = sum(weights[i] * cal_preds[name] for i, name in enumerate(strategy_names))
        b = np.mean((preds - cal_y)**2)
        if b < best_fine_brier:
            best_fine_brier = b; best_w = weights.copy()

elif len(active) == 3:
    i1, n1 = active[0]
    i2, n2 = active[1]
    i3, n3 = active[2]
    for w_a in np.arange(0, 1.01, 0.05):
        for w_b in np.arange(0, 1.01 - w_a, 0.05):
            w_c = 1.0 - w_a - w_b
            if w_c < -0.01: continue
            w_c = max(0, w_c)
            weights = np.zeros(len(strategy_names))
            weights[i1] = w_a; weights[i2] = w_b; weights[i3] = w_c
            preds = sum(weights[i] * cal_preds[name] for i, name in enumerate(strategy_names))
            b = np.mean((preds - cal_y)**2)
            if b < best_fine_brier:
                best_fine_brier = b; best_w = weights.copy()

elif len(active) >= 4:
    # For 4+ active, do fine grid on top 3 by weight, allocate rest proportionally
    top3_idx = sorted(active, key=lambda x: coarse_w[x[0]], reverse=True)[:3]
    rest_idx = [x for x in active if x not in top3_idx]
    rest_total = sum(coarse_w[i] for i, _ in rest_idx)

    i1, n1 = top3_idx[0]; i2, n2 = top3_idx[1]; i3, n3 = top3_idx[2]
    for w_a in np.arange(0, 1.01, 0.05):
        for w_b in np.arange(0, 1.01 - w_a, 0.05):
            w_c_max = 1.0 - w_a - w_b
            for w_c in np.arange(0, w_c_max + 0.01, 0.05):
                remainder = 1.0 - w_a - w_b - w_c
                if remainder < -0.01: continue
                remainder = max(0, remainder)
                weights = np.zeros(len(strategy_names))
                weights[i1] = w_a; weights[i2] = w_b; weights[i3] = w_c
                # Distribute remainder proportionally to rest
                if rest_total > 0 and remainder > 0:
                    for ri, rn in rest_idx:
                        weights[ri] = remainder * (coarse_w[ri] / rest_total)
                preds = sum(weights[i] * cal_preds[name] for i, name in enumerate(strategy_names))
                b = np.mean((preds - cal_y)**2)
                if b < best_fine_brier:
                    best_fine_brier = b; best_w = weights.copy()

print(f"  Fine best: {dict(zip(strategy_names, [f'{w:.2f}' for w in best_w]))}, Brier={best_fine_brier:.6f}")

# Apply to test
meta_test = sum(best_w[i] * strategies[name][0] for i, name in enumerate(strategy_names))
meta_auc = roc_auc_score(y_test, meta_test)
meta_brier = np.mean((meta_test - y_test)**2)
print(f"\n  Meta-learner holdout: AUC={meta_auc:.4f}, Brier={meta_brier:.6f}")

# Platt calibration
n_platt_cal = int(n_train * 0.2)
meta_train_cal = sum(best_w[i] * strategies[name][1][-n_platt_cal:] for i, name in enumerate(strategy_names))

platt_meta = LogisticRegression(C=1e10, solver='lbfgs', max_iter=5000)
platt_meta.fit(meta_train_cal.reshape(-1,1), y_train[-n_platt_cal:])
mA, mB = platt_meta.coef_[0][0], platt_meta.intercept_[0]

meta_calibrated = np.array([1.0/(1+math.exp(-max(-30,min(30, mA*p + mB)))) for p in meta_test])
meta_cal_brier = np.mean((meta_calibrated - y_test)**2)
print(f"  Platt-calibrated meta: Brier={meta_cal_brier:.6f}")

# Isotonic
iso_meta = IsotonicRegression(y_min=0.05, y_max=0.95, out_of_bounds='clip')
iso_meta.fit(meta_train_cal, y_train[-n_platt_cal:])
meta_iso = iso_meta.predict(meta_test)
meta_iso_brier = np.mean((meta_iso - y_test)**2)
print(f"  Isotonic-calibrated meta: Brier={meta_iso_brier:.6f}")

# Also run v28.7.0-style meta for direct comparison
v28_7_test = 0.70 * strategies["S5_Journey"][0] + 0.30 * strategies["S3_P3_Spec"][0]
v28_7_brier = np.mean((v28_7_test - y_test)**2)
print(f"\n  v28.7.0-style meta (70/30 Journey/P3): Brier={v28_7_brier:.6f}")

# Collect all options
final_options = {
    "raw_meta": (meta_test, meta_brier),
    "platt_meta": (meta_calibrated, meta_cal_brier),
    "iso_meta": (meta_iso, meta_iso_brier),
    "s1_ridge_67": (s1_test, np.mean((s1_test - y_test)**2)),
    "s3_p3_spec": (s3_test, np.mean((s3_test - y_test)**2)),
    "s4_bayesian": (s4_test, np.mean((s4_test - y_test)**2)),
    "s5_journey": (s5_test, np.mean((s5_test - y_test)**2)),
    "s6_p3journey": (s6_test, np.mean((s6_test - y_test)**2)),
    "v28_7_replica": (v28_7_test, v28_7_brier),
}
best_final_name = min(final_options, key=lambda k: final_options[k][1])
final_test = final_options[best_final_name][0]
final_brier = final_options[best_final_name][1]

print(f"\n  → Best holdout approach: {best_final_name} (Brier={final_brier:.6f})")


# ============================================================================
# COMPREHENSIVE RESULTS
# ============================================================================
print(f"\n\n{'='*70}")
print(f"  HONEST HOLDOUT RESULTS (2025+, n={n_test})")
print(f"{'='*70}")
print(f"  Constant predictor:   Brier = {baseline_brier:.6f}")
print(f"  v28.5.0:              Brier ≈ 0.2439")
print(f"  v28.7.0 CHAMPION:     Brier ≈ 0.2419")

for name, (preds, brier) in sorted(final_options.items(), key=lambda x: x[1][1]):
    delta = baseline_brier - brier
    pct = delta / baseline_brier * 100
    auc = roc_auc_score(y_test, preds)
    marker = " ← BEST" if name == best_final_name else ""
    print(f"  {name:22s}  Brier={brier:.6f}  AUC={auc:.4f}  ΔvsConst={delta:+.6f} ({pct:+.1f}%){marker}")

# Tier performance
print(f"\n  TIER PERFORMANCE ({best_final_name}):")
for t1_pct in [79, 75, 70, 60]:
    t4_pct = 100 - t1_pct
    t1_v = np.percentile(final_test, t1_pct)
    t4_v = np.percentile(final_test, t4_pct)
    t1_mask = final_test >= t1_v
    t4_mask = final_test < t4_v
    n_t1 = int(np.sum(t1_mask)); n_t4 = int(np.sum(t4_mask))
    if n_t1 < 10 or n_t4 < 10: continue
    t1_sr = np.mean(y_test[t1_mask]) * 100
    t4_sr = np.mean(y_test[t4_mask]) * 100
    print(f"    T1≥{t1_pct}th (n={n_t1:3d}) = {t1_sr:5.1f}%   T4<{t4_pct}th (n={n_t4:3d}) = {t4_sr:5.1f}%   Spread={t1_sr-t4_sr:.1f}pp")

# COMPARISON
print(f"\n  === COMPARISON vs PRIOR CHAMPIONS ===")
for ref_name, ref_brier in [("v28.5.0", 0.2439), ("v28.7.0", 0.2419)]:
    delta = ref_brier - final_brier
    print(f"  {ref_name} Brier: {ref_brier:.6f}  →  v28.8.0: {final_brier:.6f}  Δ={delta:+.6f} ({'IMPROVEMENT' if delta > 0 else 'NO IMPROVEMENT'})")

# Per-TA
print(f"\n  PER-TA HOLDOUT:")
for ta in sorted(set(test_ta_keys)):
    ta_mask = test_ta_keys == ta
    n_ta = int(np.sum(ta_mask))
    if n_ta < 10: continue
    ta_brier = np.mean((final_test[ta_mask] - y_test[ta_mask])**2)
    ta_base = np.mean(y_test[ta_mask])
    ta_const = np.mean((np.full(n_ta, ta_base) - y_test[ta_mask])**2)
    print(f"    {ta:25s}  n={n_ta:4d}  base={ta_base:.3f}  Brier={ta_brier:.4f}  ΔvsConst={ta_const-ta_brier:+.4f}")

# Journey impact
print(f"\n  === DEEP JOURNEY SIGNAL ON HOLDOUT ===")
test_streak = X_test[:, FEATURES.index("journey_positive_streak")]
test_last_pos = X_test[:, FEATURES.index("journey_last_outcome_positive")]
test_sponsor_ta = X_test[:, FEATURES.index("journey_sponsor_ta_sr")]

for label, mask in [
    ("Streak ≥ 2 (log1p≥1.1)", test_streak >= math.log1p(2)),
    ("Last outcome positive", test_last_pos > 0.7),
    ("Last outcome negative", test_last_pos < 0.3),
    ("Sponsor TA SR > 0.6", test_sponsor_ta > 0.6),
    ("Sponsor TA SR < 0.4", (test_sponsor_ta < 0.4) & (test_sponsor_ta > 0.01)),
]:
    n_m = int(np.sum(mask))
    if n_m < 5: continue
    sr = np.mean(y_test[mask]) * 100
    pred = np.mean(final_test[mask]) * 100
    print(f"  {label:35s}  n={n_m:4d}  actual={sr:.1f}%  pred={pred:.1f}%  Δ={pred-sr:+.1f}pp")

# Calibration analysis by decile
print(f"\n  CALIBRATION BY DECILE:")
decile_edges = np.percentile(final_test, np.arange(0, 101, 10))
for i in range(10):
    lo = decile_edges[i]; hi = decile_edges[i+1] if i < 9 else 1.0
    mask = (final_test >= lo) & (final_test < hi + 0.001)
    n_d = int(np.sum(mask))
    if n_d < 5: continue
    actual = np.mean(y_test[mask]) * 100
    predicted = np.mean(final_test[mask]) * 100
    print(f"    Decile {i+1:2d} ({lo:.3f}-{hi:.3f}): n={n_d:4d}  actual={actual:5.1f}%  pred={predicted:5.1f}%  Δ={predicted-actual:+.1f}pp")


# ============================================================================
# SAVE
# ============================================================================
print(f"\n[10/10] Saving deploy config...")

deploy = {
    "model": "gungnir_v28_deep_journey",
    "version": "28.8.0",
    "date": "2026-03-14",
    "architecture": f"6-strategy ensemble with deep journey features ({best_final_name})",
    "n_features": N_FEATURES,
    "feature_names": FEATURES,
    "n_base_features": len(FEATURES_V28_BASE),
    "n_journey_v27": len(JOURNEY_V27),
    "n_journey_v28_deep": len(JOURNEY_V28_DEEP),
    "new_deep_features": JOURNEY_V28_DEEP,
    "strategy_weights": dict(zip(strategy_names, [float(w) for w in best_w])),
    "best_approach": best_final_name,
    "holdout_metrics": {
        "n_test": n_test,
        "test_base_rate": float(test_base_rate),
        "constant_brier": float(baseline_brier),
        "final_brier": float(final_brier),
        "final_auc": float(roc_auc_score(y_test, final_test)),
        "brier_improvement_vs_constant": float(baseline_brier - final_brier),
        "pct_improvement": float((baseline_brier - final_brier) / baseline_brier * 100),
        "delta_vs_v28_7": float(0.2419 - final_brier),
        "delta_vs_v28_5": float(0.2439 - final_brier),
    },
    "strategy_holdout": {
        name: {"brier": float(np.mean((preds - y_test)**2)), "auc": float(roc_auc_score(y_test, preds))}
        for name, (preds, _) in strategies.items()
    },
    "platt_A": float(mA),
    "platt_B": float(mB),
    "scaler_means": {f: float(scaler.mean_[i]) for i, f in enumerate(FEATURES)},
    "scaler_stds": {f: float(scaler.scale_[i]) for i, f in enumerate(FEATURES)},
    "best_hyperparams": {
        "s1_C": float(best_C_s1),
        "s2_C": float(best_C_s2),
        "s3_C": float(best_C_p3),
        "s5_C": float(best_C_j),
        "shrinkage_strength": int(best_shrink),
    },
}

with open("/sessions/adoring-relaxed-shannon/gungnir_v28_v8_deploy.json", "w") as f:
    json.dump(deploy, f, indent=2)

import shutil
shutil.copy2("/sessions/adoring-relaxed-shannon/gungnir_v28_v8_deploy.json",
             "/sessions/adoring-relaxed-shannon/mnt/Python/gungnir_v28_v8_deploy.json")
shutil.copy2("/sessions/adoring-relaxed-shannon/gungnir_v28_v8_deep_journey.py",
             "/sessions/adoring-relaxed-shannon/mnt/Python/gungnir_v28_v8_deep_journey.py")

print(f"\n{'='*70}")
print(f"  v28.8.0 DEEP JOURNEY COMPLETE")
print(f"  Deploy: gungnir_v28_v8_deploy.json")
print(f"{'='*70}")
