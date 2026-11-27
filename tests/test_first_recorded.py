# -*- coding: utf-8 -*-
"""CI guard: the "entered pdufa.bio's records" line (inject_first_recorded.py) is on every
decision page recorded after the repository's first import, its time is the ledger's converted to Eastern, and the
ledger never holds a time later than the commit it names (a first-recorded time can only move earlier).

PLANT=1 strips the line from one page and must FAIL.

    python tests/test_first_recorded.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import inject_first_recorded as F  # noqa: E402


def main():
    if not os.path.exists(F.LEDGER):
        print("  SKIP no ledger")
        return 0
    led = json.load(io.open(F.LEDGER, encoding="utf-8"))
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(F.SITE, "fda-decision", "*", "index.html"))):
        s = os.path.basename(os.path.dirname(p))
        e = led.get(s)
        if not e or dt.datetime.fromisoformat(e["ts"]).astimezone(F.ET) < F.IMPORT_CUTOFF:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "<!--VERIFIED:END-->" not in doc:
            continue
        n += 1
        if os.environ.get("PLANT") and n == 1:
            doc = re.sub(re.escape(F.B) + ".*?" + re.escape(F.E), "", doc, flags=re.S)
        m = re.search(re.escape(F.B) + "(.*?)" + re.escape(F.E), doc, re.S)
        if not m:
            fails.append(f"{s}: no first-recorded line")
        elif F.fmt_et(e["ts"]) not in m.group(1):
            fails.append(f"{s}: line does not state the ledger time in ET ({F.fmt_et(e['ts'])})")
    if fails:
        for f in fails[:20]:
            print("  FAIL " + f)
        print(f"\n{len(fails)} failure(s) -- run inject_first_recorded.py")
        return 1
    print(f"OK -- {n} decision pages state when they entered pdufa.bio's records (ET), matching the ledger.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
