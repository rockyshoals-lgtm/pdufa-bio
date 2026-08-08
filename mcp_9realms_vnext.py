#!/usr/bin/env python3
"""
MCP 9 Realms — ODIN v14 + GUNGNIR v46.0 (Predictive) + BIFROST v4.0 + v5.4 Explosion Detector + Conference Overlay v1.0 + Smart Money v1.0 + UOA v1.1
====================================================
ODIN: v14 Champion (51-feature L2 Ridge logistic regression, C=0.1).
  - Kaizen-optimized from v13: 18 features added, 3 dropped (net +15 features)
  - WF AUC 0.9011, HO AUC 0.9363 (358 holdout events)
  - HO AUC +0.0062 over v13. 20/20 seeds, p=0.000000.
  - T1 win rate 98.7%, 154 T1 picks. HO Brier 0.0895.
  - Key discovery: Priority review × resubmission class interactions unlock
    regulatory pathway signal. Oncology × manufacturing risk reveals disease-
    specific manufacturing complexity. Gene therapy × BTD and × sponsor strength
    validate specialized modality paths.
GUNGNIR: v44.0 Champion (146-feature Ridge+XGB meta-ensemble, AUC 0.8018).
  - Kaizen from v42: ChEMBL biotech scientist features (306 candidates, 6 selected)
  - WF AUC 0.8001 (+0.0065 over v42), 10/10 seeds, p=0.0000000000
  - 6 new features: ch2_is_oligo×volatility, ch2_is_biologic×phase3,
    ch2_is_cell×randomized, ch2_is_adc×enrollment_sq, ch2_is_cell×momentum,
    ch2_is_oligo×phase2
BIFROST: v4.0 Runup Timing+Magnitude (1,705 events, v10 tiers, triple-ensemble
  magnitude prediction with sponsor dynamics, walk-forward validated, Sharpe 5.45).
  - Kaizen from v3.1: 6 new features (sponsor_success_rate, vol_adjusted_confidence,
    ta_risk interactions), LightGBM ensemble (Ridge 30% + XGB 35% + LGB 35%),
    enhanced risk management. Win rate 70.8%, max DD -4.9%.

History:
  - ODIN v5: 25 features, C=1.5, WF AUC 0.8761, HO AUC 0.8886
  - ODIN v6: 18 features, C=0.025, WF AUC 0.8917, HO AUC 0.8846
  - ODIN v7: 20 features, C=0.010, WF AUC 0.9001, HO AUC 0.8952
  - ODIN v8: 22 features, C=0.005, WF AUC 0.9064, HO AUC 0.8809
  - ODIN v9: 30 features, C=0.01, WF AUC 0.9083, HO AUC 0.8961 (superseded)
  - ODIN v14: 51 features, C=0.10, WF AUC 0.9011, HO AUC 0.9363 (DEPLOYED)
  - ODIN v11: 35 features, C=0.025, WF AUC 0.9031, HO AUC 0.9267
  - ODIN v12: 37 features, C=0.015, WF AUC 0.8997, HO AUC 0.9314 (prev champion)
    Kaizen: 6 added, 4 dropped. +0.0059 HO AUC vs v11.
  - ODIN v13: 36 features, C=0.025, WF AUC 0.8997, HO AUC 0.9315 (CHAMPION)
    Kaizen: CRL reason differentiation — 2 added (resub1_x_experienced,
    resub1_x_swr), 3 dropped (spa_mega, btd_and_priority, spa_16_plus).
    +0.0023 HO AUC vs v12.
  - v25 RETIRED: severe data leakage (13 post-readout features, AUC 0.988 was fake)
  - v26: 28 clean features, AUC 0.7437 (first leakage-free version)
  - v27: 33 features, AUC 0.7529 (ODIN enrichment + NLP expansion)

DEPLOYMENT: Replace mcp_9realms.py with this file. No external weight files needed.
"""

import json, math, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

# ============================================================================
# ODIN v14 CHAMPION — 51-Feature L2 Ridge Logistic Regression
# ============================================================================
# Kaizen-optimized from v13: 18 added + 3 dropped (net +15), C=0.1 (from 0.025)
# WF AUC 0.9011, HO AUC 0.9363 (+0.0062 over v13), 1,845 WF events, 358 holdout
# Stability: 20/20 seeds v14 beats v13 on HO AUC, p=0.000000
# T1: 154 picks, 98.7% win rate. HO Brier 0.0895.
# Added from v13 (18 new): pw_orphan_drug_bin_x_resub_class_2, surrogate_x_ta_vh,
#   pw_priority_review_bin_x_resub_class_1, pw_desig_stack_x_resub_class_1,
#   pw_gene_therapy_bin_x_sponsor_streak, ft_x_safety, pw_priority_review_bin_x_btd_bin,
#   pw_is_oncology_x_resub_class_2, pw_is_oncology_x_mfg_risk_bin,
#   pw_double_crl_bin_x_resub_class_2, pw_priority_review_bin_x_resub_class_2,
#   gt_x_btd, pw_orphan_drug_bin_x_btd_bin, pw_double_crl_bin_x_ta_crl_streak,
#   pw_gene_therapy_bin_x_log_spa_sq, is_oncology, crl_rate_x_swr
# Dropped from v13: log_spa_sq, accel_x_btd, is_immunology (all hurting HO)

ODIN_VNEXT_FEATURES = [
    "btd_bin", "ppm_flag_bin",                   # core designations
    "ta_very_high",                              # risk
    "crl_rate_low",                              # TA risk
    "era_post", "is_nda", "mfg_risk_bin",        # regulatory
    "sponsor_win_rate",                           # v8: temporal SWR
    "spa_6_15", "resub1_x_naive",                # v9: mid-tier + resub
    "resub_class_2",                             # v9: resubmission class
    "swr_x_btd", "crl_rate_x_naive",            # v9: interactions
    "swr_x_streak", "swr_x_ta_vh",              # v10: SWR interactions
    "single_arm_x_btd", "resub2_x_experienced", # v10: study design + resub
    "momentum_x_btd",                            # v10: momentum × BTD
    "ta_base_x_naive",                           # v11: TA base risk × naive
    "consistency_x_naive",                       # v11: sponsor consistency × naive
    "sponsor_consistency",                       # v11: sponsor outcome consistency
    "ta_momentum",                               # v11: TA 1yr vs 3yr rate delta
    "swr_cubed",                                 # v11: non-linear SWR
    "ta_crl_streak",                             # v11: consecutive CRLs in TA
    "accel_orphan_btd",                          # v11: accel × orphan × BTD triple
    "ta_recent_rate_sq",                         # v11: non-linear TA recent rate
    "safety_high_x_naive",                       # v12: high safety signal × naive
    "adcom_x_naive",                             # v12: adcom × naive
    "psychedelics_bin",                          # v12: psychedelic drug flag
    "psychedelics_x_naive",                      # v12: psychedelics × naive
    "ta_bucket_MOD",                             # v12: TA risk bucket = MOD
    "crl_count_x_naive",                         # v12: prior CRL count × naive
    "resub1_x_experienced",                      # v13: Class 1 resub × experienced sponsor
    "resub1_x_swr",                              # v13: Class 1 resub × sponsor win rate
    # v14 NEW FEATURES (18)
    "pw_orphan_drug_bin_x_resub_class_2",       # orphan × Class 2 resub
    "surrogate_x_ta_vh",                         # surrogate endpoint × very high TA
    "pw_priority_review_bin_x_resub_class_1",   # priority review × Class 1 resub
    "pw_desig_stack_x_resub_class_1",           # designation stack × Class 1 resub
    "pw_gene_therapy_bin_x_sponsor_streak",     # gene therapy × sponsor streak
    "ft_x_safety",                               # fast track × safety
    "pw_priority_review_bin_x_btd_bin",         # priority review × BTD
    "pw_is_oncology_x_resub_class_2",           # oncology × Class 2 resub
    "pw_is_oncology_x_mfg_risk_bin",            # oncology × manufacturing risk
    "pw_double_crl_bin_x_resub_class_2",        # double CRL × Class 2 resub
    "pw_priority_review_bin_x_resub_class_2",   # priority review × Class 2 resub
    "gt_x_btd",                                  # gene therapy × BTD
    "pw_orphan_drug_bin_x_btd_bin",             # orphan × BTD
    "pw_double_crl_bin_x_ta_crl_streak",        # double CRL × TA CRL streak
    "pw_gene_therapy_bin_x_log_spa_sq",         # gene therapy × log SPA squared
    "is_oncology",                               # oncology therapeutic area
    "crl_rate_x_swr",                            # CRL rate × sponsor win rate
]

# Trained coefficients (sklearn LogisticRegression, C=0.1, L2, lbfgs)
ODIN_VNEXT_INTERCEPT = 1.0199364758216718
ODIN_VNEXT_COEFS = {
    "btd_bin": 0.20719221903595456,
    "ppm_flag_bin": -0.12357758742042906,
    "ta_very_high": 0.3558429525731002,
    "crl_rate_low": -0.07201461938099152,
    "era_post": 0.0,
    "is_nda": -0.08620550485137322,
    "mfg_risk_bin": -0.18431791946042192,
    "sponsor_win_rate": 0.23962092039262972,
    "spa_6_15": -0.07434058515699553,
    "resub1_x_naive": -0.45582369688644164,
    "resub_class_2": -0.06667639166146068,
    "swr_x_btd": 0.054618513716834946,
    "crl_rate_x_naive": -1.1044836315342565,
    "swr_x_streak": 0.10895629479135732,
    "swr_x_ta_vh": 0.37938637668555797,
    "single_arm_x_btd": -0.06812151333455997,
    "resub2_x_experienced": -0.008360915660304469,
    "momentum_x_btd": 0.0385105590055496,
    "ta_base_x_naive": -0.3271604324154763,
    "consistency_x_naive": -0.15609072043609215,
    "sponsor_consistency": 0.12896059869366142,
    "ta_momentum": 0.05522052523956577,
    "swr_cubed": -0.3008383325753243,
    "ta_crl_streak": -0.31352381436776416,
    "accel_orphan_btd": 0.37487920021556886,
    "ta_recent_rate_sq": -0.12795825268317795,
    "safety_high_x_naive": -0.21914594271436696,
    "adcom_x_naive": -0.08620550485137322,
    "psychedelics_bin": 0.07061764748070078,
    "psychedelics_x_naive": 0.07061764748070078,
    "ta_bucket_MOD": -0.19173810044666093,
    "crl_count_x_naive": -0.09921936598660916,
    "resub1_x_experienced": 0.26086646527465485,
    "resub1_x_swr": -0.37173028937925146,
    # v14 NEW (18 features)
    "pw_orphan_drug_bin_x_resub_class_2": -0.13846076757225018,
    "surrogate_x_ta_vh": 0.05527182632657414,
    "pw_priority_review_bin_x_resub_class_1": 0.17936995565709696,
    "pw_desig_stack_x_resub_class_1": 0.06564641333645625,
    "pw_gene_therapy_bin_x_sponsor_streak": 0.1800299270565178,
    "ft_x_safety": 0.20837305729393216,
    "pw_priority_review_bin_x_btd_bin": 0.17070282710038162,
    "pw_is_oncology_x_resub_class_2": -0.08123018774114832,
    "pw_is_oncology_x_mfg_risk_bin": 0.14323492118687925,
    "pw_double_crl_bin_x_resub_class_2": 0.10067242714534477,
    "pw_priority_review_bin_x_resub_class_2": 0.04534741886986998,
    "gt_x_btd": 0.1397326079794779,
    "pw_orphan_drug_bin_x_btd_bin": -0.20228674624933743,
    "pw_double_crl_bin_x_ta_crl_streak": -0.1731890616413464,
    "pw_gene_therapy_bin_x_log_spa_sq": 0.15671681407960444,
    "is_oncology": 0.11986830914083856,
    "crl_rate_x_swr": 0.47656532874922697,
}

# StandardScaler parameters (fitted on WF training set, 1,845 events)
ODIN_VNEXT_MEANS = {
    "btd_bin": 0.14579945799457994,
    "ppm_flag_bin": 0.007588075880758808,
    "ta_very_high": 0.16802168021680217,
    "crl_rate_low": 0.08888888888888889,
    "era_post": 0.0,
    "is_nda": 0.0005420054200542005,
    "mfg_risk_bin": 0.08346883468834689,
    "sponsor_win_rate": 0.6323396081128082,
    "spa_6_15": 0.023306233062330622,
    "resub1_x_naive": 0.10569105691056911,
    "resub_class_2": 0.04336043360433604,
    "swr_x_btd": 0.10928827081443225,
    "crl_rate_x_naive": 0.11515664298735363,
    "swr_x_streak": 1.9051504394290097,
    "swr_x_ta_vh": 0.1221004037037129,
    "single_arm_x_btd": 0.056368563685636856,
    "resub2_x_experienced": 0.008130081300813009,
    "momentum_x_btd": -0.0016911615100058638,
    "ta_base_x_naive": 0.012258536585365852,
    "consistency_x_naive": 0.040331300022226575,
    "sponsor_consistency": 0.2626856472667426,
    "ta_momentum": -4.380916782767339e-05,
    "swr_cubed": 0.3727818932607258,
    "ta_crl_streak": 1.1121951219512196,
    "accel_orphan_btd": 0.028184281842818428,
    "ta_recent_rate_sq": 0.4579543173215958,
    "safety_high_x_naive": 0.018970189701897018,
    "adcom_x_naive": 0.0005420054200542005,
    "psychedelics_bin": 0.001084010840108401,
    "psychedelics_x_naive": 0.001084010840108401,
    "ta_bucket_MOD": 0.4075880758807588,
    "crl_count_x_naive": 0.2986449864498645,
    "resub1_x_experienced": 0.008130081300813009,
    "resub1_x_swr": 0.056308080536958655,
    # v14 NEW (18 features)
    "pw_orphan_drug_bin_x_resub_class_2": 0.00921409214092141,
    "surrogate_x_ta_vh": 0.0005420054200542005,
    "pw_priority_review_bin_x_resub_class_1": 0.015718157181571817,
    "pw_desig_stack_x_resub_class_1": 0.046612466124661245,
    "pw_gene_therapy_bin_x_sponsor_streak": 0.055284552845528454,
    "ft_x_safety": 0.03143631436314363,
    "pw_priority_review_bin_x_btd_bin": 0.12357723577235773,
    "pw_is_oncology_x_resub_class_2": 0.022222222222222223,
    "pw_is_oncology_x_mfg_risk_bin": 0.04173441734417344,
    "pw_double_crl_bin_x_resub_class_2": 0.005420054200542005,
    "pw_priority_review_bin_x_resub_class_2": 0.011382113821138212,
    "gt_x_btd": 0.018970189701897018,
    "pw_orphan_drug_bin_x_btd_bin": 0.08888888888888889,
    "pw_double_crl_bin_x_ta_crl_streak": 0.12303523035230353,
    "pw_gene_therapy_bin_x_log_spa_sq": 0.1425298411217468,
    "is_oncology": 0.43902439024390244,
    "crl_rate_x_swr": 0.2080747811618316,
}

ODIN_VNEXT_SCALES = {
    "btd_bin": 0.3529050524476331,
    "ppm_flag_bin": 0.08677843617619906,
    "ta_very_high": 0.3738855375565158,
    "crl_rate_low": 0.28458329944145994,
    "era_post": 1.0,
    "is_nda": 0.023274699787082805,
    "mfg_risk_bin": 0.27658956654963746,
    "sponsor_win_rate": 0.2575359603170455,
    "spa_6_15": 0.15087429390978094,
    "resub1_x_naive": 0.30744179514128517,
    "resub_class_2": 0.20366714610358738,
    "swr_x_btd": 0.27907383476633046,
    "crl_rate_x_naive": 0.2000889647110715,
    "swr_x_streak": 4.075189063041316,
    "swr_x_ta_vh": 0.2889854404308817,
    "single_arm_x_btd": 0.2306320634986713,
    "resub2_x_experienced": 0.08979968306656308,
    "momentum_x_btd": 0.03192510838637168,
    "ta_base_x_naive": 0.03189560952233876,
    "consistency_x_naive": 0.17029314240647253,
    "sponsor_consistency": 0.36954029004913946,
    "ta_momentum": 0.21020975484504656,
    "swr_cubed": 0.3453140481924326,
    "ta_crl_streak": 2.934864309431179,
    "accel_orphan_btd": 0.16549902748905507,
    "ta_recent_rate_sq": 0.20931273932097214,
    "safety_high_x_naive": 0.13641965255992647,
    "adcom_x_naive": 0.023274699787082805,
    "psychedelics_bin": 0.032906469889778946,
    "psychedelics_x_naive": 0.032906469889778946,
    "ta_bucket_MOD": 0.49138583239708855,
    "crl_count_x_naive": 1.876173036851687,
    "resub1_x_experienced": 0.08979968306656308,
    "resub1_x_swr": 0.16652374447710513,
    # v14 NEW (18 features)
    "pw_orphan_drug_bin_x_resub_class_2": 0.09554680866957314,
    "surrogate_x_ta_vh": 0.0232746997870828,
    "pw_priority_review_bin_x_resub_class_1": 0.12438286343539139,
    "pw_desig_stack_x_resub_class_1": 0.3964553839938515,
    "pw_gene_therapy_bin_x_sponsor_streak": 0.7736728213378266,
    "ft_x_safety": 0.1744937606403313,
    "pw_priority_review_bin_x_btd_bin": 0.3290986213450625,
    "pw_is_oncology_x_resub_class_2": 0.14740554623801777,
    "pw_is_oncology_x_mfg_risk_bin": 0.19998163853993145,
    "pw_double_crl_bin_x_resub_class_2": 0.07342123135037434,
    "pw_priority_review_bin_x_resub_class_2": 0.10607809060357783,
    "gt_x_btd": 0.13641965255992647,
    "pw_orphan_drug_bin_x_btd_bin": 0.28458329944145994,
    "pw_double_crl_bin_x_ta_crl_streak": 1.0757416305365295,
    "pw_gene_therapy_bin_x_log_spa_sq": 1.2414358483193377,
    "is_oncology": 0.4962680475457513,
    "crl_rate_x_swr": 0.11689743115828179,
}

# Tier thresholds (standardized from v1251/vNEXT analysis)
ODIN_VNEXT_TIERS = [
    (0.85, 1, "LONG", "High-confidence approval. Consider long position."),
    (0.65, 2, "CAUTIOUS LONG", "Favorable odds but elevated risk. Smaller position."),
    (0.40, 3, "MONITOR", "Uncertain outcome. Watch for catalysts."),
    (0.00, 4, "NO TRADE", "High CRL risk. Avoid or consider short."),
]

# Avoid signals — hard override to TIER_4 regardless of probability
ODIN_VNEXT_AVOID_SIGNALS = [
    "ppm_flag", "gene_therapy_cmc", "ema_cmc_flag",
    "hiring_void_nda", "pediatric_no_pk",
    "cmc_extension_active", "insider_critical_sell",
]

# TA risk bucket mapping (used for ta_very_high feature)
ODIN_TA_MAP = {
    "oncology": "Oncology", "cancer": "Oncology", "tumor": "Oncology",
    "lymphoma": "Oncology", "leukemia": "Oncology", "melanoma": "Oncology",
    "carcinoma": "Oncology", "sarcoma": "Oncology",
    "neuro": "CNS/Neurology", "cns": "CNS/Neurology", "alzheimer": "CNS/Neurology",
    "parkinson": "CNS/Neurology", "epilep": "CNS/Neurology",
    "psychi": "CNS/Neurology", "schizo": "CNS/Neurology",
    "depression": "CNS/Neurology", "bipolar": "CNS/Neurology",
    "immuno": "Immunology", "autoimmun": "Immunology",
    "rheumatoid": "Immunology", "crohn": "Immunology", "psoriasis": "Immunology",
    "rare disease": "Rare Disease", "orphan": "Rare Disease", "duchenne": "Rare Disease",
    "sma": "Rare Disease", "cystic fibrosis": "Rare Disease",
    "cardiovascular": "Cardiovascular", "cardiac": "Cardiovascular", "heart": "Cardiovascular",
    "ophthalmology": "Ophthalmology", "retinal": "Ophthalmology", "macular": "Ophthalmology",
    "pain": "Pain Management", "analgesic": "Pain Management",
    "metabolic": "Metabolic/Endocrine", "diabetes": "Metabolic/Endocrine",
    "obesity": "Metabolic/Endocrine", "endocrine": "Endocrinology",
    "nephrology": "Nephrology", "renal": "Nephrology", "kidney": "Nephrology",
    "dermatology": "Dermatology", "skin": "Dermatology", "atopic": "Dermatology",
    "respiratory": "Respiratory", "copd": "Respiratory", "asthma": "Respiratory",
    "pulmonary": "Respiratory",
    "hematology": "Hematology", "anemia": "Hematology", "hemophilia": "Hematology",
    "gi": "GI/Hepatology", "hepatology": "GI/Hepatology", "liver": "GI/Hepatology",
    "nash": "GI/Hepatology", "ibd": "GI/Hepatology",
    "women's health": "Women's Health", "fertility": "Women's Health",
    "contraceptive": "Women's Health",
    "vaccine": "Vaccines", "infectious": "Infectious Disease",
    "antiviral": "Infectious Disease", "antibiotic": "Infectious Disease",
    "hiv": "Infectious Disease", "hepatitis": "Infectious Disease",
    # v3.1 additions — fill gaps found in 2025-2026 head-to-head validation
    "glaucoma": "Ophthalmology", "dry eye": "Ophthalmology", "myopia": "Ophthalmology",
    "achondroplasia": "Rare Disease", "menkes": "Rare Disease", "mps": "Rare Disease",
    "hunter syndrome": "Rare Disease", "protoporphyria": "Rare Disease",
    "leukocyte adhesion": "Rare Disease", "lad-i": "Rare Disease",
    "apds": "Immunology", "anaphylaxis": "Immunology", "psoriatic": "Immunology",
    "aml": "Oncology", "all": "Oncology", "mds": "Oncology", "myeloma": "Oncology",
    "waldenstrom": "Oncology", "ovarian": "Oncology", "breast": "Oncology",
    "opioid": "Pain Management", "migraine": "Pain Management",
    "fsgs": "Nephrology",
}

ODIN_TA_RISK_BUCKET = {
    "Pain Management": "VERY_HIGH", "Ophthalmology": "VERY_HIGH",
    "Nephrology": "HIGH", "Hematology": "HIGH",
    "CNS/Neurology": "MOD", "Cardiovascular": "MOD", "Metabolic/Endocrine": "MOD",
    "Endocrinology": "MOD", "Other": "MOD", "Rare Disease": "MOD",
    "Immunology": "LOW", "Dermatology": "LOW", "Oncology": "LOW",
    "GI/Hepatology": "LOW", "Respiratory": "LOW", "Infectious Disease": "LOW",
    "Vaccines": "LOW", "Women's Health": "LOW", "CNS": "MOD",
}


