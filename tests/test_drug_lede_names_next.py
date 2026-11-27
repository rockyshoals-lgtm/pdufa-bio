# -*- coding: utf-8 -*-
"""test_drug_lede_names_next.py -- a drug page's opening names the indication of the date it gives.

OMW round 2, 2026-11-27, checked live on a phone: /drug/bezuclastinib opened "a Cogent Biosciences program in
advanced systemic mastocytosis. Its PDUFA date is Dec 30, 2026". Dec 30 is the nonadvanced (SUMMIT) goal; the
advanced application's goal is Jun 29, 2027. The lede took the alphabetically first pending indication; 61 drug
pages paired an indication with another application's date. The same lede lower-cased every first letter, so
"IgA nephropathy", "Crohn's disease" and "Duchenne muscular dystrophy" read "igA", "crohn's" and "duchenne".

Fails if a lede that gives a PDUFA date names an indication that neither contains nor is contained in the one the
event page for that date states, or opens its indication with a lower-cased name.

    python tests/test_drug_lede_names_next.py [site_dir]
"""
import datetime as dt
import glob
import html
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDE = re.compile(r"program in ([^<]*?)\. Its PDUFA date is <b>([A-Z][a-z]{2} \d{1,2}, \d{4})</b>")
BAD_CASE = re.compile(r"program in (?:ig[A-Z]|(?:crohn|alzheimer|parkinson|huntington|cushing|graves|sjögren)['’]"
                      r"|(?:duchenne|dravet|rett|fabry|stargardt|sanfilippo|angelman|netherton|friedreich) )")


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def check(site):
    bad, n = [], 0
    for p in sorted(glob.glob(os.path.join(site, "drug", "*", "index.html"))):
        doc = read(p)
        slug = os.path.basename(os.path.dirname(p))
        m = BAD_CASE.search(doc)
        if m:
            bad.append(f"/drug/{slug}: lede lower-cases a name ({m.group(0)!r})")
        m = LEDE.search(doc)
        if not m:
            continue
        ind, day = html.unescape(m.group(1)), m.group(2)
        hrefs = re.findall(r'href="(/pdufa/[^"]+)"[^>]*>\s*<span[^>]*>PDUFA (?:·|&middot;) ' + re.escape(day) + "<", doc)
        if len(hrefs) != 1:
            continue
        ev = read(os.path.join(site, *hrefs[0].strip("/").split("/"), "index.html"))
        k = re.search(r"<span>Indication</span><b>([^<]*)</b>", ev)
        if not k:
            continue
        n += 1
        a, b = html.unescape(k.group(1)).strip().lower(), ind.strip().lower()
        if a not in b and b not in a:            # "Pain" and "moderate-to-severe acute pain" are one application
            bad.append(f"/drug/{slug}: lede names {ind!r} for {day}, but {hrefs[0]} is for {html.unescape(k.group(1))!r}")
    return n, bad


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pdufa_site_src")
    n, bad = check(site)
    print(f"{n} drug lede(s) with a PDUFA date matched against the event page for that date")
    if not n:
        bad.append("no drug lede paired with an event page -- markup changed?")
    if bad:
        print("FAIL:\n  " + "\n  ".join(bad[:30]))
        return 1
    print("  PASS: each drug lede names the indication of the date it gives, with names capitalised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
