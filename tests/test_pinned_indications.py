# -*- coding: utf-8 -*-
"""Approved indications that were once published wrong stay as the FDA wrote them.

2026-11-27: /fda-decision/AZN-2026-06-12, /drug/truqap and /drug/capivasertib said Truqap was approved for
"dephosphorylated Phosphatase and Tensin Homolog (dPTEN) Hormone-Sensitive Prostate Cancer (HSPC)", a disease that
does not exist; a scraped tracker row had expanded "dPTEN" wrongly. The FDA's notice of June 12, 2026 approves it for
prostate cancer that is PTEN-deficient (apply_1127_truqap_indication.py).

This fails when a pinned dataset row's indication loses the FDA's wording, or when any published page or the
dataset says "dephosphorylated Phosphatase" or "dPTEN".

    python tests/test_pinned_indications.py
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
# row id -> words the FDA's own indication text must contain, and the notice they were read from
PINS = {
    "pdufa_azn_2026-06-30": (["PTEN-deficient", "abiraterone and prednisone", "prostate cancer"],
                             "https://www.fda.gov/drugs/resources-information-approved-drugs/"
                             "fda-approves-capivasertib-abiraterone-and-prednisone-pten-deficient-androgen-pathway-modulation"),
}
BANNED = ["ephosphorylated Phosphatase", "dPTEN"]
PAGES = ["fda-decision/AZN-2026-06-12", "drug/truqap", "drug/capivasertib"]


def main():
    bad = []
    s = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = {r.get("id"): r for r in json.loads(s[s.index("["):s.rindex("]") + 1])}
    for rid, (words, src) in PINS.items():
        d = (rows.get(rid) or {}).get("_d") or {}
        ind = d.get("indication") or ""
        miss = [w for w in words if w not in ind]
        if miss:
            bad.append(f"dataset {rid}: indication {ind[:80]!r} lacks {miss} (FDA: {src})")
        if d.get("indication_source") != src:
            bad.append(f"dataset {rid}: indication_source is not the FDA notice")
    for b in BANNED:
        if b in s:
            bad.append(f"dataset contains {b!r}")
    for rel in PAGES:
        p = os.path.join(SITE, rel, "index.html")
        if os.path.exists(p):
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            for b in BANNED:
                if b in doc:
                    bad.append(f"/{rel} says {b!r}")
    if bad:
        print("FAIL test_pinned_indications:")
        for b in bad:
            print("  -", b)
        print("  fix: python apply_1127_truqap_indication.py, then rebuild")
        return 1
    print(f"PASS test_pinned_indications: {len(PINS)} pinned indication(s) as the FDA wrote them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