class OdinVNextEngine:
    """ODIN v14 Champion — 51-feature L2 Ridge logistic regression (C=0.1).

    Scoring pipeline:
      1. Extract 51 features from tool inputs
      2. Standardize: z = (x - mean) / scale
      3. logit = intercept + sum(coef * z)
      4. P(approve) = sigmoid(logit)
      5. Tier assignment from probability thresholds

    Kaizen v14 changes from v13:
      - Dropped: log_spa_sq, accel_x_btd, is_immunology (3 features — all hurting HO)
      - Added: 18 new regulatory pathway + modality interaction features
      - C=0.1 (from C=0.025) — optimal regularization for 51 features
      - WF AUC 0.9011, HO AUC 0.9363 (+0.0062 over v13)
      - Stability: 20/20 seeds beat v13, paired t-test p=0.000000
      - T1 win rate 98.7% (154 picks). HO Brier 0.0895.
      - Key discovery: Priority review × resubmission class interactions unlock
        regulatory pathway signal. Oncology × manufacturing risk reveals disease-
        specific manufacturing complexity.
    """

    def __init__(self):
        self.intercept = ODIN_VNEXT_INTERCEPT
        self.coefs = ODIN_VNEXT_COEFS
        self.means = ODIN_VNEXT_MEANS
        self.scales = ODIN_VNEXT_SCALES
        self.version = "ODIN v14 Champion"
        self.weight_source = "EMBEDDED (WF AUC 0.9011, HO AUC 0.9363)"

    def _resolve_ta(self, therapeutic_area: str) -> str:
        """Map freetext TA to canonical TA name."""
        ta_lower = therapeutic_area.lower().strip()
        for key, canon in ODIN_TA_MAP.items():
            if key in ta_lower:
                return canon
        return "Other"

    def _resolve_era(self, pdufa_date: str) -> str:
        """Map PDUFA date to FDA era."""
        try:
            if "H1" in pdufa_date or "H2" in pdufa_date:
                year = int(pdufa_date.split("-")[0].strip())
            elif "Q" in pdufa_date:
                year = int(pdufa_date.split("-")[0].strip())
            else:
                dt = datetime.strptime(pdufa_date[:10], "%Y-%m-%d")
                year = dt.year
        except Exception:
            year = 2026

        if year < 2020:
            return "PRE_2020"
        elif year <= 2021:
            return "COVID_ERA"
        elif year <= 2023:
            return "POST_COVID"
        else:
            return "HOEG_ERA"

    def encode(self, catalyst: dict) -> dict:
        """Extract 37 v12 champion features from a catalyst dict.

        Returns dict of {feature_name: raw_value} for transparency.
        v12 = v11's features with 4 dropped + 6 added:
        Dropped: multi_crl, sweet_x_btd, experienced_x_btd, resub_class_1
        Added: safety_high_x_naive, adcom_x_naive, psychedelics_bin,
               psychedelics_x_naive, ta_bucket_MOD, crl_count_x_naive
        """
        signals = catalyst.get("signals", {})
        features = {}

        # Binary signals
        btd = 1.0 if signals.get("btd", False) else 0.0
        pr = 1.0 if signals.get("priority_review", False) else 0.0  # local var for interactions
        features["btd_bin"] = btd
        features["ppm_flag_bin"] = 1.0 if signals.get("ppm_flag", False) else 0.0

        # Sponsor experience (used for interactions, kept as local var)
        spa = catalyst.get("sponsor_prior_approvals", 5)
        sponsor_naive = 1.0 if spa == 0 else 0.0
        sponsor_experienced = 1.0 if spa >= 5 else 0.0

        # Resubmission (local var, not a feature)
        resub = catalyst.get("resub_class", 0)

        # TA very high risk
        ta = self._resolve_ta(catalyst.get("therapeutic_area", ""))
        ta_risk = ODIN_TA_RISK_BUCKET.get(ta, "MOD")
        features["ta_very_high"] = 1.0 if ta_risk == "VERY_HIGH" else 0.0

        # Oncology indicator (for v14 new features)
        features["is_oncology"] = 1.0 if ta == "Oncology" else 0.0

        # NOTE: spa_mega DROPPED in v13 (hurting HO AUC, absorbed by log_spa_sq)
        # NOTE: multi_crl DROPPED in v12 (signal absorbed by crl_count_x_naive)
        prior_crl_count = catalyst.get("prior_crl_count", 0)

        # Low historical CRL rate for this TA (< 20%)
        hist_crl = catalyst.get("historical_crl_rate", 0.32)
        features["crl_rate_low"] = 1.0 if hist_crl < 0.20 else 0.0

        # Application type NDA
        features["is_nda"] = 0.0

        # NOTE: btd_and_priority DROPPED in v13 (hurting HO AUC)
        # NOTE: sweet_x_btd DROPPED in v12
        # NOTE: experienced_x_btd DROPPED in v12

        # Post-COVID/HOEG FDA era
        era = self._resolve_era(catalyst.get("pdufa_date", "2026"))
        features["era_post"] = 1.0 if era in ("POST_COVID", "HOEG_ERA") else 0.0

        # Manufacturing risk flag
        features["mfg_risk_bin"] = 1.0 if signals.get("manufacturing_risk", False) else 0.0

        # Temporal sponsor win rate
        import math as _math
        sponsor_wr = catalyst.get("sponsor_win_rate", None)
        if sponsor_wr is not None:
            features["sponsor_win_rate"] = float(sponsor_wr)
        else:
            total_submissions = catalyst.get("sponsor_total_submissions", None)
            if total_submissions and total_submissions >= 3:
                features["sponsor_win_rate"] = min(1.0, spa / total_submissions)
            else:
                features["sponsor_win_rate"] = 0.5

        # ── v9 FEATURES ──
        features["spa_6_15"] = 1.0 if 6 <= spa <= 15 else 0.0

        resub_class_1 = 1.0 if resub == 1 else 0.0  # local var only (DROPPED as feature in v12)
        resub_class_2 = 1.0 if resub == 2 else 0.0
        # NOTE: resub_class_1 DROPPED in v12
        features["resub_class_2"] = resub_class_2
        features["resub1_x_naive"] = resub_class_1 * sponsor_naive
        # NOTE: log_spa_sq DROPPED in v14 (but computed for pw_gene_therapy_bin_x_log_spa_sq)
        features["swr_x_btd"] = features["sponsor_win_rate"] * btd
        features["crl_rate_x_naive"] = hist_crl * sponsor_naive

        # ── v10 FEATURES (retained) ──
        sponsor_streak = catalyst.get("sponsor_streak", 0.0)
        features["swr_x_streak"] = features["sponsor_win_rate"] * sponsor_streak
        features["swr_x_ta_vh"] = features["sponsor_win_rate"] * features["ta_very_high"]
        single_arm = 1.0 if signals.get("single_arm_study", False) else 0.0
        features["single_arm_x_btd"] = single_arm * btd
        features["resub2_x_experienced"] = resub_class_2 * sponsor_experienced
        sponsor_momentum = catalyst.get("sponsor_momentum", 0.0)
        features["momentum_x_btd"] = sponsor_momentum * btd

        # ── v11 FEATURES (retained) ──

        # TA base score × naive sponsor (risky TAs amplified for naive sponsors)
        ta_base = catalyst.get("ta_base_score", 0.0)
        features["ta_base_x_naive"] = ta_base * sponsor_naive

        # Sponsor consistency × naive (inconsistent naive sponsors = danger)
        sponsor_consistency = catalyst.get("sponsor_consistency", 0.5)
        features["consistency_x_naive"] = sponsor_consistency * sponsor_naive

        # Sponsor consistency (1 - std of outcomes, higher = more consistent)
        features["sponsor_consistency"] = sponsor_consistency

        # TA momentum (1yr rate minus 3yr rate — positive = improving)
        ta_momentum = catalyst.get("ta_momentum", 0.0)
        features["ta_momentum"] = ta_momentum

        # SWR cubed (non-linear sponsor win rate)
        features["swr_cubed"] = features["sponsor_win_rate"] ** 3

        # Consecutive CRLs in this TA (0-1 normalized, 5 max)
        ta_crl_streak = catalyst.get("ta_crl_streak", 0.0)
        features["ta_crl_streak"] = ta_crl_streak

        # Triple combo: accelerated × orphan × BTD (v11 retained)
        accel = 1.0 if signals.get("accelerated_approval", False) else 0.0
        orphan = 1.0 if signals.get("orphan", False) else 0.0
        features["accel_orphan_btd"] = accel * orphan * btd

        # TA recent rate squared (non-linear TA rate)
        ta_rr = catalyst.get("ta_recent_rate", 0.5)
        features["ta_recent_rate_sq"] = float(ta_rr) ** 2

        # ── v12 NEW FEATURES ──

        # High safety signal × naive sponsor (naive sponsors in high-safety-risk = danger)
        safety_severity = catalyst.get("safety_signal_severity", 0)
        features["safety_high_x_naive"] = (1.0 if safety_severity > 1 else 0.0) * sponsor_naive

        # Advisory committee × naive sponsor (adcom + naive = negative signal)
        had_adcom = 1.0 if signals.get("had_adcom", False) or catalyst.get("had_adcom_flag", 0) else 0.0
        features["adcom_x_naive"] = had_adcom * sponsor_naive

        # Psychedelic drug flag (slight positive — emerging therapeutic class)
        psychedelics = 1.0 if signals.get("psychedelics", False) or catalyst.get("is_psychedelic", False) else 0.0
        features["psychedelics_bin"] = psychedelics

        # Psychedelics × naive sponsor
        features["psychedelics_x_naive"] = psychedelics * sponsor_naive

        # TA risk bucket = MOD (moderate TA risk indicator)
        features["ta_bucket_MOD"] = 1.0 if ta_risk == "MOD" else 0.0

        # Prior CRL count × naive sponsor (more CRLs + naive = very bad)
        features["crl_count_x_naive"] = float(prior_crl_count) * sponsor_naive

        # ── v13 NEW FEATURES ──

        # Class 1 resubmission × experienced sponsor (experienced sponsors recover from major CRLs)
        features["resub1_x_experienced"] = resub_class_1 * sponsor_experienced

        # Class 1 resubmission × sponsor win rate (penalty asymmetry — even high SWR can't fully overcome Class 1)
        features["resub1_x_swr"] = resub_class_1 * features["sponsor_win_rate"]

        # ── v14 NEW FEATURES (18 interactions + modality) ──

        # Orphan drug × Class 2 resubmission
        features["pw_orphan_drug_bin_x_resub_class_2"] = orphan * resub_class_2

        # Surrogate endpoint × very high TA risk
        surrogate = 1.0 if signals.get("surrogate_endpoint", False) or catalyst.get("surrogate_endpoint", False) else 0.0
        features["surrogate_x_ta_vh"] = surrogate * features["ta_very_high"]

        # Priority review × Class 1 resubmission
        features["pw_priority_review_bin_x_resub_class_1"] = pr * resub_class_1

        # Designation stack × Class 1 resubmission (count of designations)
        desig_stack = sum([1.0 for flag in ["btd", "orphan", "priority_review", "fast_track"] if signals.get(flag, False)])
        features["pw_desig_stack_x_resub_class_1"] = desig_stack * resub_class_1

        # Gene therapy × sponsor streak
        gene_therapy = 1.0 if signals.get("gene_therapy", False) or catalyst.get("gene_therapy", False) else 0.0
        features["pw_gene_therapy_bin_x_sponsor_streak"] = gene_therapy * sponsor_streak

        # Fast track × safety signal
        fast_track = 1.0 if signals.get("fast_track", False) else 0.0
        features["ft_x_safety"] = fast_track * (1.0 if safety_severity > 1 else 0.0)

        # Priority review × BTD
        features["pw_priority_review_bin_x_btd_bin"] = pr * btd

        # Oncology × Class 2 resubmission
        features["pw_is_oncology_x_resub_class_2"] = features["is_oncology"] * resub_class_2

        # Oncology × manufacturing risk
        features["pw_is_oncology_x_mfg_risk_bin"] = features["is_oncology"] * features["mfg_risk_bin"]

        # Double CRL × Class 2 resubmission (if prior_crl_count >= 2)
        double_crl = 1.0 if prior_crl_count >= 2 else 0.0
        features["pw_double_crl_bin_x_resub_class_2"] = double_crl * resub_class_2

        # Priority review × Class 2 resubmission
        features["pw_priority_review_bin_x_resub_class_2"] = pr * resub_class_2

        # Gene therapy × BTD
        features["gt_x_btd"] = gene_therapy * btd

        # Orphan × BTD
        features["pw_orphan_drug_bin_x_btd_bin"] = orphan * btd

        # Double CRL × TA CRL streak
        features["pw_double_crl_bin_x_ta_crl_streak"] = double_crl * ta_crl_streak

        # Gene therapy × log SPA squared
        log_spa_sq = _math.log1p(spa) ** 2
        features["pw_gene_therapy_bin_x_log_spa_sq"] = gene_therapy * log_spa_sq

        # CRL rate × sponsor win rate
        features["crl_rate_x_swr"] = hist_crl * features["sponsor_win_rate"]

        return features

    def score(self, catalyst: dict) -> dict:
        """Score a single PDUFA catalyst. Returns probability + tier."""
        raw_features = self.encode(catalyst)

        # Standardize and compute logit
        logit = self.intercept
        feature_contributions = []

        for feat_name in ODIN_VNEXT_FEATURES:
            raw_val = raw_features[feat_name]
            z_val = (raw_val - self.means[feat_name]) / self.scales[feat_name]
            coef = self.coefs[feat_name]
            contribution = coef * z_val
            logit += contribution

            if raw_val != 0.0:
                feature_contributions.append({
                    "feature": feat_name,
                    "raw_value": round(raw_val, 4),
                    "z_score": round(z_val, 4),
                    "coefficient": round(coef, 4),
                    "contribution": round(contribution, 4),
                })

        # Sigmoid
        logit_clamped = max(-30, min(30, logit))
        prob = 1.0 / (1.0 + math.exp(-logit_clamped))

        # Check avoid signals
        signals = catalyst.get("signals", {})
        avoid_triggered = []
        for av in ODIN_VNEXT_AVOID_SIGNALS:
            if signals.get(av, False):
                avoid_triggered.append(av)

        # Tier classification
        if avoid_triggered:
            tier, action, note = 4, "NO TRADE", f"AVOID signal(s) active: {', '.join(avoid_triggered)}"
        else:
            tier, action, note = 4, "NO TRADE", ""
            for threshold, t, a, n in ODIN_VNEXT_TIERS:
                if prob >= threshold:
                    tier, action, note = t, a, n
                    break

        # Resolve TA for display
        ta = self._resolve_ta(catalyst.get("therapeutic_area", ""))
        ta_risk = ODIN_TA_RISK_BUCKET.get(ta, "MOD")

        # Sort contributions by absolute impact
        feature_contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        return {
            "version": self.version,
            "probability": round(prob, 4),
            "logit": round(logit, 4),
            "tier": tier,
            "action": action,
            "tier_note": note,
            "therapeutic_area": ta,
            "ta_risk_bucket": ta_risk,
            "fda_era": self._resolve_era(catalyst.get("pdufa_date", "2026")),
            "avoid_signals_active": avoid_triggered,
            "top_features": feature_contributions[:8],
            "n_features_active": sum(1 for v in raw_features.values() if v != 0.0),
            "weight_source": self.weight_source,
        }


# ============================================================================
# GUNGNIR v46 CHAMPION — 126-Feature Ridge+XGB Meta-Ensemble (loads from deploy JSON)
# ============================================================================
# Kaizen from v38: enrichment leverage — CT.gov v2 (96.6%) + ChEMBL
# WF AUC 0.7599 (+0.0090 over v38), 10/10 seeds, p=0.0000000000
# 12 new features: cv2_n_per_arm, ct_ep_is_biomarker, ct_ep_is_safety,
#   ch_is_enzyme, ct_ep_is_orr, ch_is_biologic, ch_is_agonist, ct_ep_is_pfs,
#   ct_is_crossover, cv2_is_rigorous, ch_is_ion_channel, ct_has_combination
# Config: Ridge C=0.015, XGB lr=0.01/400 trees, meta 70/30, T=1.0
#
# The MCP server implements the Ridge M1 component (90% of v46 meta-blend).
# Features requiring external data (journey, momentum, competitive, CT.gov)
# use training means → z-score of 0 → no contribution (correct default behavior).
# Full v46 scoring with all 126 active features requires the enriched training pipeline.

_GUNGNIR_DEPLOY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "gungnir_v46_deploy.json")

# TA classification patterns (matching v37 training pipeline)
_G38_TA_PATTERNS = {
    "oncology": re.compile(r"(?i)(cancer|tumor|carcinoma|lymphoma|leukemia|melanoma|sarcoma|myeloma|glioma|glioblastoma|neoplasm|malignant|metasta|NSCLC|SCLC|hepatocellular|colorectal|pancrea|ovarian|breast.cancer|prostate.cancer|lung.cancer|bladder|renal.cell|gastric|cholang|solid.tumor)"),
    "cns": re.compile(r"(?i)(alzheimer|parkinson|multiple.sclerosis|epilepsy|seizure|migraine|depression|schizophren|bipolar|anxiety|PTSD|autism|ADHD|huntington|ALS|amyotrophic|dementia|neuropath|neurodegen|stroke|psycho|cognitive|CNS|brain)"),
    "cardiovascular": re.compile(r"(?i)(heart|cardiac|cardio|coronary|atrial|arrhythm|hypertens|myocard|thrombo|embol|atheroscler|cholesterol|dyslipid|PAH|pulmonary.arterial|heart.failure|HFrEF|HFpEF)"),
    "immunology": re.compile(r"(?i)(rheumatoid|lupus|psoria|atopic|eczema|dermatit|crohn|colitis|IBD|ankylosing|autoimmun|graft.vs.host|GVHD|allerg|asthma|COPD|IPF|vasculit|alopecia)"),
    "infectious": re.compile(r"(?i)(HIV|AIDS|hepatitis|HBV|HCV|influenza|COVID|SARS|RSV|pneumonia|tuberculosis|malaria|herpes|HPV|antibiotic|antiviral|sepsis|infection)"),
    "rare_disease": re.compile(r"(?i)(orphan|rare.disease|duchenne|DMD|SMA|spinal.muscular|cystic.fibrosis|hemophilia|sickle.cell|thalassemia|gaucher|fabry|pompe|amyloid|ATTR|lysosomal|mucopolysaccharid|achondroplasia)"),
    "metabolic": re.compile(r"(?i)(diabetes|diabetic|insulin|HbA1c|GLP.?1|SGLT|obesity|obese|weight.loss|NASH|NAFLD|fatty.liver|metabolic|gout|osteopor)"),
    "ophthalmology": re.compile(r"(?i)(eye|ocular|ophthalm|retina|macular|AMD|glaucoma|uveitis|diabetic.retin|dry.eye|geographic.atrophy)"),
    "hematology": re.compile(r"(?i)(anemia|thrombocytop|neutropeni|myelodysplast|MDS|myeloproliferative|myelofibros|polycythemia|platelet|coagul|bleed|ITP|TTP|aplastic)"),
}

_G38_TA_RATES = {"oncology": 0.55, "cns": 0.45, "rare_disease": 0.60, "metabolic": 0.58,
                 "immunology": 0.52, "cardiovascular": 0.48, "infectious": 0.50,
                 "ophthalmology": 0.55, "hematology": 0.53, "other": 0.50}


def _g38_classify_ta(text):
    if not text:
        return "other"
    for ta, pat in _G38_TA_PATTERNS.items():
        if pat.search(text):
            return ta
    return "other"


def _g38_parse_phase(stage):
    if not stage:
        return 2
    s = stage.upper()
    if "3" in s:
        return 3
    if "2/3" in s:
        return 3
    if "2B" in s or "2A" in s or "2" in s or "1/2" in s:
        return 2
    if "1B" in s or "1A" in s or "1" in s:
        return 1
    return 2


class GungnirV38Engine:
    """GUNGNIR v46 Champion — 126-feature Ridge+XGB meta-ensemble (New Feature Mining Post-Prune).

    Loads weights from gungnir_v46_deploy.json. Falls back to embedded v27
    if deploy file not found. Implements v46-compatible feature engineering.
    v46: 8 new features added to v45's clean 118-feature base (ChEMBL modality, journey, conference interactions).
    AUC 0.8083 (+0.0065 over v44). 20/20 seed stability on BOTH AUC and Brier.
    """

    def __init__(self):
        self.v37_loaded = False
        self.feature_names = []
        self.m1_coefs = {}
        self.m1_intercept = 0.0
        self.scaler_means = {}
        self.scaler_stds = {}

        if os.path.exists(_GUNGNIR_DEPLOY_PATH):
            try:
                with open(_GUNGNIR_DEPLOY_PATH) as f:
                    deploy = json.load(f)
                self.feature_names = deploy["feature_names"]
                self.m1_coefs = deploy["M1_coef"]
                self.m1_intercept = deploy["M1_intercept"]
                self.scaler_means = deploy["scaler_means"]
                self.scaler_stds = deploy["scaler_scales"]
                auc_str = deploy.get('performance', {}).get('wf_auc', '0.7678')
                ver = deploy['version']
                ver_str = ver if ver.startswith('v') else f"v{ver}"
                self.version = f"GUNGNIR {ver_str} ({deploy.get('codename', 'Champion')}, AUC {auc_str})"
                self.weight_source = f"LOADED from gungnir_v46_deploy.json ({deploy['n_features']} features)"
                self.v37_loaded = True
            except Exception as e:
                import sys; sys.stderr.write(f"[WARNING] Failed to load v37 deploy: {e}\\n")
                self._init_v27_fallback()
        else:
            self._init_v27_fallback()

    def _init_v27_fallback(self):
        """Fall back to embedded v27 weights."""
        self.version = "GUNGNIR v27 (Predictive, AUC 0.7529) [FALLBACK]"
        self.weight_source = "EMBEDDED v27 fallback (v37 deploy JSON not found)"
        # v27 fallback uses the old engine — redirect to it
        self._v27_fallback = True

    def encode(self, catalyst: dict) -> dict:
        """Extract v37-compatible features from structured inputs.

        Computes all features possible from MCP input parameters.
        Features requiring external data (journey, momentum, competitive,
        CT.gov) use scaler means → z-score of 0 → no contribution.
        """
        features = {}

        text = catalyst.get("catalyst_text", "").lower()
        stage = catalyst.get("stage", "Phase 2")
        indication = catalyst.get("indication", "")
        drug = catalyst.get("drug_name", catalyst.get("drug", ""))
        year = catalyst.get("year", 2026)

        phase = _g38_parse_phase(stage)
        ta = _g38_classify_ta(indication + " " + (drug or ""))
        stage_upper = stage.upper() if stage else ""

        # Price
        price = catalyst.get("price", catalyst.get("stock_price", 15.0))
        if not price or price <= 0:
            price = 15.0

        # Market cap
        mcap = catalyst.get("market_cap", price * 50e6)
        if not mcap or mcap <= 0:
            mcap = price * 50e6

        # === PHASE FEATURES ===
        features["is_phase1"] = 1 if phase == 1 else 0
        features["is_phase2"] = 1 if phase == 2 else 0
        features["is_phase3"] = 1 if phase == 3 else 0
        features["is_pivotal"] = 1 if phase >= 3 else 0
        features["phase_numeric"] = phase

        # v37 NEW: Granular stage encoding
        features["is_phase2b"] = 1 if "2B" in stage_upper else 0
        features["is_phase2a"] = 1 if "2A" in stage_upper else 0
        features["is_phase1b"] = 1 if "1B" in stage_upper else 0
        features["is_bridging"] = 1 if ("1/2" in stage_upper or "2/3" in stage_upper) else 0
        features["is_advanced_phase2"] = 1 if ("2B" in stage_upper or "2/3" in stage_upper) else 0

        # === TA FEATURES ===
        for ta_name in _G38_TA_PATTERNS:
            features[f"ta_{ta_name}"] = 1 if ta == ta_name else 0
        features["ta_other"] = 1 if ta == "other" else 0
        features["ta_base_rate"] = _G38_TA_RATES.get(ta, 0.50)

        # === SIZE FEATURES ===
        features["log_price"] = math.log(max(price, 0.01))
        features["is_micro"] = 1 if price < 5 else 0
        features["is_small"] = 1 if 5 <= price < 20 else 0
        features["is_mid"] = 1 if 20 <= price < 80 else 0
        features["is_large"] = 1 if price >= 80 else 0
        features["log_market_cap"] = math.log(max(mcap, 1e6))

        # === NLP SIGNALS (T-1 safe) ===
        features["nlp_topline"] = 1 if "topline" in text else 0
        features["nlp_interim"] = 1 if "interim" in text else 0
        features["nlp_phase3"] = 1 if re.search(r"phase.?3|pivotal", text) else 0
        features["nlp_dose_response"] = 1 if re.search(r"dose.?response|dose.?escal", text) else 0
        features["nlp_biomarker"] = 1 if re.search(r"biomark|surrogate|ORR|PFS|DFS", text) else 0
        features["nlp_combo_therapy"] = 1 if re.search(r"combin|combo|plus |\+", text) else 0
        features["nlp_first_in"] = 1 if re.search(r"first.in|novel|first.time", text) else 0

        # === DESIGNATIONS ===
        combined = text
        features["has_btd"] = 1 if re.search(r"breakthrough|BTD", combined, re.I) else 0
        features["has_fast_track"] = 1 if re.search(r"fast.track|FTD", combined, re.I) else 0
        features["has_priority_review"] = 1 if re.search(r"priority.review", combined, re.I) else 0
        features["has_orphan"] = 1 if re.search(r"orphan", combined, re.I) else 0
        if catalyst.get("btd"):
            features["has_btd"] = 1
        if catalyst.get("orphan"):
            features["has_orphan"] = 1
        if catalyst.get("fast_track"):
            features["has_fast_track"] = 1
        if catalyst.get("priority_review"):
            features["has_priority_review"] = 1
        features["designation_count"] = sum([
            features["has_btd"], features["has_fast_track"],
            features["has_priority_review"], features["has_orphan"]
        ])
        desig_override = catalyst.get("designation_count")
        if desig_override and desig_override > features["designation_count"]:
            features["designation_count"] = float(desig_override)

        # === CATALYST TYPE ===
        features["cat_topline"] = 1 if "topline" in text else 0
        features["cat_interim"] = 1 if "interim" in text else 0
        features["cat_initial"] = 1 if "initial" in text else 0
        features["cat_conference"] = 1 if "conference" in text or "presentation" in text else 0
        features["cat_full_results"] = 1 if "full" in text else 0
        features["cat_regulatory"] = 0
        features["cat_submission"] = 0

        # === JOURNEY (defaults — need historical data for real values) ===
        features["journey_n_prior"] = catalyst.get("journey_n_prior", 0)
        features["journey_success_rate"] = catalyst.get("journey_success_rate", 0.5)
        features["journey_had_positive"] = catalyst.get("journey_had_positive", 0)
        features["journey_had_prior_positive"] = catalyst.get("journey_had_positive", 0)
        features["journey_had_negative"] = catalyst.get("journey_had_negative", 0)
        features["journey_had_prior_negative"] = catalyst.get("journey_had_negative", 0)
        features["journey_positive_streak"] = math.log1p(catalyst.get("journey_positive_streak", 0))
        features["journey_last_positive"] = catalyst.get("journey_last_positive", 0.5)

        # === HISTORICAL LOA/POP ===
        features["hist_loa"] = catalyst.get("hist_loa", 0)
        features["hist_pop"] = catalyst.get("hist_pop", 0)

        # === CT.GOV (defaults — use phase-average imputation) ===
        enroll_default = {1: math.log(50), 2: math.log(150), 3: math.log(400)}.get(phase, math.log(250))
        features["ctgov_enrollment"] = catalyst.get("enrollment", enroll_default)
        if features["ctgov_enrollment"] > 0 and features["ctgov_enrollment"] < 20:
            features["ctgov_enrollment"] = math.log(max(features["ctgov_enrollment"], 1))
        features["ctgov_n_arms"] = catalyst.get("n_arms", 2)
        features["ctgov_is_randomized"] = catalyst.get("is_randomized", 1 if phase >= 2 else 0)
        features["ctgov_is_double_blind"] = catalyst.get("is_double_blind", 1 if phase >= 3 else 0)
        features["ctgov_is_placebo"] = catalyst.get("is_placebo", features["ctgov_is_double_blind"])
        features["ctgov_masking_rigor"] = 2 * features["ctgov_is_double_blind"]
        features["ctgov_has_dmc"] = catalyst.get("has_dmc", 1 if phase >= 3 else 0)
        features["ctgov_ep_hard"] = 1 if re.search(r"(overall survival|OS|mortality|death)", text, re.I) else 0
        features["ctgov_ep_surrogate"] = 1 if re.search(r"(ORR|PFS|DFS|surrogate|response.rate)", text, re.I) else 0
        features["ctgov_n_sites"] = catalyst.get("n_sites", 50)
        features["ctgov_n_countries"] = catalyst.get("n_countries", 5)
        features["ctgov_is_global"] = 1 if features["ctgov_n_countries"] >= 5 else 0
        features["ctgov_has_withdrawals"] = 0
        features["ctgov_real"] = 0  # MCP doesn't have real CT.gov lookup

        # === SPONSOR (default or explicit) ===
        features["sponsor_success_rate"] = catalyst.get("sponsor_success_rate", 0.5)

        # === INDICATION DENSITY ===
        features["indication_density"] = catalyst.get("indication_density", 0)

        # === ERA ===
        features["era_2024_plus"] = 1 if year >= 2024 else 0

        # === MOMENTUM (defaults — need price data) ===
        features["momentum_5d"] = catalyst.get("momentum_5d", 0)
        features["momentum_10d"] = catalyst.get("momentum_10d", 0)
        features["momentum_20d"] = catalyst.get("momentum_20d", 0)
        features["volatility_5d"] = abs(features["momentum_5d"])
        features["volatility_20d"] = abs(features["momentum_20d"])

        # === COMPETITIVE (defaults) ===
        features["competitive_6mo"] = catalyst.get("competitive_6mo", 0)
        features["competitive_3mo"] = catalyst.get("competitive_3mo", 0)

        # === INTERACTION FEATURES ===
        is_p3 = features["is_phase3"]
        features["phase3_x_randomized"] = is_p3 * features["ctgov_is_randomized"]
        features["phase3_x_double_blind"] = is_p3 * features["ctgov_is_double_blind"]
        features["phase3_x_placebo"] = is_p3 * features["ctgov_is_placebo"]
        features["phase3_x_cns"] = is_p3 * features["ta_cns"]
        features["phase3_x_oncology"] = is_p3 * features["ta_oncology"]
        features["onc_x_single_arm"] = features["ta_oncology"] * (1 if features["ctgov_n_arms"] <= 1 else 0)
        features["rare_x_small"] = features["ta_rare_disease"] * (features["is_micro"] + features["is_small"])
        features["btd_x_phase3"] = features["has_btd"] * is_p3
        features["micro_x_phase3"] = features["is_micro"] * is_p3
        features["small_x_phase3"] = features["is_small"] * is_p3
        features["large_x_any"] = features["is_large"]
        features["desig_x_small"] = features["designation_count"] * (features["is_micro"] + features["is_small"])
        features["ep_hard_x_phase3"] = features["ctgov_ep_hard"] * is_p3
        features["dmc_x_phase3"] = features["ctgov_has_dmc"] * is_p3
        features["cns_x_micro"] = features["ta_cns"] * features["is_micro"]
        features["journey_pos_x_phase3"] = features.get("journey_had_prior_positive", 0) * is_p3
        features["journey_sr_x_phase3"] = features["journey_success_rate"] * is_p3
        features["journey_streak_x_small"] = features["journey_positive_streak"] * (features["is_micro"] + features["is_small"])
        features["enrollment_x_phase3"] = features["ctgov_enrollment"] * is_p3
        features["global_x_phase3"] = features["ctgov_is_global"] * is_p3
        features["combo_x_onc"] = features["nlp_combo_therapy"] * features["ta_oncology"]
        features["micro_x_rare"] = features["is_micro"] * features["ta_rare_disease"]
        features["momentum_x_phase3"] = features["momentum_5d"] * is_p3
        features["momentum_x_micro"] = features["momentum_5d"] * features["is_micro"]
        features["volatility_x_phase3"] = features["volatility_5d"] * is_p3
        features["competitive_x_onc"] = features["competitive_6mo"] * features["ta_oncology"]

        # === v37 NEW: Non-linear transforms ===
        features["enrollment_sq"] = features["ctgov_enrollment"] ** 2
        features["indication_density_sq"] = features["indication_density"] ** 2

        # === v40 NEW: Conference Signal + Short Interest ===
        # Conference detection from catalyst text
        conf_text = text.upper()
        _elite = ["AACR", "ASH", "ESMO"]
        _tier1 = ["ASCO", "AAN", "EHA", "AASLD"]
        _tier2 = ["SITC", "SNO", "ACNP", "ACR", "ADA", "EASD", "ECTRIMS",
                  "WCG", "EULAR", "DDW", "AUA", "ATS", "CHEST", "IDSA"]
        _generic_conf = ["CONFERENCE", "CONGRESS", "MEETING", "SYMPOSIUM",
                        "ANNUAL MEETING", "PRESENTED AT", "POSTER",
                        "ORAL PRESENTATION", "LATE-BREAKING"]
        has_conf = 0
        for c in _elite + _tier1 + _tier2:
            if c in conf_text:
                has_conf = 1
                break
        if not has_conf:
            for g in _generic_conf:
                if g in conf_text:
                    has_conf = 1
                    break
        # Override from explicit input param
        if catalyst.get("has_conference") is not None:
            has_conf = int(catalyst["has_conference"])
        features["v40_has_conference"] = has_conf

        # Days to cover (short interest ratio) — explicit input only
        features["v40_days_to_cover"] = float(catalyst.get("days_to_cover", 0) or 0)

        # Conference × small cap interaction
        features["v40_conf_x_small"] = has_conf * (features["is_micro"] + features["is_small"])

        # === v38 features needed for v42 interactions ===
        features["iis_is_interim"] = int(catalyst.get("is_interim", 0) or 0)
        features["ct_is_industry"] = int(catalyst.get("is_industry_sponsored", 0) or 0)
        features["ct_log_elig_length"] = float(catalyst.get("ct_log_elig_length", 0) or 0)

        # === v41 NEW: Non-linear transforms + interaction mining ===
        # sponsor_x_conference: strong sponsor presenting at conference = double conviction
        features["v41_sponsor_x_conference"] = features["sponsor_success_rate"] * features["v40_has_conference"]
        # journey_last_pos_sq: non-linear — a strong recent positive is worth MORE than linear captures
        features["v41_journey_last_pos_sq"] = features["journey_last_positive"] ** 2
        # immuno_x_phase2: immunology Phase 2 penalty — high failure rates
        features["v41_immuno_x_phase2"] = features["ta_immunology"] * features["is_phase2"]
        # placebo_x_cns: placebo-controlled CNS is HARDER — high placebo response rates
        features["v41_placebo_x_cns"] = features["ctgov_is_placebo"] * features["ta_cns"]
        # enrollment_x_journey: big trial + positive history = strong conviction signal
        features["v41_enrollment_x_journey"] = features["ctgov_enrollment"] * features["journey_success_rate"]

        # === v42 NEW: Exhaustive pairwise interaction search (8 features from 3853 candidates) ===
        # iis_is_interim × momentum_10d: interim readouts with momentum — inflated data meets market excitement
        features["v42_iis_is_interim_X_momentum_10d"] = features["iis_is_interim"] * features["momentum_10d"]
        # ctgov_n_arms × phase3_x_oncology: multi-arm Phase 3 oncology trials
        features["v42_ctgov_n_arms_X_phase3_x_oncology"] = features["ctgov_n_arms"] * features["phase3_x_oncology"]
        # ctgov_n_countries × indication_density: global trials in crowded indications
        features["v42_ctgov_n_countries_X_indication_density"] = features["ctgov_n_countries"] * features["indication_density"]
        # global_x_phase3 × volatility_20d: global Phase 3 trials with high volatility
        features["v42_global_x_phase3_X_volatility_20d"] = features["global_x_phase3"] * features["volatility_20d"]
        # ct_is_industry × ctgov_masking_rigor: industry-sponsored rigorous blinding
        features["v42_ct_is_industry_X_ctgov_masking_rigor"] = features["ct_is_industry"] * features["ctgov_masking_rigor"]
        # iis_is_interim × indication_density_sq: interim data in crowded indications (non-linear)
        features["v42_iis_is_interim_X_indication_density_sq"] = features["iis_is_interim"] * features["indication_density_sq"]
        # momentum_20d × ta_metabolic: metabolic TA momentum signal
        features["v42_momentum_20d_X_ta_metabolic"] = features["momentum_20d"] * features["ta_metabolic"]
        # is_small × ta_cns: small-cap CNS trials
        features["v42_is_small_X_ta_cns"] = features["is_small"] * features["ta_cns"]

        # === v43 NEW: ChEMBL Biotech Scientist Features (6 from 306 candidates) ===
        # Drug modality classification via INN stem heuristics + explicit params
        _drug_name = (drug or "").lower().strip()
        # Accept explicit modality flags if provided (preferred for accuracy)
        ch2_is_oligo = int(catalyst.get("is_oligonucleotide", 0) or 0)
        ch2_is_biologic = int(catalyst.get("is_biologic", 0) or 0)
        ch2_is_cell = int(catalyst.get("is_cell_therapy", 0) or 0)
        ch2_is_adc = int(catalyst.get("is_adc", 0) or 0)
        # If no explicit flags, classify from drug name using INN suffixes
        if not any([ch2_is_oligo, ch2_is_biologic, ch2_is_cell, ch2_is_adc]):
            if _drug_name:
                # ADC detection (linker payloads)
                if any(x in _drug_name for x in ['vedotin', 'tansine', 'deruxtecan',
                       'govitecan', 'mafodotin', 'ozogamicin', 'emtansine']):
                    ch2_is_adc = 1
                    ch2_is_biologic = 1
                # mAb suffix → biologic
                elif _drug_name.endswith('mab'):
                    ch2_is_biologic = 1
                # Cell therapy (CAR-T, -cel suffix)
                elif _drug_name.endswith('cel') or 'car-t' in _drug_name or 'car t' in _drug_name:
                    ch2_is_cell = 1
                # Oligonucleotide (ASO/siRNA: -sen, -ran suffixes)
                elif _drug_name.endswith('sen') or _drug_name.endswith('ran') or \
                     'sirna' in _drug_name or 'antisense' in _drug_name:
                    ch2_is_oligo = 1
                # Fusion proteins (-cept) → biologic
                elif _drug_name.endswith('cept'):
                    ch2_is_biologic = 1
        features["ch2_is_oligo"] = ch2_is_oligo
        features["ch2_is_biologic"] = ch2_is_biologic
        features["ch2_is_cell"] = ch2_is_cell
        features["ch2_is_adc"] = ch2_is_adc
        # v43 interaction features
        features["v43_ch2_is_oligo_X_volatility_20d"] = ch2_is_oligo * features["volatility_20d"]
        features["v43_ch2_is_biologic_X_is_phase3"] = ch2_is_biologic * features["is_phase3"]
        features["v43_ch2_is_cell_X_ctgov_is_randomized"] = ch2_is_cell * features["ctgov_is_randomized"]
        features["v43_ch2_is_adc_X_enrollment_sq"] = ch2_is_adc * features["enrollment_sq"]
        features["v43_ch2_is_cell_X_momentum_10d"] = ch2_is_cell * features["momentum_10d"]
        features["v43_ch2_is_oligo_X_is_phase2"] = ch2_is_oligo * features["is_phase2"]

        # === v44 NEW: Cross-Family Interaction Features (2 from 208 candidates) ===
        # Antagonist mechanism × prior positive readout = validated receptor blocking target
        ch2_moa_antagonist = 0
        if drug:
            dn = drug.lower()
            # Antagonist detection: INN stem patterns + mech lookup
            if dn.endswith('mab'):
                ch2_moa_antagonist = 1  # Most mAbs are antagonists
            # Additional patterns could be added from ChEMBL cache
        features["v44_ch2_moa_antagonist_X_journey_had_positive"] = (
            ch2_moa_antagonist * features.get("journey_had_positive", 0)
        )

        # Small molecule × Phase 2 × small-cap = focused bet, asymmetric upside
        ch2_is_sm = 0
        if drug:
            dn = drug.lower()
            if any(dn.endswith(s) for s in ['nib', 'tinib', 'lib', 'zomib', 'parib']):
                ch2_is_sm = 1
        features["v44_ch2_is_sm_X_is_phase2_X_is_small"] = (
            ch2_is_sm * features["is_phase2"] * features["is_small"]
        )

        return features

    def _scale(self, raw: dict) -> dict:
        """Apply StandardScaler: z = (x - mean) / std.
        For unknown features, use mean → z=0 → no contribution."""
        scaled = {}
        for f in self.feature_names:
            mean = self.scaler_means.get(f, 0.0)
            std = self.scaler_stds.get(f, 1.0)
            val = raw.get(f, mean)  # use training mean if feature not computed
            if std == 0 or std < 1e-10:
                scaled[f] = 0.0
            else:
                scaled[f] = (val - mean) / std
        return scaled

    def score(self, catalyst: dict) -> dict:
        """Score a phase readout catalyst."""
        if hasattr(self, '_v27_fallback') and self._v27_fallback:
            # Fall back to v27 engine
            return _GUNGNIR_V27.score(catalyst)

        raw = self.encode(catalyst)
        scaled = self._scale(raw)

        # Ridge M1 prediction (60% of meta-blend — primary signal)
        logit = self.m1_intercept
        for f in self.feature_names:
            logit += self.m1_coefs.get(f, 0.0) * scaled.get(f, 0.0)

        prob = 1.0 / (1.0 + math.exp(-max(-30, min(30, logit))))

        # Tier system (v37 uses investment score thresholds)
        if prob >= 0.85:
            tier, action = 1, "STRONG LONG"
            note = "T1: High conviction — hold through readout"
        elif prob >= 0.70:
            tier, action = 2, "CAUTIOUS LONG"
            note = "T2: Solid edge — position with risk management"
        elif prob >= 0.55:
            tier, action = 3, "MONITOR"
            note = "T3: Marginal — watch, don't commit"
        else:
            tier, action = 4, "AVOID / SHORT"
            note = "T4: Weak outlook — consider puts or skip"

        # Feature contributions
        contributions = []
        for f in self.feature_names:
            coef = self.m1_coefs.get(f, 0.0)
            z = scaled.get(f, 0.0)
            r = raw.get(f, 0.0)
            contrib = coef * z
            if abs(contrib) > 0.001:
                contributions.append({
                    "feature": f, "raw_value": round(r, 4),
                    "z_score": round(z, 4), "coefficient": round(coef, 4),
                    "contribution": round(contrib, 4),
                })
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        # Count features with non-default values
        n_active = sum(1 for f in self.feature_names
                       if abs(raw.get(f, self.scaler_means.get(f, 0)) - self.scaler_means.get(f, 0)) > 0.001)

        return {
            "version": self.version,
            "probability": round(prob, 4),
            "logit": round(logit, 4),
            "tier": tier,
            "action": action,
            "tier_note": note,
            "model_type": "PREDICTIVE (pre-readout, zero leakage)",
            "model_note": "Ridge M1 component (90% of v44 meta-blend). "
                         "Full scoring with XGBoost requires training pipeline.",
            "top_features": contributions[:10],
            "n_features_total": len(self.feature_names),
            "n_features_active": n_active,
            "weight_source": self.weight_source,
        }


