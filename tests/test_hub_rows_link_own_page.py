# -*- coding: utf-8 -*-
"""test_hub_rows_link_own_page.py -- a ticker hub's upcoming row opens that application's own page.

OMW round 2, 2026-11-27, checked live on a phone: the Cogent hub's two pending bezuclastinib rows
(SUMMIT, Dec 30 2026; AdvSM, Jun 29 2027) both opened the decided GIST page (approved Nov 24 as
Ekitna). Roche's Enspryng MOGAD row (Jan 10 2027) opened the approved NMOSD page, and BioMarin's
Voxzogo hypochondroplasia row (May 30 2027) opened the achondroplasia page. The hub matched by drug
word and took the first page that shared one; build_ticker_hubs.pick_event_slug() now takes the page
that states the row's own goal date.

Fails if an upcoming hub row links a decided /pdufa/ page, or links any page other than the one
/pdufa/ page of that ticker that states the row's goal date.

    python tests/test_hub_rows_link_own_page.py [site_dir]
"""
import datetime as dt
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TGT = re.compile(r"<span>FDA PDUFA target date</span><b>(\d{4}-\d{2}-\d{2})")
ROW = re.compile(r'<a class="row" href="(/pdufa/[^"]+)"><span class="t">([A-Z.]+) · ([A-Z][a-z]{2} \d{1,2}, \d{4})</span>')


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def check(site):
    bad, n = [], 0
    pages = {}
    for p in glob.glob(os.path.join(site, "pdufa", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        doc = read(p)
        m = TGT.search(doc)
        t = re.search(r"<title>([^<]*)", doc)
        pages[slug] = (m.group(1) if m else "", bool(t) and " FDA decision: " in t.group(1))
    for hub in sorted(glob.glob(os.path.join(site, "ticker", "*", "index.html"))):
        doc = read(hub)
        i = doc.find("<h2>Upcoming FDA catalysts</h2>")
        if i < 0:
            continue
        sec = doc[i:doc.find("<h2>", i + 10) if doc.find("<h2>", i + 10) > 0 else len(doc)]
        for href, tk, day in ROW.findall(sec):
            n += 1
            iso = dt.datetime.strptime(day, "%b %d, %Y").date().isoformat()
            slug = href.split("/")[2]
            own = [s for s, (t, _d) in pages.items() if t == iso and (s == tk or s.startswith(tk + "-"))]
            tgt, decided = pages.get(slug, ("", False))
            if decided:
                bad.append(f"/ticker/{tk}: the {day} row opens {href}, a decided page")
            elif len(own) == 1 and slug != own[0]:
                bad.append(f"/ticker/{tk}: the {day} row opens {href}, not /pdufa/{own[0]} (its own page)")
    return n, bad


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pdufa_site_src")
    n, bad = check(site)
    print(f"{n} upcoming hub row(s) linking a /pdufa/ page checked")
    if not n:
        bad.append("no upcoming hub rows parsed -- markup changed?")
    if bad:
        print("FAIL:\n  " + "\n  ".join(bad[:30]))
        return 1
    print("  PASS: every upcoming hub row opens the page that states its own goal date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
