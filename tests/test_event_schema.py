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

if bad:
    print("FAIL -- invalid Event schema:")
    for b in bad:
        print("   -", b)
    sys.exit(1)
print("OK -- every Event on /calendar and /readouts has startDate + location; no NUL bytes.")
