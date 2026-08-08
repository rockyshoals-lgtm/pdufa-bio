#!/usr/bin/env python3
"""
CATALYST SCORER v43.0.0 + IIS v1.0 — Full Enriched Scoring Pipeline
====================================================================
Scores 2026 catalysts through the complete Gungnir v43 enriched pipeline:
  - 144 features (v33 base + v37-v43 interaction chains)
  - CT.gov features (from catalyst_ctgov_cache.json)
  - ChEMBL v2 drug classifications (drug_classifications.json + chembl_enrichment_cache_v2.json)
  - Sponsor temporal indexes (from 1,752-event training data)
  - Indication density (from training data)
  - Journey features (defaults for future catalysts)
  - Momentum features (defaults — no live price data)
  - v37 stage granularity (Phase 1b, 2a, 2b, bridging)
  - v39 CT.gov expanded features (ct_ep_is_safety, ct_ep_is_biomarker, etc.)
  - v40 conference signal + days_to_cover
  - v41 interactions (sponsor_x_conference, journey_last_pos_sq, etc.)
  - v42 pairwise interactions (interim×momentum, n_arms×oncology, etc.)
  - v43 ChEMBL biotech scientist features (oligo×phase2, cell×randomized, etc.)

Ridge M1 scoring only (XGB model truncated — 5/600 trees unusable).
85% Ridge weight per v43 meta config.

Author: Claude Opus 4.6 / 9 Realms
Date: April 2026
"""

import os
import sys
import json
import csv
import math
import re
from collections import defaultdict, Counter

import numpy as np

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_JSON = os.path.join(DATA_DIR, "gungnir_v43_deploy.json")
CTGOV_CACHE = os.path.join(DATA_DIR, "catalyst_ctgov_cache.json")
READOUT_CSV = os.path.join(DATA_DIR, "gungnir_readout_analysis.csv")
CHEMBL_CACHE = os.path.join(DATA_DIR, "chembl_enrichment_cache_v2.json")
INN_CLASS_PATH = os.path.join(DATA_DIR, "drug_classifications.json")
XLSX_PATH = os.path.join(DATA_DIR, "fda_catalysts_2026-03-29.xlsx")
OUTPUT_JSON = os.path.join(DATA_DIR, "catalyst_scores_v43.json")

# Phase×size readout edge data (from Gungnir training)
PHASE_SIZE_EDGE = {
    (1, "nano"): (35, 30, 18), (1, "micro"): (25, 22, 15), (1, "small"): (15, 15, 12),
    (1, "mid"): (8, 10, 8), (1, "large"): (4, 5, 5),
    (2, "nano"): (30, 28, 20), (2, "micro"): (22, 20, 16), (2, "small"): (13, 14, 13),
    (2, "mid"): (7, 9, 9), (2, "large"): (3, 4, 6),
    (3, "nano"): (25, 25, 22), (3, "micro"): (18, 18, 18), (3, "small"): (10, 12, 15),
    (3, "mid"): (5, 7, 10), (3, "large"): (2, 3, 7),
    (4, "nano"): (12, 15, 10), (4, "micro"): (8, 10, 8), (4, "small"): (5, 7, 6),
    (4, "mid"): (3, 4, 4), (4, "large"): (1, 2, 3),
}

# Brand name → INN mapping for ChEMBL lookup
BRAND_MAP = {
    "KEYTRUDA": "PEMBROLIZUMAB", "OPDIVO": "NIVOLUMAB", "TECENTRIQ": "ATEZOLIZUMAB",
    "IMFINZI": "DURVALUMAB", "BAVENCIO": "AVELUMAB", "LIBTAYO": "CEMIPLIMAB",
    "YERVOY": "IPILIMUMAB", "HERCEPTIN": "TRASTUZUMAB", "AVASTIN": "BEVACIZUMAB",
    "RITUXAN": "RITUXIMAB", "HUMIRA": "ADALIMUMAB", "REMICADE": "INFLIXIMAB",
    "STELARA": "USTEKINUMAB", "DUPIXENT": "DUPILUMAB", "SKYRIZI": "RISANKIZUMAB",
    "RINVOQ": "UPADACITINIB", "OZEMPIC": "SEMAGLUTIDE", "MOUNJARO": "TIRZEPATIDE",
    "SPINRAZA": "NUSINERSEN", "ZOLGENSMA": "ONASEMNOGENE",
}


# =============================================================================
# GUNGNIR v43 ENGINE (Ridge M1 only — XGB truncated)
# =============================================================================