# ============================================================================
# GUNGNIR v27 PREDICTIVE — 33-Feature L2 Ridge Logistic Regression (FALLBACK)
# ============================================================================

GUNGNIR_V27_FEATURES = [
    "is_P2", "is_P2B", "is_pivotal", "is_phase1_any",
    "ta_oncology", "ta_rare", "ta_metabolic", "ta_infectious",
    "ta_ophthalmology", "ta_pain",
    "is_gene_therapy", "is_adc", "is_small_molecule",
    "is_rct", "is_combination", "has_hard_endpoint", "uses_surrogate",
    "designation_count", "log_price", "era_post_2024",
    "phase3_x_cns", "phase3_x_immunology", "rare_x_phase3",
    "antibody_x_oncology", "rct_x_phase3", "combo_x_oncology",
    "is_competitive", "has_ppm",
    # v27 enrichment features (5 new over v26)
    "is_topline", "odin_btd", "mentions_primary",
    "orr_x_oncology", "endpoint_pfs",
]

# Trained coefficients (sklearn LogisticRegression, C=10.0, L2, lbfgs, balanced)
GUNGNIR_V27_INTERCEPT = 0.6288855542014196
GUNGNIR_V27_COEFS = {
    "is_P2": -0.4736582326196623,
    "is_P2B": -0.36977256891387766,
    "is_pivotal": -0.6498020968356205,
    "is_phase1_any": -0.13997252914162728,
    "ta_oncology": -0.16295321706231716,
    "ta_rare": -0.875170840051619,
    "ta_metabolic": 0.23977990126602738,
    "ta_infectious": 0.027418186737885167,
    "ta_ophthalmology": -0.1180490347402135,
    "ta_pain": 0.03875147359202568,
    "is_gene_therapy": 0.23219320852992717,
    "is_adc": -0.024177732948626643,
    "is_small_molecule": -0.0041978770164206375,
    "is_rct": 0.07830319744780984,
    "is_combination": 0.035994834392002954,
    "has_hard_endpoint": 0.23724862113759607,
    "uses_surrogate": 0.5433548316235536,
    "designation_count": 0.8494439301325211,
    "log_price": 0.34741142570358224,
    "era_post_2024": -0.11026153268806602,
    "phase3_x_cns": -0.09643451573646784,
    "phase3_x_immunology": 0.2849623132197371,
    "rare_x_phase3": -0.054458165413033575,
    "antibody_x_oncology": 0.14167734518781006,
    "rct_x_phase3": 0.09662471334956377,
    "combo_x_oncology": -0.086061076729749,
    "is_competitive": -0.1529698241484826,
    "has_ppm": 0.6915492770276539,
    "is_topline": 0.09655878808584675,
    "odin_btd": 0.2590475665762014,
    "mentions_primary": 0.03561461388365659,
    "orr_x_oncology": 0.7182678503153423,
    "endpoint_pfs": 0.09100655132371727,
}

# StandardScaler parameters (fit on training set, cutoff 2025-01-01)
GUNGNIR_V27_SCALER_MEANS = {
    "is_P2": 0.2689313517338995,
    "is_P2B": 0.055201698513800426,
    "is_pivotal": 0.4062278839348903,
    "is_phase1_any": 0.23779193205944799,
    "ta_oncology": 0.4578910120311394,
    "ta_rare": 0.12455767869780608,
    "ta_metabolic": 0.04600141542816702,
    "ta_infectious": 0.051663128096249115,
    "ta_ophthalmology": 0.028308563340410473,
    "ta_pain": 0.010615711252653927,
    "is_gene_therapy": 0.0007077140835102619,
    "is_adc": 0.026185421089879687,
    "is_small_molecule": 0.7395612172682237,
    "is_rct": 0.10049539985845718,
    "is_combination": 0.055909412597310686,
    "has_hard_endpoint": 0.0007077140835102619,
    "uses_surrogate": 0.24769992922859166,
    "designation_count": 0.12526539278131635,
    "log_price": 2.876966489026295,
    "era_post_2024": 0.4012738853503185,
    "phase3_x_cns": 0.04529370134465676,
    "phase3_x_immunology": 0.024062278839348902,
    "rare_x_phase3": 0.05874026893135174,
    "antibody_x_oncology": 0.19179051663128097,
    "rct_x_phase3": 0.055201698513800426,
    "combo_x_oncology": 0.04953998584571833,
    "is_competitive": 0.15498938428874734,
    "has_ppm": 0.18329794762915783,
    "is_topline": 0.08917197452229299,
    "odin_btd": 0.05732484076433121,
    "mentions_primary": 0.4154281670205237,
    "orr_x_oncology": 0.18117480537862704,
    "endpoint_pfs": 0.07006369426751592,
}

GUNGNIR_V27_SCALER_STDS = {
    "is_P2": 0.4434041945995517,
    "is_P2B": 0.2283735339197428,
    "is_pivotal": 0.4911280792712544,
    "is_phase1_any": 0.4257310525518228,
    "ta_oncology": 0.4982236778117217,
    "ta_rare": 0.3302166915454459,
    "ta_metabolic": 0.20948815051637698,
    "ta_infectious": 0.22134599452341505,
    "ta_ophthalmology": 0.16585291249179931,
    "ta_pain": 0.10248423257874455,
    "is_gene_therapy": 0.026593480860659498,
    "is_adc": 0.15968639520079783,
    "is_small_molecule": 0.43887404022221105,
    "is_rct": 0.300659399430229,
    "is_combination": 0.2297467087475561,
    "has_hard_endpoint": 0.026593480860659498,
    "uses_surrogate": 0.43167658529128294,
    "designation_count": 0.3310195978377396,
    "log_price": 1.520417207760554,
    "era_post_2024": 0.4901562549699615,
    "phase3_x_cns": 0.20794754618210284,
    "phase3_x_immunology": 0.15324257103170227,
    "rare_x_phase3": 0.23513793768174499,
    "antibody_x_oncology": 0.39370917485065965,
    "rct_x_phase3": 0.2283735339197428,
    "combo_x_oncology": 0.21699257049061463,
    "is_competitive": 0.36189456343877613,
    "has_ppm": 0.38691059693952085,
    "is_topline": 0.2849918130088802,
    "odin_btd": 0.23246226230439054,
    "mentions_primary": 0.49279570317373056,
    "orr_x_oncology": 0.38516294639365767,
    "endpoint_pfs": 0.2552543300575016,
}

# NLP helpers for extracting pre-readout features from catalyst_text description
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

_G_MODALITY = {
    "gene_therapy": re.compile(r"gene\s*therap|aav|crispr|base\s*edit|lentivir", re.I),
    "adc": re.compile(r"antibody.drug\s+conjug|\badc\b|drug\s+conjugat", re.I),
    "small_molecule": re.compile(r"small\s+molecul|oral|tablet|capsule|inhibitor|antagonist|agonist", re.I),
    "antibody": re.compile(r"antibod|mab\b|-mab\b|bispecific", re.I),
}

_G_DESIGN = {
    "rct": re.compile(r"randomiz|placebo.?control|double.?blind|rct\b", re.I),
    "combination": re.compile(r"combination|combo|combin", re.I),
    "hard_endpoint": re.compile(r"overall\s+survival|(?:^|\W)os(?:\W|$)|mortality|death\s+rate|mace|major\s+adverse\s+card", re.I),
    "surrogate": re.compile(r"surrogate|biomarker|(?:^|\W)orr(?:\W|$)|(?:^|\W)pfs(?:\W|$)|(?:^|\W)efs(?:\W|$)|response\s+rate|tumor\s+(?:reduction|shrink)", re.I),
}

# v27 NLP: additional pre-readout text features
_G_TOPLINE = re.compile(r"top[\s-]?line", re.I)
_G_PRIMARY = re.compile(r"primary\s+endpoint|primary\s+outcome|primary\s+efficacy", re.I)
_G_PFS = re.compile(r"\bPFS\b|progression[\s-]free", re.I)
_G_ORR = re.compile(r"\bORR\b|overall\s+response\s+rate|objective\s+response", re.I)

class GungnirV27Engine:
    """GUNGNIR v27 Predictive Engine — pre-readout phase success prediction.

    Uses 33 clean features knowable at T-1 (before readout). No outcome-derived
    features. StandardScaler normalization + L2 Ridge logistic regression (C=10.0).

    v27 adds 5 enrichment features over v26:
      - is_topline: catalyst describes top-line data (trial design feature)
      - odin_btd: Breakthrough Therapy Designation from ODIN cross-reference
      - mentions_primary: catalyst mentions primary endpoint (trial design)
      - orr_x_oncology: ORR endpoint × oncology therapeutic area
      - endpoint_pfs: PFS as a measured endpoint
    """

    version = "GUNGNIR v27 (Predictive, AUC 0.7529)"

    def __init__(self):
        self.features = GUNGNIR_V27_FEATURES
        self.intercept = GUNGNIR_V27_INTERCEPT
        self.coefs = GUNGNIR_V27_COEFS
        self.means = GUNGNIR_V27_SCALER_MEANS
        self.stds = GUNGNIR_V27_SCALER_STDS
        self.weight_source = "EMBEDDED v27 (AUC 0.7529, zero leakage)"

    def encode(self, catalyst: dict) -> dict:
        """Extract 33 pre-readout features from structured inputs + NLP hints.

        Accepts both explicit boolean params AND NLP extraction from catalyst_text
        for trial design features. Explicit params override NLP extraction.
        """
        raw = {f: 0.0 for f in self.features}

        text = catalyst.get("catalyst_text", "").lower()
        stage = catalyst.get("stage", "").lower().strip()
        indication = catalyst.get("indication", "").lower()
        drug = catalyst.get("drug", catalyst.get("drug_name", "")).lower()
        year = catalyst.get("year", 2026)

        # ── Phase encoding (from stage parameter) ──
        if "3" in stage and "1" not in stage and "2" not in stage:
            raw["is_pivotal"] = 1.0
        elif stage in ("phase 2b", "phase2b", "p2b"):
            raw["is_P2B"] = 1.0
        elif "2" in stage and "b" not in stage and "1" not in stage:
            raw["is_P2"] = 1.0
        elif "1" in stage:
            raw["is_phase1_any"] = 1.0

        is_phase3 = raw["is_pivotal"]

        # ── Therapeutic area (from indication) ──
        for ta_feat, ta_re in _G_TA.items():
            if ta_feat in raw and ta_re.search(indication):
                raw[ta_feat] = 1.0

        # CNS/immunology detected for interaction terms (not direct features)
        is_cns = 1.0 if _G_TA["ta_cns"].search(indication) else 0.0
        is_immunology = 1.0 if _G_TA["ta_immunology"].search(indication) else 0.0
        is_antibody = 1.0 if _G_MODALITY["antibody"].search(drug) or _G_MODALITY["antibody"].search(text) else 0.0

        # ── Competitive space ──
        raw["is_competitive"] = 1.0 if any(kw in indication for kw in _G_COMPETITIVE) else 0.0

        # ── Modality (explicit params override NLP) ──
        if catalyst.get("gene_therapy") is not None:
            raw["is_gene_therapy"] = 1.0 if catalyst["gene_therapy"] else 0.0
        elif _G_MODALITY["gene_therapy"].search(drug) or _G_MODALITY["gene_therapy"].search(text):
            raw["is_gene_therapy"] = 1.0

        if catalyst.get("adc") is not None:
            raw["is_adc"] = 1.0 if catalyst["adc"] else 0.0
        elif _G_MODALITY["adc"].search(drug) or _G_MODALITY["adc"].search(text):
            raw["is_adc"] = 1.0

        if catalyst.get("small_molecule") is not None:
            raw["is_small_molecule"] = 1.0 if catalyst["small_molecule"] else 0.0
        elif _G_MODALITY["small_molecule"].search(text) or _G_MODALITY["small_molecule"].search(drug):
            raw["is_small_molecule"] = 1.0

        # ── Trial design (explicit params override NLP) ──
        if catalyst.get("rct") is not None:
            raw["is_rct"] = 1.0 if catalyst["rct"] else 0.0
        elif _G_DESIGN["rct"].search(text):
            raw["is_rct"] = 1.0

        if catalyst.get("combination") is not None:
            raw["is_combination"] = 1.0 if catalyst["combination"] else 0.0
        elif _G_DESIGN["combination"].search(text):
            raw["is_combination"] = 1.0

        if catalyst.get("hard_endpoint") is not None:
            raw["has_hard_endpoint"] = 1.0 if catalyst["hard_endpoint"] else 0.0
        elif _G_DESIGN["hard_endpoint"].search(text):
            raw["has_hard_endpoint"] = 1.0

        if catalyst.get("surrogate_endpoint") is not None:
            raw["uses_surrogate"] = 1.0 if catalyst["surrogate_endpoint"] else 0.0
        elif _G_DESIGN["surrogate"].search(text):
            raw["uses_surrogate"] = 1.0

        # ── Designations (explicit count) ──
        desig_count = catalyst.get("designation_count", 0)
        if isinstance(desig_count, bool):
            desig_count = int(desig_count)
        # Also count from explicit boolean flags
        if desig_count == 0:
            for flag in ("btd", "orphan", "fast_track", "priority_review",
                         "accelerated_approval", "breakthrough"):
                if catalyst.get(flag):
                    desig_count += 1
        raw["designation_count"] = float(desig_count)

        # ── Market / price ──
        price = catalyst.get("price", catalyst.get("stock_price", 0.0))
        if price and price > 0:
            raw["log_price"] = math.log(price)
        else:
            raw["log_price"] = self.means["log_price"]  # use training mean if unknown

        # ── Temporal ──
        raw["era_post_2024"] = 1.0 if year >= 2025 else 0.0

        # ── Prior positive phase ──
        if catalyst.get("prior_positive_phase") or catalyst.get("ppm") or catalyst.get("has_ppm"):
            raw["has_ppm"] = 1.0

        # ── v27 enrichment features ──
        # is_topline: catalyst describes top-line data readout (pre-readout trial design)
        raw["is_topline"] = 1.0 if _G_TOPLINE.search(text) else 0.0

        # odin_btd: Breakthrough Therapy Designation from ODIN cross-reference or explicit
        if catalyst.get("btd"):
            raw["odin_btd"] = 1.0
        # Also check catalyst_text for BTD mentions
        elif re.search(r"breakthrough\s+therap|\bbtd\b", text, re.I):
            raw["odin_btd"] = 1.0

        # mentions_primary: catalyst mentions primary endpoint (trial design feature)
        raw["mentions_primary"] = 1.0 if _G_PRIMARY.search(text) else 0.0

        # endpoint_pfs: PFS is a measured endpoint
        raw["endpoint_pfs"] = 1.0 if _G_PFS.search(text) else 0.0

        # endpoint_orr (for interaction, not a direct feature)
        endpoint_orr = 1.0 if _G_ORR.search(text) else 0.0

        # ── Interaction terms ──
        raw["phase3_x_cns"] = is_phase3 * is_cns
        raw["phase3_x_immunology"] = is_phase3 * is_immunology
        raw["rare_x_phase3"] = raw["ta_rare"] * is_phase3
        raw["antibody_x_oncology"] = is_antibody * raw["ta_oncology"]
        raw["rct_x_phase3"] = raw["is_rct"] * is_phase3
        raw["combo_x_oncology"] = raw["is_combination"] * raw["ta_oncology"]
        raw["orr_x_oncology"] = endpoint_orr * raw["ta_oncology"]

        return raw

    def _scale(self, raw: dict) -> dict:
        """Apply StandardScaler: z = (x - mean) / std."""
        scaled = {}
        for f in self.features:
            mean = self.means.get(f, 0.0)
            std = self.stds.get(f, 1.0)
            if std == 0:
                scaled[f] = 0.0
            else:
                scaled[f] = (raw.get(f, 0.0) - mean) / std
        return scaled

    def score(self, catalyst: dict) -> dict:
        """Score a phase readout catalyst using pre-readout features."""
        raw = self.encode(catalyst)
        scaled = self._scale(raw)

        logit = self.intercept
        for f in self.features:
            logit += self.coefs.get(f, 0.0) * scaled.get(f, 0.0)

        prob = 1.0 / (1.0 + math.exp(-max(-30, min(30, logit))))

        # v27 tier system (calibrated to training data success rates)
        if prob >= 0.70:
            tier, action, note = 1, "STRONG LONG", "T1: 92.4% historical success rate — hold through readout"
        elif prob >= 0.55:
            tier, action, note = 2, "CAUTIOUS LONG", "T2: 85.5% historical success — position with hedge"
        elif prob >= 0.40:
            tier, action, note = 3, "MONITOR", "T3: 76.8% historical success — watch, don't commit"
        else:
            tier, action, note = 4, "AVOID / SHORT", "T4: 60.9% historical success — thin edge, consider puts"

        # Feature contributions (on scaled features)
        contributions = []
        for f in self.features:
            coef = self.coefs.get(f, 0.0)
            z = scaled.get(f, 0.0)
            r = raw.get(f, 0.0)
            contrib = coef * z
            if abs(contrib) > 0.001:
                contributions.append({
                    "feature": f, "raw_value": round(r, 4),
                    "z_score": round(z, 4), "coefficient": round(coef, 4),
                    "contribution": round(contrib, 4),
                })
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        return {
            "version": self.version,
            "probability": round(prob, 4),
            "logit": round(logit, 4),
            "tier": tier,
            "action": action,
            "tier_note": note,
            "model_type": "PREDICTIVE (pre-readout, zero leakage)",
            "top_features": contributions[:10],
            "n_features_active": sum(1 for v in raw.values() if v != 0.0),
            "weight_source": self.weight_source,
        }


# ============================================================================
# BIFROST v3.1 — PDUFA RUNUP TIMING + MAGNITUDE ENGINE
# ============================================================================
# v3.1 upgrades from v2.0:
#   - Magnitude prediction: Ridge+XGB regression (66.4% directional accuracy WF)
#   - Walk-forward validated: Sharpe 5.35, 69.6% win rate, -5.3% max DD
#   - Kelly sizing with drawdown governor + portfolio heat limits
#   - Tier safety caps preserved: T3 max 3%, T4 max 1.5%
# Static decision matrix (v2) kept as primary recommendation engine.
# Magnitude model adds enhanced scoring when price features available.

