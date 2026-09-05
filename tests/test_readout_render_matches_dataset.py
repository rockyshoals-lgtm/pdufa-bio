# -*- coding: utf-8 -*-
"""The /readouts results module may not render a row its dataset disagrees with.

Audit 2026-09-04 §4: TYRA's date was corrected to 2027 in the dataset, but the
"recently reported" module kept rendering "TYRA · Aug 2026" WITH A -8% MOVE -- a
measured market reaction attached to an event that, by our own data, has not happened.
Root cause: the module preferred a fossil `dm` month field over the corrected event
date. The renderer now uses the event date and skips Reported rows; this guard asserts
the RESULT so the two layers cannot drift apart again:

  - every auto-logged window row ("TK · Mon YYYY" inside the results block) must match
    a dataset Readout row for that ticker whose event month EQUALS the rendered month
    and whose status is still Estimated/Guided (a Reported row belongs in the
    confirmed section, with its outcome in words);
  - no rendered window month may be in the future.
"""
import datetime as dt
import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MON3 = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
     "Nov", "Dec"], 1)}


def test_results_module_matches_dataset():
    page = io.open(os.path.join(SITE, "readouts", "index.html"), encoding="utf-8",
                   errors="replace").read()
    # Scope: the block opens with <div id="readout-results"> and closes with the
    # comment marker. Two failed scoping attempts are worth recording: an opening
    # COMMENT marker doesn't exist (guard passed on a planted phantom), and a
    # whole-page scan flagged the forward table's legitimate future month rows.
    m = re.search(r'<div id="readout-results">([\s\S]*?)<!--/readout-results-->', page)
    if not m:
        return                                   # module absent: nothing to disagree
    block = m.group(1)

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    by_tk = {}
    for r in rows:
        if r.get("type") == "Readout":
            by_tk.setdefault(str(r.get("t", "")).upper(), []).append(r)

    cur = dt.date.today().strftime("%Y-%m")
    bad = []
    # auto-window rows render "TK · Mon YYYY" WITHOUT a day; confirmed rows render a
    # full ISO date, so this pattern selects only the window rows.
    for mm in re.finditer(r'class="t">([A-Z]{1,6}) (?:&middot;|·) '
                          r'([A-Z][a-z]{2}) (\d{4})\b(?!-)', block):
        tk, mon, yr = mm.group(1), mm.group(2), mm.group(3)
        if mon not in MON3:
            continue
        ym = f"{yr}-{MON3[mon]:02d}"
        if ym >= cur:
            bad.append(f"{tk} {ym}: window month not yet elapsed")
            continue
        ok = any(str(r.get("d", ""))[:7] == ym
                 and str(r.get("st")) in ("Estimated", "Guided")
                 for r in by_tk.get(tk, []))
        if not ok:
            bad.append(f"{tk} {ym}: no Estimated/Guided dataset readout in that month "
                       f"(TYRA-class phantom: a move rendered for a non-event)")
    assert not bad, ("results module disagrees with the dataset:\n  "
                     + "\n  ".join(bad))


if __name__ == "__main__":
    test_results_module_matches_dataset()
    print("OK")