class GungnirV43:
    def __init__(self):
        with open(DEPLOY_JSON) as f:
            deploy = json.load(f)
        self.version = deploy["version"]
        self.feature_names = deploy["feature_names"]
        self.n_features = deploy["n_features"]
        self.config = deploy.get("config", {})

        # Coefficients (dict keyed by feature name)
        self.m1_coef = deploy["M1_coef"]
        self.m1_intercept = deploy["M1_intercept"]
        self.m2_coef = deploy.get("M2_coef", {})
        self.m2_intercept = deploy.get("M2_intercept", 0)
        self.m3_coef = deploy.get("M3_coef", {})
        self.m3_intercept = deploy.get("M3_intercept", 0)

        # Scaler (dict keyed by feature name)
        self.scaler_means = deploy["scaler_means"]
        self.scaler_scales = deploy["scaler_scales"]

    def _scale(self, features_dict):
        """Scale features using stored means/scales."""
        scaled = {}
        for name in self.feature_names:
            val = features_dict.get(name, 0.0)
            mean = self.scaler_means.get(name, 0.0)
            scale = self.scaler_scales.get(name, 1.0)
            scaled[name] = (val - mean) / scale if scale > 1e-10 else 0.0
        return scaled

    def _sigmoid(self, z):
        z = max(-500, min(500, z))
        return 1.0 / (1.0 + math.exp(-z))

    def _logit(self, coef_dict, intercept, scaled):
        z = intercept
        for name in self.feature_names:
            z += coef_dict.get(name, 0.0) * scaled.get(name, 0.0)
        return z

    def score(self, features_dict):
        """Score a single event. Returns dict with probability, tier, p_good_plus, p_crash."""
        scaled = self._scale(features_dict)

        # M1: Binary probability
        z1 = self._logit(self.m1_coef, self.m1_intercept, scaled)
        p_binary = self._sigmoid(z1)

        # M2: GOOD+ probability
        z2 = self._logit(self.m2_coef, self.m2_intercept, scaled)
        p_good = self._sigmoid(z2)

        # M3: CRASH probability
        z3 = self._logit(self.m3_coef, self.m3_intercept, scaled)
        p_crash = self._sigmoid(z3)

        # Temperature scaling (T=1.0 for v43, so no change)
        T = self.config.get("temperature", 1.0)
        if T != 1.0:
            p_binary = self._sigmoid(z1 / T)

        # Tier assignment
        if p_binary >= 0.70:
            tier, label = "T1", "Strong Positive"
        elif p_binary >= 0.55:
            tier, label = "T2", "Lean Positive"
        elif p_binary >= 0.40:
            tier, label = "T3", "Uncertain"
        else:
            tier, label = "T4", "Lean Negative"

        return {
            "probability": round(p_binary, 4),
            "tier": tier,
            "tier_label": label,
            "p_good_plus": round(p_good, 4),
            "p_crash": round(p_crash, 4),
            "ridge_z": round(z1, 4),
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_phase(stage_str):
    """Extract phase number and PDUFA flag from stage string."""
    s = stage_str.lower()
    is_pdufa = "pdufa" in s or "nda" in s or "bla" in s or "sNDA" in s.upper() or "505" in s
    if is_pdufa:
        return 4, True
    if "phase 3" in s or "phase3" in s or "pivotal" in s:
        return 3, False
    if "phase 2b" in s:
        return 2, False
    if "phase 2a" in s:
        return 2, False
    if "phase 2" in s or "phase2" in s or "phase ii" in s:
        return 2, False
    if "phase 1b" in s or "phase1b" in s:
        return 1, False
    if "phase 1" in s or "phase1" in s or "phase i" in s:
        return 1, False
    return 2, False


def parse_stage_granular(stage_str):
    """Parse granular stage for v37+ features."""
    s = stage_str.lower()
    result = {
        "is_phase1": 0, "is_phase1b": 0, "is_phase2": 0,
        "is_phase2a": 0, "is_phase2b": 0, "is_phase3": 0,
        "is_pivotal": 0, "is_bridging": 0,
    }
    if "pdufa" in s or "nda" in s or "bla" in s or "505" in s:
        # PDUFA — not a phase readout
        return result
    if "pivotal" in s:
        result["is_pivotal"] = 1
        result["is_phase3"] = 1
        return result
    if "1/2" in s or "1b/2" in s or "2/3" in s:
        result["is_bridging"] = 1
    if "phase 3" in s or "phase3" in s or "p3" in s:
        result["is_phase3"] = 1
    elif "phase 2b" in s or "phase2b" in s:
        result["is_phase2b"] = 1
        result["is_phase2"] = 1
    elif "phase 2a" in s or "phase2a" in s:
        result["is_phase2a"] = 1
        result["is_phase2"] = 1
    elif "phase 2" in s or "phase2" in s or "phase ii" in s:
        result["is_phase2"] = 1
    elif "phase 1b" in s or "phase1b" in s:
        result["is_phase1b"] = 1
        result["is_phase1"] = 1
    elif "phase 1" in s or "phase1" in s or "phase i" in s:
        result["is_phase1"] = 1
    return result


TA_KEYWORDS = {
    "oncology": ["cancer", "tumor", "carcinoma", "lymphoma", "leukemia", "myeloma",
                  "melanoma", "sarcoma", "glioblastoma", "glioma", "mesothelioma",
                  "oncology", "neoplasm", "malignant"],
    "cns": ["alzheimer", "parkinson", "epilepsy", "seizure", "depression",
            "schizophrenia", "anxiety", "migraine", "neuropath", "als",
            "huntington", "multiple sclerosis", "ms ", "cns", "brain", "neural",
            "psychiatric", "psychedelic", "ptsd", "bipolar", "adhd", "dementia"],
    "rare_disease": ["orphan", "rare", "duchenne", "sma", "cystic fibrosis",
                      "huntington", "fabry", "gaucher", "pompe", "niemann",
                      "friedreich", "tay-sachs", "phenylketonuria"],
    "immunology": ["autoimmune", "lupus", "rheumatoid", "psoriasis", "crohn",
                    "colitis", "dermatitis", "eczema", "alopecia areata",
                    "ankylosing", "immunology"],
    "cardiovascular": ["cardiovascular", "heart failure", "atrial", "hypertension",
                        "coronary", "cardiac", "thrombosis", "stroke", "aneurysm"],
    "infectious": ["hiv", "hepatitis", "covid", "influenza", "bacterial",
                    "infection", "antibiotic", "antiviral", "fungal", "rsv"],
    "metabolic": ["diabetes", "obesity", "metabolic", "nafld", "nash",
                   "hypercholesterol", "dyslipidemia", "gout"],
    "hematology": ["anemia", "hemophilia", "sickle cell", "thalassemia",
                    "myelofibrosis", "myelodysplastic", "thrombocytopenia",
                    "hematolog"],
    "ophthalmology": ["macular", "retinal", "glaucoma", "optic", "uveitis",
                       "dry eye", "geographic atrophy", "eye", "ocular", "ophthalm"],
}


def classify_ta(text):
    t = text.lower()
    for ta, keywords in TA_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return ta
    return "other"


TA_BASE_RATES = {
    "oncology": 0.65, "cns": 0.52, "rare_disease": 0.68, "immunology": 0.60,
    "cardiovascular": 0.58, "infectious": 0.62, "metabolic": 0.60,
    "hematology": 0.63, "ophthalmology": 0.55, "other": 0.57,
}


def size_tier(price):
    if not price:
        return "small"
    if price < 2:
        return "nano"
    if price < 10:
        return "micro"
    if price < 50:
        return "small"
    if price < 200:
        return "mid"
    return "large"


def size_tier_from_mcap(mcap):
    """More accurate size tier from market cap (in raw dollars)."""
    if not mcap:
        return None
    mcap_m = mcap / 1e6  # Convert to millions
    if mcap_m < 50:
        return "nano"
    if mcap_m < 300:
        return "micro"
    if mcap_m < 2000:
        return "small"
    if mcap_m < 10000:
        return "mid"
    return "large"


# =============================================================================
# ChEMBL DRUG CLASSIFICATION (from v43 kaizen)
# =============================================================================

def parse_primary_drug(raw):
    """Extract primary drug name from catalyst event."""
    if not raw:
        return None
    s = str(raw)
    s = re.sub(r'\s*-\s*\([A-Z][A-Z0-9\-/\s]*\)\s*$', '', s)
    s = re.sub(r'\s*-\s*\([A-Z][A-Z0-9\-/\s]*$', '', s)
    parts = re.split(r'\s+(?:and|plus|\+|in combination with)\s+', s, flags=re.IGNORECASE)
    p = parts[0].strip()
    m = re.search(r'\(([a-z][a-z\-\s]+)\)', p)
    if m:
        p = m.group(1)
    else:
        m2 = re.match(r'^[A-Z]{3,}(?:\s+[A-Z]{3,})*\s+\(([^)]+)\)', p)
        if m2:
            p = m2.group(1)
    p = re.sub(r'\s*\([^)]*\)', '', p)
    return p.strip(' -').upper()


def clean_for_lookup(name):
    if not name:
        return name
    if name in BRAND_MAP:
        return BRAND_MAP[name]
    return re.sub(r'-[A-Z]{2,5}$', '', name).strip()


def classify_drug_modality(drug_raw, chembl_cache, inn_class):
    """Classify drug modality using ChEMBL + INN stem + heuristics."""
    drug = parse_primary_drug(drug_raw)
    lookup = clean_for_lookup(drug)
    dl = (drug or '').lower()

    # Try ChEMBL cache first
    info = None
    for key in [drug, lookup]:
        if key and key in chembl_cache:
            info = chembl_cache[key]
            break

    mod = 'unknown'
    mech = 'unknown'

    if info:
        mt = (info.get('molecule_type') or '').lower()
        if 'antibody' in mt and 'conjugate' in mt:
            mod = 'adc'
        elif 'antibody' in mt:
            mod = 'mab'
        elif 'protein' in mt:
            mod = 'protein'
        elif 'oligonucleotide' in mt:
            mod = 'oligo'
        elif 'cell' in mt:
            mod = 'cell'
        elif 'gene' in mt:
            mod = 'gene'
        elif 'small molecule' in mt or 'small_molecule' in mt:
            mod = 'sm'
        elif 'vaccine' in mt:
            mod = 'vaccine'

        mt2 = info.get('mechanism_type')
        if mt2:
            mech = mt2.lower()
        elif info.get('mechanisms'):
            a = (info['mechanisms'][0].get('action') or '').lower()
            if a:
                mech = a

    # Try INN classification
    if mod == 'unknown':
        for key in [drug, lookup]:
            if key and key in inn_class:
                m2 = inn_class[key].get('modality', 'unknown')
                if m2 != 'unknown':
                    if 'antibody' in m2:
                        mod = 'mab'
                    elif m2 == 'small_molecule':
                        mod = 'sm'
                    elif 'cell' in m2:
                        mod = 'cell'
                    elif 'gene' in m2:
                        mod = 'gene'
                    elif 'oligo' in m2:
                        mod = 'oligo'
                    elif 'peptide' in m2 or 'fusion' in m2:
                        mod = 'peptide'
                    elif 'adc' in m2 or 'conjugate' in m2:
                        mod = 'adc'
                    break

    # INN suffix heuristics
    if mod == 'unknown' and dl:
        if dl.endswith('mab'):
            mod = 'mab'
        elif any(x in dl for x in ['vedotin', 'tansine', 'deruxtecan', 'govitecan', 'mafodotin']):
            mod = 'adc'
        elif dl.endswith('cel') or 'car-t' in dl:
            mod = 'cell'
        elif dl.endswith('vec') or 'aav' in dl:
            mod = 'gene'
        elif dl.endswith('nib') or dl.endswith('tinib'):
            mod = 'sm'
        elif dl.endswith('sen') or 'sirna' in dl:
            mod = 'oligo'
        elif dl.endswith('cept'):
            mod = 'peptide'
        elif dl.endswith('tide'):
            mod = 'peptide'

    if mech == 'unknown' and dl:
        if any(dl.endswith(s) for s in ['nib', 'tinib']) or 'parib' in dl or 'lisib' in dl or 'zomib' in dl:
            mech = 'inhibitor'
        elif dl.endswith('mab'):
            mech = 'antibody_binding'

    # Build binary features
    ch2 = {
        'ch2_is_sm': int(mod == 'sm'),
        'ch2_is_mab': int(mod == 'mab'),
        'ch2_is_adc': int(mod == 'adc'),
        'ch2_is_biologic': int(mod in ('mab', 'adc', 'protein')),
        'ch2_is_cell': int(mod == 'cell'),
        'ch2_is_gene': int(mod == 'gene'),
        'ch2_is_oligo': int(mod == 'oligo'),
        'ch2_is_advanced': int(mod in ('cell', 'gene', 'oligo')),
        'ch2_is_peptide': int(mod in ('peptide',)),
        'ch2_moa_inhibitor': int(mech == 'inhibitor'),
        'ch2_moa_agonist': int(mech == 'agonist'),
        'ch2_moa_antagonist': int(mech in ('antagonist', 'antagonist_antibody')),
        'ch2_is_combo': int(bool(re.search(r'\band\b|\bplus\b|\+|combination|combo', drug_raw or '', re.IGNORECASE))),
    }
    ch2['_matched'] = mod != 'unknown'
    return ch2


# =============================================================================
# NLP FEATURES (T-1 safe)
# =============================================================================

NLP_PATTERNS = {
    "nlp_biomarker": [r"(?i)biomarker", r"(?i)surrogate\s+endpoint"],
    "nlp_combo_therapy": [r"(?i)combin", r"(?i)\+\s*\w+", r"(?i)plus\s+\w+"],
    "nlp_dose_response": [r"(?i)dose.?response", r"(?i)dose.?dependent", r"(?i)dose.?escalation"],
    "nlp_first_in": [r"(?i)first.?in.?(?:class|human|patient)"],
    "nlp_interim": [r"(?i)\binterim\b", r"(?i)\bpreliminary\b"],
    "nlp_phase3": [r"(?i)phase\s*3", r"(?i)phase\s*III", r"(?i)pivotal"],
    "nlp_topline": [r"(?i)topline", r"(?i)top.?line"],
}


def extract_nlp_features(text):
    features = {}
    for feat, patterns in NLP_PATTERNS.items():
        features[feat] = 0
        for p in patterns:
            if re.search(p, text or ""):
                features[feat] = 1
                break
    return features


# =============================================================================
# IIS (INTERIM INFLATION SCORE) OVERLAY
# =============================================================================

IIS_INTERIM_PATTERNS = [
    r"(?i)\binterim\b",
    r"(?i)\bpreliminary\b(?!.*(?:full|final|topline))",
    r"(?i)\binitial\s+(?:data|results|analysis)",
    r"(?i)\bearly\s+(?:data|results|signal|look)",
    r"(?i)\bupdated?\s+(?:data|results|analysis)\b",
    r"(?i)\bpartial\s+(?:data|results)",
    r"(?i)\bfutility\b",
    r"(?i)\bDSMB\b",
]

IIS_COMBINED_DOSE_PATTERNS = [
    r"(?i)\bcombined\s+(?:dose|arm)",
    r"(?i)\bpooled\s+(?:analysis|data|dose|arm)",
    r"(?i)\ball\s+(?:treated|dose|arm).*(?:vs|versus)\s+(?:placebo|control)",
]


def compute_iis_overlay(event, ctgov_data=None):
    cat_text = (event.get("catalyst_text", "") or "").lower()
    stage = (event.get("stage", "") or "").lower()
    next_cat = (event.get("next_catalyst", "") or "").lower()
    full_text = cat_text + " " + stage + " " + next_cat

    is_interim = 0
    interim_evidence = []
    for p in IIS_INTERIM_PATTERNS:
        m = re.search(p, full_text)
        if m:
            is_interim = 1
            interim_evidence.append(m.group())

    is_combined_dose = 0
    for p in IIS_COMBINED_DOSE_PATTERNS:
        if re.search(p, full_text):
            is_combined_dose = 1

    n_per_arm = 60
    if ctgov_data and "error" not in ctgov_data:
        enrollment = ctgov_data.get("enrollment") or 0
        n_arms = ctgov_data.get("n_arms") or 2
        if enrollment > 0 and n_arms > 0:
            n_per_arm = round(enrollment / n_arms)

    iis_score = 0
    iis_flags = []

    if is_interim:
        iis_score += 10
        iis_flags.append("INTERIM_DATA")
        if n_per_arm < 12:
            iis_score += 20
            iis_flags.append("TINY_N_LT_12")
        elif n_per_arm < 20:
            iis_score += 12
            iis_flags.append("TINY_N_LT_20")
        if is_combined_dose:
            iis_score += 15
            iis_flags.append("COMBINED_DOSE")
    elif n_per_arm < 20:
        iis_score += 8
        iis_flags.append("SMALL_TRIAL")

    if iis_score >= 46:
        iis_tier, pos_mod = "IIS_HIGH", 0.0
    elif iis_score >= 21:
        iis_tier, pos_mod = "IIS_MODERATE", 0.5
    elif iis_score > 0:
        iis_tier, pos_mod = "IIS_LOW", 0.8
    else:
        iis_tier, pos_mod = "IIS_CLEAR", 1.0

    return {
        "iis_score": iis_score, "iis_tier": iis_tier, "iis_flags": iis_flags,
        "iis_is_interim": is_interim, "iis_n_per_arm": n_per_arm,
        "iis_combined_dose": is_combined_dose, "iis_position_modifier": pos_mod,
        "iis_interim_evidence": "; ".join(interim_evidence) if interim_evidence else "",
    }


# =============================================================================
# FEATURE ENGINEERING — Full v43 (144 features)
# =============================================================================

def engineer_v43_features(event, ctgov_data=None, ch2_features=None):
    """Engineer all 144 v43 features for a single catalyst event."""
    features = {}

    phase = event.get("phase") or 2
    ta = event.get("ta", "other")
    stier = event.get("size_tier", "small")
    price = event.get("price")
    mcap = event.get("market_cap")

    # --- STAGE GRANULARITY (v37) ---
    stage_str = event.get("stage", "") or ""
    stage_g = parse_stage_granular(stage_str)
    for k, v in stage_g.items():
        features[k] = v

    # If no granular stage was set, set the main phase
    if not any(stage_g.get(k, 0) for k in ["is_phase1", "is_phase1b", "is_phase2",
                                             "is_phase2a", "is_phase2b", "is_phase3"]):
        if phase == 1:
            features["is_phase1"] = 1
        elif phase == 2:
            features["is_phase2"] = 1
        elif phase == 3:
            features["is_phase3"] = 1

    features["phase_numeric"] = min(phase, 3)

    # --- SIZE ---
    features["is_micro"] = 1 if stier == "micro" else 0
    features["is_small"] = 1 if stier == "small" else 0
    features["is_mid"] = 1 if stier == "mid" else 0
    features["is_large"] = 1 if stier == "large" else 0
    features["log_price"] = math.log(max(price, 0.01)) if price else math.log(10)
    features["log_market_cap"] = math.log(max(mcap, 1)) if mcap else math.log(500)

    # --- TA ---
    features["ta_oncology"] = 1 if ta == "oncology" else 0
    features["ta_cns"] = 1 if ta == "cns" else 0
    features["ta_rare_disease"] = 1 if ta == "rare_disease" else 0
    features["ta_immunology"] = 1 if ta == "immunology" else 0
    features["ta_cardiovascular"] = 1 if ta == "cardiovascular" else 0
    features["ta_infectious"] = 1 if ta == "infectious" else 0
    features["ta_metabolic"] = 1 if ta == "metabolic" else 0
    features["ta_hematology"] = 1 if ta == "hematology" else 0
    features["ta_ophthalmology"] = 1 if ta == "ophthalmology" else 0
    features["ta_other"] = 1 if ta == "other" else 0
    features["ta_base_rate"] = TA_BASE_RATES.get(ta, 0.57)

    # --- DESIGNATIONS ---
    drug_text = (event.get("drug", "") or "").lower() + " " + (event.get("catalyst_text", "") or "").lower()
    features["has_btd"] = 1 if "breakthrough" in drug_text else 0
    features["has_fast_track"] = 1 if "fast track" in drug_text else 0
    features["has_orphan"] = 1 if "orphan" in drug_text else 0
    features["has_priority_review"] = 1 if "priority" in drug_text else 0
    features["designation_count"] = sum([features["has_btd"], features["has_fast_track"],
                                          features["has_orphan"], features["has_priority_review"]])

    # --- NLP ---
    full_text = (event.get("catalyst_text", "") or "") + " " + (event.get("next_catalyst", "") or "")
    nlp = extract_nlp_features(full_text + " " + stage_str)
    for k, v in nlp.items():
        features[k] = v

    # --- CATALYST TYPE ---
    next_cat = (event.get("next_catalyst", "") or "").lower()
    features["cat_topline"] = 1 if "topline" in next_cat or "top-line" in next_cat else 0
    features["cat_interim"] = 1 if "interim" in next_cat else 0
    features["cat_initial"] = 1 if "initial" in next_cat else 0
    features["cat_conference"] = 1 if any(c in next_cat for c in ["asco", "ash", "aacr", "esmo", "aha", "aan"]) else 0
    features["cat_regulatory"] = 1 if "regulatory" in next_cat or "decision" in next_cat else 0
    features["cat_full_results"] = 1 if "full" in next_cat else 0
    features["cat_submission"] = 1 if "submission" in next_cat or "filing" in next_cat else 0

    # --- HISTORICAL LOA/POP ---
    features["hist_loa"] = (event.get("hist_loa") or 0) / 100.0
    features["hist_pop"] = (event.get("hist_pop") or 0) / 100.0

    # --- IIS ---
    features["iis_is_interim"] = event.get("_iis_is_interim", 0)

    # --- CT.GOV (v33 base + v38/v39 expanded) ---
    ctgov = ctgov_data or {}
    if "error" in ctgov:
        ctgov = {}

    if ctgov:
        enroll = ctgov.get("enrollment")
        features["ctgov_enrollment"] = math.log(max(enroll, 1)) if enroll else math.log(100)
        features["ctgov_n_arms"] = ctgov.get("n_arms", 2)
        features["ctgov_is_randomized"] = ctgov.get("is_randomized", 0)
        features["ctgov_is_double_blind"] = ctgov.get("is_double_blind", 0)
        features["ctgov_is_placebo"] = ctgov.get("is_placebo", 0)
        features["ctgov_masking_rigor"] = ctgov.get("masking_rigor", 0)
        features["ctgov_has_dmc"] = ctgov.get("has_dmc", 0)
        features["ctgov_ep_hard"] = ctgov.get("ep_hard", 0)
        features["ctgov_ep_surrogate"] = ctgov.get("ep_surrogate", 0)
        features["ctgov_n_sites"] = min(ctgov.get("n_sites", 0), 500)
        features["ctgov_n_countries"] = min(ctgov.get("n_countries", 0), 50)
        features["ctgov_is_global"] = ctgov.get("is_global", 0)
        features["ctgov_has_withdrawals"] = ctgov.get("has_withdrawals", 0)
        features["ctgov_real"] = 1

        # v38 features
        features["ct_is_industry"] = 1 if ctgov.get("sponsor_class", "").upper() == "INDUSTRY" else 0
        elig_len = ctgov.get("elig_text_length", 0)
        if not elig_len:
            # Estimate from primary_endpoint_text length as proxy
            ep_text = ctgov.get("primary_endpoint_text", "")
            elig_len = len(ep_text) * 3 if ep_text else 500
        features["ct_log_elig_length"] = math.log1p(max(0, elig_len))

        # v39 expanded CT.gov features
        features["ct_ep_is_safety"] = ctgov.get("ep_safety", ctgov.get("ep_is_safety", 0))
        features["ct_ep_is_pfs"] = 1 if "pfs" in (ctgov.get("primary_endpoint_text", "") or "").lower() or \
                                         "progression" in (ctgov.get("primary_endpoint_text", "") or "").lower() else 0
        features["ct_ep_is_biomarker"] = 1 if any(kw in (ctgov.get("primary_endpoint_text", "") or "").lower()
                                                    for kw in ["biomarker", "ctdna", "psa", "hba1c", "a1c",
                                                               "antibod", "titer", "viral load"]) else 0
        features["ct_has_combination"] = ctgov.get("has_combination",
                                                     1 if (ctgov.get("n_interventions", 1) or 1) > 1 else 0)
        features["ct_active_comp_x_phase3"] = ctgov.get("has_active_comparator", 0) * features.get("is_phase3", 0)

    else:
        # Phase-average imputation
        PHASE_AVG = {
            1: {"enrollment": 146, "n_sites": 13, "n_countries": 2.7, "pct_randomized": 0.63,
                "pct_double_blind": 0.35, "pct_placebo": 0.30, "pct_dmc": 0.55,
                "pct_ep_hard": 0.25, "pct_ep_surrogate": 0.60, "pct_global": 0.20},
            2: {"enrollment": 247, "n_sites": 45, "n_countries": 6.0, "pct_randomized": 0.83,
                "pct_double_blind": 0.55, "pct_placebo": 0.50, "pct_dmc": 0.70,
                "pct_ep_hard": 0.35, "pct_ep_surrogate": 0.50, "pct_global": 0.45},
            3: {"enrollment": 1287, "n_sites": 147, "n_countries": 14.6, "pct_randomized": 0.91,
                "pct_double_blind": 0.72, "pct_placebo": 0.68, "pct_dmc": 0.82,
                "pct_ep_hard": 0.50, "pct_ep_surrogate": 0.35, "pct_global": 0.70},
        }
        pa = PHASE_AVG.get(phase, PHASE_AVG[2])
        features["ctgov_enrollment"] = math.log(max(pa["enrollment"], 1))
        features["ctgov_n_arms"] = 2 if phase >= 2 else 1
        features["ctgov_is_randomized"] = round(pa["pct_randomized"])
        features["ctgov_is_double_blind"] = round(pa["pct_double_blind"])
        features["ctgov_is_placebo"] = round(pa["pct_placebo"])
        features["ctgov_masking_rigor"] = 2 if features["ctgov_is_double_blind"] else 0
        features["ctgov_has_dmc"] = round(pa["pct_dmc"])
        features["ctgov_ep_hard"] = round(pa["pct_ep_hard"])
        features["ctgov_ep_surrogate"] = round(pa["pct_ep_surrogate"])
        features["ctgov_n_sites"] = min(pa["n_sites"], 500)
        features["ctgov_n_countries"] = min(pa["n_countries"], 50)
        features["ctgov_is_global"] = 1 if pa["n_countries"] >= 5 else 0
        features["ctgov_has_withdrawals"] = 0
        features["ctgov_real"] = 0
        features["ct_is_industry"] = 1  # most catalysts are industry-sponsored
        features["ct_log_elig_length"] = math.log1p(500)
        features["ct_ep_is_safety"] = 0
        features["ct_ep_is_pfs"] = 0
        features["ct_ep_is_biomarker"] = 0
        features["ct_has_combination"] = 0
        features["ct_active_comp_x_phase3"] = 0

    # --- JOURNEY (defaults for future catalysts) ---
    features["journey_n_prior"] = 0
    features["journey_success_rate"] = 0.5
    features["journey_had_prior_positive"] = 0
    features["journey_had_prior_negative"] = 0
    features["journey_positive_streak"] = 0
    features["journey_last_positive"] = 0.5
    features["journey_had_positive"] = 0
    features["journey_had_negative"] = 0
    features["journey_n_positive"] = 0
    features["journey_n_negative"] = 0

    # --- SPONSOR & INDICATION (from temporal indexes) ---
    features["sponsor_success_rate"] = event.get("_sponsor_sr", 0.5)
    features["indication_density"] = math.log1p(event.get("_indication_count", 0))

    # --- MOMENTUM (defaults — no live price data) ---
    features["momentum_5d"] = 0
    features["momentum_10d"] = 0
    features["momentum_20d"] = 0
    features["volatility_5d"] = 0
    features["volatility_20d"] = 0

    # --- COMPETITIVE LANDSCAPE ---
    comp = event.get("_competitive", {})
    features["competitive_6mo"] = min(comp.get("n_6mo", 0), 20)
    features["competitive_3mo"] = min(comp.get("n_3mo", 0), 10)

    # --- v37 FEATURES ---
    enroll_raw = features["ctgov_enrollment"]
    features["enrollment_sq"] = enroll_raw ** 2
    features["indication_density_sq"] = features["indication_density"] ** 2

    # --- v39 ChEMBL mechanism features ---
    ch2 = ch2_features or {}
    features["ch_is_enzyme"] = 0  # From training — not same as ch2 modality
    features["ch_is_agonist"] = 0
    features["ch_is_ion_channel"] = 0
    # Try to derive from ch2 MOA
    if ch2:
        features["ch_is_agonist"] = ch2.get("ch2_moa_agonist", 0)
        # enzyme and ion_channel would need ChEMBL target_class, approximate from mech
        if ch2.get("ch2_moa_inhibitor", 0):
            features["ch_is_enzyme"] = 1  # Many inhibitors target enzymes

    # --- v39 expanded features ---
    features["orphan_x_micro"] = features["has_orphan"] * features["is_micro"]
    ind_density_raw = event.get("_indication_count", 0)
    features["ind_maturity_high"] = 1 if ind_density_raw > 10 else 0

    # --- v33 BASE INTERACTIONS ---
    features["phase3_x_randomized"] = features.get("is_phase3", 0) * features["ctgov_is_randomized"]
    features["phase3_x_double_blind"] = features.get("is_phase3", 0) * features["ctgov_is_double_blind"]
    features["phase3_x_placebo"] = features.get("is_phase3", 0) * features["ctgov_is_placebo"]
    features["phase3_x_cns"] = features.get("is_phase3", 0) * features["ta_cns"]
    features["phase3_x_oncology"] = features.get("is_phase3", 0) * features["ta_oncology"]
    features["onc_x_single_arm"] = features["ta_oncology"] * (1 if features["ctgov_n_arms"] <= 1 else 0)
    features["rare_x_small"] = features["ta_rare_disease"] * (features["is_micro"] + features["is_small"])
    features["btd_x_phase3"] = features["has_btd"] * features.get("is_phase3", 0)
    features["micro_x_phase3"] = features["is_micro"] * features.get("is_phase3", 0)
    features["small_x_phase3"] = features["is_small"] * features.get("is_phase3", 0)
    features["large_x_any"] = features["is_large"]
    features["desig_x_small"] = features["designation_count"] * (features["is_micro"] + features["is_small"])
    features["ep_hard_x_phase3"] = features["ctgov_ep_hard"] * features.get("is_phase3", 0)
    features["dmc_x_phase3"] = features["ctgov_has_dmc"] * features.get("is_phase3", 0)
    features["cns_x_micro"] = features["ta_cns"] * features["is_micro"]
    features["journey_pos_x_phase3"] = features["journey_had_prior_positive"] * features.get("is_phase3", 0)
    features["journey_sr_x_phase3"] = features["journey_success_rate"] * features.get("is_phase3", 0)
    features["journey_streak_x_small"] = features["journey_positive_streak"] * (features["is_micro"] + features["is_small"])
    features["enrollment_x_phase3"] = features["ctgov_enrollment"] * features.get("is_phase3", 0)
    features["global_x_phase3"] = features["ctgov_is_global"] * features.get("is_phase3", 0)
    features["combo_x_onc"] = features.get("nlp_combo_therapy", 0) * features["ta_oncology"]
    features["micro_x_rare"] = features["is_micro"] * features["ta_rare_disease"]

    # v33 momentum/competitive interactions
    features["momentum_x_phase3"] = features["momentum_5d"] * features.get("is_phase3", 0)
    features["momentum_x_micro"] = features["momentum_5d"] * features["is_micro"]
    features["volatility_x_phase3"] = features["volatility_5d"] * features.get("is_phase3", 0)
    features["competitive_x_onc"] = features["competitive_6mo"] * features["ta_oncology"]

    # --- ERA ---
    features["era_2024_plus"] = 1

    # --- v40 FEATURES (conference + SI) ---
    conf_text = (event.get("conference", "") or "").lower() + " " + next_cat
    has_conference = 1 if any(c in conf_text for c in ["asco", "ash", "aacr", "esmo", "aha", "aan",
                                                         "sitc", "sno", "eha", "ehrs", "wclc",
                                                         "sabcs", "san antonio"]) else 0
    features["v40_has_conference"] = has_conference
    features["v40_days_to_cover"] = 0  # No SI data for future catalysts
    features["v40_conf_x_small"] = has_conference * (features["is_micro"] + features["is_small"])

    # --- v41 INTERACTIONS ---
    features["v41_sponsor_x_conference"] = features["sponsor_success_rate"] * features["v40_has_conference"]
    features["v41_journey_last_pos_sq"] = features["journey_last_positive"] ** 2
    features["v41_immuno_x_phase2"] = features["ta_immunology"] * features.get("is_phase2", 0)
    features["v41_placebo_x_cns"] = features["ctgov_is_placebo"] * features["ta_cns"]
    features["v41_enrollment_x_journey"] = features["ctgov_enrollment"] * features["journey_success_rate"]

    # --- v42 PAIRWISE INTERACTIONS ---
    features["v42_iis_is_interim_X_momentum_10d"] = features["iis_is_interim"] * features["momentum_10d"]
    features["v42_ctgov_n_arms_X_phase3_x_oncology"] = features["ctgov_n_arms"] * features["phase3_x_oncology"]
    features["v42_ctgov_n_countries_X_indication_density"] = features["ctgov_n_countries"] * features["indication_density"]
    features["v42_global_x_phase3_X_volatility_20d"] = features["global_x_phase3"] * features["volatility_20d"]
    features["v42_ct_is_industry_X_ctgov_masking_rigor"] = features["ct_is_industry"] * features["ctgov_masking_rigor"]
    features["v42_iis_is_interim_X_indication_density_sq"] = features["iis_is_interim"] * features["indication_density_sq"]
    features["v42_momentum_20d_X_ta_metabolic"] = features["momentum_20d"] * features["ta_metabolic"]
    features["v42_is_small_X_ta_cns"] = features["is_small"] * features["ta_cns"]

    # --- v43 ChEMBL BIOTECH SCIENTIST FEATURES ---
    if ch2:
        features["v43_ch2_is_oligo_X_volatility_20d"] = ch2.get("ch2_is_oligo", 0) * features["volatility_20d"]
        features["v43_ch2_is_biologic_X_is_phase3"] = ch2.get("ch2_is_biologic", 0) * features.get("is_phase3", 0)
        features["v43_ch2_is_cell_X_ctgov_is_randomized"] = ch2.get("ch2_is_cell", 0) * features["ctgov_is_randomized"]
        features["v43_ch2_is_adc_X_enrollment_sq"] = ch2.get("ch2_is_adc", 0) * features["enrollment_sq"]
        features["v43_ch2_is_cell_X_momentum_10d"] = ch2.get("ch2_is_cell", 0) * features["momentum_10d"]
        features["v43_ch2_is_oligo_X_is_phase2"] = ch2.get("ch2_is_oligo", 0) * features.get("is_phase2", 0)
    else:
        for f in ["v43_ch2_is_oligo_X_volatility_20d", "v43_ch2_is_biologic_X_is_phase3",
                   "v43_ch2_is_cell_X_ctgov_is_randomized", "v43_ch2_is_adc_X_enrollment_sq",
                   "v43_ch2_is_cell_X_momentum_10d", "v43_ch2_is_oligo_X_is_phase2"]:
            features[f] = 0

    return features


# =============================================================================
# INVESTMENT SCORING
# =============================================================================

def compute_investment_score(gungnir_result, event):
    prob = gungnir_result["probability"]
    p_good = gungnir_result["p_good_plus"]
    p_crash = gungnir_result["p_crash"]
    phase = event.get("phase") or 2
    stier = event.get("size_tier", "mid")
    ta = event.get("ta", "other")
    is_pdufa = event.get("is_pdufa", False)

    size_edge = PHASE_SIZE_EDGE.get((min(phase, 3), stier), (0, 5, 10))
    avg_ret_if_positive = size_edge[0]
    good_plus_rate = size_edge[1]
    crash_rate = size_edge[2]

    neg_avg = {1: -3, 2: -19, 3: -14, 4: -5}.get(phase, -10)
    ev = prob * avg_ret_if_positive + (1 - prob) * neg_avg

    raw_score = (
        prob * 30 +
        max(ev, 0) / 30 * 25 +
        good_plus_rate / 25 * 15 +
        (1 - crash_rate / 50) * 15 +
        p_good * 100 * 10 / 100 +
        (1 - p_crash) * 5
    )
    investment_score = max(0, min(100, raw_score))

    if investment_score >= 75:
        inv_tier, inv_action = "ALPHA", "Strong Long"
    elif investment_score >= 55:
        inv_tier, inv_action = "BETA", "Cautious Long"
    elif investment_score >= 40:
        inv_tier, inv_action = "GAMMA", "Watch / Small Position"
    elif investment_score >= 25:
        inv_tier, inv_action = "DELTA", "Avoid / Very Small"
    else:
        inv_tier, inv_action = "OMEGA", "No Trade"

    if inv_tier == "ALPHA":
        position = "3-5%" if stier in ["small", "micro"] else "2-3%"
    elif inv_tier == "BETA":
        position = "2-3%" if stier in ["small", "micro"] else "1-2%"
    elif inv_tier == "GAMMA":
        position = "1%" if stier in ["small", "micro"] else "0.5%"
    else:
        position = "0%"

    flags = []
    if stier in ["micro", "small"] and phase >= 3 and prob >= 0.6:
        flags.append("MONSTER_POTENTIAL")
    if ta == "rare_disease" and prob >= 0.55:
        flags.append("RARE_DISEASE_EDGE")
    if ta == "cns" and phase >= 3:
        flags.append("CNS_HIGH_VARIANCE")
    if stier == "large":
        flags.append("LARGE_CAP_MUTED")
    if p_crash >= 0.15:
        flags.append("HIGH_CRASH_RISK")
    if is_pdufa:
        flags.append("PDUFA_EVENT")
    if p_good >= 0.15:
        flags.append("HIGH_UPSIDE_POTENTIAL")

    return {
        "investment_score": round(investment_score, 1),
        "investment_tier": inv_tier,
        "investment_action": inv_action,
        "expected_value": round(ev, 2),
        "avg_ret_if_positive": round(avg_ret_if_positive, 1),
        "good_plus_rate": round(good_plus_rate, 1),
        "crash_rate": round(crash_rate, 1),
        "position_size": position,
        "flags": flags,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 80)
    print("CATALYST SCORER v43.0.0 + IIS v1.0 — Full Enriched Pipeline")
    print("=" * 80)

    # Load Gungnir v43
    gungnir = GungnirV43()
    print(f"\n[ENGINE] Gungnir {gungnir.version} loaded ({gungnir.n_features} features, Ridge M1 only)")
    print(f"  Config: Ridge C={gungnir.config.get('ridge_c')}, meta={gungnir.config.get('meta_ridge')}/"
          f"{gungnir.config.get('meta_xgb')} Ridge/XGB")

    # Load ChEMBL caches
    chembl_cache = {}
    if os.path.exists(CHEMBL_CACHE):
        with open(CHEMBL_CACHE) as f:
            chembl_cache = json.load(f)
    inn_class = {}
    if os.path.exists(INN_CLASS_PATH):
        with open(INN_CLASS_PATH) as f:
            inn_class = json.load(f)
    print(f"[CHEMBL] {len(chembl_cache)} ChEMBL entries, {len(inn_class)} INN classifications")

    # Build sponsor track record + indication density from training data
    print("[HISTORY] Building sponsor/indication indexes from training data...")
    sponsor_final = {}
    indication_counts = defaultdict(int)
    with open(READOUT_CSV) as f:
        for r in csv.DictReader(f):
            ticker = r.get("ticker", "").strip()
            outcome = r.get("outcome", "")
            indication = r.get("indication", "").lower()[:40]
            if ticker:
                if ticker not in sponsor_final:
                    sponsor_final[ticker] = {"n_pos": 0, "n_neg": 0}
                if outcome == "positive":
                    sponsor_final[ticker]["n_pos"] += 1
                elif outcome == "negative":
                    sponsor_final[ticker]["n_neg"] += 1
            if indication:
                indication_counts[indication] += 1

    sponsor_sr = {}
    for ticker, d in sponsor_final.items():
        total = d["n_pos"] + d["n_neg"]
        sponsor_sr[ticker] = d["n_pos"] / total if total > 0 else 0.5
    print(f"  Sponsors: {len(sponsor_sr)} | Indications: {len(indication_counts)}")

    # Build competitive landscape from training data
    print("[COMPETITIVE] Building competitive landscape from training data...")
    from datetime import datetime, timedelta
    indication_timeline = defaultdict(list)
    with open(READOUT_CSV) as f:
        for r in csv.DictReader(f):
            ind = r.get("indication", "").lower()[:40]
            date = r.get("date", "")
            if ind and date:
                indication_timeline[ind].append(date)

    # Load Excel
    import openpyxl
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    data_rows = rows[1:]
    print(f"[LOAD] {len(data_rows)} catalysts from Excel")

    # Parse events
    events = []
    for r in data_rows:
        ticker = str(r[0] or "").strip()
        if not ticker:
            continue
        try:
            price = float(r[2]) if r[2] else None
        except (ValueError, TypeError):
            price = None
        try:
            mcap = float(r[14]) if r[14] else None
        except (ValueError, TypeError, IndexError):
            mcap = None

        phase, is_pdufa = parse_phase(str(r[6] or ""))
        ta = classify_ta(str(r[5] or "") + " " + str(r[3] or ""))

        # Use mcap-based size tier if available, else price-based
        stier = size_tier_from_mcap(mcap) if mcap else size_tier(price)

        events.append({
            "ticker": ticker,
            "name": str(r[1] or ""),
            "price": price,
            "drug": str(r[3] or ""),
            "nct_id": str(r[4] or "").strip(),
            "indication": str(r[5] or ""),
            "stage": str(r[6] or ""),
            "status": str(r[7] or ""),
            "next_catalyst": str(r[8] or ""),
            "catalyst_date": str(r[9] or ""),
            "catalyst_text": str(r[10] or ""),
            "conference": str(r[11] or "") if len(r) > 11 else "",
            "hist_loa": (float(r[12]) if r[12] else None) if len(r) > 12 else None,
            "hist_pop": (float(r[13]) if r[13] else None) if len(r) > 13 else None,
            "market_cap": mcap,
            "phase": phase,
            "is_pdufa": is_pdufa,
            "ta": ta,
            "size_tier": stier,
        })

    print(f"[PARSE] {len(events)} events")

    # Load CT.gov cache
    ctgov_cache = {}
    if os.path.exists(CTGOV_CACHE):
        with open(CTGOV_CACHE) as f:
            ctgov_cache = json.load(f)
    print(f"[CTGOV] {len(ctgov_cache)} cached entries")

    # Attach enrichment to events
    for event in events:
        event["_sponsor_sr"] = sponsor_sr.get(event["ticker"], 0.5)
        ind = event.get("indication", "").lower()[:40]
        event["_indication_count"] = indication_counts.get(ind, 0)

        # Competitive landscape
        cat_date = event.get("catalyst_date", "")
        if cat_date and ind:
            # Count events in same indication within 6mo and 3mo windows
            try:
                if "." in cat_date:
                    dt = datetime.strptime(cat_date[:10], "%Y-%m-%d")
                else:
                    dt = datetime.strptime(cat_date[:10], "%Y-%m-%d")
                d6 = (dt - timedelta(days=180)).strftime("%Y-%m-%d")
                d3 = (dt - timedelta(days=90)).strftime("%Y-%m-%d")
                dates_in_ind = indication_timeline.get(ind, [])
                event["_competitive"] = {
                    "n_6mo": sum(1 for d in dates_in_ind if d6 <= d < cat_date),
                    "n_3mo": sum(1 for d in dates_in_ind if d3 <= d < cat_date),
                }
            except (ValueError, TypeError):
                event["_competitive"] = {"n_6mo": 0, "n_3mo": 0}
        else:
            event["_competitive"] = {"n_6mo": 0, "n_3mo": 0}

    sr_matched = sum(1 for e in events if e["_sponsor_sr"] != 0.5)
    ind_matched = sum(1 for e in events if e["_indication_count"] > 0)
    comp_matched = sum(1 for e in events if e.get("_competitive", {}).get("n_6mo", 0) > 0)
    print(f"  Sponsor SR matched: {sr_matched}/{len(events)} | Indication: {ind_matched}/{len(events)} | Competitive: {comp_matched}/{len(events)}")

    # Classify drugs
    print("[CHEMBL] Classifying drug modalities...")
    ch2_matched = 0
    for event in events:
        ch2 = classify_drug_modality(event.get("drug", ""), chembl_cache, inn_class)
        event["_ch2"] = ch2
        if ch2.get("_matched"):
            ch2_matched += 1
    print(f"  Drug modality matched: {ch2_matched}/{len(events)} ({ch2_matched/max(len(events),1)*100:.1f}%)")

    # Pre-compute IIS for iis_is_interim feature
    for event in events:
        ctgov_data = ctgov_cache.get(event["nct_id"], {})
        iis = compute_iis_overlay(event, ctgov_data)
        event["_iis_is_interim"] = iis["iis_is_interim"]

    # Score all events
    print(f"\n[SCORE] Scoring {len(events)} catalysts with Gungnir v43 enriched pipeline...")
    scored = []
    ctgov_matched = 0
    for event in events:
        ctgov_data = ctgov_cache.get(event["nct_id"], {})
        if ctgov_data and "error" not in ctgov_data:
            ctgov_matched += 1

        features = engineer_v43_features(event, ctgov_data, event.get("_ch2"))

        # Verify all 144 features are present
        missing = [f for f in gungnir.feature_names if f not in features]
        if missing:
            for f in missing:
                features[f] = 0  # Default missing features to 0

        gungnir_result = gungnir.score(features)
        inv_result = compute_investment_score(gungnir_result, event)

        # IIS overlay
        iis_result = compute_iis_overlay(event, ctgov_data)
        if iis_result["iis_flags"]:
            if iis_result["iis_position_modifier"] < 1.0:
                inv_result["flags"].extend(iis_result["iis_flags"])
                if iis_result["iis_position_modifier"] == 0.0:
                    inv_result["position_size"] = "0% (IIS BLOCK)"
                elif iis_result["iis_position_modifier"] == 0.5:
                    inv_result["flags"].append("IIS_HALF_SIZE")
                elif iis_result["iis_position_modifier"] == 0.8:
                    inv_result["flags"].append("IIS_REDUCED")

        scored.append({
            "ticker": event["ticker"],
            "name": event["name"],
            "drug": event["drug"],
            "indication": event["indication"],
            "stage": event["stage"],
            "status": event["status"],
            "next_catalyst": event["next_catalyst"],
            "catalyst_date": event["catalyst_date"],
            "conference": event.get("conference", ""),
            "price": event["price"],
            "market_cap": event["market_cap"],
            "size_tier": event["size_tier"],
            "phase": event["phase"],
            "is_pdufa": event["is_pdufa"],
            "ta": event["ta"],
            "hist_loa": event["hist_loa"],
            "hist_pop": event["hist_pop"],
            "has_ctgov": bool(ctgov_data and "error" not in ctgov_data),
            "drug_modality": "matched" if event.get("_ch2", {}).get("_matched") else "unknown",
            "gungnir_probability": gungnir_result["probability"],
            "gungnir_tier": gungnir_result["tier"],
            "gungnir_tier_label": gungnir_result["tier_label"],
            "p_good_plus": gungnir_result["p_good_plus"],
            "p_crash": gungnir_result["p_crash"],
            "ridge_z": gungnir_result["ridge_z"],
            "sponsor_sr": round(event.get("_sponsor_sr", 0.5), 3),
            "indication_density": round(features.get("indication_density", 0), 3),
            "competitive_6mo": features.get("competitive_6mo", 0),
            "iis_score": iis_result["iis_score"],
            "iis_tier": iis_result["iis_tier"],
            "iis_flags": iis_result["iis_flags"],
            "iis_is_interim": iis_result["iis_is_interim"],
            "iis_n_per_arm": iis_result["iis_n_per_arm"],
            **inv_result,
        })

    print(f"  CT.gov matched: {ctgov_matched}/{len(events)}")

    scored.sort(key=lambda x: -x["investment_score"])

    # Write output
    with open(OUTPUT_JSON, "w") as f:
        json.dump(scored, f, indent=2, default=str)

    # Summary
    print(f"\n{'='*80}")
    print("v43.0.0 ENRICHED INVESTMENT TIER SUMMARY")
    print(f"{'='*80}")
    for t in ["ALPHA", "BETA", "GAMMA", "DELTA", "OMEGA"]:
        subset = [s for s in scored if s["investment_tier"] == t]
        cnt = len(subset)
        if cnt == 0:
            continue
        avg_score = sum(s["investment_score"] for s in subset) / cnt
        avg_ev = sum(s["expected_value"] for s in subset) / cnt
        avg_prob = sum(s["gungnir_probability"] for s in subset) / cnt
        print(f"  {t:6s}: {cnt:4d} catalysts  avg_score={avg_score:.1f}  avg_prob={avg_prob:.0%}  avg_EV={avg_ev:+.1f}%")

    print(f"\n  Top 20 Picks:")
    for s in scored[:20]:
        flags = " ".join(f"[{f}]" for f in s.get("flags", []))
        print(f"    {s['investment_score']:5.1f}  {s['investment_tier']:5s}  {s['ticker']:6s}  "
              f"${s['price'] or 0:>8.2f}  P{s['phase'] or '?'}  {s['ta']:12s}  "
              f"Prob={s['gungnir_probability']:.0%}  Good={s['p_good_plus']:.0%}  Crash={s['p_crash']:.0%}  "
              f"EV={s['expected_value']:+.1f}%  SR={s['sponsor_sr']:.2f}  "
              f"{s['drug'][:25]}  {flags}")

    # IIS Summary
    iis_interim = [s for s in scored if s.get("iis_is_interim")]
    iis_flagged = sum(1 for s in scored if s.get("iis_flags"))
    print(f"\n{'='*80}")
    print("IIS OVERLAY SUMMARY")
    print(f"{'='*80}")
    print(f"  Interim readouts: {len(iis_interim)} | Total IIS-flagged: {iis_flagged}")

    # CT.gov coverage
    ctgov_pct = ctgov_matched / max(len(events), 1) * 100
    print(f"\n  CT.gov coverage: {ctgov_matched}/{len(events)} ({ctgov_pct:.1f}%)")
    print(f"  Drug modality coverage: {ch2_matched}/{len(events)} ({ch2_matched/max(len(events),1)*100:.1f}%)")
    print(f"  Sponsor SR coverage: {sr_matched}/{len(events)} ({sr_matched/max(len(events),1)*100:.1f}%)")

    # Portfolio check
    portfolio = ["GRCE", "WHWK", "CRDF", "CABA", "ALXO"]
    port_scores = [s for s in scored if s["ticker"] in portfolio]
    if port_scores:
        print(f"\n{'='*80}")
        print("CURRENT PORTFOLIO")
        print(f"{'='*80}")
        for s in sorted(port_scores, key=lambda x: -x["investment_score"]):
            flags = " ".join(f"[{f}]" for f in s.get("flags", []))
            print(f"    {s['investment_score']:5.1f}  {s['investment_tier']:5s}  {s['ticker']:6s}  "
                  f"Prob={s['gungnir_probability']:.0%}  Good={s['p_good_plus']:.0%}  Crash={s['p_crash']:.0%}  "
                  f"EV={s['expected_value']:+.1f}%  SR={s['sponsor_sr']:.2f}  "
                  f"{s['drug'][:30]}  {flags}")

    print(f"\n[OUTPUT] {len(scored)} scored → {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    os.chdir(DATA_DIR)
    sys.exit(main())