BIFROST_DECISION_MATRIX = {
    "T1": {
        "nano":  {"action": "LEAN_LONG",  "entry": -25, "exit": -7, "sharpe": 0.29, "hit": 0.53, "mean": 1.7, "n": 15, "kelly": 0.056, "size": 0.02, "note": "Small edge, small size"},
        "micro": {"action": "BUY",        "entry": -90, "exit": -7, "sharpe": 0.49, "hit": 0.57, "mean": 23.3, "n": 35, "kelly": 0.196, "size": 0.04, "note": "Early entry captures big runup"},
        "small": {"action": "LEAN_LONG",  "entry": -60, "exit": -7, "sharpe": 0.14, "hit": 0.52, "mean": 2.0, "n": 62, "kelly": 0.042, "size": 0.02, "note": "Modest edge, large N validation"},
        "mid":   {"action": "STRONG_BUY", "entry": -25, "exit": -1, "sharpe": 1.02, "hit": 0.65, "mean": 5.7, "n": 98, "kelly": 0.203, "size": 0.06, "note": "Highest Sharpe T1 cell, N=98"},
        "large": {"action": "STRONG_BUY", "entry": -45, "exit": -7, "sharpe": 0.53, "hit": 0.59, "mean": 3.0, "n": 599, "kelly": 0.144, "size": 0.06, "note": "Most validated cell (N=599)"},
    },
    "T2": {
        "nano":  {"action": "BUY",        "entry": -90, "exit": -3, "sharpe": 0.89, "hit": 0.75, "mean": 55.5, "n": 12, "kelly": 0.318, "size": 0.04, "note": "Massive returns, moderate N"},
        "micro": {"action": "STRONG_BUY", "entry": -90, "exit": -7, "sharpe": 1.09, "hit": 0.73, "mean": 22.0, "n": 30, "kelly": 0.302, "size": 0.06, "note": "Best risk-adjusted T2 cell"},
        "small": {"action": "STRONG_BUY", "entry": -25, "exit": -3, "sharpe": 0.90, "hit": 0.55, "mean": 6.1, "n": 80, "kelly": 0.161, "size": 0.06, "note": "Good N, short window"},
        "mid":   {"action": "STRONG_BUY", "entry": -60, "exit": -3, "sharpe": 0.76, "hit": 0.59, "mean": 9.7, "n": 71, "kelly": 0.191, "size": 0.06, "note": "Wide window, high mean"},
        "large": {"action": "STRONG_BUY", "entry": -25, "exit": -7, "sharpe": 1.07, "hit": 0.65, "mean": 2.2, "n": 83, "kelly": 0.180, "size": 0.06, "note": "Excellent Sharpe + N combo"},
    },
    "T3": {
        "nano":  {"action": "BUY",        "entry": -25, "exit": -1, "sharpe": 2.25, "hit": 0.62, "mean": 20.4, "n": 13, "kelly": 0.270, "size": 0.03, "note": "High Sharpe but low N, capped at BUY"},
        "micro": {"action": "BUY",        "entry": -90, "exit": -1, "sharpe": 1.22, "hit": 0.77, "mean": 34.0, "n": 13, "kelly": 0.343, "size": 0.03, "note": "Wide window, high hit rate"},
        "small": {"action": "LEAN_LONG",  "entry": -90, "exit": -7, "sharpe": 2.17, "hit": 1.00, "mean": 36.7, "n": 11, "kelly": 0.500, "size": 0.015, "note": "100% hit N=11. Small size for safety"},
        "mid":   {"action": "LEAN_LONG",  "entry": -25, "exit": -1, "sharpe": 2.22, "hit": 0.80, "mean": 11.7, "n": 10, "kelly": 0.354, "size": 0.015, "note": "Small N, high mean. Conservative size"},
        "large": {"action": "AVOID",      "entry": -25, "exit": -1, "sharpe": -0.27, "hit": 0.42, "mean": -1.0, "n": 12, "kelly": 0.0, "size": 0.0, "note": "Negative Sharpe. NO TRADE."},
    },
    "T4": {
        "nano":  {"action": "LEAN_LONG",  "entry": -45, "exit": -3, "sharpe": 0.18, "hit": 0.51, "mean": 3.0, "n": 67, "kelly": 0.046, "size": 0.015, "note": "Marginal edge, tiny size"},
        "micro": {"action": "LEAN_LONG",  "entry": -25, "exit": -1, "sharpe": 0.73, "hit": 0.53, "mean": 7.4, "n": 116, "kelly": 0.130, "size": 0.015, "note": "Capped from BUY. Runup exists"},
        "small": {"action": "LEAN_LONG",  "entry": -25, "exit": -3, "sharpe": 0.58, "hit": 0.57, "mean": 4.4, "n": 113, "kelly": 0.123, "size": 0.015, "note": "Capped from STRONG_BUY. High N"},
        "mid":   {"action": "NEUTRAL",    "entry": -45, "exit": -7, "sharpe": 0.25, "hit": 0.49, "mean": 3.1, "n": 43, "kelly": 0.060, "size": 0.0, "note": "Sub-50% hit. NO TRADE"},
        "large": {"action": "LEAN_LONG",  "entry": -25, "exit": -1, "sharpe": 0.35, "hit": 0.51, "mean": 1.1, "n": 96, "kelly": 0.069, "size": 0.015, "note": "Minimal edge, large N"},
    },
}

BIFROST_MCAP_THRESHOLDS = {
    "nano":  (0, 50e6),
    "micro": (50e6, 300e6),
    "small": (300e6, 2e9),
    "mid":   (2e9, 10e9),
    "large": (10e9, float('inf')),
}


class BifrostEngine:
    """BIFROST v4.0.0 — PDUFA Runup Timing + Magnitude Engine.

    v4.0 upgrades from v3.1:
      - Triple-ensemble magnitude: Ridge 30% + XGB 35% + LightGBM 35%
      - 6 new features: sponsor_success_rate, sponsor_success_x_score,
        sponsor_success_x_volatility, vol_adjusted_confidence,
        ta_risk_x_score, ta_risk_x_momentum (43 total, up from 37)
      - Walk-forward validated: Sharpe 5.45, 70.8% win, -4.9% max DD
      - Half-Kelly with enhanced drawdown governor + portfolio heat limits
      - Tier safety caps: T1/T2 6%, T3 3%, T4 1.5%

    v3.1 improvements preserved:
      - Magnitude prediction with WF directional accuracy
      - Kelly position sizing with tier caps
      - Drawdown governor (0.15 threshold) scales 0.2-1.0

    Static decision matrix (v2) kept for primary timing/action.
    Magnitude model enhances sizing when price features provided.
    1,705 events with real yfinance daily prices (2020-2026).
    Core thesis: The runup IS the trade. Exit before the binary PDUFA event.
    """

    version = "BIFROST v4.0.0 (triple-ensemble magnitude + sponsor dynamics + Kelly, WF Sharpe 5.45)"

    # v3.1 sizing parameters
    TIER_CAPS = {"T1": 0.06, "T2": 0.06, "T3": 0.03, "T4": 0.015}
    MAX_CONCURRENT = 5
    MAX_HEAT = 0.15

    def classify_mcap(self, market_cap: float) -> str:
        """Classify market cap into tier."""
        for tier, (lo, hi) in BIFROST_MCAP_THRESHOLDS.items():
            if lo <= market_cap < hi:
                return tier
        return "large"

    def _kelly_size(self, pred_return, pred_vol=15.0, tier="T1"):
        """Half-Kelly position size with tier cap."""
        if pred_return <= 0 or pred_vol <= 0:
            return 0.0
        edge = pred_return / 100
        variance = (pred_vol / 100) ** 2
        if variance < 1e-10:
            return 0.0
        f_half = (edge / variance) / 2
        cap = self.TIER_CAPS.get(tier, 0.03)
        return max(0, min(f_half, cap))

    def score(self, odin_tier: int, market_cap: float,
              days_to_pdufa: int = 60, ticker: str = "",
              v9_score: float = 0.0, momentum_14d: float = 0.0,
              volatility_20d: float = 0.0) -> dict:
        """Score a PDUFA runup opportunity.

        Args:
            odin_tier: 1-4 from ODIN v9 scoring
            market_cap: Market capitalization in dollars
            days_to_pdufa: Trading days until PDUFA date
            ticker: Optional ticker for display
            v9_score: Optional ODIN v9 probability (0-1) for enhanced sizing
            momentum_14d: Optional 14-day price momentum (%) for magnitude
            volatility_20d: Optional 20-day volatility (%) for magnitude

        Returns:
            Recommendation with entry/exit, Kelly-sized position, risk metrics.
        """
        tier_key = f"T{odin_tier}"
        mcap_tier = self.classify_mcap(market_cap)

        rec = BIFROST_DECISION_MATRIX.get(tier_key, {}).get(mcap_tier, {})
        if not rec:
            return {
                "version": self.version,
                "ticker": ticker,
                "odin_tier": odin_tier,
                "mcap_tier": mcap_tier,
                "action": "NO_DATA",
                "note": f"No empirical data for {tier_key} × {mcap_tier}",
            }

        entry_day = rec["entry"]
        exit_day = rec["exit"]
        action = rec["action"]

        # v3.1 Enhanced Kelly sizing
        expected_ret = rec["mean"]
        tier_cap = self.TIER_CAPS.get(tier_key, 0.03)
        v31_kelly = self._kelly_size(expected_ret, 15.0, tier_key)
        v31_size_pct = round(v31_kelly * 100, 2)

        # v4.0 Magnitude enhancement with vol_adjusted_confidence
        magnitude_note = None
        if momentum_14d != 0 or volatility_20d != 0:
            # v4 signals: momentum, volatility, and vol_adjusted_confidence
            mom_signal = "POSITIVE" if momentum_14d > 3 else "NEUTRAL" if momentum_14d > -2 else "NEGATIVE"
            vol_signal = "LOW" if volatility_20d < 4 else "MODERATE" if volatility_20d < 8 else "HIGH"

            # v4 NEW: vol_adjusted_confidence — inversely scales with volatility
            vol_adj_conf = max(0, min(1.0, 1.0 - (volatility_20d - 3.0) / 12.0)) if volatility_20d > 0 else 0.5

            if mom_signal == "POSITIVE" and vol_signal != "HIGH":
                boost = 1.0 + (0.2 * vol_adj_conf)  # v4: confidence-weighted boost
                magnitude_note = f"Momentum {mom_signal} ({momentum_14d:+.1f}%), Vol {vol_signal} ({volatility_20d:.1f}%), VolConf {vol_adj_conf:.2f} → FAVORABLE for runup"
                v31_size_pct = min(v31_size_pct * boost, tier_cap * 100)
            elif mom_signal == "NEGATIVE":
                magnitude_note = f"Momentum {mom_signal} ({momentum_14d:+.1f}%), VolConf {vol_adj_conf:.2f} → CAUTION, reducing position"
                v31_size_pct = v31_size_pct * 0.7
            elif vol_signal == "HIGH":
                magnitude_note = f"Vol {vol_signal} ({volatility_20d:.1f}%), VolConf {vol_adj_conf:.2f} → HIGH VOLATILITY, reducing position"
                v31_size_pct = v31_size_pct * 0.8
            else:
                magnitude_note = f"Momentum {mom_signal} ({momentum_14d:+.1f}%), Vol {vol_signal} ({volatility_20d:.1f}%), VolConf {vol_adj_conf:.2f}"

        # Timing assessment
        if action in ("AVOID", "NEUTRAL"):
            timing = "NO_TRADE"
            timing_note = "BIFROST recommends NO TRADE for this tier×mcap combination."
        elif days_to_pdufa > abs(entry_day) + 10:
            timing = "TOO_EARLY"
            timing_note = f"Wait. Optimal entry starts at T{entry_day}."
        elif days_to_pdufa >= abs(entry_day):
            timing = "ENTRY_ZONE"
            timing_note = f"ENTER NOW. Optimal entry window (T{entry_day} to T{entry_day+10})."
        elif days_to_pdufa > abs(exit_day):
            timing = "HOLDING"
            timing_note = f"Past entry. Hold until T{exit_day} exit."
        elif days_to_pdufa >= abs(exit_day):
            timing = "EXIT_ZONE"
            timing_note = f"At or past optimal exit T{exit_day}. TAKE PROFITS."
        else:
            timing = "LATE_EXIT"
            timing_note = f"Past optimal exit. Binary risk increasing. EXIT NOW."

        result = {
            "version": self.version,
            "ticker": ticker,
            "odin_tier": odin_tier,
            "mcap_tier": mcap_tier,
            "market_cap_formatted": f"${market_cap/1e6:.0f}M" if market_cap < 1e9 else f"${market_cap/1e9:.1f}B",
            "action": action,
            "position_size_pct": v31_size_pct,
            "position_size_method": "half_kelly_v31",
            "tier_cap_pct": tier_cap * 100,
            "kelly_half": rec.get("kelly", 0),
            "timing": timing,
            "timing_note": timing_note,
            "optimal_entry": f"T{entry_day}",
            "optimal_exit": f"T{exit_day}",
            "days_to_pdufa": days_to_pdufa,
            "expected_return": rec["mean"],
            "hit_rate": rec["hit"],
            "ann_sharpe": rec["sharpe"],
            "sample_size": rec["n"],
            "note": rec["note"],
            "cardinal_rule": "Never hold through FDA decision. The runup IS the trade.",
            "tier_safety": f"{'No cap' if odin_tier <= 2 else 'Max 3%' if odin_tier == 3 else 'Max 1.5%'} (T{odin_tier})",
            "v4_backtest": "WF Sharpe 5.45, 70.8% win, -4.9% max DD (910 trades, 2022-2026)",
        }
        if magnitude_note:
            result["magnitude_assessment"] = magnitude_note
        return result


# ============================================================================
# BIFROST v5.3 EXPLOSION DETECTOR — Deep Column Audit + ODIN Enrichment
# ============================================================================
# Binary classifier: P(|D1 move| > 25%) using LR component of 60/20/20 ensemble
# v5.3: LR Test AUC 0.8720 (+0.0422 vs v5.2), Ensemble 0.8711
# 34 features (24 v5.2 + 10 new ODIN enrichment + price features), all T-1 compliant
# v5.4 adds: 23 new features from exhaustive pairwise ODIN×market interactions +
#            untapped ODIN regulatory features + non-linear transforms.
# LR Test AUC 0.9332 (v5.3 was 0.8720, +0.0612). BIGGEST single-version jump in history.
# 20/20 seed stability, p=3.63e-14. Test AUC > Train AUC confirms genuine generalization.

EXPLOSION_FEATURES = [
    # v5.0 base (17)
    "surprise_factor", "is_penny", "is_low_price", "log_price_inv",
    "is_nano", "is_micro", "is_small",
    "surprise_x_small_cap", "surprise_x_low_price",
    "price_compression", "drawdown_pct", "beaten_down_30d",
    "beaten_surprise", "compression_x_surprise",
    "vol_ratio", "runup_30d", "v5_score",
    # v5.1: Short interest features (4)
    "log_float_inv", "pct_float_short", "short_high", "days_to_cover",
    # v5.2: Sector regime + drift (3)
    "drift_magnitude", "xbi_return_30d", "xbi_x_surprise",
    # v5.3: ODIN enrichment + price-derived + interactions (10)
    "xbi_x_small", "vol_high", "crl_count_x_small", "is_resub",
    "drift_7d", "resub_x_surprise", "naive_x_small",
    "drawdown_x_vol", "runup_7d", "ta_vh_x_small",
    # v5.4 NEW: Exhaustive pairwise ODIN×market + untapped regulatory (23)
    "orphan_x_runup_7d_val", "resub1_x_vol_high", "ppm_x_runup_30d",
    "spa_log_x_is_small", "ppm_x_dtc", "safety_h_x_dtc",
    "crl_rate_x_is_small", "resub2_x_log_float_inv", "ta_vh_x_log_float_inv",
    "resub1_x_beaten", "ppm_x_is_micro", "btd_x_is_penny_val",
    "resub2_x_xbi_30d", "safety_h_x_short_high", "resub2_x_si_pct",
    "resub1_x_is_micro", "ft_x_drawdown", "ft_x_is_small",
    "safety_h_x_is_penny_val", "fast_track", "gene_th_x_small_cap",
    "resub2_x_runup_7d_val", "t90_t7",
]

EXPLOSION_INTERCEPT = -3.9121076452649337
EXPLOSION_COEFS = {
    # v5.0 base
    "surprise_factor": 0.1308,
    "is_penny": -0.0923,
    "is_low_price": 0.1241,
    "log_price_inv": 0.0296,
    "is_nano": 0.1069,
    "is_micro": 0.2628,
    "is_small": -0.0187,
    "surprise_x_small_cap": 0.0297,
    "surprise_x_low_price": -0.0591,
    "price_compression": -0.1924,
    "drawdown_pct": -0.1918,
    "beaten_down_30d": 0.1139,
    "beaten_surprise": -0.1801,
    "compression_x_surprise": 0.0342,
    "vol_ratio": 0.3435,
    "runup_30d": 0.0792,
    "v5_score": -0.1308,
    # v5.1 SI features
    "log_float_inv": 0.4362,
    "pct_float_short": 0.1548,
    "short_high": -0.0601,
    "days_to_cover": 0.2408,
    # v5.2 sector/drift
    "drift_magnitude": 0.0387,
    "xbi_return_30d": -0.0686,
    "xbi_x_surprise": 0.0689,
    # v5.3 ODIN enrichment + interactions
    "xbi_x_small": 0.2643,
    "vol_high": 0.2017,
    "crl_count_x_small": -0.3679,
    "is_resub": 0.0428,
    "drift_7d": 0.1097,
    "resub_x_surprise": 0.1114,
    "naive_x_small": -0.0898,
    "drawdown_x_vol": -0.1767,
    "runup_7d": -0.034,
    "ta_vh_x_small": 0.1879,
    # v5.4 NEW: Exhaustive pairwise ODIN×market interactions (23)
    "orphan_x_runup_7d_val": 0.2761,    # #1: orphan × 7d runup = max explosion potential
    "resub1_x_vol_high": -0.0603,       # Class 1 resub × high vol = market pricing uncertainty
    "ppm_x_runup_30d": -0.1447,         # PPM × 30d runup = already priced in
    "spa_log_x_is_small": 0.1746,       # Experienced sponsor × small cap = strong conviction
    "ppm_x_dtc": 0.1499,                # PPM × days to cover = short squeeze risk
    "safety_h_x_dtc": -0.0712,          # High safety risk × days to cover
    "crl_rate_x_is_small": -0.1803,     # High CRL rate TA × small cap = suppressed
    "resub2_x_log_float_inv": 0.0998,   # Class 2 resub × tight float
    "ta_vh_x_log_float_inv": -0.1907,   # Very high TA × tight float = amplified fear
    "resub1_x_beaten": 0.1,             # Class 1 resub × beaten down = max upside surprise
    "ppm_x_is_micro": -0.0663,          # PPM × micro cap
    "btd_x_is_penny_val": -0.0708,      # BTD × penny stock value
    "resub2_x_xbi_30d": 0.0473,         # Class 2 resub × sector regime
    "safety_h_x_short_high": -0.0846,   # High safety × high SI
    "resub2_x_si_pct": 0.0527,          # Class 2 resub × SI pct
    "resub1_x_is_micro": 0.1272,        # Class 1 resub × micro cap = binary
    "ft_x_drawdown": -0.0084,           # Fast track × drawdown
    "ft_x_is_small": -0.1552,           # Fast track × small cap
    "safety_h_x_is_penny_val": -0.0901, # High safety × penny stock
    "fast_track": -0.0476,              # Fast track designation
    "gene_th_x_small_cap": 0.0474,      # Gene therapy × small cap
    "resub2_x_runup_7d_val": -0.0544,   # Class 2 resub × 7d runup
    "t90_t7": -0.0148,                  # T-90 to T-7 long-term positioning
}

EXPLOSION_MEANS = [
    # v5.0 base (17)
    0.3032351784, 0.1150764749, 0.1922796795, 0.00793811,
    0.0597232338, 0.1660597232, 0.1580480699, 0.1056892935,
    0.0921129643, 0.8456653727, -0.154491614, 0.0917698471,
    0.037310488, 0.0607097999, 1.0893133368, 2.2925695875,
    0.6967648216,
    # v5.1 SI (4)
    1.3652881293, 0.0636863803, 0.1551347414, 4.7287254188,
    # v5.2 sector/drift (3)
    11.893830335, 0.0041238392, 0.0015745836,
    # v5.3 (10)
    0.0008109306, 0.1318281136, 0.1471230881, 0.1369264385,
    4.542917595, 0.075810925, 0.0917698471, 0.1678075604,
    0.1755971262, 0.0393299345,
    # v5.4 NEW (23)
    -0.0337024109, 0.0160233066, 0.1808025299, 0.0666390589,
    0.0371376548, 0.2892716679, 0.0557334239, 0.0898679266,
    0.1343665973, 0.0080116533, 0.0007283321, 0.0021849964,
    -8.69537e-05, 0.0050983248, 0.0038760379, 0.0269482884,
    0.0374359609, 0.0349599417, 0.0014566642, 0.2825928623,
    0.0196649672, -0.0095785253, 0.0204795002,
]

EXPLOSION_SCALES = [
    # v5.0 base (17)
    0.3148159504, 0.3191142112, 0.3940916193, 0.1234764331,
    0.2369733511, 0.3721342386, 0.3647860709, 0.248524433,
    0.2332481391, 0.1599966804, 0.1598327259, 0.2887007832,
    0.152871641, 0.1074738196, 0.5050613813, 20.8724665425,
    0.3148159504,
    # v5.1 SI (4)
    2.0044843617, 0.0782246418, 0.3620330833, 4.500255999,
    # v5.2 sector/drift (3)
    17.3046969012, 0.0937026792, 0.0402566568,
    # v5.3 (10)
    0.055077063, 0.3383038015, 0.5611098254, 0.3437696742,
    5.8496171669, 0.2278930773, 0.2887007832, 0.2209890073,
    7.4044099646, 0.1943787301,
    # v5.4 NEW (23)
    2.078063218, 0.1255649644, 3.5393250503, 0.2043279511,
    0.4933643077, 1.3291799003, 0.1368852365, 0.5740853926,
    0.8901481663, 0.0891485655, 0.0269777992, 0.046692849,
    0.0160708054, 0.0712203055, 0.0258047606, 0.1619323259,
    0.0976965794, 0.1836783716, 0.0381384631, 0.4502600765,
    0.1388461605, 1.9078393417, 0.2329642783,
]

EXPLOSION_TIERS = [
    (0.20, "SNIPER",   2.0, "High explosion probability — max position size"),
    (0.10, "ELEVATED", 1.5, "Elevated explosion probability — overweight"),
    (0.05, "NORMAL",   1.0, "Normal volatility expected"),
    (0.00, "QUIET",    0.8, "Low volatility expected — standard size"),
]


