# -*- coding: utf-8 -*-
"""test_decision_names_whole.py -- no decided row shows a name an old build cut off.

UX pass 2026-11-20. /decisions and its sub-lists showed "CTx-1301 (fixed dose, pediatri", "LNTH-2501 (Gallium-68
edotreot", "ZYNYZ (retifanlimab-dlwr) - (P" and "EBGLYSS (lebrikizumab-lbkz) -". whole_decision_names.py makes them
whole from the decision page's own name. This fails if any page holds a decided row that pass would still change
(it was skipped, or a writer after it cut a name again).

    python tests/test_decision_names_whole.py
"""
import glob
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import whole_decision_names as W  # noqa: E402


def main():
    bad, rows = [], 0
    for p in sorted(glob.glob(os.path.join(W.SITE, "**", "index.html"), recursive=True)):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "/fda-decision/" not in doc:
            continue
        rows += len(W.ROW.findall(doc))
        _new, n = W.fix(doc)
        if n:
            bad.append(f"/{os.path.relpath(os.path.dirname(p), W.SITE).replace(os.sep, '/')}: {n} decided row(s) "
                       f"with a cut-off name (python whole_decision_names.py)")
    print(f"{rows} decided row(s) checked")
    if not rows:
        print("FAIL: no decided rows parsed -- markup changed?")
        return 1
    if bad:
        print("FAIL:\n  " + "\n  ".join(bad[:30]))
        return 1
    print("  PASS: every decided row names its drug whole")
    return 0


if __name__ == "__main__":
    sys.exit(main())
