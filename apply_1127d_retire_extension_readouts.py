# -*- coding: utf-8 -*-
"""apply_1127d_retire_extension_readouts.py -- retire Estimated readout rows that point at studies which are not
readouts, and copy each remaining Estimated row's registry titles onto the row.

WHY (2026-11-27). /readouts listed "Seralutinib, Dec 2026" for Gossamer. The trial behind it, NCT06274801
(PROSERA-EXT), is an open-label extension whose treatment period "is planned to run until the market approval of
seralutinib"; its primary outcome is adverse-event incidence. Its Dec 2026 primary completion is a registry
placeholder, not a topline readout. phase_readout_miner.is_catalyst() has refused extension studies since
2026-10-11, but rows added before then were never re-checked. All 146 Estimated rows' registry titles were read;
13 are standalone extension or long-term safety studies (an extension PERIOD inside a randomized trial is kept). Each
title below was read from ClinicalTrials.gov on 2026-11-27.

TITLES. scratchpad est_titles.json (registry titles for every Estimated row's NCT, read 2026-11-27) is copied into
_d.nct_id.title / brief_title so tests/test_readout_not_extension.py can check the rows now; refresh_readout_registry
keeps them current on every rebuild.

Idempotent. Facts only; not investment advice.

    python apply_1127d_retire_extension_readouts.py [titles.json]
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")

# id -> (NCT, the registry's own words that make it a non-readout)
RETIRE = {
    "readout_goss_2026-12-15": ("NCT06274801", "Open-label Extension Study of Seralutinib in Adult Subjects With PAH (PROSERA-EXT); treatment runs until market approval"),
    "readout_goss_2027-12-15": ("NCT04816604", "Open-label Extension Study of GB002 (seralutinib); registry status terminated"),
    "readout_jspr_2026-08-15": ("NCT06736262", "A Phase 2, Open-Label, Extension Study; registry status terminated"),
    "readout_cort_2026-12-15": ("NCT03604198", "An Open-Label Extension Study of the Safety of Relacorilant in Endogenous Cushing Syndrome"),
    "readout_insm_2026-12-15": ("NCT05649748", "An Open-Label Extension Study ... Long-Term Use of Treprostinil Palmitil Inhalation Powder in PAH"),
    "readout_onc_2026-12-15": ("NCT04170283", "An Open-label, Multi-center, Long-term Extension Study of Zanubrutinib Regimens in B-cell Malignancies"),
    "readout_ions_2027-03-15": ("NCT05681351", "CORE-OLE: An Open-Label Extension Study of Olezarsen in Severe Hypertriglyceridemia"),
    "readout_mbx_2027-05-15": ("NCT06531941", "An Extension Study to Evaluate the Long-Term Safety and Tolerability of MBX 2109 (Avail-Ext)"),
    "readout_supn_2026-09-15": ("NCT02736656", "Open-Label Extension Study ... Long Term Safety and Efficacy of SPN-812 (pediatric ADHD)"),
    "readout_mdgl_2027-03-15": ("NCT04951219", "52-Week, Phase 3, Open-Label Extension Study ... Resmetirom (MAESTRO-NAFLD-OLE)"),
    "readout_sny_2026-11-15": ("NCT07216079", "An Open-label Extension Study for Oral Rilzabrutinib in Adults With Chronic ITP ... in Japan"),
    "readout_ptct_2026-06-15": ("NCT05166161", "A Long-Term Safety Study of PTC923 (sepiapterin) in Phenylketonuria"),
    "readout_ions_2026-12-15": ("NCT05392114", "An Open-Label, Long Term Safety and Efficacy Study of Donidalorsen in HAE"),
}


# drug pages whose only rows were the retired ones -> their company's hub (build_drug_pages.py 301s them; a slug that
# gets a page again, e.g. seralutinib once the FDA sets a goal date, drops out of the redirects on its own)
RETIRED_PAGES = {"seralutinib": "/ticker/GOSS", "mbx-2109": "/ticker/MBX", "treprostinil-palmitil": "/ticker/INSM",
                 "donidalorsen": "/ticker/IONS", "ptc923": "/ticker/PTCT", "spn-812": "/ticker/SUPN"}
RETIRED_FILE = os.path.join(HERE, "_drug_pages_retired.json")


def main():
    titles = {}
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        titles = json.load(io.open(sys.argv[1], encoding="utf-8"))
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    before = len(rows)
    rows = [r for r in rows if r.get("id") not in RETIRE]
    titled = 0
    for r in rows:
        if r.get("type") != "Readout" or r.get("st") != "Estimated":
            continue
        dd = r.setdefault("_d", {})
        raw = dd.get("nct_id")
        if not raw:
            continue
        if not isinstance(raw, dict):
            raw = dd["nct_id"] = {"nct": raw}
        t = titles.get(str(raw.get("nct") or "")) or {}
        if t.get("found") is False:
            continue
        for k in ("title", "brief_title"):
            if t.get(k) and raw.get(k) != t[k]:
                raw[k] = t[k]
                titled += 1
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=True) + src[j:])
    ret = json.load(io.open(RETIRED_FILE, encoding="utf-8"))
    ret.setdefault("pages", {}).update(RETIRED_PAGES)
    io.open(RETIRED_FILE, "w", encoding="utf-8").write(json.dumps(ret, indent=1, ensure_ascii=False) + "\n")
    print(f"retired {before - len(rows)} row(s); {titled} registry title field(s) written")


if __name__ == "__main__":
    main()
