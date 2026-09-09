# -*- coding: utf-8 -*-
"""A diagnostic must never be described as a treatment.

Audit 2026-09-09b item 2. Two days before its FDA decision, /pdufa/TLX read "TLX101-Px is
under FDA review to treat recurrent or progressive glioma." TLX101-Px is Pixclara
(floretyrosine F 18), a PET imaging agent submitted for the CHARACTERISATION of recurrent or
progressive glioma from treatment-related change. It does not treat anything. The story
builder hard-coded "to treat" for every application, and the therapeutic candidate TLX101 --
a genuinely different programme -- made the error easy to miss.

Contract: on any published page, a product our own data marks or names as a diagnostic may
not be paired with a therapy verb. Sources: the dataset's `_d.modality` field, plus the
diagnostic cues our indication text uses (PET imaging, -CDx, -Px, "characterisation of").

Proved 0 -> 1 -> 0 on 2026-09-09 by restoring "to treat" to the TLX page.
"""
import glob
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")

CUE = re.compile(r"\b(?:PET imaging|imaging agent|radiodiagnostic|diagnostic agent|"
                 r"to characteris[ez]e|characteris[ez]ation of|companion diagnostic|"
                 r"-CDx\b|-Px\b|contrast agent)\b", re.I)
THERAPY_VERB = re.compile(r"(?:is under FDA review|under review|submitted|approved|indicated)"
                          r"\s+to\s+treat", re.I)


def diagnostic_rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    out = {}
    for r in rows:
        d = r.get("_d") or {}
        blob = f"{r.get('name', '')} {d.get('indication', '') or ''}"
        if str(d.get("modality", "")).lower() == "diagnostic" or CUE.search(blob):
            tk = str(r.get("t") or "").upper()
            if tk:
                out.setdefault(tk, set()).add(str(r.get("name") or ""))
    return out


def test_no_diagnostic_called_a_treatment():
    diags = diagnostic_rows()
    assert diags, "no diagnostic row found in the dataset -- guard cannot see"
    bad = []
    for tk, names in sorted(diags.items()):
        for p in glob.glob(os.path.join(SITE, "pdufa", f"{tk}*", "index.html")):
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            m = THERAPY_VERB.search(doc)
            if m:
                slug = os.path.basename(os.path.dirname(p))
                bad.append(f"/pdufa/{slug}: {m.group(0)!r} on a page for a diagnostic "
                           f"({', '.join(sorted(names))[:60]})")
    assert not bad, ("diagnostic(s) described as a treatment (the TLX101-Px class):\n  "
                     + "\n  ".join(bad))


if __name__ == "__main__":
    test_no_diagnostic_called_a_treatment()
    print("OK")