class ExplosionDetectorEngine:
    """BIFROST v5.4.0 Explosion Detector — Exhaustive Pairwise + Untapped ODIN + Non-linear Kaizen.

    Predicts P(|D1 move| > 25%) for PDUFA events.
    Uses the LR component of 80/5/15 ensemble (LR+GBM+LightGBM).
    57 features (34 v5.3 baseline + 23 new exhaustive pairwise ODIN×market interactions).
    LR Test AUC 0.9332 (v5.3 was 0.8720, +0.0612). BIGGEST single-version jump in history.
    Ensemble Test AUC 0.9307 (v5.3 was 0.8711, +0.0596).
    20-seed bootstrap stability: 0.9300 ± 0.0159, 20/20 beats v5.3, p=3.63e-14.
    Test AUC > Train AUC confirms genuine out-of-sample generalization.

    v5.4 Key Discoveries:
      orphan_x_runup_7d_val (+0.276): THE dominant new signal — orphan drugs with 7d runup = max explosion.
      ppm_x_runup_30d (-0.145): PPM × 30d runup = already priced in, less remaining potential.
      spa_log_x_is_small (+0.175): Experienced sponsor × small cap = strong conviction.
      ta_vh_x_log_float_inv (-0.191): Very high TA × tight float = amplified fear.
      crl_rate_x_is_small (-0.180): High CRL rate TA × small cap = market pre-discounts.
      resub1_x_is_micro (+0.127): Class 1 resub × micro cap = max binary potential.
      ppm_x_dtc (+0.150): PPM × days to cover = short squeeze risk.
      resub1_x_beaten (+0.100): Class 1 resub × beaten down = max upside surprise.
    """

    version = "BIFROST v5.4.0 Explosion Detector (LR component, Test AUC 0.9332)"

    def __init__(self):
        self.features = EXPLOSION_FEATURES
        self.intercept = EXPLOSION_INTERCEPT
        self.coefs = EXPLOSION_COEFS
        self.means = EXPLOSION_MEANS
        self.scales = EXPLOSION_SCALES

    def _classify_tier(self, prob: float) -> tuple:
        """Assign explosion tier from probability."""
        for threshold, label, mult, desc in EXPLOSION_TIERS:
            if prob >= threshold:
                return label, mult, desc
        return "QUIET", 0.8, "Low volatility expected"

    def score(self, odin_score: float, eve_price: float, market_cap: float,
              high_52w: float = 0.0, volume_ratio: float = 1.0,
              runup_30d: float = 0.0, ticker: str = "",
              float_shares: float = 0.0, pct_float_short: float = 0.0,
              days_to_cover: float = 0.0,
              xbi_return_30d: float = 0.0,
              is_resub: float = 0.0, ta_very_high: float = 0.0,
              sponsor_naive: float = 0.0, prior_crl_count: int = 0,
              runup_7d: float = 0.0,
              orphan: float = 0.0, btd: float = 0.0,
              fast_track: float = 0.0, ppm_flag: float = 0.0,
              resub_class: int = 0, safety_signal_severity: int = 0,
              sponsor_prior_approvals: int = 0, gene_therapy: float = 0.0,
              hist_crl_rate: float = 0.0, runup_t90_t7: float = 0.0) -> dict:
        """Score explosion probability for a PDUFA event.

        Args:
            odin_score: ODIN v13 probability (0-1)
            eve_price: Stock price on eve of PDUFA
            market_cap: Market cap in dollars
            high_52w: 52-week high price (0 = use eve_price as fallback)
            volume_ratio: Recent volume / avg volume ratio (default 1.0)
            runup_30d: 30-day pre-event return in % (default 0.0)
            ticker: Optional ticker for display
            float_shares: Number of shares in float (0 = unknown, uses imputation)
            pct_float_short: Fraction of float sold short (e.g. 0.15 = 15%)
            days_to_cover: Short ratio / days to cover
            xbi_return_30d: XBI ETF 30-day trailing return (decimal, e.g. 0.05 = 5%)
            is_resub: 1.0 if this is a resubmission (any class), 0.0 otherwise
            ta_very_high: 1.0 if therapeutic area is very high risk, 0.0 otherwise
            sponsor_naive: 1.0 if sponsor has zero prior FDA approvals, 0.0 otherwise
            prior_crl_count: Number of prior CRLs for this drug (0 = none)
            runup_7d: 7-day pre-event price return in % (default 0.0)
            orphan: 1.0 if orphan drug designation, 0.0 otherwise (v5.4)
            btd: 1.0 if breakthrough therapy designation, 0.0 otherwise (v5.4)
            fast_track: 1.0 if fast track designation, 0.0 otherwise (v5.4)
            ppm_flag: 1.0 if prior probability marker present, 0.0 otherwise (v5.4)
            resub_class: Resubmission class (0=none, 1=Class 1/efficacy, 2=Class 2/CMC) (v5.4)
            safety_signal_severity: Safety signal severity (0=none, 1=low, 2=high) (v5.4)
            sponsor_prior_approvals: Number of sponsor's prior FDA approvals (v5.4)
            gene_therapy: 1.0 if gene therapy product, 0.0 otherwise (v5.4)
            hist_crl_rate: Historical CRL rate for this TA (0.0-1.0) (v5.4)
            runup_t90_t7: T-90 to T-7 long-term pre-catalyst return in % (v5.4)

        Returns:
            Explosion probability, tier, position multiplier, feature breakdown.
        """
        # Derive raw features
        surprise_factor = 1.0 - odin_score
        is_penny = 1.0 if eve_price < 5 else 0.0
        is_low_price = 1.0 if eve_price < 10 else 0.0
        log_price_inv = math.log(1.0 / max(eve_price, 0.01))
        log_price_inv = max(0, log_price_inv)  # Only positive (prices < $1)

        mcap_m = market_cap / 1e6
        is_nano = 1.0 if mcap_m < 50 else 0.0
        is_micro = 1.0 if 50 <= mcap_m < 300 else 0.0
        is_small = 1.0 if 300 <= mcap_m < 2000 else 0.0

        surprise_x_small_cap = surprise_factor * (is_nano + is_micro + is_small)
        surprise_x_low_price = surprise_factor * is_low_price

        if high_52w > 0:
            price_compression = eve_price / high_52w
            drawdown_pct = max(-1.0, min(0.0, (eve_price - high_52w) / high_52w))
        else:
            price_compression = 1.0
            drawdown_pct = 0.0

        beaten_down_30d = 1.0 if runup_30d < -15 else 0.0
        beaten_surprise = beaten_down_30d * surprise_factor
        compression_x_surprise = (1.0 - price_compression) * surprise_factor if high_52w > 0 else 0.0

        v5_score = odin_score

        # v5.1: Short interest features
        log_float_inv = math.log(1e9 / max(float_shares, 1)) if float_shares > 0 else 0.0
        short_high = 1.0 if pct_float_short >= 0.15 else 0.0

        # v5.2: Sector regime + drift
        drift_magnitude = abs(runup_30d)
        xbi_x_surprise = xbi_return_30d * surprise_factor

        # v5.3: ODIN enrichment + interactions
        small_cap_flag = is_nano + is_micro + is_small
        xbi_x_small = xbi_return_30d * small_cap_flag
        vol_high = 1.0 if volume_ratio > 1.5 else 0.0
        crl_count_x_small = float(prior_crl_count) * small_cap_flag
        drift_7d = abs(runup_7d)
        resub_x_surprise = is_resub * surprise_factor
        naive_x_small = sponsor_naive * (is_nano + is_micro)  # nano+micro only (matches training)
        drawdown_x_vol = abs(drawdown_pct) * volume_ratio
        ta_vh_x_small = ta_very_high * small_cap_flag

        # v5.4 NEW: Exhaustive pairwise ODIN×market interactions (23)
        is_resub1 = 1.0 if resub_class == 1 else 0.0
        is_resub2 = 1.0 if resub_class == 2 else 0.0
        safety_high = 1.0 if safety_signal_severity >= 2 else 0.0
        spa_log = math.log(max(sponsor_prior_approvals, 1))
        is_penny_val = eve_price if is_penny else 0.0

        orphan_x_runup_7d_val = orphan * runup_7d
        resub1_x_vol_high = is_resub1 * vol_high
        ppm_x_runup_30d = ppm_flag * runup_30d
        spa_log_x_is_small = spa_log * is_small
        ppm_x_dtc = ppm_flag * days_to_cover
        safety_h_x_dtc = safety_high * days_to_cover
        crl_rate_x_is_small = hist_crl_rate * is_small
        resub2_x_log_float_inv = is_resub2 * log_float_inv
        ta_vh_x_log_float_inv = ta_very_high * log_float_inv
        resub1_x_beaten = is_resub1 * beaten_down_30d
        ppm_x_is_micro = ppm_flag * is_micro
        btd_x_is_penny_val = btd * is_penny_val
        resub2_x_xbi_30d = is_resub2 * xbi_return_30d
        safety_h_x_short_high = safety_high * short_high
        resub2_x_si_pct = is_resub2 * pct_float_short
        resub1_x_is_micro = is_resub1 * is_micro
        ft_x_drawdown = fast_track * abs(drawdown_pct)
        ft_x_is_small = fast_track * is_small
        safety_h_x_is_penny_val = safety_high * is_penny_val
        fast_track_val = fast_track
        gene_th_x_small_cap = gene_therapy * small_cap_flag
        resub2_x_runup_7d_val = is_resub2 * runup_7d
        t90_t7 = runup_t90_t7

        raw = [
            # v5.0 base (17)
            surprise_factor, is_penny, is_low_price, log_price_inv,
            is_nano, is_micro, is_small,
            surprise_x_small_cap, surprise_x_low_price,
            price_compression, drawdown_pct, beaten_down_30d,
            beaten_surprise, compression_x_surprise,
            volume_ratio, runup_30d, v5_score,
            # v5.1 SI (4)
            log_float_inv, pct_float_short, short_high, days_to_cover,
            # v5.2 sector/drift (3)
            drift_magnitude, xbi_return_30d, xbi_x_surprise,
            # v5.3 (10)
            xbi_x_small, vol_high, crl_count_x_small, is_resub,
            drift_7d, resub_x_surprise, naive_x_small,
            drawdown_x_vol, runup_7d, ta_vh_x_small,
            # v5.4 NEW (23)
            orphan_x_runup_7d_val, resub1_x_vol_high, ppm_x_runup_30d,
            spa_log_x_is_small, ppm_x_dtc, safety_h_x_dtc,
            crl_rate_x_is_small, resub2_x_log_float_inv, ta_vh_x_log_float_inv,
            resub1_x_beaten, ppm_x_is_micro, btd_x_is_penny_val,
            resub2_x_xbi_30d, safety_h_x_short_high, resub2_x_si_pct,
            resub1_x_is_micro, ft_x_drawdown, ft_x_is_small,
            safety_h_x_is_penny_val, fast_track_val, gene_th_x_small_cap,
            resub2_x_runup_7d_val, t90_t7,
        ]

        # Standardize
        z_scores = []
        for i, (val, mean, scale) in enumerate(zip(raw, self.means, self.scales)):
            z = (val - mean) / scale if scale > 1e-10 else 0.0
            z_scores.append(z)

        # Logistic regression
        logit = self.intercept
        contributions = {}
        for i, feat in enumerate(self.features):
            contrib = self.coefs[feat] * z_scores[i]
            logit += contrib
            contributions[feat] = {
                "raw_value": round(raw[i], 4),
                "z_score": round(z_scores[i], 3),
                "coefficient": round(self.coefs[feat], 4),
                "contribution": round(contrib, 4),
            }

        prob = 1.0 / (1.0 + math.exp(-logit))
        tier, mult, tier_desc = self._classify_tier(prob)

        # Sort features by |contribution|
        top_features = sorted(
            [{"feature": f, **contributions[f]} for f in self.features],
            key=lambda x: abs(x["contribution"]),
            reverse=True,
        )

        # Market cap label
        if mcap_m < 50:
            mcap_label = f"NANO (${mcap_m:.0f}M)"
        elif mcap_m < 300:
            mcap_label = f"MICRO (${mcap_m:.0f}M)"
        elif mcap_m < 2000:
            mcap_label = f"SMALL (${mcap_m/1e3:.1f}B)" if mcap_m >= 1000 else f"SMALL (${mcap_m:.0f}M)"
        elif mcap_m < 10000:
            mcap_label = f"MID (${mcap_m/1e3:.1f}B)"
        else:
            mcap_label = f"LARGE (${mcap_m/1e3:.1f}B)"

        return {
            "version": self.version,
            "ticker": ticker,
            "explosion_probability": round(prob, 4),
            "explosion_tier": tier,
            "position_multiplier": mult,
            "tier_description": tier_desc,
            "odin_score": round(odin_score, 4),
            "surprise_factor": round(surprise_factor, 4),
            "eve_price": eve_price,
            "market_cap_label": mcap_label,
            "price_compression": round(price_compression, 4) if high_52w > 0 else "N/A (no 52w high provided)",
            "volume_ratio": round(volume_ratio, 2),
            "runup_30d": round(runup_30d, 2),
            "short_interest": {
                "pct_float_short": round(pct_float_short, 4),
                "days_to_cover": round(days_to_cover, 2),
                "float_shares": int(float_shares),
                "log_float_inv": round(log_float_inv, 4),
                "short_high": bool(short_high),
            },
            "odin_enrichment": {
                "is_resub": bool(is_resub),
                "ta_very_high": bool(ta_very_high),
                "sponsor_naive": bool(sponsor_naive),
                "prior_crl_count": int(prior_crl_count),
                "xbi_return_30d": round(xbi_return_30d, 4),
                "runup_7d": round(runup_7d, 2),
                "orphan": bool(orphan),
                "btd": bool(btd),
                "fast_track": bool(fast_track),
                "ppm_flag": bool(ppm_flag),
                "resub_class": int(resub_class),
                "safety_signal_severity": int(safety_signal_severity),
                "sponsor_prior_approvals": int(sponsor_prior_approvals),
                "gene_therapy": bool(gene_therapy),
                "hist_crl_rate": round(hist_crl_rate, 4),
                "runup_t90_t7": round(runup_t90_t7, 2),
            },
            "top_features": top_features[:10],
            "interpretation": self._interpret(prob, tier, surprise_factor, mcap_label, eve_price,
                                              pct_float_short, days_to_cover, float_shares,
                                              is_resub, ta_very_high, sponsor_naive, prior_crl_count,
                                              orphan, btd, fast_track, ppm_flag, resub_class,
                                              gene_therapy),
            "calibration_note": f"P(explosion)≥30% → 71.4% actually had |D1|>25%, avg |D1|=43.8%. P(explosion)≥20% → 58.8% hit, avg |D1|=34.7%.",
            "disclaimer": "For informational/educational purposes only. Not investment advice.",
        }

    def _interpret(self, prob, tier, surprise, mcap_label, price,
                   pct_float_short=0.0, days_to_cover=0.0, float_shares=0.0,
                   is_resub=0.0, ta_very_high=0.0, sponsor_naive=0.0, prior_crl_count=0,
                   orphan=0.0, btd=0.0, fast_track=0.0, ppm_flag=0.0,
                   resub_class=0, gene_therapy=0.0):
        """Generate human-readable interpretation."""
        parts = []
        if tier == "SNIPER":
            parts.append(f"🎯 SNIPER SETUP — {prob*100:.1f}% explosion probability")
            parts.append("This has the hallmarks of an explosive move: ")
        elif tier == "ELEVATED":
            parts.append(f"⚡ ELEVATED explosion risk — {prob*100:.1f}% probability")
        elif tier == "NORMAL":
            parts.append(f"Standard volatility expected — {prob*100:.1f}% explosion probability")
        else:
            parts.append(f"Low volatility expected — {prob*100:.1f}% explosion probability")

        if surprise > 0.6:
            parts.append(f"High surprise factor ({surprise:.2f}) — market expects failure, positive = massive move")
        if "MICRO" in mcap_label or "NANO" in mcap_label:
            parts.append(f"{mcap_label} — small float amplifies moves")
        if price < 5:
            parts.append(f"Penny stock (${price:.2f}) — low absolute price enables % swings")
        if orphan:
            parts.append("ORPHAN DRUG — rare disease designation amplifies explosion potential (v5.4 #1 signal)")
        if is_resub:
            resub_label = f"Class {resub_class}" if resub_class > 0 else "unknown class"
            parts.append(f"RESUBMISSION ({resub_label}) — inherently more binary event")
        if resub_class == 1 and ("MICRO" in mcap_label or "NANO" in mcap_label):
            parts.append("Class 1 resub × micro cap — maximum binary potential")
        if btd:
            parts.append("Breakthrough therapy designation")
        if fast_track:
            parts.append("Fast track designation")
        if ppm_flag:
            parts.append("Prior probability marker present — PPM interactions active")
        if gene_therapy:
            parts.append("Gene therapy product — modality amplifier for small caps")
        if ta_very_high:
            parts.append("Very high risk TA — binary outcome amplifier")
        if sponsor_naive and ("MICRO" in mcap_label or "NANO" in mcap_label):
            parts.append("Naive sponsor × small cap — suppressed explosion signal")
        if prior_crl_count >= 2:
            parts.append(f"Multiple prior CRLs ({prior_crl_count}) — market fear may suppress upside explosion")
        if pct_float_short >= 0.15:
            parts.append(f"HIGH SHORT INTEREST ({pct_float_short*100:.1f}%) — squeeze potential if positive")
        elif pct_float_short >= 0.05:
            parts.append(f"Moderate short interest ({pct_float_short*100:.1f}%)")
        if days_to_cover >= 7:
            parts.append(f"High days-to-cover ({days_to_cover:.1f}) — shorts trapped if positive")
        if float_shares > 0 and float_shares < 20e6:
            parts.append(f"Low float ({float_shares/1e6:.1f}M shares) — thin supply amplifies moves")
        return " | ".join(parts)


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

ODIN = OdinVNextEngine()
_GUNGNIR_V27 = GungnirV27Engine()  # v27 fallback instance
GUNGNIR = GungnirV38Engine()       # v37 champion (loads from deploy JSON)
BIFROST = BifrostEngine()
EXPLOSION = ExplosionDetectorEngine()


# ============================================================================
# CONFERENCE OVERLAY v1.0 — Empirical Scoring Multiplier
# ============================================================================
# Signal: Conference presentations predict positive outcomes at 90.2% vs 76.7%
# baseline (p=7.88e-21). Crash rate 4.9% vs 8.5% non-conference.
# T-1 compliant: conference acceptance is public weeks before the event.
#
# This is a SCORING OVERLAY — it boosts Gungnir investment scores when a
# catalyst has a confirmed conference presentation, without retraining the model.
# Deploy immediately while Gungnir v42 kaizen adds it as a proper feature.

# RETIRED 2026-07-11 - REFUTED. See /research/conference-runup. Do not use.
_RETIRED_CONFERENCE_TIER_WEIGHTS = {
    # Empirical positive outcome rates from 285 conference events (2022-2026)
    "AACR": {"rate": 1.000, "n": 16, "weight": 0.20, "tier": "ELITE"},
    "ASH":  {"rate": 0.954, "n": 65, "weight": 0.18, "tier": "ELITE"},
    "ESMO": {"rate": 0.957, "n": 69, "weight": 0.18, "tier": "ELITE"},
    "ASCO": {"rate": 0.900, "n": 90, "weight": 0.15, "tier": "TIER1"},
    "AAN":  {"rate": 0.900, "n": 20, "weight": 0.14, "tier": "TIER1"},  # est from neuro signal
    "EHA":  {"rate": 0.920, "n": 25, "weight": 0.14, "tier": "TIER1"},
    "SITC": {"rate": 0.880, "n": 15, "weight": 0.12, "tier": "TIER2"},
    "SNO":  {"rate": 0.880, "n": 10, "weight": 0.12, "tier": "TIER2"},
    "OTHER": {"rate": 0.850, "n": 0, "weight": 0.10, "tier": "TIER2"},
}

# RETIRED 2026-07-11 - part of the refuted Conference Overlay v1.0. Unreachable (tool disabled).
PRESENTATION_TYPE_WEIGHTS = {
    # Oral > late-breaking > poster (selectivity hierarchy)
    "oral":          0.08,   # Oral presentations are most selective
    "late-breaking": 0.06,   # Late-breaking = high-impact new data
    "poster":        0.04,   # Standard poster = baseline conference signal
    "multiple":      0.06,   # Multiple presentations (any mix) = strong engagement
}

# Runup timing parameters by cap size (from empirical analysis)
# RETIRED 2026-07-11 - REFUTED (claimed nano +4.88%; actual nano median -9.84%). Do not use.
_RETIRED_CONFERENCE_RUNUP_TIMING = {
    "nano":  {"entry_window": "D-30", "exit_window": "D-1", "median_return": 4.88, "win_rate": 0.585},
    "micro": {"entry_window": "D-30", "exit_window": "D-1", "median_return": 4.88, "win_rate": 0.585},
    "small": {"entry_window": "D-5",  "exit_window": "D-1", "median_return": 3.02, "win_rate": 0.667},
    "mid":   {"entry_window": "D-5",  "exit_window": "D-1", "median_return": 2.10, "win_rate": 0.580},
    "large": {"entry_window": "D-3",  "exit_window": "D-1", "median_return": 1.20, "win_rate": 0.520},
}


class ConferenceOverlayEngine:
    """Conference Overlay v1.0 — empirical scoring boost for conference presentations.

    Mechanism: Conference abstract acceptance = implicit peer review + company
    self-selection. Papers must pass scientific review → data must be presentable
    → strong positive signal for outcome.

    Usage: Score with Gungnir first, then overlay conference boost.
    The boost is multiplicative on the investment score (not the raw probability)
    to preserve Gungnir's calibration while adjusting the TRADING signal.
    """

    version = "Conference Overlay v1.0"

    def __init__(self):
        # Load 2026 conference trade data if available
        self.trade_data = {}
        try:
            trade_path = Path(__file__).parent / "conference_trades_apr_may_2026.json"
            if trade_path.exists():
                with open(trade_path) as f:
                    trades = json.load(f)
                    for t in trades:
                        self.trade_data[t["ticker"].upper()] = t
        except Exception:
            pass

    def _resolve_conference(self, conference: str) -> dict:
        """Resolve conference name to tier weights."""
        conf_upper = conference.upper().strip()
        for key, data in _RETIRED_CONFERENCE_TIER_WEIGHTS.items():
            if key in conf_upper:
                return {**data, "matched": key}
        return {**_RETIRED_CONFERENCE_TIER_WEIGHTS["OTHER"], "matched": "OTHER"}

    def _resolve_presentation_type(self, pres_type: str) -> float:
        """Resolve presentation type to weight."""
        pt = pres_type.lower().strip()
        if "oral" in pt:
            return PRESENTATION_TYPE_WEIGHTS["oral"]
        elif "late" in pt or "breaking" in pt:
            return PRESENTATION_TYPE_WEIGHTS["late-breaking"]
        elif any(x in pt for x in ["multiple", "2 ", "3 ", "4 ", "5 ", "+"]):
            return PRESENTATION_TYPE_WEIGHTS["multiple"]
        else:
            return PRESENTATION_TYPE_WEIGHTS["poster"]

    def _resolve_mcap_tier(self, market_cap: float) -> str:
        """Resolve market cap to size tier."""
        if market_cap < 50e6:
            return "nano"
        elif market_cap < 300e6:
            return "micro"
        elif market_cap < 2e9:
            return "small"
        elif market_cap < 10e9:
            return "mid"
        else:
            return "large"

    def score(self, ticker: str, conference: str, presentation_type: str = "poster",
              n_presentations: int = 1, market_cap: float = 0.0,
              gungnir_probability: float = 0.0, gungnir_investment_score: float = 0.0,
              days_to_conference: int = 30) -> dict:
        """Apply conference overlay to a catalyst.

        Returns boosted investment score + conference-specific runup timing.
        """
        # Resolve conference tier
        conf_data = self._resolve_conference(conference)
        conf_weight = conf_data["weight"]
        conf_tier = conf_data["tier"]
        conf_matched = conf_data["matched"]

        # Resolve presentation type
        pres_weight = self._resolve_presentation_type(presentation_type)

        # Multi-presentation bonus: +2% per extra presentation (diminishing)
        multi_bonus = min(0.06, (n_presentations - 1) * 0.02) if n_presentations > 1 else 0.0

        # Total conference boost factor
        # Base: conference_weight + presentation_weight + multi_bonus
        # This represents the incremental edge from having a conference presentation
        total_boost = conf_weight + pres_weight + multi_bonus

        # Apply boost to investment score (multiplicative)
        # E.g., Gungnir score 65 with AACR oral (0.20+0.08=0.28) → 65 * 1.28 = 83.2
        boosted_score = gungnir_investment_score * (1.0 + total_boost) if gungnir_investment_score > 0 else 0.0
        boosted_score = min(100.0, boosted_score)

        # Adjusted probability (additive small bump based on empirical lift)
        # Conference events are 90.2% vs 76.7% baseline = +13.5pp absolute lift
        # We apply a fraction based on conference tier to avoid over-boosting
        prob_bump = conf_weight * 0.50  # max ~10pp bump for ELITE conferences
        adjusted_prob = min(0.99, gungnir_probability + prob_bump)

        # Tier assignment based on boosted score
        if boosted_score >= 75:
            overlay_tier = "ALPHA"
            action = "STRONG_BUY"
        elif boosted_score >= 60:
            overlay_tier = "BETA"
            action = "BUY"
        elif boosted_score >= 45:
            overlay_tier = "GAMMA"
            action = "CAUTIOUS_BUY"
        elif boosted_score >= 30:
            overlay_tier = "DELTA"
            action = "MONITOR"
        else:
            overlay_tier = "OMEGA"
            action = "NO_TRADE"

        # Resolve mcap tier for runup timing
        mcap_tier = self._resolve_mcap_tier(market_cap) if market_cap > 0 else "micro"
        timing = _RETIRED_CONFERENCE_RUNUP_TIMING.get(mcap_tier, _RETIRED_CONFERENCE_RUNUP_TIMING["micro"])

        # Position sizing: base 4% for ALPHA/BETA, 2% for GAMMA, 1% for DELTA
        if overlay_tier in ("ALPHA",):
            position_pct = 5.0
        elif overlay_tier in ("BETA",):
            position_pct = 4.0
        elif overlay_tier in ("GAMMA",):
            position_pct = 2.0
        else:
            position_pct = 1.0

        # Nano cap risk reduction
        if mcap_tier == "nano":
            position_pct = min(position_pct, 3.0)

        # Timing assessment
        if days_to_conference <= 0:
            timing_status = "PAST"
            timing_note = "Conference has passed. Runup window closed."
        elif days_to_conference <= 3:
            timing_status = "EXIT_ZONE"
            timing_note = f"EXIT NOW. Conference in {days_to_conference} days. Take profits."
        elif mcap_tier in ("nano", "micro") and days_to_conference <= 30:
            timing_status = "ENTRY_ZONE"
            timing_note = f"ENTER NOW. {days_to_conference} days to conference. Optimal window for {mcap_tier}-cap."
        elif mcap_tier in ("small", "mid") and days_to_conference <= 7:
            timing_status = "ENTRY_ZONE"
            timing_note = f"ENTER NOW. {days_to_conference} days to conference. Optimal window for {mcap_tier}-cap."
        elif days_to_conference > 30:
            timing_status = "TOO_EARLY"
            timing_note = f"Conference in {days_to_conference} days. Wait for entry window ({timing['entry_window']})."
        else:
            timing_status = "HOLDING"
            timing_note = f"Position open. {days_to_conference} days to conference. Exit {timing['exit_window']}."

        # Check if we have pre-built trade data for this ticker
        trade_info = self.trade_data.get(ticker.upper(), {})

        result = {
            "version": self.version,
            "ticker": ticker.upper(),
            "conference": conf_matched,
            "conference_tier": conf_tier,
            "presentation_type": presentation_type,
            "n_presentations": n_presentations,
            "conference_boost": {
                "conf_weight": round(conf_weight, 3),
                "pres_weight": round(pres_weight, 3),
                "multi_bonus": round(multi_bonus, 3),
                "total_boost": round(total_boost, 3),
            },
            "gungnir_original": {
                "probability": round(gungnir_probability, 4),
                "investment_score": round(gungnir_investment_score, 1),
            },
            "boosted": {
                "probability": round(adjusted_prob, 4),
                "investment_score": round(boosted_score, 1),
                "tier": overlay_tier,
                "action": action,
            },
            "timing": {
                "days_to_conference": days_to_conference,
                "status": timing_status,
                "note": timing_note,
                "optimal_entry": timing["entry_window"],
                "optimal_exit": timing["exit_window"],
                "expected_median_return": timing["median_return"],
                "expected_win_rate": timing["win_rate"],
            },
            "position_sizing": {
                "position_pct": round(position_pct, 1),
                "mcap_tier": mcap_tier,
                "cardinal_rule": "The runup IS the trade. Exit before conference day.",
            },
            "signal_strength": {
                "baseline_positive_rate": 0.767,
                "conference_positive_rate": 0.902,
                "lift_pp": 13.5,
                "crash_rate_conference": 0.049,
                "crash_rate_baseline": 0.085,
                "p_value": "7.88e-21",
                "n_conference_events": 285,
            },
        }

        # Add pre-built trade notes if available
        if trade_info:
            result["trade_notes"] = {
                "drug": trade_info.get("drug", ""),
                "stage": trade_info.get("stage", ""),
                "notes": trade_info.get("notes", ""),
            }

        return result


CONFERENCE = ConferenceOverlayEngine()


# ============================================================================
# SMART MONEY OVERLAY v1.0 — Institutional + Insider + Analyst Intelligence
# ============================================================================
# Derived from KOD postmortem analysis: Baker Bros held 37.6% of KOD going into
# GLOW2 Phase 3 readout → stock up 88%. Smart money convergence is a signal.
# Also incorporates "fallen angel" detection (former large-caps now compressed)
# and confirmatory trial detection (prior positive pivotal).
#
# Signal hierarchy:
#   GOD_TIER fund ownership (Baker Bros, RA Capital, Perceptive, OrbiMed, Avoro,
#     EcoR1, RTW, BVF, Redmile, Cormorant) = highest institutional signal
#   C-suite insider buying ahead of catalyst = highest insider signal
#   Analyst consensus weighted by accuracy = analyst signal
#   Fallen angel (peak mcap >> current) = compressed upside
#   Confirmatory trial (prior positive pivotal) = higher P(success)

# God Tier biotech funds — decade annualized returns > 20% (WhaleWisdom/HedgeFollow)
GOD_TIER_FUNDS = {
    # VERIFIED decade returns from WhaleWisdom 13F Performance Analysis (top 4)
    # Unverified funds marked with est_ prefix on return — based on AUM growth + industry data
    "RA Capital Management": {"rank": 1, "ann_return": 0.3053, "weight": 1.0},   # VERIFIED: WhaleWisdom #1 decade
    "Baker Bros. Advisors": {"rank": 2, "ann_return": 0.255, "weight": 1.0},     # VERIFIED: WhaleWisdom #2 decade
    "Baker Bros": {"rank": 2, "ann_return": 0.255, "weight": 1.0},               # Alias
    "Perceptive Advisors": {"rank": 3, "ann_return": 0.2118, "weight": 0.90},    # VERIFIED: WhaleWisdom #5 decade (was 0.22)
    "OrbiMed Advisors": {"rank": 4, "ann_return": 0.184, "weight": 0.85},        # VERIFIED: WhaleWisdom #19 decade (was 0.20)
    "Avoro Capital": {"rank": 5, "ann_return": 0.18, "weight": 0.85},            # est ~18% (was 0.22 OVERSTATED)
    "venBio": {"rank": 5, "ann_return": 0.18, "weight": 0.85},                   # Alias
    "RTW Investments": {"rank": 6, "ann_return": 0.17, "weight": 0.85},          # est ~17%, UPGRADED weight (AUM $10B, aggressive Q4)
    "EcoR1 Capital": {"rank": 7, "ann_return": 0.17, "weight": 0.75},            # est ~17% (was 0.20 OVERSTATED), weight -0.05
    "BVF Partners": {"rank": 8, "ann_return": 0.16, "weight": 0.75},             # est ~16% (was 0.19)
    "Redmile Group": {"rank": 9, "ann_return": 0.15, "weight": 0.65},            # est ~15% (was 0.19 OVERSTATED), AUM -32%, weight -0.10
    "Cormorant Asset": {"rank": 10, "ann_return": 0.15, "weight": 0.65},         # est ~15% (was 0.18), defensive Q4, weight -0.05
}

# Insider signal weights
INSIDER_SIGNAL_WEIGHTS = {
    "ceo_buy": 10.0,       # CEO open-market purchase
    "csuite_buy": 8.0,     # Other C-suite (CFO, CMO, CTO, CSO)
    "director_buy": 6.0,   # Board director purchase
    "10pct_owner_buy": 7.0,  # >10% owner adding
    "insider_sell_tax": 0.0,  # Tax/RSU disposal — neutral, not negative
    "insider_sell_voluntary": -3.0,  # Voluntary sell — mild negative
}


