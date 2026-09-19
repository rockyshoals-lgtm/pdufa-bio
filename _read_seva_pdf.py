# -*- coding: utf-8 -*-
"""Extract the sevabertinib SUPPL-1 approval letter and label with pypdf.

Decides whether our unsourced BAYRY row -- "Sevabertinib (BAY 2927088), HER2-mutant NSCLC, 1L,
goal 2026-11-30, Upcoming" -- is the application the FDA approved on 2026-09-09, or a different
one. The FDA's own letter names the indication, so it settles it rather than leaving me to infer
from the fact that a SUPPL-1 is "probably" the 1L expansion.
"""
import re
import sys

from pypdf import PdfReader

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def text(p):
    return "\n".join((pg.extract_text() or "") for pg in PdfReader(p).pages)


for path, label in [("_seva_letter.pdf", "APPROVAL LETTER"),
                    ("_seva_label.pdf", "LABEL")]:
    t = re.sub(r"[ \t]+", " ", text(path))
    print(f"\n{'=' * 78}\n=== {label}: {path}")
    if label == "APPROVAL LETTER":
        print(t[:2400])
    else:
        for key in [r"INDICATIONS AND USAGE", r"is indicated for[^.]{0,400}",
                    r"first-line", r"previously treated", r"HER2"]:
            m = re.search(key, t, re.I)
            if m:
                print(f"\n  [{key}] ...{t[max(0, m.start() - 160):m.end() + 460]}...")
