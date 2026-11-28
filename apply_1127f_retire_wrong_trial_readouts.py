# -*- coding: utf-8 -*-
"""apply_1127f_retire_wrong_trial_readouts.py -- retire Estimated readout rows whose date came from a trial of a
different drug, or from a trial another company runs, and record the true registry name of the rows that are right.

WHY (2026-11-27). An Estimated row's date is the ClinicalTrials.gov primary-completion window of ONE trial. A new
guard (tests/test_readout_name_matches_trial.py) compared each row's drug with its trial's registry titles; the
lead sponsor of every Estimated row's trial was also read from the registry the same day. 12 rows were dated by a
trial that is not about their drug or not their company's:

  wrong drug   HOWL WTX-330 (trial is WTX-124), LEGN LCAR-B38M (Tianjin trial of LUCAR-G39D), AXSM AXS-14 (an AXS-05
               neuroimaging study), IOVA lifileucel+pembrolizumab (a terminated pediatric
               TIL study of LN-145/LN-144, 5 enrolled; not that regimen), LTRN Tavocept (trial is
               LP-184), OGN Elonva (trial is the AIO PHERFLOT pembrolizumab/trastuzumab/FLOT study), CLRB NOV-002
               (trial is CLR 131), ACRS A-101 (trial is ATI-045), CGEM CLN-081 (trial is CLN-619), WVE WVE-210201
               (trial is WVE-006 in AATD)
  wrong company TMO MK-7240 (lead sponsor Merck Sharp & Dohme), ILMN 18F-mFBG (lead sponsor Innervate
               Radiopharmaceuticals, formerly Illumina Radiopharmaceuticals; not Illumina, Inc.)

Every one of these windows had already passed and the site showed "no topline" against them, which reads as the
company having missed a readout it never guided. The rows go. Their drug pages 301 to the company page (or, for the
two wrong-company rows, to the real sponsor's page or /readouts).

Rows whose registry title uses a code or brand name for the same drug are kept and listed in _readout_ta_manual.json
"trial_name_ok" with that name and where it was read.

Idempotent. Facts only; not investment advice.
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MANUAL = os.path.join(HERE, "_readout_ta_manual.json")
RETIRED_FILE = os.path.join(HERE, "_drug_pages_retired.json")
CHECKED = "2026-11-27"

RETIRE = {
    "readout_howl_2026-07-15": ("NCT05479812", "Registry title names WTX-124, not WTX-330"),
    "readout_legn_2026-06-15": ("NCT06395870", "Tianjin Medical University trial of LUCAR-G39D, not LCAR-B38M"),
    "readout_axsm_2026-07-15": ("NCT07523048", "Open-label neuroimaging study of dextromethorphan-bupropion (AXS-05), not AXS-14"),
    "readout_iova_2026-07-15": ("NCT06566092", "Terminated pediatric TIL study (LN-145/LN-144, 5 enrolled); not lifileucel plus pembrolizumab"),
    "readout_ltrn_2026-07-15": ("NCT05933265", "Registry title names LP-184, not Tavocept"),
    "readout_ogn_2027-10-15": ("NCT05504720", "AIO PHERFLOT trial of pembrolizumab, trastuzumab and FLOT; not Elonva"),
    "readout_clrb_2026-08-15": ("NCT03478462", "Registry title names CLR 131, not NOV-002"),
    "readout_acrs_2026-08-15": ("NCT07011706", "Trial of ATI-045, not A-101"),
    "readout_cgem_2026-09-15": ("NCT06381141", "Registry title names CLN-619, not CLN-081"),
    "readout_wve_2026-09-15": ("NCT06405633", "Trial of WVE-006 in AATD, not WVE-210201"),
    "readout_tmo_2026-08-15": ("NCT06052059", "Lead sponsor Merck Sharp & Dohme LLC (MK-7240); not a Thermo Fisher trial"),
    "readout_ilmn_2026-07-15": ("NCT04724369", "Lead sponsor Innervate Radiopharmaceuticals LLC (formerly Illumina Radiopharmaceuticals); not Illumina, Inc."),
}

RETIRED_PAGES = {"wtx-330": "/ticker/HOWL", "lcar-b38m-car-t": "/ticker/LEGN", "axs-14": "/ticker/AXSM",
                 "tavocept": "/ticker/LTRN", "nov-002": "/ticker/CLRB", "a-101": "/ticker/ACRS",
                 "cln-081": "/ticker/CGEM", "wve-210201": "/ticker/WVE", "mk-7240": "/ticker/MRK",
                 "18f-mfbg": "/readouts"}

# id -> (registry name for the row's drug, or None where the titles name no drug; where it was read)
TRIAL_NAME_OK = {
    "readout_calc_2026-07-15": ("Auxora", "Auxora is CalciMedica's brand name for CM4620 (registry title)"),
    "readout_cccc_2026-09-15": (None, "Cemsidomide is CFT7455; the registry record NCT04756726 is C4's CFT7455 study"),
    "readout_immp_2026-09-15": (None, "Eftilagimod alfa is IMP321; registry interventions name it"),
    "readout_cadl_2027-01-15": ("rQNestin34.5v.2", "CAN-3110 is rQNestin34.5v.2 (registry title)"),
    "readout_siga_2027-01-15": ("TPOXX", "TPOXX is the brand name of tecovirimat (registry title)"),
    "readout_aim_2027-04-15": (None, "Registry interventions for NCT03899987 name rintatolimod (Ampligen)"),
    "readout_cldx_2027-04-15": (None, "Registry interventions for NCT05349890 name CDX-1140; Celldex is a collaborator"),
    "readout_ions_2027-06-15": ("AKCEA-APOCIII-LRX", "AKCEA-APOCIII-LRX is olezarsen (registry title)"),
    "readout_kytx_2027-06-15": (None, "Registry interventions for NCT06475495 name KYV101; Kyverna is a collaborator"),
    "readout_btai_2027-07-15": ("BXCL501", "BXCL501 is dexmedetomidine sublingual film, now Teva's (registry title)"),
    "readout_maia_2027-09-15": ("THIO", "THIO is 6-thio-2'-deoxyguanosine (registry title)"),
    "readout_legn_2027-12-15": ("Claudin 18.2", "LB1908 is Legend's Claudin 18.2-targeted CAR-T (registry title)"),
    "readout_otlk_2027-12-15": ("ONS-5010", "ONS-5010 is Outlook's ophthalmic bevacizumab (registry title)"),
}


def main():
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    before = len(rows)
    rows = [r for r in rows if r.get("id") not in RETIRE]
    if len(rows) != before:
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])

    man = json.load(io.open(MANUAL, encoding="utf-8"))
    man["nct_mismatch"] = [e for e in man.get("nct_mismatch", []) if e.get("id") not in RETIRE]
    have = {e.get("id") for e in man.get("trial_name_ok", [])}
    for rid, (nm, basis) in TRIAL_NAME_OK.items():
        if rid in have:
            continue
        e = {"id": rid, "basis": basis, "checked": CHECKED}
        if nm:
            e["title_name"] = nm
        man.setdefault("trial_name_ok", []).append(e)
    io.open(MANUAL, "w", encoding="utf-8").write(json.dumps(man, indent=1, ensure_ascii=False) + "\n")

    ret = json.load(io.open(RETIRED_FILE, encoding="utf-8"))
    ret.setdefault("pages", {}).update(RETIRED_PAGES)
    io.open(RETIRED_FILE, "w", encoding="utf-8").write(json.dumps(ret, indent=1, ensure_ascii=False) + "\n")
    print(f"retired {before - len(rows)} row(s); trial_name_ok now {len(man['trial_name_ok'])}")


if __name__ == "__main__":
    main()
