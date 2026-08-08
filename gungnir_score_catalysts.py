# -*- coding: utf-8 -*-
"""
gungnir_score_catalysts.py  —  nightly auto-rescore for the pdufa.bio crawl.

Closes the DFTX gap: every PhaseReadout in catalysts_public.csv gets a live GUNGNIR v46 score.
Methodology = the DFTX post-mortem reconstruction: derive the features we can confidently get
from each row (phase, TA, market-cap tier, drug modality/MOA, conference, interim/topline) and
hold unknown features (journey history, designations, trial-design microstructure) at the v46
training mean (zero standardized contribution). Scores the Ridge backbone M1 (90% of the binary
ensemble), plus the GOOD+ and CRASH heads. XGBoost (10%) is intentionally omitted -> these are
faithful *estimates*, not the exact production score, and are labelled gungnir_est_*.

Usage:  python gungnir_score_catalysts.py [catalysts_public.csv] [out.csv]
Outputs: catalysts_scored.csv  (input columns + gungnir_est_p_positive / _p_goodplus / _p_crash /
         _tier / _features_set), and prints a tier summary.
"""
import sys, os, csv, json, math, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "catalysts_public.csv")
OUT  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "catalysts_scored.csv")

DEPLOY = json.load(open(os.path.join(HERE, "gungnir_v46_deploy.json")))
FN  = DEPLOY["feature_names"]; MU = DEPLOY["scaler_mean"]; SC = DEPLOY["scaler_scale"]
HEADS = {"p_positive": (DEPLOY["M1_coef"], DEPLOY["M1_intercept"]),
         "p_goodplus": (DEPLOY["M2_coef"], DEPLOY["M2_intercept"]),
         "p_crash":    (DEPLOY["M3_coef"], DEPLOY["M3_intercept"])}

def _load(name):
    p = os.path.join(HERE, name)
    try: return json.load(open(p)) if os.path.exists(p) else {}
    except Exception: return {}
CHEMBL = { str(k).upper(): v for k, v in _load("chembl_enrichment_cache_v2.json").items() }
DRUGCLS = { str(k).upper(): v for k, v in _load("drug_classifications.json").items() }

# ----------------------------------------------------------------- feature derivation
def classify_ta(ind):
    s = (ind or "").lower()
    def has(*ws): return any(w in s for w in ws)
    if has("cancer","tumor","tumour","carcinoma","myeloma","lymphoma","leukemia","leukaemia",
           "melanoma","sarcoma","glioma","glioblastoma","oncolog","nsclc","sclc","neoplasm",
           "malignan","metasta","adenocarcinoma","mesothelioma"): return "ta_oncology"
    if has("depress","anxiety","parkinson","alzheimer","schizophren","epilep","migraine","cns",
            "psychiat","bipolar"," als","sclerosis","neuro","cognit","addiction","ptsd","insomnia",
            "huntington","pain","seizure"): return "ta_cns"
    if has("dermatitis","psoriasis","arthritis","asthma","lupus","colitis","crohn","eczema",
            "immune","ulcerative","atopic","rheumat","vitiligo","urticaria","ibd","sjogren","graft"): return "ta_immunology"
    if has("obesity","diabet","nash","mash","metabolic","weight","cholesterol","nafld","dyslipid","overweight"): return "ta_metabolic"
    if has("heart","cardiac","cardiovascular","hypertension","hfpef","hfref","thrombos","atrial",
            "coronary","angina","lipoprotein"): return "ta_cardiovascular"
    if has("anemia","anaemia","hemophilia","haemophilia","sickle","thrombocytopenia","hematolog",
            "haematolog"," itp","myelofibrosis","von willebrand"): return "ta_hematology"
    if has("influenza","hepatitis","covid","hiv","infection","viral","bacterial","vaccine",
            "pneumococc","rsv","sepsis","tuberculosis","fungal","antibiotic","zoster"): return "ta_infectious"
    if has("duchenne","dystrophy","angioedema","cystic fibrosis","rare","orphan","amyloid",
            "gaucher","fabry","pompe","hereditary","ataxia","spinal muscular"): return "ta_rare_disease"
    return "ta_other"

