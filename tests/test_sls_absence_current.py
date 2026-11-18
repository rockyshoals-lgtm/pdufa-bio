# -*- coding: utf-8 -*-
"""CI guard: /sls may not say the 80th REGAL event is unannounced after SELLAS has announced it.

WHY (red team 2026-11-17)
SELLAS announced the 80th event on Oct 28, 2026 and REGAL topline on Nov 17, 2026, both by press
release. check_sls_filings.py only reads EDGAR, so /sls kept saying "80th event announced? Not yet"
for three weeks, through the topline, while its own activity feed listed the Oct 28 release.

THE INVARIANTS
  1. If the SLS activity log or the dataset shows the 80th event or the REGAL topline, then
     _sls_verified_through.json records it ("event80", and "topline" once reported).
  2. Once "event80" is recorded, neither /sls nor /research/sls-deep-dive carries an absence claim.

    python tests/test_sls_absence_current.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")


def load(p, default):
    try:
        return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))
    except Exception:
        return default


def evidence():
    ev = []
    for e in (load("_sls_activity.json", {}).get("events") or []):
        if re.search(r"80th event", str(e.get("title") or ""), re.I):
            ev.append(("event80", e.get("date"), e.get("title")))
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    for r in json.loads(src[src.index("["):src.rindex("]") + 1]):
        if r.get("t") == "SLS" and r.get("st") == "Reported" and "REGAL" in str(r.get("name")):
            ev.append(("topline", r.get("d"), r.get("name")))
    return ev


def check(state, ev, pages):
    from sls_resolution import ABSENCE
    fails = []
    for k, d, what in ev:
        if not state.get(k):
            fails.append(f"{what!r} ({d}) is not recorded under '{k}' in _sls_verified_through.json")
    if state.get("event80"):
        for rel, doc in pages.items():
            left = [w for w in ABSENCE if w in doc]
            if left:
                fails.append(f"/{rel} still carries an absence claim: {left} (run sls_resolution.py)")
    return fails


def self_test():
    pages = {"sls": "80th event announced? <div>Not yet</div>"}
    a = check({}, [("event80", "2026-10-28", "Reaches 80th Event")], {})
    b = check({"event80": {"date": "2026-10-28"}}, [], {"sls": '<div class="big">>Not yet<</div>'})
    c = check({"event80": {"date": "2026-10-28"}}, [("event80", "x", "y")], {"sls": "Yes"})
    ok = len(a) == 1 and len(b) == 1 and not c
    if not ok:
        print("SELF-TEST FAILED", a, b, c)
    return ok


def main():
    if not self_test():
        return 1
    pages = {}
    for rel in ("sls/index.html", "research/sls-deep-dive/index.html"):
        p = os.path.join(SITE, rel)
        if os.path.exists(p):
            pages[rel] = io.open(p, encoding="utf-8", errors="replace").read()
    fails = check(load("_sls_verified_through.json", {}), evidence(), pages)
    if fails:
        print(f"FAIL: /sls is behind what SELLAS has announced ({len(fails)}):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- every REGAL announcement on file is recorded, and the SLS pages carry no stale absence claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
