# -*- coding: utf-8 -*-
"""The INCY calendar rows still imply Incyte holds the zilurgisertib application. It does not.

Audit 09-10b item 3, verified first-hand in Mirum's 8-K of 2026-05-06 (accession
0001759425-26-000036, EX-99.1): "The FDA has accepted the NDA for zilurgisertib in FOP under
Priority Review with a Prescription Drug User Fee Act (PDUFA) date of September 26, 2026. Mirum
licensed zilurgisertib from Incyte for development and commercialization globally."

The dataset row was relabelled, but the calendar rows render from their own markup and still read
a bare "zilurgisertib" under the INCY ticker on a page headed "PDUFA target dates" -- which reads
as Incyte's application. Incyte is the LICENSOR; Mirum is the applicant. The row is worth keeping
(Incyte carries real economic exposure to the decision) but it has to say what it is.
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

NEW = "Zilurgisertib (Mirum holds the NDA; Incyte licensed it out): FOP"
ROW = re.compile(r'(<a class="row"[^>]*>\s*<div class="t">INCY[^<]*</div><div class="d">)'
                 r'(.*?)(</div>)', re.S)

n = 0
for p in set(glob.glob("pdufa_site_src/calendar/**/index.html", recursive=True)):
    d = io.open(p, encoding="utf-8", errors="replace").read()
    orig = d

    def rep(m):
        global n
        if "zilurgisertib" not in m.group(2).lower():
            return m.group(0)
        n += 1
        return m.group(1) + NEW + m.group(3)

    d = ROW.sub(rep, d)
    if d != orig:
        io.open(p, "w", encoding="utf-8").write(d)
        print(f"  {os.path.relpath(p)}")

print(f"{n} INCY calendar row(s) relabelled")