INN = [  # (regex on lowercase drug, modality flags)
 (r"(mab|umab|zumab|ximab)$", dict(is_biologic=1, is_mab=1)),
 (r"cept$",                   dict(is_biologic=1)),
 (r"(cel|leucel|cabtagene|autoleucel|denocel)$", dict(is_cell=1, is_biologic=1)),
 (r"(vec|gene)$|aav|adeno-?associated", dict(is_biologic=1)),
 (r"(rsen|mersen|sen|siran|sirna|nersen|aso|antisense|oligonucleotide)\b", dict(is_oligo=1)),
 (r"(tinib|ciclib|parib|rafenib|degib|lisib|metinib|zomib)$", dict(is_sm=1)),
 (r"(vaccine|vax)\b",         dict(is_biologic=1)),
 (r"(tide|relin)$",           dict()),  # peptide-ish, leave generic
]
def classify_modality(drug):
    d = (drug or "").strip(); up = d.upper(); low = d.lower()
    m = dict(is_sm=0, is_biologic=0, is_mab=0, is_adc=0, is_oligo=0, is_cell=0,
             agonist=0, antagonist=0, enzyme=0, ion_channel=0, known=0)
    rec = CHEMBL.get(up)
    if rec:
        m["known"] = 1
        if rec.get("is_biologic"): m["is_biologic"] = 1
        if str(rec.get("molecule_type","")).lower().startswith("small"): m["is_sm"] = 1
        mt = str(rec.get("mechanism_type","")).lower()
        acts = " ".join(str(x.get("action","")) for x in (rec.get("mechanisms") or [])).lower()
        if "agonist" in mt or "agonist" in acts: m["agonist"] = 1
        if "antagonist" in mt or "antagonist" in acts: m["antagonist"] = 1
        tc = str(rec.get("target_class","")).lower()
        if "enzyme" in tc or "protease" in tc or "kinase" in tc: m["enzyme"] = 1
        if "ion channel" in tc or "ion_channel" in tc: m["ion_channel"] = 1
    else:
        dc = DRUGCLS.get(up, {})
        mod = str(dc.get("modality","")).lower()
        if "antibody" in mod or "mab" in mod: m["is_biologic"] = 1; m["is_mab"] = 1
        elif "oligo" in mod or "sirna" in mod or "antisense" in mod: m["is_oligo"] = 1
        elif "cell" in mod: m["is_cell"] = 1; m["is_biologic"] = 1
        elif "small" in mod: m["is_sm"] = 1
        else:
            for pat, flags in INN:
                if re.search(pat, low):
                    m.update({k: v for k, v in flags.items()}); break
    if "adc" in low or "deruxtecan" in low or "vedotin" in low or "govitecan" in low:
        m["is_adc"] = 1; m["is_biologic"] = 1
    if not any(m[k] for k in ("is_sm","is_biologic","is_mab","is_adc","is_oligo","is_cell")):
        m["is_sm"] = 1  # default modality
    return m

def parse_phase(snippet, ctype):
    t = (str(snippet) + " " + str(ctype)).lower()
    f = dict(p1=0, p2=0, p3=0, p2a=0, p2b=0, p1b=0)
    if re.search(r"phase\s*3|phase3|p3|phase iii", t): f["p3"] = 1
    elif re.search(r"phase\s*2|phase2|p2|phase ii", t): f["p2"] = 1
    elif re.search(r"phase\s*1|phase1|p1|phase i\b", t): f["p1"] = 1
    if re.search(r"phase\s*2a|phase 2a|2a\b", t): f["p2a"] = 1
    if re.search(r"phase\s*2b|phase 2b|2b\b", t): f["p2b"] = 1
    if re.search(r"phase\s*1b|phase 1b|1b\b", t): f["p1b"] = 1
    return f

CONF = ["asco","ash","aacr","esmo","eha","aan","ada ","easl","eular","sitc","sno","ena","aasld","kidney week","obesityweek"]
def to_f(x):
    try:
        v = float(str(x).replace(",","").replace("$","")); return v if v == v else None
    except Exception: return None

