# -*- coding: utf-8 -*-
"""apply_1024_fda_records.py -- Drugs@FDA caught up with two decisions published as notice-dated (audit 2026-10-24).

openFDA (last_updated 2026-10-23):
  NDA 221276 ORIG-1, GLAXOSMITHKLINE, TYPE 1, AP 2026-10-20, HIBSAGO, letter
    https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/221276Orig1s000Ltr.pdf  (same day as the FDA's notice)
  BLA 761174 SUPPL-15, GLAXOSMITHKLINE, EFFICACY, AP 2026-10-19, JEMPERLI, no letter PDF linked yet
The dataset rows already carried the right FDA day (from the FDA's own notices); this updates the record names and the
one hand-written sentence on each page that said the letter "had not been posted". Facts only; not investment advice.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
FIX = {
    "GSK-2026-10-20": (r"The FDA's letter had not been posted on Drugs@FDA when this page was published\.",
                       'Drugs@FDA records the approval as NDA 221276, original application, with the FDA\'s letter dated '
                       'October 20, 2026 (<a href="https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/221276Orig1s000Ltr.pdf" '
                       'rel="noopener" style="color:#e3ba5e">FDA letter</a>).'),
    "GSK-2026-10-19": (r"The FDA's letter for BLA 761174 had not been posted on Drugs@FDA when this page was published\.",
                       'Drugs@FDA records BLA 761174 supplement 15 approved October 19, 2026, the day the FDA\'s notification '
                       'states; no letter PDF was linked there when this sentence was written.'),
}
for slug, (old, new) in FIX.items():
    p = os.path.join(SITE, "fda-decision", slug, "index.html")
    doc = io.open(p, encoding="utf-8").read()
    doc2, n = re.subn(old, new, doc)
    if n:
        io.open(p, "w", encoding="utf-8").write(doc2)
    print(f"  /fda-decision/{slug}: {n} sentence(s) rewritten")
