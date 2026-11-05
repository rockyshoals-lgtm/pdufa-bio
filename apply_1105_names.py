# -*- coding: utf-8 -*-
"""apply_1105_names.py -- name fixes found in the 2026-11-05 audit (facts only).

CGEM 2027-02-27: Cullinan's 8-K names the application "Zipalertinib NDA for relapsed EGFR ex20ins NSCLC"; the row said
only "CLN-081" (zipalertinib's code), which is not what a searcher or answer engine types.
CYTK 2026-11-14: the sNDA is MAPLE-HCM, aficamten vs metoprolol in OBSTRUCTIVE HCM (Cytokinetics 8-K 2026-05-05); the
row said non-obstructive (that is ACACIA-HCM, a different application). Text already swapped on published pages.
"""
import io, json, os
SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdufa_site_src")
P = os.path.join(SITE, "api", "v1", "dataset.mjs")
s = io.open(P, encoding="utf-8").read(); i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
for r in rows:
    if r["id"] == "pdufa_cgem_2027-02-27":
        r["name"] = "Zipalertinib (CLN-081) - relapsed EGFR exon 20 insertion NSCLC"
        r.setdefault("_d", {}).update({"inn": "zipalertinib", "indication": "Relapsed EGFR exon 20 insertion non-small cell lung cancer"})
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
J = os.path.join(SITE, "api", "data.js")
t = io.open(J, encoding="utf-8").read(); k = t.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(t[k:])
for c in slate["catalysts"]:
    if c.get("ticker") == "CGEM" and c.get("date") == "2027-02-27":
        c["drug"] = "Zipalertinib (CLN-081) - relapsed EGFR exon 20 insertion NSCLC"
        c["indication"] = "Relapsed EGFR exon 20 insertion non-small cell lung cancer"
io.open(J, "w", encoding="utf-8").write(t[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + t[k + end:])
print("names fixed: CGEM zipalertinib")
