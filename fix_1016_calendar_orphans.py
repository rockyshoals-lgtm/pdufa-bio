# -*- coding: utf-8 -*-
"""fix_1016_calendar_orphans.py -- remove /calendar rows for events retired on 2026-10-15 (audit 2026-10-16).

The /calendar grid is patched in place by the builders, never regenerated, so retiring a decision page (301) left
its row behind with its link rewritten to the ticker page:
  BMY  2026-06-01  Camzyos SCOUT-HCM  -- June 1 was the FDA's acceptance; approved 2026-09-30 (row present)
  ZVRA/XOMA 2026-06-08  Miplyffa      -- an Orange Book patent listing, not an FDA action
  LGND 2026-06-08  "Approved" Miplyffa, linked to /fda-decision/LGND-2026-04-13 (a FILSPARI page)
Each is listed as still pending or as an approval on a day nothing happened. Idempotent.
"""
import html
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdufa_site_src", "calendar", "index.html")
DROP = [("BMY", "2026-06-01", "camzyos"), ("ZVRA", "2026-06-08", "miplyffa"), ("XOMA", "2026-06-08", "miplyffa"),
        ("LGND", "2026-06-08", "miplyffa")]
t = io.open(P, encoding="utf-8").read()
n = 0


def kill(m):
    global n
    txt = html.unescape(re.sub(r"<[^>]+>", " ", m.group(0))).lower()
    lab = re.match(r"\s*([a-z/ ]+?)\s*·\s*(\d{4}-\d{2}-\d{2})", txt)
    if lab:
        for tk, d, drug in DROP:
            if tk.lower() in lab.group(1).split() and lab.group(2) == d and drug in txt:
                n += 1
                return ""
    return m.group(0)


t2 = re.sub(r'<a class="row"[^>]*>.*?</a>', kill, t, flags=re.S)
if t2 != t:
    io.open(P, "w", encoding="utf-8").write(t2)
print(f"calendar orphans removed: {n}")

# /calendar/2026/june: two rows carried another drug's name over a correct date and decision link. The dataset
# rows are pdufa_achv_2026-06-20 "Cytisinicline - (ORCA-3)" (CRL, NDA 218995 letter) and pdufa_ions_2026-06-30
# "Olezarsen - (CORE)" (Tryngolza, approved 2026-06-24). The page said "Custirsen: Non-Small Cell Lung Cancer"
# and "Donidalorsen".
J = os.path.join(os.path.dirname(P), "2026", "june", "index.html")
tj = io.open(J, encoding="utf-8").read()
fixes = 0
for tk, d, wrong, right in (("ACHV", "2026-06-20", "Custirsen: Non-Small Cell Lung Cancer", "Cytisinicline: Smoking cessation (ORCA-3)"),
                            ("IONS", "2026-06-30", "Donidalorsen", "TRYNGOLZA (olezarsen): Severe hypertriglyceridemia (CORE)"),
                            # same product, code name only: the decision page names VEPPANU (vepdegestrant), not ARV-471
                            ("ARVN", "2026-06-05", "ARV-471: Advanced Breast Cancer",
                             "VEPPANU (vepdegestrant, ARV-471): Advanced Breast Cancer")):
    rx = re.compile(r'(<a class="row"[^>]*>\s*<div class="t">' + tk + r'\s*&middot;\s*' + d + r'.*?<div class="d">.*?)'
                    + re.escape(wrong) + r'(.*?</a>)', re.S)
    tj, k = rx.subn(lambda m: m.group(1) + right + m.group(2), tj, count=1)
    fixes += k
io.open(J, "w", encoding="utf-8").write(tj)
print(f"june archive rows relabelled: {fixes}")
