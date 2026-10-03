# -*- coding: utf-8 -*-
"""CI guard: /patent-cliff/exclusivity lists the Orange Book's NDA exclusivities, counted honestly (audit 4.3).

Fails, on the rendered page, when the count in the h1 differs from the table rows; when a row's end date is
before the build's Eastern date or after 2031; when the page does not state the Orange Book file date or the
"not a generic launch" disclosure; or when /patent-cliff does not link it.

    python tests/test_exclusivity_cliff.py
"""
import datetime as dt
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def main():
    p = os.path.join(SITE, "patent-cliff", "exclusivity", "index.html")
    if not os.path.exists(p):
        print("FAIL: /patent-cliff/exclusivity not built")
        return 1
    doc = io.open(p, encoding="utf-8").read()
    fails = []
    m = re.search(r"<h1>Regulatory exclusivity cliff: (\d+) FDA exclusivities", doc)
    rows = re.findall(r'<tr><td style="padding:4px;white-space:nowrap">([A-Z][a-z]{2}) (\d{1,2}), (\d{4})</td>', doc)
    if not m or int(m.group(1)) != len(rows):
        fails.append(f"h1 states {m.group(1) if m else '?'}, table has {len(rows)} rows")
    built = re.search(r"end between ([A-Z][a-z]+) (\d{1,2}), (\d{4})", doc)
    lo = dt.datetime.strptime(" ".join(built.groups()), "%B %d %Y").date() if built else None
    for mo, d, y in rows:
        day = dt.date(int(y), MON[mo], int(d))
        if (lo and day < lo) or day > dt.date(2031, 12, 31):
            fails.append(f"row dated {day} outside {lo}..2031-12-31")
            break
    if "Orange Book data files dated" not in doc or "not a generic launch" not in doc:
        fails.append("page lacks the Orange Book file date or the disclosure")
    hub = io.open(os.path.join(SITE, "patent-cliff", "index.html"), encoding="utf-8").read()
    if 'href="/patent-cliff/exclusivity"' not in hub:
        fails.append("/patent-cliff does not link /patent-cliff/exclusivity")
    if fails:
        print("FAIL: exclusivity cliff:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- /patent-cliff/exclusivity lists {len(rows)} NDA exclusivities, dated and disclosed, linked from the hub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
