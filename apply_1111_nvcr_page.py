# -*- coding: utf-8 -*-
"""apply_1111_nvcr_page.py -- NVCR Optune Mya gets its decision page; BAYRY company name made canonical.

Several builders (weekly page, event-page banner, decision listings) link every Decided row to
/fda-decision/{T}-{dcd}; NVCR's row had none, so three pages linked a 404. build_decision_page.py now labels the
outcome "Not approvable letter (device PMA)" (never a CRL). Bayer's existing rows say "Bayer", so the new asundexian
row does too (test_company_names_canonical). Facts only, not investment advice.
"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
NVCR_8K = "https://www.sec.gov/Archives/edgar/data/1645113/000164511326000085/myadecisionpr.htm"
P = os.path.join(SITE, "api", "v1", "dataset.mjs")
s = io.open(P, encoding="utf-8").read(); i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
for r in rows:
    if r.get("id") == "pdufa_nvcr_2026-11-15":
        r["url"] = "/fda-decision/NVCR-2026-11-09"
    if r.get("id") == "pdufa_bayry_2026-11-09_asundexian":
        r["company"] = "Bayer"
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
import build_decision_page as bdp
px = json.load(open(os.path.join(HERE, "_chart_pxcache.json")))
bdp.build({"ticker": "NVCR", "date": "2026-11-09", "outcome": "Not approvable letter",
           "drug": "Optune Mya",
           "indication": "Brain metastases from non-small cell lung cancer, after stereotactic radiation (adults)",
           "company": "NovoCure Limited", "cap": "Small",
           "headline": ("Novocure announced on November 9, 2026 that the FDA issued a Not Approvable Letter on its "
                        "Premarket Approval (PMA) application for Optune Mya in adults with brain metastases from "
                        "non-small cell lung cancer following stereotactic radiation."),
           "pdufa_note": ("This is a medical-device PMA decision, not a drug application, so there is no PDUFA goal date "
                          "and no Complete Response Letter. Per Novocure, the FDA cited uncertainty around the degree of "
                          "clinical benefit and raised no safety concerns; Novocure plans to meet the FDA to discuss options "
                          "that would not require additional clinical studies. The letter's own date is not public; the "
                          "date on this page is Novocure's announcement."),
           "source": NVCR_8K, "source_label": "Novocure 8-K (EX-99.1), November 9, 2026"}, px)
import re
pp = os.path.join(SITE, "fda-decision", "NVCR-2026-11-09", "index.html")
doc = io.open(pp, encoding="utf-8").read()
desc = "NVCR: FDA Not Approvable Letter on the Optune Mya device PMA (NSCLC brain metastases), announced Nov 9, 2026. Run-up and source."
for pat in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")'):
    doc = re.sub(pat, lambda m: m.group(1) + desc + m.group(2), doc)
io.open(pp, "w", encoding="utf-8").write(doc)
print("NVCR decision page built; BAYRY company canonical", len(desc))
