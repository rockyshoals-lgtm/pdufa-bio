# -*- coding: utf-8 -*-
"""A /drug title that states a PDUFA date states a live one, and the page body says the same date.

2026-11-27: build_drug_pages puts "<drug> PDUFA Date: <Mon D, YYYY>" in the title of a drug with a
live day-precision PDUFA date, because "<drug> pdufa date" is the question Bing's AI answers cite us
for most. A title is what an answer engine quotes, so it must never carry a date that has passed or
one the page itself does not state.

    python tests/test_drug_title_pdufa_date.py      (PLANT=stale makes it fail)
"""
import datetime as dt, glob, html, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from site_dates import eastern_today

MON = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
FULL = ["January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December"]
PAT = re.compile(r"<title>[^<]*PDUFA Date: (\w{3}) (\d{1,2}), (\d{4})")


def main():
    today = eastern_today()
    bad, n = [], 0
    for f in sorted(glob.glob(os.path.join(HERE, "pdufa_site_src", "drug", "*", "index.html"))):
        h = open(f, encoding="utf-8", errors="replace").read()
        if os.environ.get("PLANT") == "stale" and n == 0 and "<title>" in h:
            h = h.replace("<title>", "<title>X PDUFA Date: Jan 2, 2020 | ", 1)
        m = PAT.search(h)
        if not m:
            continue
        n += 1
        slug = os.path.basename(os.path.dirname(f))
        d = dt.date(int(m.group(3)), MON[m.group(1)], int(m.group(2)))
        if d < today:
            bad.append(f"/drug/{slug}: title states {d}, which has passed")
            continue
        body = html.unescape(re.sub(r"<[^>]+>", " ", h[h.find("<body"):]))
        forms = (f"{FULL[d.month - 1]} {d.day}, {d.year}", f"{m.group(1)} {d.day}, {d.year}", d.isoformat())
        if not any(x in body for x in forms):
            bad.append(f"/drug/{slug}: title states {d}, but the page body never does")
    print(f"{n} drug title(s) state a PDUFA date; {len(bad)} problem(s)")
    for b in bad[:20]:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