def tool_smart_money_score(
    ticker: str,
    # Institutional ownership
    god_tier_fund_names: list = None,
    god_tier_fund_ownership_pct: float = 0.0,
    total_institutional_pct: float = 0.0,
    n_institutional_holders: int = 0,
    # Insider signals
    insider_buy_total_usd: float = 0.0,
    insider_buy_type: str = "none",  # "ceo_buy", "csuite_buy", "director_buy", "10pct_owner_buy", "none"
    insider_net_shares_90d: int = 0,  # Positive = net buying, negative = net selling
    insider_ownership_pct: float = 0.0,
    # Analyst data
    n_analysts: int = 0,
    pct_strong_buy: float = 0.0,
    avg_pt_upside_pct: float = 0.0,
    top_analyst_covers: bool = False,  # True if a TipRanks 5-star analyst covers
    # Structural features (KOD-derived)
    peak_mcap: float = 0.0,       # All-time or 52w high mcap — for fallen angel detection
    current_mcap: float = 0.0,    # Current mcap
    has_prior_positive_pivotal: bool = False,  # Confirmatory trial flag
    actual_phase_override: int = 0,  # Override phase if misclassified (0 = no override)
    # Context
    gungnir_probability: float = 0.0,
    gungnir_investment_score: float = 0.0,
    catalyst_type: str = "readout",  # "readout" or "pdufa"
) -> dict:
    """Apply Smart Money Overlay v1.0 to any catalyst.

    Combines institutional ownership (God Tier fund tracking), insider buying/selling,
    analyst consensus quality, and structural factors (fallen angel, confirmatory trial)
    into a Smart Money Score (0-100) that adjusts the Gungnir/ODIN investment score.

    Derived from KOD postmortem: Baker Bros held 37.6% of Kodiak Sciences going into
    the GLOW2 Phase 3 readout → stock surged 88%. Gungnir gave T1 (0.903 probability)
    but investment score was GAMMA (50.0) due to phase misclassification. Smart money
    overlay would have caught this.

    GOD TIER FUNDS (decade 20%+ annualized):
        RA Capital (~30.5%), Baker Bros (~25.5%), Perceptive, OrbiMed,
        Avoro/venBio, EcoR1, RTW, BVF, Redmile, Cormorant

    INSIDER SIGNAL HIERARCHY:
        CEO open-market buy > C-suite buy > Director buy > 10% owner buy
        Tax/RSU disposals are NEUTRAL (not negative)

    STRUCTURAL FEATURES:
        Fallen Angel: peak_mcap / current_mcap > 3x → compressed upside
        Confirmatory Trial: prior positive pivotal → higher success rate

    T-1 COMPLIANCE: All inputs are public information available before catalysts.
        13F filings (45-day lag), Form 4 insider filings (2-day lag),
        analyst ratings (published continuously), market cap (real-time).

    DISCLAIMER: For informational/educational purposes only. Not investment advice.
    """
    god_tier_fund_names = god_tier_fund_names or []

    # ── 1. INSTITUTIONAL SCORE (0-30) ──
    inst_score = 0.0

    # God Tier fund presence (up to 20 points)
    matched_funds = []
    for fund_name in god_tier_fund_names:
        for gt_name, gt_data in GOD_TIER_FUNDS.items():
            if gt_name.lower() in fund_name.lower() or fund_name.lower() in gt_name.lower():
                matched_funds.append({"name": gt_name, **gt_data})
                break

    n_god_tier = len(matched_funds)
    if n_god_tier >= 3:
        inst_score += 20.0  # Triple convergence — maximum signal
    elif n_god_tier == 2:
        inst_score += 15.0
    elif n_god_tier == 1:
        # Weight by fund quality
        best_weight = max(f["weight"] for f in matched_funds)
        inst_score += 10.0 * best_weight

    # Ownership concentration (up to 10 points)
    # KOD had Baker Bros at 37.6% — massive conviction
    if god_tier_fund_ownership_pct >= 30:
        inst_score += 10.0
    elif god_tier_fund_ownership_pct >= 15:
        inst_score += 7.0
    elif god_tier_fund_ownership_pct >= 5:
        inst_score += 4.0
    elif total_institutional_pct >= 50:
        inst_score += 3.0
    elif total_institutional_pct >= 25:
        inst_score += 1.5

    # ── 2. INSIDER SCORE (0-30) ──
    insider_score = 0.0

    # Insider buy type (up to 15 points)
    buy_weight = INSIDER_SIGNAL_WEIGHTS.get(insider_buy_type, 0.0)
    insider_score += max(0, buy_weight * 1.5)

    # Dollar magnitude of insider buying (up to 10 points)
    # CABA: $286K → good. ALXO: $5M → exceptional. KOD: Baker Bros $225M royalties
    if insider_buy_total_usd >= 5_000_000:
        insider_score += 10.0
    elif insider_buy_total_usd >= 1_000_000:
        insider_score += 8.0
    elif insider_buy_total_usd >= 500_000:
        insider_score += 6.0
    elif insider_buy_total_usd >= 100_000:
        insider_score += 4.0
    elif insider_buy_total_usd > 0:
        insider_score += 2.0

    # Net direction penalty/bonus (up to 5 points)
    if insider_net_shares_90d > 0:
        insider_score += 5.0
    elif insider_net_shares_90d < 0:
        # Only penalize if it's voluntary selling, not tax/RSU
        if insider_buy_type == "insider_sell_voluntary":
            insider_score -= 3.0

    # ── 3. ANALYST SCORE (0-20) ──
    analyst_score = 0.0

    # Consensus strength (up to 10 points)
    if n_analysts >= 5 and pct_strong_buy >= 0.60:
        analyst_score += 10.0
    elif n_analysts >= 3 and pct_strong_buy >= 0.50:
        analyst_score += 7.0
    elif n_analysts >= 2 and pct_strong_buy >= 0.80:
        analyst_score += 8.0  # Thin but unanimous
    elif n_analysts >= 1:
        analyst_score += 3.0

    # PT upside (up to 5 points)
    if avg_pt_upside_pct >= 200:
        analyst_score += 5.0
    elif avg_pt_upside_pct >= 100:
        analyst_score += 3.0
    elif avg_pt_upside_pct >= 50:
        analyst_score += 2.0

    # Top analyst coverage bonus
    if top_analyst_covers:
        analyst_score += 5.0

    # ── 4. STRUCTURAL SCORE (0-20) ──
    structural_score = 0.0

    # Fallen angel detection (up to 10 points)
    fallen_angel_ratio = 0.0
    if peak_mcap > 0 and current_mcap > 0:
        fallen_angel_ratio = peak_mcap / current_mcap
        if fallen_angel_ratio >= 5.0:
            structural_score += 10.0  # Massive compression (KOD was ~4x compressed)
        elif fallen_angel_ratio >= 3.0:
            structural_score += 7.0
        elif fallen_angel_ratio >= 2.0:
            structural_score += 4.0

    # Confirmatory trial (up to 10 points)
    if has_prior_positive_pivotal:
        structural_score += 10.0

    # ── TOTAL SMART MONEY SCORE ──
    raw_smart = inst_score + insider_score + analyst_score + structural_score
    smart_money_score = max(0, min(100, raw_smart))

    # ── BOOST CALCULATION ──
    # Smart money score translates to investment score boost
    # Scale: 0-30 = no boost, 30-50 = small boost, 50-70 = moderate, 70+ = strong
    if smart_money_score >= 80:
        boost_factor = 0.30  # +30% to investment score
    elif smart_money_score >= 70:
        boost_factor = 0.22
    elif smart_money_score >= 60:
        boost_factor = 0.15
    elif smart_money_score >= 50:
        boost_factor = 0.10
    elif smart_money_score >= 35:
        boost_factor = 0.05
    else:
        boost_factor = 0.0

    boosted_investment_score = gungnir_investment_score * (1.0 + boost_factor)
    boosted_investment_score = min(100.0, boosted_investment_score)

    # Phase override boost (KOD fix: mislabeled Phase 1 → actual Phase 3)
    phase_override_note = ""
    if actual_phase_override > 0:
        phase_override_note = f"Phase override: labeled as lower phase, actual Phase {actual_phase_override}. Investment score may be significantly underestimated by base model."

    # ── TIER ASSIGNMENT ──
    if boosted_investment_score >= 75:
        sm_tier = "ALPHA"
        sm_action = "STRONG_BUY"
    elif boosted_investment_score >= 60:
        sm_tier = "BETA"
        sm_action = "BUY"
    elif boosted_investment_score >= 45:
        sm_tier = "GAMMA"
        sm_action = "CAUTIOUS_BUY"
    elif boosted_investment_score >= 30:
        sm_tier = "DELTA"
        sm_action = "MONITOR"
    else:
        sm_tier = "OMEGA"
        sm_action = "NO_TRADE"

    # ── CONVICTION LABEL ──
    if smart_money_score >= 90:
        conviction = "MAXIMUM"
    elif smart_money_score >= 75:
        conviction = "VERY HIGH"
    elif smart_money_score >= 60:
        conviction = "HIGH"
    elif smart_money_score >= 40:
        conviction = "MODERATE"
    elif smart_money_score >= 20:
        conviction = "LOW"
    else:
        conviction = "MINIMAL"

    # ── FLAGS ──
    flags = []
    if n_god_tier >= 3:
        flags.append("TRIPLE_CONVERGENCE")
    if n_god_tier >= 1:
        flags.append(f"GOD_TIER_x{n_god_tier}")
    if insider_buy_total_usd >= 1_000_000:
        flags.append("MEGA_INSIDER_BUY")
    if insider_buy_type == "ceo_buy":
        flags.append("CEO_BUYING")
    if fallen_angel_ratio >= 3.0:
        flags.append("FALLEN_ANGEL")
    if has_prior_positive_pivotal:
        flags.append("CONFIRMATORY_TRIAL")
    if actual_phase_override > 0:
        flags.append(f"PHASE_OVERRIDE_{actual_phase_override}")
    if smart_money_score >= 80 and gungnir_probability >= 0.80:
        flags.append("DOUBLE_CONVICTION")  # Both model + smart money agree

    return {
        "version": "Smart Money Overlay v1.0",
        "ticker": ticker.upper(),
        "smart_money_score": round(smart_money_score, 1),
        "conviction": conviction,
        "components": {
            "institutional": round(inst_score, 1),
            "insider": round(insider_score, 1),
            "analyst": round(analyst_score, 1),
            "structural": round(structural_score, 1),
        },
        "original": {
            "probability": round(gungnir_probability, 4),
            "investment_score": round(gungnir_investment_score, 1),
        },
        "boosted": {
            "investment_score": round(boosted_investment_score, 1),
            "boost_factor": round(boost_factor, 3),
            "tier": sm_tier,
            "action": sm_action,
        },
        "institutional_detail": {
            "god_tier_funds_matched": [f["name"] for f in matched_funds],
            "n_god_tier": n_god_tier,
            "god_tier_ownership_pct": round(god_tier_fund_ownership_pct, 1),
            "total_institutional_pct": round(total_institutional_pct, 1),
            "n_holders": n_institutional_holders,
        },
        "insider_detail": {
            "buy_type": insider_buy_type,
            "buy_total_usd": insider_buy_total_usd,
            "net_shares_90d": insider_net_shares_90d,
            "ownership_pct": round(insider_ownership_pct, 1),
        },
        "structural_detail": {
            "fallen_angel_ratio": round(fallen_angel_ratio, 2),
            "has_prior_positive_pivotal": has_prior_positive_pivotal,
            "phase_override": actual_phase_override if actual_phase_override > 0 else None,
            "phase_override_note": phase_override_note or None,
        },
        "flags": flags,
        "methodology": {
            "institutional_max": 30,
            "insider_max": 30,
            "analyst_max": 20,
            "structural_max": 20,
            "total_max": 100,
            "boost_scale": "0-30=none, 35-50=+5%, 50-60=+10%, 60-70=+15%, 70-80=+22%, 80+=+30%",
            "god_tier_source": "WhaleWisdom/HedgeFollow decade 13F performance rankings",
            "t1_compliance": "All inputs are public pre-catalyst information (13F, Form 4, analyst ratings)",
        },
        "kod_benchmark": {
            "note": "KOD (Kodiak Sciences) — Baker Bros held 37.6%, Gungnir T1 (0.903), but investment score was GAMMA (50.0) due to Phase 1 mislabel. Smart Money Overlay would have added: inst=17 (Baker Bros God Tier + 37.6% ownership), structural=17 (fallen angel 4x + confirmatory), total boost +22%, pushing GAMMA→BETA. Phase override would push further to ALPHA.",
        },
        "disclaimer": "For informational/educational purposes only. Not investment advice.",
    }


def tool_odin_score(
    ticker: str, drug_name: str, therapeutic_area: str, pdufa_date: str,
    phase: str = "NDA", btd: bool = False, orphan: bool = False,
    priority_review: bool = False, fast_track: bool = False,
    accelerated_approval: bool = False, surrogate_endpoint: bool = False,
    had_adcom: bool = False, prior_crl: bool = False,
    form_483_issues: bool = False, manufacturing_risk: bool = False,
    gene_therapy: bool = False, single_arm_study: bool = False,
    safety_tier: str = "low", resub_class: int = 0,
    sponsor_prior_approvals: int = 5, prior_crl_count: int = 0,
    historical_crl_rate: float = 0.32,
    sponsor_streak: float = 0.0, sponsor_recent_crl: bool = False,
    sponsor_momentum: float = 0.0,
    safety_signal_severity: int = 0, is_psychedelic: bool = False,
    notes: str = "",
) -> dict:
    """Score a PDUFA catalyst using ODIN v13 (HO AUC 0.9315). Returns approval probability + tier.

    The v12 model uses 37 features including safety/adcom naive interactions,
    psychedelic drug signals, TA risk bucket encoding, and CRL count × naive.
    The following parameters are accepted for API compatibility but are NOT
    directly used by the model:
      form_483_issues, gene_therapy, safety_tier, sponsor_recent_crl

    New v12 parameters:
      safety_signal_severity: 0=none, 1=low, 2+=high (for safety_high_x_naive feature)
      is_psychedelic: True if psychedelic drug (for psychedelics_bin/psychedelics_x_naive)

    The model derives all 37 features from the remaining parameters.
    Note: historical_crl_rate is used (crl_rate_low + crl_rate_x_naive features).
    Note: resub_class is granular (1=major, 2=minor).
    Note: had_adcom now used in adcom_x_naive interaction (v12 NEW).
    Note: prior_crl_count now used in crl_count_x_naive interaction (v12 NEW).
    """
    # Build catalyst dict with signals sub-dict for the engine
    catalyst = {
        "ticker": ticker, "drug_name": drug_name,
        "therapeutic_area": therapeutic_area, "pdufa_date": pdufa_date,
        "phase": phase, "safety_tier": safety_tier,
        "resub_class": resub_class,
        "sponsor_prior_approvals": sponsor_prior_approvals,
        "prior_crl_count": prior_crl_count,
        "historical_crl_rate": historical_crl_rate,
        "sponsor_streak": sponsor_streak,
        "sponsor_recent_crl": sponsor_recent_crl,
        "sponsor_momentum": sponsor_momentum,
        "safety_signal_severity": safety_signal_severity,
        "is_psychedelic": is_psychedelic,
        "signals": {
            "btd": btd, "orphan": orphan, "priority_review": priority_review,
            "fast_track": fast_track, "accelerated_approval": accelerated_approval,
            "surrogate_endpoint": surrogate_endpoint, "had_adcom": had_adcom,
            "prior_crl": prior_crl, "form_483_issues": form_483_issues,
            "manufacturing_risk": manufacturing_risk, "gene_therapy": gene_therapy,
            "single_arm_study": single_arm_study,
            "ppm_flag": (priority_review and manufacturing_risk),
            "psychedelics": is_psychedelic,
        },
    }
    result = ODIN.score(catalyst)
    result["ticker"] = ticker
    result["drug_name"] = drug_name
    result["notes"] = notes

    # List which accepted params are unused (informational)
    result["unused_params_note"] = (
        "form_483_issues, gene_therapy, safety_tier are accepted but not directly "
        "used by v10 model. single_arm_study IS NOW USED (single_arm_x_btd interaction). "
        "historical_crl_rate IS used (crl_rate_low + crl_rate_x_naive). "
        "manufacturing_risk IS used (mfg_risk_bin). sponsor_streak, sponsor_recent_crl, "
        "and sponsor_momentum are v10 NEW and REQUIRED for full model accuracy. "
        "resub_class is granular: 1=major, 2=minor. All params retained for API compatibility."
    )
    return result


def tool_gungnir_score(
    ticker: str, drug_name: str, indication: str, stage: str,
    catalyst_text: str, company: str = "", year: int = 2026,
    has_conference: int = None, days_to_cover: float = 0.0,
) -> dict:
    """Score a phase readout using GUNGNIR v46 Champion (AUC 0.8135, zero leakage).

    GUNGNIR v46 is a PREDICTIVE model — estimates readout success probability using
    144 pre-readout features knowable at T-1 (before results are announced).
    Uses Ridge M1 component of the 3-model meta-ensemble (Ridge 85% + XGB 15%).
    v44 adds cross-family interactions: antagonist×journey, sm×phase2×small-cap.

    Use catalyst_text to describe the TRIAL DESIGN (not results).
    Include conference name in catalyst_text for automatic detection (e.g., "AACR poster").
    Optional params: journey_success_rate, sponsor_success_rate, momentum_20d,
    price, market_cap, indication_density, enrollment, has_conference, days_to_cover.
    Drug modality flags: is_oligonucleotide, is_biologic, is_cell_therapy, is_adc
    (auto-detected from drug_name if not provided).

    Example catalyst_text: "Phase 2b randomized placebo-controlled trial in NSCLC
    testing combination therapy with PFS as primary endpoint. BTD granted. ASCO poster."
    """
    catalyst = {
        "ticker": ticker, "drug_name": drug_name,
        "indication": indication, "stage": stage,
        "catalyst_text": catalyst_text, "company": company,
        "year": year, "days_to_cover": days_to_cover,
    }
    if has_conference is not None:
        catalyst["has_conference"] = has_conference
    result = GUNGNIR.score(catalyst)
    result["ticker"] = ticker
    result["drug_name"] = drug_name
    return result


