# -*- coding: utf-8 -*-
"""
GUNGNIR v46 post-mortem — DFTX / DT120 (MM120, lysergide/LSD) EMERGE Phase 3 MDD
Readout 2026-06-22: hit primary + all key secondaries (p<0.0001, +8.1 MADRS), stock +~50-55%.

We never produced a live score for DFTX (see postmortem .md for why). This script RECONSTRUCTS
what the v46 champion's Ridge backbone (M1 = 90% of the binary ensemble) would have output given
the documented pre-readout feature values below. Unknown CT.gov trial-design specifics are held at
the training mean (zero standardized contribution). XGBoost (10% of the ensemble) is omitted.

Run:  python gungnir_dftx_postmortem.py
"""
import json, math

d  = json.load(open("gungnir_v46_deploy.json"))
fn = d["feature_names"]; mu = d["scaler_mean"]; sc = d["scaler_scale"]
HEADS = {"positive": (d["M1_coef"], d["M1_intercept"]),
         "GOOD+":    (d["M2_coef"], d["M2_intercept"]),
         "CRASH":    (d["M3_coef"], d["M3_intercept"])}

# ---- Documented pre-readout state (T-1) for DT120 EMERGE Phase 3 MDD ----
# Sources: Definium/MindMed PRs, JAMA (MM120 GAD Ph2b), CT.gov, our crawler row (catalysts_public.csv).
V = {
 # Phase 3 pivotal
 "is_phase1":0,"is_phase1b":0,"is_phase2":0,"is_phase2a":0,"is_phase2b":0,"is_phase3":1,
 "phase_numeric":3,"nlp_phase3":1,"is_pivotal":1,"is_bridging":0,
 "phase3_x_cns":1,"phase3_x_placebo":1,"phase3_x_randomized":1,"phase3_x_double_blind":1,
 "phase3_x_oncology":0,"dmc_x_phase3":1,"ct_active_comp_x_phase3":0,"global_x_phase3":1,
 "small_x_phase3":0,"micro_x_phase3":0,
 # Size ~ $2.67B = MID cap
 "is_micro":0,"is_small":0,"is_mid":1,"is_large":0,"log_market_cap":math.log(2.67e9),
 "cns_x_micro":0,"v42_is_small_X_ta_cns":0,
 # TA = CNS / psychiatry (MDD)
 "ta_cns":1,"ta_oncology":0,"ta_immunology":0,"ta_metabolic":0,"ta_cardiovascular":0,
 "ta_hematology":0,"ta_infectious":0,"ta_rare_disease":0,"ta_other":0,
 "v41_placebo_x_cns":1,"v41_immuno_x_phase2":0,
 # Modality/MOA: LSD = small molecule, 5-HT2A AGONIST
 "ch_is_agonist":1,"ch_is_enzyme":0,"ch_is_ion_channel":0,
 "v46_p1_ch2_moa_agonist":1,"v44_ch2_moa_antagonist_X_journey_had_positive":0,
 "v43_ch2_is_biologic_X_is_phase3":0,"v44_ch2_is_sm_X_is_phase2_X_is_small":0,
 # Journey: strong positive (Ph2b GAD win, JAMA, BTD; Ph3 GAD ongoing, not yet read out)
 "journey_last_positive":1,"v46_p5_log1p_journey_last_positive":math.log1p(1.0),
 "v41_journey_last_pos_sq":1,"journey_success_rate":1,"journey_had_positive":1,
 "journey_had_negative":0,"journey_n_negative":0,"journey_sr_x_phase3":1,
 # Designations: BTD (+ fast track) — NOTE: sensitivity feature, see postmortem
 "designation_count":2,"has_orphan":0,
 # Conference: none (company topline PR)
 "v40_has_conference":0,"v41_sponsor_x_conference":0,"v40_conf_x_small":0,
 # Full topline (NOT interim)
 "iis_is_interim":0,"nlp_interim":0,"nlp_topline":1,"nlp_first_in":0,"nlp_biomarker":0,"nlp_combo_therapy":0,
 # Trial design (known): placebo, randomized, double-blind, DSMB, industry, multinational, CT.gov-matched
 "ctgov_is_placebo":1,"ctgov_is_randomized":1,"ctgov_is_double_blind":1,"ctgov_has_dmc":1,
 "ct_is_industry":1,"ctgov_is_global":1,"ctgov_real":1,
 # Market microstructure (pre-readout): near 52w highs, elevated short interest (~31% of float)
 "momentum_5d":0.0,"momentum_10d":0.02,"momentum_20d":0.05,"v40_days_to_cover":7.0,
 "era_2024_plus":1,
}

def score(coef, inter):
    contrib = {}
    z = inter
    for f in fn:
        x = V.get(f, mu[f])              # unset feature -> mean -> 0 contribution
        c = coef[f] * (x - mu[f]) / sc[f]
        z += c; contrib[f] = c
    return z, 1/(1+math.exp(-z)), contrib

if __name__ == "__main__":
    print("GUNGNIR v46 Ridge backbone (M1 = 90% of binary ensemble); XGB(10%) omitted.\n")
    for name,(coef,inter) in HEADS.items():
        logit, p, contrib = score(coef, inter)
        print(f"P({name}) = {p*100:5.1f}%   (logit {logit:+.3f})")
        for f,c in sorted(contrib.items(), key=lambda kv:-abs(kv[1]))[:8]:
            if abs(c) > 1e-6:
                print(f"    {c:+.3f}  {f}  (x={V.get(f,'mean')})")
        print()