def derive(row):
    """Return {feature_name: value} for confidently-derivable features (rest -> mean)."""
    v = {}
    snip = row.get("snippet",""); ind = row.get("indication",""); drug = row.get("drug","")
    ph = parse_phase(snip, row.get("catalyst_type",""))
    ta = classify_ta(ind); mod = classify_modality(drug)
    mc = to_f(row.get("market_cap"))
    text = (str(snip) + " " + str(row.get("sources","")) ).lower()
    conf = 1 if any(c in text for c in CONF) else 0
    interim = 1 if "interim" in text else 0
    topline = 1 if ("topline" in text or "top-line" in text) else 0
    # size tiers
    is_micro = is_small = is_mid = is_large = 0
    if mc is not None:
        if mc < 300e6: is_micro = 1
        elif mc < 2e9: is_small = 1
        elif mc < 10e9: is_mid = 1
        else: is_large = 1
    def s(name, val):
        if name in MU: v[name] = val
    # phase
    s("is_phase1", ph["p1"]); s("is_phase2", ph["p2"]); s("is_phase3", ph["p3"])
    s("is_phase2a", ph["p2a"]); s("is_phase2b", ph["p2b"]); s("is_phase1b", ph["p1b"])
    s("phase_numeric", 3 if ph["p3"] else 2 if ph["p2"] else 1 if ph["p1"] else 2)
    s("nlp_phase3", ph["p3"]); s("is_pivotal", 1 if ph["p3"] else 0)
    # TA one-hot
    for t in ("ta_oncology","ta_cns","ta_immunology","ta_metabolic","ta_cardiovascular",
              "ta_hematology","ta_infectious","ta_rare_disease","ta_other"):
        s(t, 1 if ta == t else 0)
    # size
    s("is_micro", is_micro); s("is_small", is_small); s("is_mid", is_mid); s("is_large", is_large)
    if mc and mc > 0: s("log_market_cap", math.log(mc))
    # modality / MOA
    s("ch_is_agonist", mod["agonist"]); s("ch_is_enzyme", mod["enzyme"]); s("ch_is_ion_channel", mod["ion_channel"])
    s("v46_p1_ch2_moa_agonist", mod["agonist"])
    # conference / interim / topline
    s("v40_has_conference", conf); s("v40_conf_x_small", conf * is_small)
    s("iis_is_interim", interim); s("nlp_interim", interim); s("nlp_topline", topline)
    # computable interactions (only where BOTH components are derived)
    s("small_x_phase3", is_small * ph["p3"]); s("micro_x_phase3", is_micro * ph["p3"])
    s("phase3_x_cns", ph["p3"] * (1 if ta == "ta_cns" else 0)); s("phase3_x_oncology", ph["p3"] * (1 if ta == "ta_oncology" else 0))
    s("cns_x_micro", is_micro * (1 if ta == "ta_cns" else 0)); s("v42_is_small_X_ta_cns", is_small * (1 if ta == "ta_cns" else 0))
    s("v41_immuno_x_phase2", (1 if ta == "ta_immunology" else 0) * ph["p2"])
    s("v43_ch2_is_biologic_X_is_phase3", mod["is_biologic"] * ph["p3"])
    s("v43_ch2_is_oligo_X_is_phase2", mod["is_oligo"] * ph["p2"])
    s("v44_ch2_is_sm_X_is_phase2_X_is_small", mod["is_sm"] * ph["p2"] * is_small)
    meta = dict(phase=("P3" if ph["p3"] else "P2" if ph["p2"] else "P1" if ph["p1"] else "?"),
                ta=ta, mod=[k for k in ("is_sm","is_biologic","is_mab","is_adc","is_oligo","is_cell") if mod[k]],
                moa=("agonist" if mod["agonist"] else "antagonist" if mod["antagonist"] else ""),
                size=("micro" if is_micro else "small" if is_small else "mid" if is_mid else "large" if is_large else "?"),
                conf=conf, n_set=len(v))
    return v, meta

def sigmoid(z): return 1/(1+math.exp(-max(-30, min(30, z))))
def score_row(row):
    feat, meta = derive(row)
    out = {}
    for name, (coef, inter) in HEADS.items():
        z = inter
        for f in FN:
            x = feat.get(f, MU[f])
            z += coef[f] * (x - MU[f]) / SC[f]
        out[name] = sigmoid(z)
    return out, meta

def tier(p_pos, p_good):
    if p_pos >= 0.85 and p_good >= 0.55: return "ALPHA"
    if p_pos >= 0.70: return "BETA"
    if p_pos >= 0.50: return "GAMMA"
    if p_pos >= 0.35: return "DELTA"
    return "OMEGA"

def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8", errors="ignore")))
    import collections
    tcount = collections.Counter()
    fieldnames = list(rows[0].keys()) if rows else []
    for c in ["gungnir_est_p_positive","gungnir_est_p_goodplus","gungnir_est_p_crash","gungnir_est_tier","gungnir_est_features_set"]:
        if c not in fieldnames: fieldnames.append(c)
    for r in rows:
        if (r.get("category") or "").lower() != "readout":
            for c in fieldnames[-5:]: r.setdefault(c, "")
            continue
        sc_, meta = score_row(r)
        t = tier(sc_["p_positive"], sc_["p_goodplus"])
        tcount[t] += 1
        r["gungnir_est_p_positive"] = round(sc_["p_positive"], 4)
        r["gungnir_est_p_goodplus"] = round(sc_["p_goodplus"], 4)
        r["gungnir_est_p_crash"]    = round(sc_["p_crash"], 4)
        r["gungnir_est_tier"]       = t
        r["gungnir_est_features_set"] = f'{meta["phase"]}|{meta["ta"]}|{",".join(meta["mod"]) or "?"}|{meta["moa"] or "-"}|{meta["size"]}|conf={meta["conf"]}|n={meta["n_set"]}'
    w = csv.DictWriter(open(OUT, "w", newline="", encoding="utf-8"), fieldnames=fieldnames)
    w.writeheader()
    for r in rows: w.writerow(r)
    print(f"scored {sum(tcount.values())} readouts -> {OUT}")
    for t in ["ALPHA","BETA","GAMMA","DELTA","OMEGA"]:
        if tcount[t]: print(f"  {t:6s} {tcount[t]}")

if __name__ == "__main__":
    main()