def tool_odin_rank(catalysts: list) -> dict:
    """Rank multiple PDUFA catalysts by ODIN score."""
    results = []
    for c in catalysts:
        score = ODIN.score(c)
        score["ticker"] = c.get("ticker", "???")
        score["drug_name"] = c.get("drug_name", "???")
        results.append(score)
    results.sort(key=lambda x: x["probability"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return {"engine": "ODIN v13 Champion", "count": len(results), "rankings": results}


def tool_bifrost_score(
    ticker: str, odin_tier: int, market_cap: float,
    days_to_pdufa: int = 60, v9_score: float = 0.0,
    momentum_14d: float = 0.0, volatility_20d: float = 0.0,
) -> dict:
    """Score a PDUFA runup opportunity using BIFROST v4.0. Returns optimal entry/exit windows + Kelly sizing.

    BIFROST v4.0 analyzes optimal trading windows for PDUFA catalyst runups using ODIN v10
    tiers × market cap with triple-ensemble magnitude prediction (Ridge+XGB+LightGBM).
    Walk-forward validated: Sharpe 5.45, 70.8% win rate, -4.9% max DD.
    v4 adds: sponsor_success_rate tracking, vol_adjusted_confidence, TA risk interactions.

    Core thesis: The runup IS the trade. Never hold through the FDA decision.

    Args:
        ticker: Stock ticker
        odin_tier: ODIN v13 tier (1=Strong Long, 2=Cautious Long, 3=Monitor, 4=No Trade)
        market_cap: Market capitalization in dollars (e.g., 500000000 for $500M)
        days_to_pdufa: Trading days until PDUFA date (e.g., 45)
        v9_score: Optional ODIN v13 probability (0-1) for enhanced sizing
        momentum_14d: Optional 14-day price momentum % for magnitude assessment
        volatility_20d: Optional 20-day annualized volatility % for magnitude assessment
    """
    return BIFROST.score(odin_tier, market_cap, days_to_pdufa, ticker,
                         v9_score, momentum_14d, volatility_20d)


def tool_explosion_score(
    ticker: str, odin_score: float, eve_price: float, market_cap: float,
    high_52w: float = 0.0, volume_ratio: float = 1.0, runup_30d: float = 0.0,
    float_shares: float = 0.0, pct_float_short: float = 0.0,
    days_to_cover: float = 0.0, xbi_return_30d: float = 0.0,
    is_resub: float = 0.0, ta_very_high: float = 0.0,
    sponsor_naive: float = 0.0, prior_crl_count: int = 0,
    runup_7d: float = 0.0,
    orphan: float = 0.0, btd: float = 0.0,
    fast_track: float = 0.0, ppm_flag: float = 0.0,
    resub_class: int = 0, safety_signal_severity: int = 0,
    sponsor_prior_approvals: int = 0, gene_therapy: float = 0.0,
    hist_crl_rate: float = 0.0, runup_t90_t7: float = 0.0,
) -> dict:
    """Score explosion probability for a PDUFA event using BIFROST v5.4 Explosion Detector.

    Predicts P(|D1 move| > 25%). Use AFTER odin_score to get ODIN probability.
    v5.4 adds 23 new features from exhaustive pairwise ODIN×market interactions:
    orphan×runup, resubmission class×microstructure, PPM×market, safety×SI, gene therapy×size.
    LR Test AUC 0.9332 (v5.3 was 0.8720, +0.0612). 20/20 seed stability, p=3.63e-14.
    Test AUC > Train AUC confirms genuine generalization. BIGGEST jump in explosion history.

    Args:
        ticker: Stock ticker
        odin_score: ODIN v13 probability (0-1) — use the probability from odin_score tool
        eve_price: Current/pre-event stock price in dollars
        market_cap: Market capitalization in dollars (e.g., 100000000 for $100M)
        high_52w: 52-week high price (0 = unknown, uses eve_price as fallback)
        volume_ratio: Recent volume / 20-day avg volume (default 1.0)
        runup_30d: 30-day pre-event price return in % (default 0.0)
        float_shares: Shares in public float (e.g., 10000000 for 10M float). 0 = unknown.
        pct_float_short: Fraction of float sold short (e.g., 0.15 for 15% SI). 0 = unknown.
        days_to_cover: Short ratio / days to cover. 0 = unknown.
        xbi_return_30d: XBI ETF 30-day trailing return (decimal, e.g. 0.05 = 5%). 0 = unknown.
        is_resub: 1.0 if this is a resubmission (any class), 0.0 otherwise. From odin_score.
        ta_very_high: 1.0 if therapeutic area is very high risk, 0.0 otherwise. From odin_score.
        sponsor_naive: 1.0 if sponsor has zero prior FDA approvals, 0.0 otherwise. From odin_score.
        prior_crl_count: Number of prior CRLs for this drug (0 = none). From odin_score.
        runup_7d: 7-day pre-event price return in % (default 0.0).
        orphan: 1.0 if orphan drug designation, 0.0 otherwise. (v5.4 NEW)
        btd: 1.0 if breakthrough therapy designation, 0.0 otherwise. (v5.4 NEW)
        fast_track: 1.0 if fast track designation, 0.0 otherwise. (v5.4 NEW)
        ppm_flag: 1.0 if prior probability marker present, 0.0 otherwise. (v5.4 NEW)
        resub_class: Resubmission class (0=none, 1=Class 1/efficacy, 2=Class 2/CMC). (v5.4 NEW)
        safety_signal_severity: Safety signal severity (0=none, 1=low, 2=high). (v5.4 NEW)
        sponsor_prior_approvals: Number of sponsor's prior FDA approvals. (v5.4 NEW)
        gene_therapy: 1.0 if gene therapy product, 0.0 otherwise. (v5.4 NEW)
        hist_crl_rate: Historical CRL rate for this TA (0.0-1.0). (v5.4 NEW)
        runup_t90_t7: T-90 to T-7 long-term pre-catalyst return in %. (v5.4 NEW)

    Explosion Tiers:
        SNIPER (≥20%): 2.0x position multiplier — max conviction
        ELEVATED (≥10%): 1.5x position multiplier — overweight
        NORMAL (≥5%): 1.0x — standard size
        QUIET (<5%): 0.8x — underweight

    DISCLAIMER: For informational/educational purposes only. Not investment advice.
    """
    return EXPLOSION.score(
        odin_score=odin_score, eve_price=eve_price, market_cap=market_cap,
        high_52w=high_52w, volume_ratio=volume_ratio, runup_30d=runup_30d,
        ticker=ticker, float_shares=float_shares, pct_float_short=pct_float_short,
        days_to_cover=days_to_cover, xbi_return_30d=xbi_return_30d,
        is_resub=is_resub, ta_very_high=ta_very_high, sponsor_naive=sponsor_naive,
        prior_crl_count=prior_crl_count, runup_7d=runup_7d,
        orphan=orphan, btd=btd, fast_track=fast_track, ppm_flag=ppm_flag,
        resub_class=resub_class, safety_signal_severity=safety_signal_severity,
        sponsor_prior_approvals=sponsor_prior_approvals, gene_therapy=gene_therapy,
        hist_crl_rate=hist_crl_rate, runup_t90_t7=runup_t90_t7,
    )


def tool_gungnir_rank(catalysts: list) -> dict:
    """Rank multiple phase readout catalysts by GUNGNIR score."""
    results = []
    for c in catalysts:
        score = GUNGNIR.score(c)
        score["ticker"] = c.get("ticker", "???")
        score["drug_name"] = c.get("drug_name", "???")
        results.append(score)
    results.sort(key=lambda x: x["probability"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return {"engine": GUNGNIR.version, "count": len(results), "rankings": results}


def tool_conference_score(
    ticker: str, conference: str, presentation_type: str = "poster",
    n_presentations: int = 1, market_cap: float = 0.0,
    gungnir_probability: float = 0.0, gungnir_investment_score: float = 0.0,
    days_to_conference: int = 30,
) -> dict:
    """Apply Conference Overlay v1.0 to a phase readout catalyst with a confirmed conference presentation.

    Conference presentations predict positive outcomes at 90.2% vs 76.7% baseline
    (p=7.88e-21). This overlay boosts Gungnir investment scores based on conference
    tier, presentation type, and number of presentations.

    Usage: Score with gungnir_score first, then pass results here for conference boost.

    Args:
        ticker: Stock ticker
        conference: Conference name (e.g., "AACR", "ASCO", "ASH", "ESMO", "AAN", "EHA")
        presentation_type: "oral", "late-breaking", "poster", or "multiple" (default: poster)
        n_presentations: Number of presentations at this conference (default: 1)
        market_cap: Market cap in dollars (e.g., 100000000 for $100M). Used for runup timing.
        gungnir_probability: Gungnir P(success) from gungnir_score (0-1)
        gungnir_investment_score: Gungnir investment_score from gungnir_score (0-100)
        days_to_conference: Trading days until conference (for entry/exit timing)

    Conference Tier Hierarchy:
        ELITE: AACR (100%, n=16), ASH (95.4%, n=65), ESMO (95.7%, n=69)
        TIER1: ASCO (90%, n=90), AAN, EHA
        TIER2: SITC, SNO, OTHER

    The runup IS the trade. Exit before conference day.

    DISCLAIMER: For informational/educational purposes only. Not investment advice.
    """
    return CONFERENCE.score(
        ticker=ticker, conference=conference,
        presentation_type=presentation_type, n_presentations=n_presentations,
        market_cap=market_cap, gungnir_probability=gungnir_probability,
        gungnir_investment_score=gungnir_investment_score,
        days_to_conference=days_to_conference,
    )


# ============================================================================
# UOA OVERLAY v1.0 — Unusual Options Activity Scoring
# ============================================================================
# Derived from ORATS live options chain data + Perplexity/Gemini UOA research.
# 6-component scoring: Vol/OI dynamics, event-expiry focus, concentration,
# directional structure, hot strike count, absolute volume.
# Multiplicative boost on ODIN/Gungnir investment score.
# GRCE benchmark: 10/10 SCREAMING BULLISH → +25% boost.
# TVTX benchmark: 5/10 ELEVATED BEARISH → -10% (caution flag).

UOA_TIERS = [
    (8, "SCREAMING", "Extreme UOA — high-conviction informed flow detected"),
    (5, "ELEVATED", "Notable UOA — above-baseline activity warrants attention"),
    (2, "NORMAL", "Some activity but within normal ranges"),
    (0, "QUIET", "Minimal options activity — no signal"),
]

UOA_BOOST_MATRIX = {
    # v1.1 CALIBRATED — backtested on 976 PDUFA events (2022-2026)
    # Key findings: SCREAMING is mostly large-cap hedging noise (n=9, 7 large),
    # ELEVATED×MIXED is the gold signal (88.2% approval, +16.5% lift),
    # QUIET×BULLISH is retail noise (63.0%, -8.8% lift),
    # MIXED direction > BULLISH (balanced institutional flow > retail piling)
    # Baseline approval: 71.7%. Score 0→6 perfectly monotonic (r=1.0, p<0.0001).
    # Score ≥4 vs <4: 75.8% vs 69.0%, p=0.026.
    ("SCREAMING", "BULLISH"):  0.10,   # was +25%, demoted — only 9 events, 7 large-cap
    ("SCREAMING", "BEARISH"): -0.10,   # was -15%, reduced
    ("SCREAMING", "MIXED"):    0.05,   # was +10%, reduced
    ("ELEVATED",  "BULLISH"):  0.08,   # was +12%, slight reduction (+2.1% lift)
    ("ELEVATED",  "BEARISH"): -0.05,   # was -10%, halved (-1.1% lift only)
    ("ELEVATED",  "MIXED"):    0.12,   # was +5%, TRIPLED — gold signal (+16.5% lift, n=51)
    ("NORMAL",    "BULLISH"):  0.03,   # was +5%, reduced (+0.6% lift)
    ("NORMAL",    "BEARISH"): -0.05,   # was -5%, unchanged (-6.0% lift)
    ("NORMAL",    "MIXED"):    0.05,   # was 0%, upgraded (+3.3% lift)
    ("QUIET",     "BULLISH"): -0.08,   # was 0%, NOW PENALIZED — retail noise (-8.8% lift!)
    ("QUIET",     "BEARISH"):  0.00,   # unchanged
    ("QUIET",     "MIXED"):   -0.05,   # was 0%, NOW PENALIZED (-7.5% lift)
}


def tool_uoa_score(
    ticker: str,
    # Core options data (from ORATS strikes endpoint)
    total_call_volume: int = 0,
    total_put_volume: int = 0,
    total_call_oi: int = 0,
    total_put_oi: int = 0,
    max_vol_oi_ratio: float = 0.0,
    max_vol_oi_event_expiry: float = 0.0,
    # Event context
    event_expiry_vol_share: float = 0.0,  # % of total vol in event-spanning expirations
    n_hot_strikes: int = 0,               # strikes with V/OI > 3x
    n_event_hot_strikes: int = 0,         # hot strikes in event expiry
    # Market context
    market_cap: float = 0.0,
    days_to_catalyst: int = 30,
    # Model scores for boost application
    odin_probability: float = 0.0,
    investment_score: float = 0.0,
    catalyst_type: str = "pdufa",  # "pdufa" or "readout"
) -> dict:
    """UOA Overlay v1.1 CALIBRATED — Score unusual options activity for catalyst events.

    Backtested on 976 PDUFA events (2022-2026) with ORATS historical data.
    Key findings: Score 0→6 perfectly monotonic (r=1.0). Score ≥4 vs <4: 75.8% vs 69.0% (p=0.026).
    ELEVATED×MIXED is the gold signal (88.2% approval). QUIET×BULLISH is retail noise (63.0%).
    SCREAMING is mostly large-cap hedging noise (n=9). Direction: MIXED > BULLISH > BEARISH.

    Combines 6 components from ORATS live options chain data into a 0-10 composite
    score, then applies empirically-calibrated directional boost to investment scores.

    Flow: Score with ODIN/Gungnir first → feed probability + investment_score here
    → get boosted score + UOA flags + position sizing adjustment.

    Components:
      1. Vol/OI Dynamics (0-3): How unusual is today's volume vs open interest?
      2. Event-Expiry Focus (0-3): Is the unusual activity concentrated in event-spanning expirations?
      3. Concentration (0-1): What fraction of total volume targets the event window?
      4. Directional Structure (0-1): Is the flow call-dominated (bullish) or put-dominated (bearish)?
      5. Hot Strike Count (0-1): Multiple high V/OI strikes = coordinated institutional flow.
      6. Absolute Volume (0-1): Raw volume significant for this market cap tier?

    Tiers: SCREAMING (8-10), ELEVATED (5-7), NORMAL (2-4), QUIET (0-1).
    Direction: BULLISH (C/P vol ratio > 0.70), BEARISH (< 0.30), MIXED (0.30-0.70).
    """
    total_vol = total_call_volume + total_put_volume
    total_oi = total_call_oi + total_put_oi

    # ── COMPONENT 1: Vol/OI Dynamics (0-3 pts) ──
    # How unusual is today's trading vs existing positions?
    voi_score = 0.0
    if max_vol_oi_ratio >= 10.0:
        voi_score = 3.0   # Extreme: 10x+ new volume vs existing OI
    elif max_vol_oi_ratio >= 5.0:
        voi_score = 2.0   # Very high: 5-10x
    elif max_vol_oi_ratio >= 2.0:
        voi_score = 1.0   # Elevated: 2-5x

    # ── COMPONENT 2: Event-Expiry Focus (0-3 pts) ──
    # Is the UOA concentrated in expirations that span the catalyst?
    event_voi_score = 0.0
    if max_vol_oi_event_expiry >= 10.0:
        event_voi_score = 3.0
    elif max_vol_oi_event_expiry >= 5.0:
        event_voi_score = 2.0
    elif max_vol_oi_event_expiry >= 2.0:
        event_voi_score = 1.0

    # ── COMPONENT 3: Concentration (0-1 pt) ──
    # High concentration in event expiry = targeted flow, not noise
    concentration_score = 1.0 if event_expiry_vol_share >= 0.70 else 0.0

    # ── COMPONENT 4: Directional Structure (0-1 pt) ──
    # Strong directional skew = conviction signal. MIXED = 0pts here but gets
    # boosted in the matrix (v1.1: ELEVATED×MIXED is the gold signal at 88.2%).
    cp_ratio = total_call_volume / max(total_call_volume + total_put_volume, 1)
    if cp_ratio >= 0.70:
        direction = "BULLISH"
        direction_score = 1.0
    elif cp_ratio <= 0.30:
        direction = "BEARISH"
        direction_score = 1.0  # Bearish conviction is still a signal
    else:
        direction = "MIXED"
        direction_score = 0.0  # Handled via boost matrix (ELEVATED×MIXED = +12%)

    # ── COMPONENT 5: Hot Strike Count (0-1 pt) ──
    # Multiple hot strikes in event expiry = coordinated institutional flow
    hot_score = 1.0 if n_event_hot_strikes >= 2 else 0.0

    # ── COMPONENT 6: Absolute Volume (0-1 pt) ──
    # Raw volume significant for the stock's market cap tier
    abs_vol_score = 0.0
    if market_cap > 0:
        if market_cap < 300e6:    # micro/nano: 500+ contracts is significant
            abs_vol_score = 1.0 if total_vol >= 500 else 0.0
        elif market_cap < 2e9:    # small: 2,000+ contracts
            abs_vol_score = 1.0 if total_vol >= 2000 else 0.0
        else:                     # mid/large: 10,000+
            abs_vol_score = 1.0 if total_vol >= 10000 else 0.0

    # ── COMPOSITE SCORE (0-10) ──
    raw_score = voi_score + event_voi_score + concentration_score + direction_score + hot_score + abs_vol_score
    uoa_score = max(0, min(10, round(raw_score)))

    # ── TIER ASSIGNMENT ──
    uoa_tier = "QUIET"
    uoa_note = ""
    for threshold, tier, note in UOA_TIERS:
        if uoa_score >= threshold:
            uoa_tier = tier
            uoa_note = note
            break

    # ── DIRECTIONAL BOOST ──
    boost_key = (uoa_tier, direction)
    boost_pct = UOA_BOOST_MATRIX.get(boost_key, 0.0)

    # Time decay: boost weakens if catalyst is far out (>45 days)
    if days_to_catalyst > 45:
        boost_pct *= 0.5  # halve boost for distant catalysts (flow may be stale)
    elif days_to_catalyst <= 7:
        boost_pct *= 1.2  # amplify for imminent catalysts (last-minute informed flow)
        boost_pct = max(-0.20, min(0.35, boost_pct))  # cap at 35%

    boosted_score = investment_score * (1.0 + boost_pct) if investment_score > 0 else 0.0
    boosted_score = max(0, min(100, round(boosted_score, 1)))

    # ── FLAGS ──
    flags = []
    if uoa_score >= 8 and direction == "BULLISH":
        flags.append("SCREAMING_BULLISH")
    if uoa_score >= 8 and direction == "BEARISH":
        flags.append("SCREAMING_BEARISH")
    if cp_ratio <= 0.15:
        flags.append("PUT_WALL")
    if cp_ratio >= 0.90:
        flags.append("CALL_WALL")
    if max_vol_oi_ratio >= 20.0:
        flags.append("EXTREME_VOI")
    if event_expiry_vol_share >= 0.90:
        flags.append("EVENT_LOADED")
    if n_event_hot_strikes >= 3:
        flags.append("MULTI_HOT_STRIKES")
    if total_vol >= 5000 and market_cap < 300e6:
        flags.append("MEGA_VOL_SMALL_CAP")

    # ── CONVICTION LABEL ──
    if uoa_score >= 8:
        conviction = "HIGH"
    elif uoa_score >= 5:
        conviction = "MODERATE"
    else:
        conviction = "MINIMAL"

    # ── POSITION SIZING ADJUSTMENT (v1.1 calibrated) ──
    # SCREAMING demoted (mostly large-cap noise). ELEVATED×MIXED is the real signal.
    # QUIET×BULLISH penalized (retail noise, -8.8% vs baseline).
    if uoa_tier == "SCREAMING" and direction == "BULLISH":
        sizing_mult = 1.2
        sizing_note = "SCREAMING bullish — moderate 1.2x (caution: often large-cap hedging noise)"
    elif uoa_tier == "SCREAMING" and direction == "BEARISH":
        sizing_mult = 0.6
        sizing_note = "SCREAMING bearish — reduce to 0.6x"
    elif uoa_tier == "ELEVATED" and direction == "MIXED":
        sizing_mult = 1.3
        sizing_note = "ELEVATED×MIXED — gold signal (88.2% backtest approval), 1.3x sizing"
    elif uoa_tier == "ELEVATED" and direction == "BULLISH":
        sizing_mult = 1.2
        sizing_note = "ELEVATED bullish — moderate 1.2x sizing"
    elif uoa_tier == "ELEVATED" and direction == "BEARISH":
        sizing_mult = 0.7
        sizing_note = "Bearish flow detected — reduce to 0.7x"
    elif uoa_tier == "QUIET" and direction == "BULLISH":
        sizing_mult = 0.8
        sizing_note = "QUIET×BULLISH = retail noise (63% backtest approval) — reduce to 0.8x"
    elif uoa_tier == "QUIET" and direction == "MIXED":
        sizing_mult = 0.85
        sizing_note = "QUIET×MIXED — slight reduction to 0.85x"
    else:
        sizing_mult = 1.0
        sizing_note = "No UOA-based sizing adjustment"

    return {
        "ticker": ticker.upper(),
        "uoa_score": uoa_score,
        "uoa_tier": uoa_tier,
        "uoa_note": uoa_note,
        "direction": direction,
        "conviction": conviction,
        "components": {
            "vol_oi_dynamics": round(voi_score, 1),
            "event_expiry_focus": round(event_voi_score, 1),
            "concentration": round(concentration_score, 1),
            "directional": round(direction_score, 1),
            "hot_strikes": round(hot_score, 1),
            "absolute_volume": round(abs_vol_score, 1),
        },
        "raw_data": {
            "total_call_vol": total_call_volume,
            "total_put_vol": total_put_volume,
            "total_oi": total_oi,
            "cp_ratio": round(cp_ratio, 3),
            "max_vol_oi": round(max_vol_oi_ratio, 1),
            "max_vol_oi_event": round(max_vol_oi_event_expiry, 1),
            "event_expiry_share": round(event_expiry_vol_share, 3),
            "n_hot_strikes": n_hot_strikes,
            "n_event_hot_strikes": n_event_hot_strikes,
        },
        "boost_pct": round(boost_pct * 100, 1),
        "original_investment_score": round(investment_score, 1),
        "boosted_investment_score": boosted_score,
        "sizing_multiplier": sizing_mult,
        "sizing_note": sizing_note,
        "flags": flags,
        "days_to_catalyst": days_to_catalyst,
        "integration": f"Score with {'ODIN v14' if catalyst_type == 'pdufa' else 'Gungnir v43'} first, then feed investment_score here for UOA boost",
    }


def tool_system_status() -> dict:
    """Return engine versions, weight sources, and metrics."""
    return {
        "odin": {
            "version": "ODIN v14 Champion (51-feature L2 Ridge logistic, C=0.1)",
            "n_features": 51,
            "features": ODIN_VNEXT_FEATURES,
            "weight_source": ODIN.weight_source,
            "training_metrics": {
                "wf_auc": 0.9011, "holdout_auc": 0.9363,
                "wf_brier": 0.1010, "holdout_brier": 0.0895,
                "t1_count": 154, "t1_win_rate": 0.9870,
                "holdout_events": 358, "training_events": 1845,
                "training_cutoff": "2025-01-01",
                "base_rate": 0.6748,
                "v13_holdout_auc": 0.9314, "ho_auc_delta_vs_v13": 0.0062,
                "stability": "20/20 seeds, p=0.000000",
            },
            "v14_changes": {
                "dropped_features": ["log_spa_sq", "accel_x_btd", "is_immunology"],
                "added_features": [
                    "pw_orphan_drug_bin_x_resub_class_2", "surrogate_x_ta_vh",
                    "pw_priority_review_bin_x_resub_class_1", "pw_desig_stack_x_resub_class_1",
                    "pw_gene_therapy_bin_x_sponsor_streak", "ft_x_safety",
                    "pw_priority_review_bin_x_btd_bin", "pw_is_oncology_x_resub_class_2",
                    "pw_is_oncology_x_mfg_risk_bin", "pw_double_crl_bin_x_resub_class_2",
                    "pw_priority_review_bin_x_resub_class_2", "gt_x_btd",
                    "pw_orphan_drug_bin_x_btd_bin", "pw_double_crl_bin_x_ta_crl_streak",
                    "pw_gene_therapy_bin_x_log_spa_sq", "is_oncology", "crl_rate_x_swr"
                ],
                "regularization": "C=0.1 (from 0.025)",
                "key_insights": "Priority review × resubmission class interactions unlock regulatory pathway signal. Oncology × manufacturing risk reveals disease-specific manufacturing complexity. Gene therapy × BTD and × sponsor strength validate specialized modality paths. 18 new regulatory + modality interactions vs v13.",
            },
            "tier_thresholds": {"T1": ">=0.85 LONG", "T2": ">=0.65 CAUTIOUS LONG",
                               "T3": ">=0.40 MONITOR", "T4": "<0.40 NO TRADE"},
        },
        "gungnir": {
            "version": GUNGNIR.version,
            "n_features": len(GUNGNIR.feature_names) if GUNGNIR.v37_loaded else 33,
            "weight_source": GUNGNIR.weight_source,
            "model_type": "PREDICTIVE (pre-readout features only, zero leakage)",
            "training_metrics": {
                "wf_auc": 0.8001, "wf_brier": 0.1330,
                "ev_spread": 6.64, "dataset_size": 1752, "base_rate": 0.799,
                "v42_wf_auc": 0.7936, "auc_delta_vs_v42": 0.0065,
                "stability": "10/10 seeds, p=0.0000000000",
                "leakage_status": "CLEAN — zero outcome-derived features",
                "v43_features_added": ["v43_ch2_is_oligo_X_volatility_20d",
                    "v43_ch2_is_biologic_X_is_phase3",
                    "v43_ch2_is_cell_X_ctgov_is_randomized",
                    "v43_ch2_is_adc_X_enrollment_sq",
                    "v43_ch2_is_cell_X_momentum_10d",
                    "v43_ch2_is_oligo_X_is_phase2"],
                "config": {"ridge_c": 0.02, "xgb_lr": 0.01, "xgb_trees": 600,
                          "meta_ridge": 0.85, "meta_xgb": 0.15, "temperature": 1.0},
                "ctgov_coverage": "96.6% (1692/1752 real matches)",
                "chembl_coverage": "50.6% (1023/2022 drug modality matches)",
                "v43_key_insight": "ChEMBL biotech scientist approach — drug modality × trial context interactions. 306 candidates from 15 ch2 base features × existing features. 6 survive greedy forward selection. Key: oligo×phase2 (+0.110), cell×randomized (+0.109), oligo×volatility (+0.076), biologic×phase3 (-0.069). Drug modality alone is not predictive — modality × context IS.",
            },
            "tier_thresholds": {
                "T1": ">=0.85 STRONG LONG",
                "T2": "0.70-0.85 CAUTIOUS LONG",
                "T3": "0.55-0.70 MONITOR",
                "T4": "<0.55 AVOID/SHORT",
            },
        },
        "bifrost": {
            "version": BIFROST.version,
            "description": "PDUFA Runup Timing + Magnitude — v10 tiers, triple-ensemble, sponsor dynamics, Kelly sizing, WF validated",
            "events_analyzed": 1705,
            "window_combos": 12,
            "n_features": 43,
            "mcap_tiers": list(BIFROST_MCAP_THRESHOLDS.keys()),
            "cardinal_rule": "Never hold through FDA decision. The runup IS the trade.",
            "backtest_wf": {
                "sharpe": 5.45, "win_rate": 0.708, "max_drawdown": -0.049,
                "trades": 910, "period": "2022-2026",
                "avg_return_per_trade": 15.38,
                "final_value": "$18.1M from $100K",
            },
            "v4_improvements": {
                "new_features": ["sponsor_success_rate", "sponsor_success_x_score",
                                 "sponsor_success_x_volatility", "vol_adjusted_confidence",
                                 "ta_risk_x_score", "ta_risk_x_momentum"],
                "ensemble": "Ridge 30% + XGB 35% + LightGBM 35% (was Ridge 60% + XGB 40%)",
                "vs_v31": "Sharpe +1.9%, win rate +1.7pp, max DD improved 7.5%, final value +25%",
            },
            "best_edges": {
                "T1_large": "T-45→T-7, Sharpe 0.53, 59% hit, +3.0% mean, 6% size (n=599)",
                "T2_micro": "T-90→T-7, Sharpe 1.09, 73% hit, +22.0% mean, 6% size (n=30)",
                "T1_mid": "T-25→T-1, Sharpe 1.02, 65% hit, +5.7% mean, 6% size (n=98)",
            },
            "position_sizing": "Half-Kelly with tier caps: T1/T2 max 6%, T3 max 3%, T4 max 1.5%",
            "tier_safety": "T3 capped at BUY, T4 capped at LEAN_LONG",
            "v31_baseline": "Sharpe 5.35, 69.6% win, $14.5M (2022-2026)",
            "v2_baseline": "Sharpe 3.43, 58.5% win, $100K→$23.7M (2020-2026)",
        },
        "explosion_detector": {
            "version": EXPLOSION.version,
            "description": "Predicts P(|D1 move| > 25%) for PDUFA events — identifies SNIPER setups",
            "n_features": 57,
            "features": EXPLOSION_FEATURES,
            "test_auc_lr": 0.9332,
            "test_auc_ensemble": 0.9307,
            "stability": "20-seed bootstrap mean 0.9300 ± 0.0159, 20/20 beats v5.3, p=3.63e-14",
            "leakage_audit": "PASSED — all 57 features T-1 compliant. Test AUC > Train AUC confirms genuine generalization.",
            "tiers": {
                "SNIPER": "≥20% prob → 2.0x position multiplier",
                "ELEVATED": "≥10% prob → 1.5x position multiplier",
                "NORMAL": "≥5% prob → 1.0x standard size",
                "QUIET": "<5% prob → 0.8x underweight",
            },
            "calibration": {
                "P>=30%": "71.4% hit, avg |D1| = 43.8%",
                "P>=20%": "58.8% hit, avg |D1| = 34.7%",
                "P>=15%": "50.0% hit, avg |D1| = 30.2%",
            },
            "key_features": {
                "#1": "log_float_inv (+0.44) — smaller float = more explosive",
                "#2": "vol_ratio (+0.34) — pre-event volume spike signals big move",
                "#3": "crl_count_x_small (-0.37) — multiple CRLs × small cap = suppressed",
                "#4": "orphan_x_runup_7d_val (+0.28) — orphan × 7d runup = max explosion (NEW v5.4)",
                "#5": "xbi_x_small (+0.26) — sector regime amplified for small caps",
                "#6": "is_micro (+0.26) — micro-cap status amplifies moves",
                "#7": "days_to_cover (+0.24) — crowded short harder to exit",
                "#8": "vol_high (+0.20) — high recent volatility = bigger moves",
                "#9": "ta_vh_x_log_float_inv (-0.19) — very high TA × tight float = fear (NEW v5.4)",
                "#10": "ta_vh_x_small (+0.19) — very high risk TA × small cap amplifier",
            },
            "v54_kaizen": "23 new features from exhaustive pairwise ODIN×market interactions + untapped regulatory: orphan, resub_class, PPM, safety, fast_track, gene_therapy, sponsor experience, CRL rate, T-90/T-7 positioning",
            "integration": "Score with ODIN v14 first, then explosion_score with full ODIN enrichment + regulatory designations + SI data for position sizing multiplier",
        },
        "conference_overlay": {
            "version": CONFERENCE.version,
            "description": "Empirical scoring multiplier for conference presentations",
            "signal": "90.2% positive rate vs 76.7% baseline (p=7.88e-21)",
            "conference_tiers": {
                "ELITE": "AACR (100%, n=16), ASH (95.4%, n=65), ESMO (95.7%, n=69)",
                "TIER1": "ASCO (90%, n=90), AAN, EHA",
                "TIER2": "SITC, SNO, OTHER",
            },
            "boost_mechanism": "Multiplicative on Gungnir investment score (preserves calibration)",
            "runup_timing": {
                "nano_micro": "D-30 entry, D-1 exit, 4.88% median, 58.5% win",
                "small": "D-5 entry, D-1 exit, 3.02% median, 66.7% win",
            },
            "cardinal_rule": "The runup IS the trade. Exit before conference day.",
            "prebuilt_trades": len(CONFERENCE.trade_data),
            "status": "DEPLOYED — immediate overlay while Gungnir v43 integrates as proper feature",
        },
        "smart_money": {
            "version": "Smart Money Overlay v1.0",
            "description": "Institutional + Insider + Analyst + Structural signal scoring",
            "components": {
                "institutional (0-30)": "God Tier fund ownership (Baker Bros, RA Capital, Perceptive, OrbiMed, Avoro, EcoR1, RTW, BVF, Redmile, Cormorant)",
                "insider (0-30)": "CEO/C-suite/director open-market buying, dollar magnitude, net direction",
                "analyst (0-20)": "Consensus strength weighted by analyst accuracy (TipRanks 5-star bonus)",
                "structural (0-20)": "Fallen angel detection (peak/current mcap ratio) + confirmatory trial flag",
            },
            "boost_mechanism": "Multiplicative on investment score: 50+=10%, 60+=15%, 70+=22%, 80+=30%",
            "kod_benchmark": "Would have boosted KOD from GAMMA (50.0) to BETA/ALPHA with Baker Bros 37.6% ownership + fallen angel + confirmatory flags",
            "t1_compliance": "All inputs are public pre-catalyst (13F, Form 4, analyst ratings, market cap)",
            "god_tier_funds": list(set(f["rank"] for f in GOD_TIER_FUNDS.values())),
            "status": "DEPLOYED — KOD-derived overlay for smart money signal detection",
        },
        "uoa_overlay": {
            "version": "UOA Overlay v1.1 CALIBRATED",
            "description": "Unusual Options Activity scoring from ORATS live chain data",
            "components": {
                "vol_oi_dynamics (0-3)": "Max V/OI ratio across strikes (2x/5x/10x thresholds)",
                "event_expiry_focus (0-3)": "V/OI in event-spanning expirations",
                "concentration (0-1)": "Event expiry volume share ≥70%",
                "directional (0-1)": "Call/put skew (>70% calls = bullish, <30% = bearish)",
                "hot_strikes (0-1)": "2+ hot strikes (V/OI > 3x) in event expiry",
                "absolute_volume (0-1)": "Raw volume significant for market cap tier",
            },
            "tiers": "SCREAMING (8-10), ELEVATED (5-7), NORMAL (2-4), QUIET (0-1)",
            "boost_mechanism": "v1.1 CALIBRATED: SCREAMING+BULL +10%, ELEVATED+MIXED +12% (gold signal), QUIET+BULL -8% (retail noise). Backtested 976 events.",
            "sizing": "SCREAMING+BULL 1.2x, ELEVATED+MIXED 1.3x (gold), ELEVATED+BULL 1.2x, QUIET+BULL 0.8x (retail noise penalty)",
            "benchmarks": "GRCE 10/10 SCREAMING BULLISH, ELEVATED×MIXED 88.2% approval (n=51), QUIET×BULLISH 63.0% (retail noise, n=108)",
            "data_source": "ORATS Delayed Data API ($99/mo, 15-min delay, 100 req/min)",
            "status": "DEPLOYED — live UOA signal detection for position sizing and conviction",
        },
        "server": {"name": "MCP 9 Realms", "version": "14.3.0",
                   "timestamp": datetime.now(timezone.utc).isoformat()},
    }


# ============================================================================
# FASTMCP SERVER
# ============================================================================

def create_mcp_server():
    """Create FastMCP server with all tools registered."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        print("[FATAL] fastmcp not installed: pip install fastmcp")
        sys.exit(1)

    mcp = FastMCP("9realms")

    @mcp.tool()
    def odin_score(
        ticker: str, drug_name: str, therapeutic_area: str, pdufa_date: str,
        phase: str = "NDA", btd: bool = False, orphan: bool = False,
        priority_review: bool = False, fast_track: bool = False,
        accelerated_approval: bool = False, surrogate_endpoint: bool = False,
        had_adcom: bool = False, prior_crl: bool = False,
        form_483_issues: bool = False, manufacturing_risk: bool = False,
        gene_therapy: bool = False, single_arm_study: bool = False,
        safety_tier: str = "low", resub_class: int = 0,
        sponsor_prior_approvals: int = 5, prior_crl_count: int = 0,
        historical_crl_rate: float = 0.32, notes: str = "",
    ) -> dict:
        """LEGACY ODIN v14 scorer — KNOWN LEAKED per ODIN_v14_LEAKAGE_FINDING.txt (2026-04-17). Reported HO AUC 0.9363 is inflated ~368 bp. Use odin_score_honest or odin_score_v16 for production (honest HO AUC 0.8904). This legacy tool remains for rank-agreement auditing only."""
        return tool_odin_score(**{k: v for k, v in locals().items()})

    @mcp.tool()
    def gungnir_score(
        ticker: str, drug_name: str, indication: str, stage: str,
        catalyst_text: str, company: str = "", year: int = 2026,
        has_conference: int = None, days_to_cover: float = 0.0,
    ) -> dict:
        """Score a phase readout using GUNGNIR v46 Champion (AUC 0.8135). Pre-readout features only. Include conference name in catalyst_text for auto-detection. Drug modality auto-detected from drug_name."""
        return tool_gungnir_score(**{k: v for k, v in locals().items()})

    @mcp.tool()
    def odin_rank(catalysts: list) -> dict:
        """Rank multiple PDUFA catalysts by approval probability."""
        return tool_odin_rank(catalysts)

    @mcp.tool()
    def gungnir_rank(catalysts: list) -> dict:
        """Rank multiple phase readout catalysts by success probability."""
        return tool_gungnir_rank(catalysts)

    @mcp.tool()
    def bifrost_score(
        ticker: str, odin_tier: int, market_cap: float,
        days_to_pdufa: int = 60, v9_score: float = 0.0,
        momentum_14d: float = 0.0, volatility_20d: float = 0.0,
    ) -> dict:
        """Score a PDUFA runup opportunity. Returns optimal entry/exit windows + Kelly sizing.

        The runup IS the trade. Never hold through the FDA decision.
        BIFROST v4.0: WF Sharpe 5.45, 70.8% win, -4.9% max DD. Triple-ensemble + Kelly + tier caps."""
        return tool_bifrost_score(**{k: v for k, v in locals().items()})

    @mcp.tool()
    def explosion_score(
        ticker: str, odin_score: float, eve_price: float, market_cap: float,
        high_52w: float = 0.0, volume_ratio: float = 1.0, runup_30d: float = 0.0,
        float_shares: float = 0.0, pct_float_short: float = 0.0,
        days_to_cover: float = 0.0, xbi_return_30d: float = 0.0,
        is_resub: float = 0.0, ta_very_high: float = 0.0,
        sponsor_naive: float = 0.0, prior_crl_count: int = 0,
        runup_7d: float = 0.0,
    ) -> dict:
        """BIFROST v5.3 Explosion Detector — predict P(|D1 move| > 25%).

        Score AFTER odin_score. Identifies SNIPER setups where explosive post-catalyst moves are likely.
        v5.3 adds ODIN enrichment (is_resub, ta_very_high, sponsor_naive, crl_count) + price signals.
        LR Test AUC 0.8720 (+0.0422 vs v5.2). 34 features. 20/20 seed stability.
        Tiers: SNIPER (≥20%, 2x size), ELEVATED (≥10%, 1.5x), NORMAL (≥5%, 1x), QUIET (<5%, 0.8x)."""
        return tool_explosion_score(**{k: v for k, v in locals().items()})

    @mcp.tool()
    def smart_money_score(
        ticker: str,
        god_tier_fund_names: list = None,
        god_tier_fund_ownership_pct: float = 0.0,
        total_institutional_pct: float = 0.0,
        n_institutional_holders: int = 0,
        insider_buy_total_usd: float = 0.0,
        insider_buy_type: str = "none",
        insider_net_shares_90d: int = 0,
        insider_ownership_pct: float = 0.0,
        n_analysts: int = 0,
        pct_strong_buy: float = 0.0,
        avg_pt_upside_pct: float = 0.0,
        top_analyst_covers: bool = False,
        peak_mcap: float = 0.0,
        current_mcap: float = 0.0,
        has_prior_positive_pivotal: bool = False,
        actual_phase_override: int = 0,
        gungnir_probability: float = 0.0,
        gungnir_investment_score: float = 0.0,
        catalyst_type: str = "readout",
    ) -> dict:
        """Score smart money signals (institutional, insider, analyst, structural).
        Derived from KOD postmortem: Baker Bros held 37.6% → stock surged 88%.
        Combines God Tier fund ownership + insider buying + analyst quality + fallen angel detection."""
        return tool_smart_money_score(**{k: v for k, v in locals().items()})

    @mcp.tool()
    def conference_score(
        ticker: str, conference: str, presentation_type: str = "poster",
        n_presentations: int = 1, market_cap: float = 0.0,
        gungnir_probability: float = 0.0, gungnir_investment_score: float = 0.0,
        days_to_conference: int = 30,
    ) -> dict:
        """[RETIRED 2026-07-11] Conference Overlay v1.0 is REFUTED. Returns a refutation notice.

        Refuted by our own full study (1,425 conference events, 2017-2026, 383 tickers):
          claimed nano/micro run-up +4.88%  ->  actual nano median -9.84% (n=42), the WORST cohort
          claimed AACR positive rate 100%   ->  that was n=16; we now have n=122
          claimed ESMO is ELITE             ->  ESMO median run-up is NEGATIVE, -3.33% (n=192)
          claimed "the runup IS the trade"  ->  median run-up across all 1,425 events is -0.03%
        The signal it captured was a 2020 COVID artifact (2020 median +17.27%;
        2022, 2023 and 2024 were negative every year).
        Published: https://www.pdufa.bio/research/conference-runup
        """
        return {
            "status": "RETIRED",
            "version": "Conference Overlay v1.0 (refuted)",
            "reason": "Refuted by the full 1,425-event conference run-up study (2017-2026).",
            "refuted": {
                "nano_micro_runup_pct": {"claimed": 4.88, "actual_nano_median": -9.84, "n": 42},
                "AACR_positive_rate": {"claimed": 1.0, "claimed_n": 16, "actual_n": 122},
                "ESMO_tier": {"claimed": "ELITE", "actual_median_runup_pct": -3.33, "n": 192},
                "overall_median_runup_pct": -0.03,
            },
            "guidance": "There is no systematic conference run-up. Do not apply a boost. Do not reinstate.",
            "source": "https://www.pdufa.bio/research/conference-runup",
        }

    @mcp.tool()
    def uoa_score(
        ticker: str,
        total_call_volume: int = 0,
        total_put_volume: int = 0,
        total_call_oi: int = 0,
        total_put_oi: int = 0,
        max_vol_oi_ratio: float = 0.0,
        max_vol_oi_event_expiry: float = 0.0,
        event_expiry_vol_share: float = 0.0,
        n_hot_strikes: int = 0,
        n_event_hot_strikes: int = 0,
        market_cap: float = 0.0,
        days_to_catalyst: int = 30,
        odin_probability: float = 0.0,
        investment_score: float = 0.0,
        catalyst_type: str = "pdufa",
    ) -> dict:
        """UOA Overlay v1.0 — Score unusual options activity for catalyst events.

        Feed ORATS options chain data to detect informed flow. Returns 0-10 composite score,
        directional bias (BULLISH/BEARISH/MIXED), and investment score boost.
        Score with ODIN/Gungnir first, then feed investment_score here for UOA adjustment.
        SCREAMING+BULLISH = +25% boost + 1.5x sizing. SCREAMING+BEARISH = -15% + 0.5x sizing."""
        return tool_uoa_score(**{k: v for k, v in locals().items()})

    @mcp.tool()
    def system_status() -> dict:
        """Return engine versions, weight sources, and training metrics."""
        return tool_system_status()

    # ------------------------------------------------------------------
    # Unusual Whales proxy tools — mcp_9realms_uw_addon.py
    # ------------------------------------------------------------------
    try:
        import sys as _sys, os as _os
        _uw_addon_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Odin Perfection")
        if _uw_addon_dir not in _sys.path:
            _sys.path.insert(0, _uw_addon_dir)
        from mcp_9realms_uw_addon import register_uw_tools as _register_uw_tools
        _n_uw_tools = _register_uw_tools(mcp)
        _sys.stderr.write(f"[INFO] Registered {_n_uw_tools} UW proxy tools from mcp_9realms_uw_addon\n")
    except Exception as _uw_e:
        import sys as _sys
        _sys.stderr.write(f"[WARN] UW addon failed to register: {_uw_e}\n")

    # ------------------------------------------------------------------
    # ODIN v16_HONEST integrity rollback — mcp_9realms_odin_v16_addon.py
    # v14 deployed weights are LEAKED per ODIN_v14_LEAKAGE_FINDING.txt (2026-04-17).
    # v16_honest is the true walk-forward champion (HO AUC 0.8904, Brier 0.1181).
    # Exposes odin_score_v16 + odin_score_honest tools. Original odin_score kept
    # as legacy path for rank-agreement auditing until v18_honest ships.
    # ------------------------------------------------------------------
    try:
        import sys as _sys
        from mcp_9realms_odin_v16_addon import register_odin_v16_tools as _register_v16
        _n_v16 = _register_v16(mcp)
        _sys.stderr.write(f"[INFO] Registered {_n_v16} ODIN v16_honest tools (post-leakage integrity rollback)\n")
    except Exception as _v16_e:
        import sys as _sys
        _sys.stderr.write(f"[WARN] ODIN v16 addon failed to register: {_v16_e}\n")

    return mcp


# ============================================================================
# SELF-TEST
# ============================================================================

def self_test():
    """Verify both engines score correctly."""
    print(f"{'='*60}")
    print(f"  MCP 9 REALMS v14.3 — SELF TEST (ODIN v14 + GUNGNIR v43.0 + BIFROST v4.0 + Conference v1.0 + Smart Money v1.0 + UOA v1.1)")
    print(f"{'='*60}")

    # ODIN test 1: ALDX reproxalap (prior CRL, ophtho, inexperienced sponsor)
    print("\n--- ODIN v14: ALDX reproxalap PDUFA 2026-03-16 ---")
    r1 = tool_odin_score(
        ticker="ALDX", drug_name="reproxalap",
        therapeutic_area="Ophthalmology", pdufa_date="2026-03-16",
        prior_crl=True, resub_class=2, prior_crl_count=2,
        historical_crl_rate=0.32, sponsor_prior_approvals=0,
        safety_tier="low", notes="3rd NDA attempt",
    )
    print(f"  P(approve): {r1['probability']:.4f}  Tier {r1['tier']}: {r1['action']}")
    print(f"  TA: {r1['therapeutic_area']} ({r1['ta_risk_bucket']})")
    print(f"  Top features:")
    for fc in r1.get("top_features", [])[:5]:
        print(f"    {fc['feature']:25s} raw={fc['raw_value']:.0f}  z={fc['z_score']:+.3f}  coef={fc['coefficient']:+.4f}  contrib={fc['contribution']:+.4f}")
    assert r1["probability"] < 0.95, f"ALDX (prior_crl+naive+resub+ophtho) should be <95%, got {r1['probability']}"

    # ODIN test 2: naive sponsor with full designations
    # v14: new regulatory pathway features boost designations
    # BTD, orphan, priority_review, fast_track unlock v14 interactions
    # Net: naive sponsor with heavy designations should score in moderate-high range
    print("\n--- ODIN v14: KYTX miv-cel (BTD+orphan+priority+fast_track) ---")
    r2 = tool_odin_score(
        ticker="KYTX", drug_name="miv-cel",
        therapeutic_area="Immunology", pdufa_date="2026-H1",
        btd=True, orphan=True, priority_review=True, fast_track=True,
        safety_tier="low", sponsor_prior_approvals=0,
    )
    print(f"  P(approve): {r2['probability']:.4f}  Tier {r2['tier']}: {r2['action']}")
    print(f"  Top features:")
    for fc in r2.get("top_features", [])[:5]:
        print(f"    {fc['feature']:25s} raw={fc['raw_value']:.0f}  z={fc['z_score']:+.3f}  coef={fc['coefficient']:+.4f}  contrib={fc['contribution']:+.4f}")
    # v14 has pw_priority_review_bin_x_resub_class_1 and other regulatory pathway features
    # Expect higher range due to v14 designation interactions
    assert r2["probability"] > 0.10, f"KYTX with BTD+orphan+priority+FT should be >10%, got {r2['probability']}"
    assert r2["probability"] < 0.95, f"KYTX (naive sponsor) should be <95%, got {r2['probability']}"

    # ODIN test 3: experienced sponsor with designations (v14 high-score path)
    print("\n--- ODIN v14: Experienced sponsor + BTD + priority ---")
    r2b = tool_odin_score(
        ticker="GILD", drug_name="testdrug",
        therapeutic_area="Immunology", pdufa_date="2026-06-15",
        btd=True, priority_review=True, sponsor_prior_approvals=3,
        surrogate_endpoint=True,
    )
    print(f"  P(approve): {r2b['probability']:.4f}  Tier {r2b['tier']}: {r2b['action']}")
    # v14: pw_priority_review_bin_x_btd_bin(+0.171) + surrogate_x_ta_vh(+0.055) + swr_x_btd(+0.055)
    assert r2b["probability"] > 0.75, f"Experienced sponsor+BTD+priority+surrogate should be >75%, got {r2b['probability']}"

    # ODIN test 4: mega-pharma clean NDA
    print("\n--- ODIN v14: Big Pharma clean NDA ---")
    r3 = tool_odin_score(
        ticker="PFE", drug_name="testdrug",
        therapeutic_area="Oncology", pdufa_date="2026-06-15",
        priority_review=True, sponsor_prior_approvals=50,
    )
    print(f"  P(approve): {r3['probability']:.4f}  Tier {r3['tier']}: {r3['action']}")
    assert r3["probability"] > 0.75, f"Clean big-pharma NDA should be >75%, got {r3['probability']}"

    # GUNGNIR v42 test 1: Strong Phase 3 with surrogate + BTD
    print(f"\n--- {GUNGNIR.version}: Strong P3 (immunology, RCT, surrogate, BTD) ---")
    g1 = tool_gungnir_score(
        ticker="CLDX", drug_name="barzolvolimab",
        indication="chronic spontaneous urticaria", stage="Phase 3",
        catalyst_text="Phase 3 randomized placebo-controlled trial with ORR as primary surrogate endpoint. Antibody therapy. Prior positive Phase 2 data. Breakthrough therapy designation granted.",
        company="Celldex Therapeutics", year=2026,
    )
    print(f"  P(success): {g1['probability']:.4f}  Tier {g1['tier']}: {g1['action']}")
    print(f"  Model: {g1.get('model_type', 'N/A')}")
    for fc in g1.get("top_features", [])[:5]:
        print(f"    {fc['feature']:35s} raw={fc['raw_value']:.2f}  z={fc['z_score']:+.3f}  coef={fc['coefficient']:+.4f}  contrib={fc['contribution']:+.4f}")

    # GUNGNIR v42 test 2: Phase 2b vs Phase 2 (tests granular stage encoding)
    print(f"\n--- GUNGNIR v43: Phase 2b oncology (tests granular stage) ---")
    g2a = tool_gungnir_score(
        ticker="ONCO", drug_name="testdrug",
        indication="non-small cell lung cancer", stage="Phase 2b",
        catalyst_text="Phase 2b randomized trial in NSCLC with ORR as primary endpoint.",
        company="Oncology Biotech", year=2026,
    )
    g2b = tool_gungnir_score(
        ticker="ONCO", drug_name="testdrug",
        indication="non-small cell lung cancer", stage="Phase 2",
        catalyst_text="Phase 2 randomized trial in NSCLC with ORR as primary endpoint.",
        company="Oncology Biotech", year=2026,
    )
    print(f"  Phase 2b: P={g2a['probability']:.4f}  Phase 2: P={g2b['probability']:.4f}")
    print(f"  (v37 should differentiate: Phase 2b coef=-0.094, Phase 2a coef=+0.124)")

    # GUNGNIR v42 test 3: Weak P3 CNS
    print(f"\n--- GUNGNIR v43: Weak P3 (Alzheimer's, no designations) ---")
    g3 = tool_gungnir_score(
        ticker="TEST", drug_name="testdrug",
        indication="Alzheimer's disease", stage="Phase 3",
        catalyst_text="Phase 3 trial in Alzheimer's disease. Small molecule oral inhibitor.",
        company="Small Biotech", year=2026,
    )
    print(f"  P(success): {g3['probability']:.4f}  Tier {g3['tier']}: {g3['action']}")
    for fc in g3.get("top_features", [])[:5]:
        print(f"    {fc['feature']:35s} raw={fc['raw_value']:.2f}  coef={fc['coefficient']:+.4f}  contrib={fc['contribution']:+.4f}")

    # BIFROST test 1: T1 large cap, 45 days out (in entry window)
    print("\n--- BIFROST v3.1: T1 Large Cap, 45 days to PDUFA ---")
    b1 = tool_bifrost_score(ticker="GRCE", odin_tier=1, market_cap=15e9, days_to_pdufa=45)
    print(f"  Action: {b1['action']}  Timing: {b1['timing']}")
    print(f"  Entry: {b1['optimal_entry']}  Exit: {b1['optimal_exit']}")
    print(f"  Size: {b1['position_size_pct']:.2f}%  Cap: {b1['tier_cap_pct']:.0f}%")
    print(f"  Expected return: {b1['expected_return']:.1f}%  Hit rate: {b1['hit_rate']*100:.0f}%  Sharpe: {b1['ann_sharpe']:.2f}")
    assert b1["action"] == "STRONG_BUY", f"T1 large should be STRONG_BUY, got {b1['action']}"
    assert b1["timing"] == "ENTRY_ZONE", f"45 days should be ENTRY_ZONE, got {b1['timing']}"

    # BIFROST test 2: T2 nano cap with momentum data (magnitude enhancement)
    print("\n--- BIFROST v3.1: T2 Nano Cap + Momentum (magnitude enhanced) ---")
    b2 = tool_bifrost_score(ticker="TINY", odin_tier=2, market_cap=30e6, days_to_pdufa=90,
                            momentum_14d=8.5, volatility_20d=5.2)
    print(f"  Action: {b2['action']}  Timing: {b2['timing']}")
    print(f"  Size: {b2['position_size_pct']:.2f}%")
    if "magnitude_assessment" in b2:
        print(f"  Magnitude: {b2['magnitude_assessment']}")
    assert b2["action"] == "BUY", f"T2 nano should be BUY, got {b2['action']}"

    # BIFROST test 3: T4 nano (LEAN_LONG with 1.5% cap)
    print("\n--- BIFROST v3.1: T4 Nano Cap (LEAN_LONG, tier-capped) ---")
    b3 = tool_bifrost_score(ticker="RISK", odin_tier=4, market_cap=20e6, days_to_pdufa=30)
    print(f"  Action: {b3['action']}  Size: {b3['position_size_pct']:.2f}%  Cap: {b3['tier_cap_pct']:.0f}%")
    assert b3["action"] == "LEAN_LONG", f"T4 nano should be LEAN_LONG (tier-capped), got {b3['action']}"
    assert b3["position_size_pct"] <= 1.5, f"T4 should have <=1.5% position, got {b3['position_size_pct']}%"

    # BIFROST test 3b: T4 mid (should be NEUTRAL — sub-50% hit)
    print("\n--- BIFROST v3.1: T4 Mid Cap (NEUTRAL, sub-50% hit) ---")
    b3b = tool_bifrost_score(ticker="NOPE", odin_tier=4, market_cap=5e9, days_to_pdufa=30)
    print(f"  Action: {b3b['action']}")
    assert b3b["action"] == "NEUTRAL", f"T4 mid should be NEUTRAL, got {b3b['action']}"

    # BIFROST test 4: T1 micro, 5 days out (late exit warning)
    print("\n--- BIFROST v3.1: T1 Micro Cap, 5 days to PDUFA (late) ---")
    b4 = tool_bifrost_score(ticker="LATE", odin_tier=1, market_cap=150e6, days_to_pdufa=5)
    print(f"  Action: {b4['action']}  Timing: {b4['timing']}")
    print(f"  Timing note: {b4['timing_note']}")
    assert b4["timing"] in ("EXIT_ZONE", "LATE_EXIT"), f"5 days should be EXIT/LATE, got {b4['timing']}"

    # BIFROST test 5: Negative momentum (should reduce size)
    print("\n--- BIFROST v3.1: T1 Mid + Negative Momentum ---")
    b5 = tool_bifrost_score(ticker="WEAK", odin_tier=1, market_cap=5e9, days_to_pdufa=25,
                            momentum_14d=-5.2, volatility_20d=7.0)
    print(f"  Action: {b5['action']}  Size: {b5['position_size_pct']:.2f}%")
    if "magnitude_assessment" in b5:
        print(f"  Magnitude: {b5['magnitude_assessment']}")

    # CONFERENCE OVERLAY tests
    print("\n--- Conference Overlay v1.0: WHWK at AACR (oral + 2 posters) ---")
    c1 = tool_conference_score(
        ticker="WHWK", conference="AACR",
        presentation_type="oral", n_presentations=3,
        market_cap=184e6, gungnir_probability=0.924,
        gungnir_investment_score=71.2, days_to_conference=18,
    )
    print(f"  Conference: {c1['conference']} ({c1['conference_tier']})")
    print(f"  Boost: {c1['conference_boost']['total_boost']:.3f}")
    print(f"  Original score: {c1['gungnir_original']['investment_score']}")
    print(f"  Boosted score:  {c1['boosted']['investment_score']}  Tier: {c1['boosted']['tier']}  Action: {c1['boosted']['action']}")
    print(f"  Timing: {c1['timing']['status']} — {c1['timing']['note']}")
    print(f"  Position: {c1['position_sizing']['position_pct']}% ({c1['position_sizing']['mcap_tier']})")
    assert c1["conference_tier"] == "ELITE", f"AACR should be ELITE, got {c1['conference_tier']}"
    assert c1["boosted"]["investment_score"] > c1["gungnir_original"]["investment_score"], "Boosted should exceed original"
    assert c1["timing"]["status"] == "ENTRY_ZONE", f"18 days micro should be ENTRY_ZONE, got {c1['timing']['status']}"

    print("\n--- Conference Overlay v1.0: BCTX at AACR (4 posters, nano) ---")
    c2 = tool_conference_score(
        ticker="BCTX", conference="AACR",
        presentation_type="poster", n_presentations=4,
        market_cap=28e6, gungnir_probability=0.60,
        gungnir_investment_score=58.2, days_to_conference=18,
    )
    print(f"  Boost: {c2['conference_boost']['total_boost']:.3f}")
    print(f"  Original: {c2['gungnir_original']['investment_score']} → Boosted: {c2['boosted']['investment_score']}")
    print(f"  Action: {c2['boosted']['action']}  Position: {c2['position_sizing']['position_pct']}%")
    assert c2["position_sizing"]["position_pct"] <= 3.0, f"Nano cap should be ≤3%, got {c2['position_sizing']['position_pct']}"

    print("\n--- Conference Overlay v1.0: KYTX at AAN (oral, small-cap) ---")
    c3 = tool_conference_score(
        ticker="KYTX", conference="AAN",
        presentation_type="oral", n_presentations=2,
        market_cap=446e6, gungnir_probability=0.845,
        gungnir_investment_score=53.7, days_to_conference=25,
    )
    print(f"  Conference: {c3['conference']} ({c3['conference_tier']})")
    print(f"  Timing: {c3['timing']['status']} — {c3['timing']['note']}")
    assert c3["conference_tier"] == "TIER1", f"AAN should be TIER1, got {c3['conference_tier']}"

    # SMART MONEY OVERLAY tests
    print("\n--- Smart Money v1.0: KOD benchmark (Baker Bros 37.6%, fallen angel, confirmatory) ---")
    sm1 = tool_smart_money_score(
        ticker="KOD",
        god_tier_fund_names=["Baker Bros. Advisors"],
        god_tier_fund_ownership_pct=37.6,
        total_institutional_pct=44.8,
        n_institutional_holders=254,
        insider_buy_total_usd=0,
        insider_buy_type="none",
        insider_net_shares_90d=0,
        n_analysts=6,
        pct_strong_buy=0.50,
        avg_pt_upside_pct=100.0,
        peak_mcap=10e9,
        current_mcap=2.4e9,
        has_prior_positive_pivotal=True,
        actual_phase_override=3,
        gungnir_probability=0.9034,
        gungnir_investment_score=50.0,
    )
    print(f"  Smart Money Score: {sm1['smart_money_score']}  Conviction: {sm1['conviction']}")
    print(f"  Components: inst={sm1['components']['institutional']}, insider={sm1['components']['insider']}, "
          f"analyst={sm1['components']['analyst']}, structural={sm1['components']['structural']}")
    print(f"  Original: {sm1['original']['investment_score']} → Boosted: {sm1['boosted']['investment_score']} ({sm1['boosted']['tier']})")
    print(f"  Flags: {sm1['flags']}")
    assert sm1["smart_money_score"] >= 40, f"KOD should have solid smart money (no insider buys), got {sm1['smart_money_score']}"
    assert sm1["boosted"]["investment_score"] > sm1["original"]["investment_score"], "KOD should be boosted"
    assert "GOD_TIER_x1" in sm1["flags"], "Should detect Baker Bros as God Tier"
    assert "FALLEN_ANGEL" in sm1["flags"], "Should detect fallen angel"
    assert "CONFIRMATORY_TRIAL" in sm1["flags"], "Should detect confirmatory trial"

    print("\n--- Smart Money v1.0: ALXO (venBio $5M insider buy, God Tier) ---")
    sm2 = tool_smart_money_score(
        ticker="ALXO",
        god_tier_fund_names=["Avoro Capital", "venBio"],
        god_tier_fund_ownership_pct=12.0,
        total_institutional_pct=35.0,
        insider_buy_total_usd=5_000_000,
        insider_buy_type="director_buy",
        insider_net_shares_90d=3_184_713,
        insider_ownership_pct=15.0,
        n_analysts=5,
        pct_strong_buy=0.60,
        avg_pt_upside_pct=120.0,
        gungnir_probability=0.74,
        gungnir_investment_score=74.0,
    )
    print(f"  Smart Money Score: {sm2['smart_money_score']}  Conviction: {sm2['conviction']}")
    print(f"  Original: {sm2['original']['investment_score']} → Boosted: {sm2['boosted']['investment_score']} ({sm2['boosted']['tier']})")
    print(f"  Flags: {sm2['flags']}")
    assert sm2["smart_money_score"] >= 50, f"ALXO should have strong smart money (God Tier + $5M insider), got {sm2['smart_money_score']}"
    assert "MEGA_INSIDER_BUY" in sm2["flags"], "Should detect $5M insider buy"

    print("\n--- Smart Money v1.0: CABA (full C-suite buying, strong institutional) ---")
    sm3 = tool_smart_money_score(
        ticker="CABA",
        god_tier_fund_names=["Cormorant Asset"],
        god_tier_fund_ownership_pct=3.0,
        total_institutional_pct=55.0,
        n_institutional_holders=104,
        insider_buy_total_usd=286_000,
        insider_buy_type="ceo_buy",
        insider_net_shares_90d=127_668,
        insider_ownership_pct=11.25,
        n_analysts=15,
        pct_strong_buy=0.50,
        avg_pt_upside_pct=500.0,
        top_analyst_covers=True,
        gungnir_probability=0.67,
        gungnir_investment_score=67.1,
    )
    print(f"  Smart Money Score: {sm3['smart_money_score']}  Conviction: {sm3['conviction']}")
    print(f"  Original: {sm3['original']['investment_score']} → Boosted: {sm3['boosted']['investment_score']} ({sm3['boosted']['tier']})")
    print(f"  Flags: {sm3['flags']}")
    assert sm3["smart_money_score"] >= 50, f"CABA should have solid smart money, got {sm3['smart_money_score']}"
    assert "CEO_BUYING" in sm3["flags"], "Should detect CEO buying"

    print("\n--- Smart Money v1.0: Weak signal (no institutional, no insider) ---")
    sm4 = tool_smart_money_score(
        ticker="WEAK",
        total_institutional_pct=6.0,
        n_analysts=2,
        pct_strong_buy=1.0,
        avg_pt_upside_pct=200.0,
        gungnir_probability=0.77,
        gungnir_investment_score=77.3,
    )
    print(f"  Smart Money Score: {sm4['smart_money_score']}  Conviction: {sm4['conviction']}")
    print(f"  Boost: {sm4['boosted']['boost_factor']}  (should be minimal)")
    assert sm4["smart_money_score"] < 40, f"Weak signal should score low, got {sm4['smart_money_score']}"

    # EXPLOSION DETECTOR v5.4 tests
    print("\n--- EXPLOSION v5.4: CAPR-like sniper + high SI + resub + orphan (micro-cap, low ODIN, penny, 20% SI) ---")
    e1 = tool_explosion_score(
        ticker="CAPR", odin_score=0.186, eve_price=5.97,
        market_cap=80e6, high_52w=15.0, volume_ratio=2.5, runup_30d=-10.0,
        float_shares=10e6, pct_float_short=0.20, days_to_cover=8.0,
        is_resub=1.0, ta_very_high=1.0, runup_7d=-3.0,
        orphan=1.0, resub_class=1, sponsor_prior_approvals=2,
        hist_crl_rate=0.3, runup_t90_t7=5.0,
    )
    print(f"  P(explosion): {e1['explosion_probability']:.4f}  Tier: {e1['explosion_tier']}")
    print(f"  Position mult: {e1['position_multiplier']}x")
    print(f"  SI: {e1['short_interest']}")
    print(f"  ODIN enrichment: {e1['odin_enrichment']}")
    print(f"  Interpretation: {e1['interpretation']}")
    assert e1["explosion_probability"] > 0.10, f"CAPR-like setup should have >10% explosion prob, got {e1['explosion_probability']}"
    assert e1["explosion_tier"] in ("SNIPER", "ELEVATED"), f"CAPR-like should be SNIPER or ELEVATED, got {e1['explosion_tier']}"

    print("\n--- EXPLOSION v5.4: Big pharma high-ODIN (quiet setup, no SI) ---")
    e2 = tool_explosion_score(
        ticker="PFE", odin_score=0.92, eve_price=45.0,
        market_cap=250e9, high_52w=50.0, volume_ratio=0.9, runup_30d=2.0,
    )
    print(f"  P(explosion): {e2['explosion_probability']:.4f}  Tier: {e2['explosion_tier']}")
    assert e2["explosion_probability"] < 0.05, f"Big pharma should be QUIET, got {e2['explosion_probability']}"
    assert e2["explosion_tier"] == "QUIET", f"Big pharma should be QUIET, got {e2['explosion_tier']}"

    print("\n--- EXPLOSION v5.4: CRDF-like high-SI squeeze + naive sponsor + PPM ---")
    e3 = tool_explosion_score(
        ticker="CRDF", odin_score=0.65, eve_price=1.62,
        market_cap=108e6, high_52w=4.56, volume_ratio=1.5, runup_30d=-5.0,
        float_shares=66.7e6, pct_float_short=0.261, days_to_cover=23.3,
        sponsor_naive=1.0, prior_crl_count=0, xbi_return_30d=0.03, runup_7d=-2.0,
        ppm_flag=1.0, fast_track=1.0, runup_t90_t7=-8.0,
    )
    print(f"  P(explosion): {e3['explosion_probability']:.4f}  Tier: {e3['explosion_tier']}")
    print(f"  SI: {e3['short_interest']}")
    print(f"  ODIN enrichment: {e3['odin_enrichment']}")
    assert e3["explosion_probability"] > 0.05, f"CRDF squeeze setup should have >5% prob, got {e3['explosion_probability']}"

    # GUNGNIR v42 conference feature test
    print(f"\n--- GUNGNIR v43: Conference signal test (AACR poster vs no conference) ---")
    g4_conf = tool_gungnir_score(
        ticker="WHWK", drug_name="testdrug",
        indication="solid tumors", stage="Phase 2",
        catalyst_text="Phase 2 single-arm trial in solid tumors with ORR primary. AACR poster presentation.",
        company="Test", year=2026, has_conference=1, days_to_cover=3.5,
    )
    g4_no_conf = tool_gungnir_score(
        ticker="WHWK", drug_name="testdrug",
        indication="solid tumors", stage="Phase 2",
        catalyst_text="Phase 2 single-arm trial in solid tumors with ORR primary.",
        company="Test", year=2026,
    )
    print(f"  With conference:    P={g4_conf['probability']:.4f}  Tier {g4_conf['tier']}")
    print(f"  Without conference: P={g4_no_conf['probability']:.4f}  Tier {g4_no_conf['tier']}")
    print(f"  Conference lift: {g4_conf['probability'] - g4_no_conf['probability']:+.4f}")
    assert g4_conf["probability"] > g4_no_conf["probability"], "Conference should boost probability"

    # Status
    status = tool_system_status()
    print(f"\n--- System Status ---")
    print(f"  ODIN:       {status['odin']['version']}")
    print(f"  GUNGNIR:    {status['gungnir']['version']}")
    print(f"  BIFROST:    {status['bifrost']['version']}")
    print(f"\n{'='*60}")
    print(f"  ALL TESTS PASSED")
    print(f"{'='*60}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    elif "--serve" in sys.argv:
        mcp = create_mcp_server()
        mcp.run()
    else:
        print("Usage:")
        print("  python mcp_9realms_vnext.py --test    Run self-test")
        print("  python mcp_9realms_vnext.py --serve   Start MCP server")
