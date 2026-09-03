# -*- coding: utf-8 -*-
"""ingest_readouts_2026_09_02.py -- the four guided readouts the SLS audit caught.

Audit 2026-09-02e: while the PDUFA watcher was catching MIMRYLO, two guided READOUTS
resolved with nobody looking (TENX Phase 3, 24 days stale; MPLT Phase 2, 38 days), one
row carried a date wrong by a year (TYRA), and one a precision error (ALZN). Every fact
below is from the company's own release, linked on the row; TENX carries the company's
multiplicity caveat verbatim because "missed its endpoint" alone would misinform.
Idempotent by row id.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")

FIX = {
    "readout_tenx_2026-08-31": {
        "name": "TNX-103 (oral levosimendan) Phase 3 LEVEL topline",
        "d": "2026-08-10", "dp": "day", "st": "Reported",
        "url": "https://www.globenewswire.com/news-release/2026/08/10/3341675/12401/en/"
               "tenax-therapeutics-announces-topline-results-from-phase-3-level-"
               "clinical-trial-of-tnx-103-in-patients-with-ph-hfpef.html",
        "_d_merge": {
            "nct_id": "NCT05983250",
            "review": "Phase 3 LEVEL did not meet its primary endpoint: patients walked "
                      "3.5 metres further than placebo at Week 12 (p=0.63), a difference "
                      "small enough to be chance; the key secondary (KCCQ-TSS) was also "
                      "not met. A prespecified subgroup with baseline 6MWD under 333 m "
                      "improved 26.3 m (nominal p=0.0112) and NT-proBNP fell 49% versus "
                      "placebo (nominal p<0.0001), but the company states: 'Nominal "
                      "p-values are not adjusted for multiplicity and these analyses do "
                      "not establish efficacy.' Tenax intends to request a Type C "
                      "meeting with FDA. Full results were a Late-Breaking Clinical "
                      "Science presentation at ESC Congress 2026 (Munich, Aug 28-31). "
                      "Note: LEVEL-2 is a separate, still-running Phase 3 of the same "
                      "drug (enrollment completing end of 2027) -- this row previously "
                      "mis-named the trial.",
        },
    },
    "readout_mplt_2026-08-31": {
        "name": "ML-007C-MA Phase 2 ZEPHYR topline (schizophrenia)",
        "d": "2026-07-27", "dp": "day", "st": "Reported",
        "url": "https://www.globenewswire.com/news-release/2026/07/27/3333379/0/en/"
               "MapLight-Therapeutics-Announces-Positive-Topline-Results-from-Phase-2-"
               "ZEPHYR-Trial-of-ML-007C-MA-in-Schizophrenia.html",
        "_d_merge": {
            "review": "Phase 2 ZEPHYR met its primary endpoint: statistically "
                      "significant improvement in PANSS total score versus placebo at "
                      "Week 5 on the 210/3 mg BID dose in acute schizophrenia. "
                      "Generally well tolerated; no serious or drug-related severe "
                      "adverse events reported.",
        },
    },
    "readout_tyra_2026-08-31": {
        # The company guides INITIAL RESULTS IN 2027 (TYRA Q2 2026 results); our
        # 2026-08-31 date was simply not true. Year precision is the honest encoding.
        "name": "SURF303 Phase 2a/b initial results (LG-UTUC)",
        "d": "2027-12-31", "dp": "year", "st": "Guided",
        "url": "https://ir.tyra.bio/news-releases/news-release-details/"
               "tyra-biosciences-reports-second-quarter-2026-financial-results",
        "_d_merge": {
            "review": "Phase 2a/b in low-grade upper tract urothelial carcinoma; first "
                      "patient dosed. Company guides initial results in 2027.",
        },
    },
    "readout_alzn_2026-08-31": {
        # Guided to Q3 2026 (through Sep 30), not August. The March 2026 'Lithium in
        # Brain' bioequivalence study already read out -- this row is the BIPOLAR Ph II.
        "name": "AL001 Phase II topline (bipolar disorder)",
        "d": "2026-09-30", "dp": "quarter", "st": "Guided",
        "_d_merge": {
            "review": "Company guidance: Phase II bipolar disorder topline in Q3 2026. "
                      "(A separate AL001 study, the 'Lithium in Brain' bioequivalence "
                      "trial, already reported in March 2026.)",
        },
    },
    "readout_sls_regal_2026q4": {
        # Provenance defect: the row cited pdufa.bio itself. The Aug 11, 2026 8-K
        # (Ex 99.1) is the primary source, and it re-confirms the guidance.
        "url": "https://www.sec.gov/Archives/edgar/data/1390478/000139047826000013/"
               "sls-202608118xkexhibit991.htm",
        "_d_merge": {
            "source_note": "Aug 11, 2026 8-K Ex 99.1: final analysis of Phase 3 REGAL "
                           "to be conducted following the 80th event (78 of 80 as of "
                           "May 11); event-driven, announcement when the 80th event "
                           "occurs.",
        },
    },
    "readout_sls_2026-12-31": {
        "url": "https://www.sec.gov/Archives/edgar/data/1390478/000139047826000013/"
               "sls-202608118xkexhibit991.htm",
        "_d_merge": {
            "source_note": "Aug 11, 2026 8-K Ex 99.1: 28 patients enrolled in Phase 2 "
                           "of SLS009 in newly diagnosed first-line AML; topline data "
                           "expected in Q4 2026.",
        },
    },
}


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i = src.find("[")
    arr, end = json.JSONDecoder().raw_decode(src[i:])
    changed = 0
    for r in arr:
        fix = FIX.get(r.get("id"))
        if not fix:
            continue
        before = json.dumps(r, sort_keys=True)
        for k, v in fix.items():
            if k == "_d_merge":
                d = r.get("_d") or {}
                d.update(v)
                r["_d"] = d
            else:
                r[k] = v
        if json.dumps(r, sort_keys=True) != before:
            changed += 1
            print(f"  {r['id']}: {r.get('st')} {r.get('d')} ({r.get('dp')})")
    io.open(DATASET, "w", encoding="utf-8").write(
        src[:i] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False)
        + src[i + end:])
    print(f"readout ingest: {changed} row(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
