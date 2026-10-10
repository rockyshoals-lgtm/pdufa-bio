# -*- coding: utf-8 -*-
"""CI guard: no run-up caption calls the announcement day the FDA decision when fda_action_date differs
(audit 2026-10-04 P2; JUVMO said "FDA decision 9/28/26" for a 9/25 letter).

    python tests/test_chart_caption_fda_date.py
"""
import io, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import fix_chart_captions as F  # noqa: E402


def main():
    fails, n = [], 0
    for (tk, day), fad in sorted(F.pairs().items()):
        p = os.path.join(F.SITE, "fda-decision", f"{tk}-{day}", "index.html")
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "Daily close, T-120" not in doc:
            continue
        n += 1
        if f"FDA decision {F.mdy(day)}." in doc or f'>PDUFA {F.mdy(day)}<' in doc:
            fails.append(f"/fda-decision/{tk}-{day}: caption calls the announcement day ({F.mdy(day)}) the FDA decision; FDA acted {fad}")
        elif f"FDA action {F.mdy(fad)}" not in doc:
            fails.append(f"/fda-decision/{tk}-{day}: caption does not name the FDA action day {fad}")
    if fails:
        print(f"FAIL: {len(fails)} caption(s) misdate the FDA decision:")
        for f in fails[:15]:
            print("   " + f)
        return 1
    print(f"OK -- {n} decision pages announced on a day other than the FDA's action day; every caption names both.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
