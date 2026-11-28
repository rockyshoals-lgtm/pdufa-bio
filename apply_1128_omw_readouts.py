# -*- coding: utf-8 -*-
"""apply_1128_omw_readouts.py -- three registry-estimate readouts that the sponsor's own words contradict,
red-teamed 2026-11-27 (ET evening; Nov 28 UTC).

THE SWEEP. 20 future-window Estimated rows (ClinicalTrials.gov primary-completion dates) were checked against each
sponsor's newest releases and SEC filings for its own timing. 17 have no company timing statement (KYTX KYSA-7, BIIB
PREVAIL, BLTE PHOENIX, LLY SURMOUNT-MMO, MRK EXPrESSIVE-10, VERA PIONEER final, TLX ProstACT Global, INTS
INVINCIBLE-3, RARE x2, SVRA IMPACT, BTAI, ONC ALMOND, OTLK NORSE SEVEN, KPTI XPORT-DLBCL-030, SUPN BIS-001ER) or
only an ambiguous one (VKTX: "these studies" completed in 2027) and keep their registry window. Three change; each
source was re-opened by an independent red-team pass that found the sentence verbatim:

  readout_arvn_2026-12-15  VERITAC-3, NCT05909397 (Phase 3 vepdegestrant + palbociclib). Arvinas, Jan 10, 2025
      (company IR site): "the VERITAC-3 trial evaluating vepdegestrant plus palbociclib in the first-line will not
      proceed beyond the study lead-in." The registry's Dec 2026 date (59 enrolled) is the lead-in's, not a Phase 3
      readout. The row goes.
  readout_rnac_2026-12-15  Descartes-08 Phase 2 in SLE, NCT06038474. Cartesian, Nov 13, 2025 (GlobeNewswire): month-3
      data on 3 patients, and the company will "pause further development of Descartes-08 in SLE, including enrollment
      in the Phase 2 trial." No readout is guided. The row goes.
  readout_incy_2027-09-15  axatilimab + corticosteroids Phase 3 in newly diagnosed chronic GVHD, NCT06585774. The
      same readout is already listed with the company's own timing as readout_sndx_2028-12-31 (Syndax, the
      co-developer, Nov 2, 2026: "The Company expects topline data from the Phase 3 trial of axatilimab in combination
      with corticosteroids in early 2028.", and the same release names "a Phase 3 combination trial with steroids
      (NCT06585774)"). The registry estimate was a second, earlier listing of one readout. It goes; the Syndax row
      records the NCT it names.

Every remaining drug page keeps rows (ARV-471 TACTIVE-U, Descartes-08 AURORA/TRITON/HELIOS, axatilimab), so no page is
retired. Each change gets a /corrections entry. Guard: tests/test_readout_1128_retired.py.

Idempotent. Facts only, not investment advice. RULE 1: dates are calendar dates as printed by the sponsor (ET).

    python apply_1128_omw_readouts.py [--dry-run]
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
CORR = os.path.join(HERE, "_corrections.json")
DAY = "2026-11-27"

ARVN_URL = "https://ir.arvinas.com/news-releases/news-release-details/arvinas-updates-guidance-first-and-second-line-phase-3"
RNAC_URL = ("https://www.globenewswire.com/news-release/2025/11/13/3187838/0/en/Cartesian-Therapeutics-Announces-Strong-"
            "Efficacy-Signal-in-Phase-2-Trial-of-Descartes-08-in-Patients-with-SLE-and-Expansion-of-Clinical-"
            "Development-into-Myositis.html")
SNDX_ROW = "readout_sndx_2028-12-31"

RETIRE = {
    "readout_arvn_2026-12-15": {"nct": "NCT05909397", "page": "/ticker/ARVN",
        "was": "Arvinas's VERITAC-3 Phase 3 trial of vepdegestrant plus palbociclib (NCT05909397) was listed as an "
               "upcoming readout, estimated December 2026 from the registry.",
        "now": "Removed. Arvinas said on Jan 10, 2025 that VERITAC-3 \"will not proceed beyond the study lead-in\", so "
               "the registry's December 2026 date is the lead-in's, not a Phase 3 readout.",
        "src": "Arvinas press release, Jan 10, 2025 (company IR site)"},
    "readout_rnac_2026-12-15": {"nct": "NCT06038474", "page": "/ticker/RNAC",
        "was": "Cartesian's Phase 2 trial of Descartes-08 in lupus (SLE, NCT06038474) was listed as an upcoming "
               "readout, estimated December 2026 from the registry.",
        "now": "Removed. On Nov 13, 2025 Cartesian reported early data from 3 patients and said it would pause "
               "development of Descartes-08 in SLE, including enrollment in the trial. No readout is guided.",
        "src": "Cartesian Therapeutics press release, Nov 13, 2025 (GlobeNewswire)"},
    "readout_incy_2027-09-15": {"nct": "NCT06585774", "page": "/ticker/INCY",
        "was": "Incyte's Phase 3 trial of axatilimab with corticosteroids in chronic GVHD (NCT06585774) was listed as "
               "an upcoming readout, estimated September 2027 from the registry.",
        "now": "Removed as a second listing of one readout. Syndax, which co-develops axatilimab, said on Nov 2, 2026 "
               "that it expects topline data from this Phase 3 trial in early 2028; that row stays under SNDX.",
        "src": "Syndax press release, Nov 2, 2026 (GlobeNewswire)"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    by = {r["id"]: r for r in rows}
    for rid, f in RETIRE.items():
        r = by.get(rid)
        if r is None:
            print(f"  {rid}: already gone")
            continue
        blk = (r.get("_d") or {}).get("nct_id") or {}
        assert r.get("st") == "Estimated", f"{rid} is {r.get('st')}, expected Estimated"
        assert str(blk.get("nct") or "").upper() == f["nct"], f"{rid}: NCT {blk.get('nct')} != {f['nct']}"
        print(f"  {rid}: retire")
    sndx = by.get(SNDX_ROW)
    assert sndx and "early 2028" in str((sndx.get("_d") or {}).get("guidance_text") or ""), "Syndax row missing or changed"
    sd = sndx["_d"]
    sd["nct_stated"] = "NCT06585774"
    sd["supersedes_estimate"] = "readout_incy_2027-09-15"
    rows = [r for r in rows if r["id"] not in RETIRE]
    corr = json.load(io.open(CORR, encoding="utf-8"))
    have = {(e.get("date"), e.get("page"), e.get("was")) for e in corr["entries"]}
    for f in RETIRE.values():
        if (DAY, f["page"], f["was"]) not in have:
            corr["entries"].append({"date": DAY, "page": f["page"], "was": f["was"], "now": f["now"], "source": f["src"]})
    if a.dry_run:
        print("--dry-run: nothing written")
        return 0
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
    io.open(CORR, "w", encoding="utf-8").write(json.dumps(corr, indent=1, ensure_ascii=False) + "\n")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
