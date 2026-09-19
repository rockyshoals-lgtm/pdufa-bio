# -*- coding: utf-8 -*-
"""Prove tests/test_cross_surface_values.py: 0 -> planted 1 -> 0, once per invariant.

Also proves the REPAIRED ratchet in test_calendar_matches_dataset, which shipped on 09-10 as a
no-op (`len(set) > len(list)`) and therefore never once did its job.
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
XS = os.path.join("tests", "test_cross_surface_values.py")
CAL = os.path.join("tests", "test_calendar_matches_dataset.py")
STUDY = os.path.join("pdufa_site_src", "research", "fda-decision-timing", "index.html")
BI = os.path.join("pdufa_site_src", "build-info.json")
LEDGER = "_calendar_unbacked_q4_rows.json"


def run(t):
    p = subprocess.run([PY, t], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip().splitlines()


TOUCH = [STUDY, BI, LEDGER]
bk = tempfile.mkdtemp()
for i, p in enumerate(TOUCH):
    shutil.copy2(p, os.path.join(bk, str(i)))
# every /pdufa page too (invariant 2 plants into one)
pdufa_pages = sorted(glob.glob(os.path.join("pdufa_site_src", "pdufa", "*", "index.html")))
pbk = tempfile.mkdtemp()
for i, p in enumerate(pdufa_pages):
    shutil.copy2(p, os.path.join(pbk, str(i)))


def restore():
    for i, p in enumerate(TOUCH):
        shutil.copy2(os.path.join(bk, str(i)), p)
    for i, p in enumerate(pdufa_pages):
        shutil.copy2(os.path.join(pbk, str(i)), p)


ok = True
rc, out = run(XS)
print(f"[baseline]          rc={rc}  {out[-1][:96] if out else ''}")
ok &= rc == 0

# 1 -- make the study disagree with the pages that cite it.
# The numbers live inside <b> tags -- "Of the <b>30</b> ... <b>18</b> came <b>before</b>" -- so
# a plant written against the RENDERED sentence silently does nothing, which is exactly what
# happened on the first run of this prover and is why a prover is worth writing.
d = io.open(STUDY, encoding="utf-8", errors="replace").read()
io.open(STUDY, "w", encoding="utf-8").write(
    d.replace("Of the <b>30</b>", "Of the <b>27</b>", 1)
     .replace("<b>18</b> came <b>before</b>", "<b>15</b> came <b>before</b>", 1))
rc, out = run(XS)
print(f"[1 statistic split] rc={rc}  {out[0][:96] if out else ''}")
ok &= rc == 1
restore()

# 2 -- put a withdrawn day back on an event page
tgt = os.path.join("pdufa_site_src", "pdufa", "ABBV-tavapadon", "index.html")
d = io.open(tgt, encoding="utf-8", errors="replace").read()
io.open(tgt, "w", encoding="utf-8").write(
    d.replace("<span>FDA PDUFA target date</span><b>Dec 2026</b>",
              "<span>FDA PDUFA target date</span><b>2026-12-31</b>"))
rc, out = run(XS)
print(f"[2 day resurrected] rc={rc}  {out[0][:96] if out else ''}")
ok &= rc == 1
restore()

# 4 -- a negative countdown
j = json.loads(io.open(BI, encoding="utf-8").read())
j["next_days"] = -3
io.open(BI, "w", encoding="utf-8").write(json.dumps(j, indent=1))
rc, out = run(XS)
print(f"[4 negative next]   rc={rc}  {out[0][:96] if out else ''}")
ok &= rc == 1
restore()

rc, out = run(XS)
print(f"[healed]            rc={rc}  {out[-1][:96] if out else ''}")
ok &= rc == 0

# ---- the repaired ratchet -------------------------------------------------------------
rc, out = run(CAL)
print(f"\n[ratchet baseline]  rc={rc}")
ok &= rc == 0
led = json.loads(io.open(LEDGER, encoding="utf-8").read())
led["rows"].append({"ticker": "ZZZ", "window": "Q4 2026", "page": "/pdufa/ZZZ",
                    "page_asserts": "planted", "what": "planted", "external_sources": [],
                    "verdict": "planted"})
io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(led, indent=1))
rc, out = run(CAL)
hit = [l for l in out if "unbacked list holds" in l]
print(f"[ratchet grown]     rc={rc}  {hit[0][:110] if hit else (out[0][:110] if out else '')}")
ok &= rc == 1
restore()
rc, out = run(CAL)
print(f"[ratchet healed]    rc={rc}")
ok &= rc == 0

print("\nPROVEN 0 -> 1 -> 0 on every invariant" if ok else "\nNOT PROVEN")
sys.exit(0 if ok else 1)
