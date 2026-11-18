# -*- coding: utf-8 -*-
"""Guard: every schema.org Event on /calendar and /readouts must be VALID for Google — i.e. carry
both `startDate` and `location`. Undatable catalysts must be demoted to a non-Event type (WebPage),
not left as an invalid Event. Also fails on stray NUL bytes (encoding corruption). This locks in the
fix_event_schema.py result so a future page regeneration can't silently reintroduce 200+ invalid
Events on the two highest-value index pages.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..", "pdufa_site_src")
EVENT = re.compile(r'\{"@type":"Event"(?:[^{}]|\{[^{}]*\})*\}')

bad = []
for page in ["calendar/index.html", "readouts/index.html", "adcomm/index.html"]:
    p = os.path.join(SITE, page)
    if not os.path.exists(p):
        continue
    h = open(p, encoding="utf-8", errors="replace").read()
    if "\x00" in h:
        bad.append(f"{page}: contains {h.count(chr(0))} NUL byte(s)")
    invalid = sum(1 for m in EVENT.finditer(h)
                  if '"startDate"' not in m.group(0) or '"location"' not in m.group(0))
    total = len(EVENT.findall(h))
    # Google requires a datetime WITH timezone on Event.startDate for rich-result eligibility;
    # a bare YYYY-MM-DD is what made ~206 items ineligible (GSC: "94% not eligible").
    dateonly = len(re.findall(r'"startDate":"\d{4}-\d{2}-\d{2}"', h))
    print(f"  {page:22s} Events={total:4d} invalid={invalid} date_only_startDate={dateonly}")
    if invalid:
        bad.append(f"{page}: {invalid} Event object(s) missing startDate/location")
    if dateonly:
        bad.append(f"{page}: {dateonly} startDate(s) lack a time+timezone (not rich-result eligible)")

# 2026-11-18 (Google SEO): Search Console listed 2 invalid Events. They were not on the three index
# pages above but on the hand-built /adcomm/CAPR-2026-07-29 and /adcomm/REPL-2026-07-30 pages, which
# carried a bare Event (name, startDate, url; no location). Every built page is now checked for
# Google's two required Event fields, parsing the JSON-LD so key order and spacing don't matter.
import glob, json
LD = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)


def _events(n):
    if isinstance(n, dict):
        t = n.get("@type")
        if t == "Event" or (isinstance(t, list) and "Event" in t):
            yield n
        for v in n.values():
            yield from _events(v)
    elif isinstance(n, list):
        for v in n:
            yield from _events(v)


n_pages = n_ev = 0
for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
    rel = os.path.relpath(p, SITE).replace(os.sep, "/")
    h = open(p, encoding="utf-8", errors="replace").read()
    if '"Event"' not in h:
        continue
    n_pages += 1
    for blob in LD.findall(h):
        try:
            data = json.loads(blob)
        except ValueError:
            continue          # unparseable JSON-LD: Google can't read it either; not this guard's subject
        for ev in _events(data):
            n_ev += 1
            miss = [k for k in ("startDate", "location") if not ev.get(k)]
            if miss:
                bad.append(f"{rel}: Event {str(ev.get('name'))[:60]!r} lacks {', '.join(miss)} "
                           f"(Google counts it invalid; give it the real field or drop the Event)")
print(f"  site-wide: {n_ev} Event node(s) on {n_pages} page(s) checked for startDate + location")

if bad:
    print("FAIL -- invalid Event schema:")
    for b in bad:
        print("   -", b)
    sys.exit(1)
print("OK -- every Event on the site has startDate + location; no NUL bytes on the index pages.")
