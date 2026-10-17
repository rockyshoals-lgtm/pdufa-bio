# -*- coding: utf-8 -*-
"""CI guard: a decided /pdufa/ event page introduces itself as decided (audit 2026-10-17, 2a).

On 2026-10-17, 10 of 27 decided event pages told search engines the decision was pending ("IBRX's FDA PDUFA target
is Jan 6, 2027 for ANKTIVA", eleven days after the approval), the IRD/VTRS page was titled "IRD / VTRS PDUFA date:
... Oct 17, 2026", 25 carried a schema.org Event with eventStatus EventScheduled, and two banners said "the FDA
decided this application on" a day only the sponsor's announcement states. For every indexable event page with a
DECBAN, fails when:
  1. the title, meta description, og:description or twitter:description is in the pending tense;
  2. any JSON-LD carries an Event (or EventScheduled);
  3. the banner states an FDA decision day for a row whose decision date is the sponsor's announcement
     (_d.decision_date_unsourced with no fda_action_date).
Plants: PLANT_EVT=desc | event | banner must each FAIL.

    python tests/test_decided_event_pages_meta.py
"""
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
STALE = re.compile(r"PDUFA target is|PDUFA date is|PDUFA date:|goal date [A-Z][a-z]+ \d{1,2}, \d{4} under|"
                   r"due to decide|decision is expected|is expected to make|target decision date|under FDA review",
                   re.I)
B, E = "<!--DECBAN:BEGIN-->", "<!--DECBAN:END-->"


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    by_tkd = {(str(r.get("t") or "").upper(), str(r.get("dcd") or "")[:10]): r for r in rows if r.get("dcd")}
    plant = os.environ.get("PLANT_EVT", "")
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B not in doc or re.search(r'<meta name="robots" content="noindex', doc):
            continue
        if slug == "IBRX-anktiva":
            if plant == "desc":
                doc = re.sub(r'(<meta name="description" content=")[^"]*',
                             r"\1IBRX&#x27;s FDA PDUFA target is Jan 6, 2027 for ANKTIVA", doc, count=1)
            if plant == "event":
                doc = doc.replace("</head>", '<script type="application/ld+json">{"@type": "Event", "eventStatus": '
                                  '"https://schema.org/EventScheduled"}</script></head>', 1)
        if slug == "IRD-phentolamine-ophthalmic" and plant == "banner":
            doc = doc.replace("approval was announced on", "the FDA decided this application on", 1)
        n += 1
        for lab, rx in (("title", r"<title>(.*?)</title>"),
                        ("description", r'<meta name="description" content="([^"]*)"'),
                        ("og:description", r'<meta property="og:description" content="([^"]*)"'),
                        ("twitter:description", r'<meta name="twitter:description" content="([^"]*)"')):
            m = re.search(rx, doc, re.S)
            if m and STALE.search(html.unescape(m.group(1))):
                fails.append(f"/pdufa/{slug}: {lab} is in the pending tense: '{html.unescape(m.group(1))[:100]}'")
        if re.search(r'"@type"\s*:\s*"Event"', doc) or "EventScheduled" in doc:
            fails.append(f"/pdufa/{slug}: decided, but its JSON-LD still carries an Event")
        ban = doc.split(B, 1)[1].split(E, 1)[0]
        lm = re.search(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', ban)
        row = by_tkd.get((lm.group(1), lm.group(2))) if lm else None
        d = (row or {}).get("_d") or {}
        if d.get("decision_date_unsourced") and not d.get("fda_action_date") and "the FDA decided this application on" in ban:
            fails.append(f"/pdufa/{slug}: banner states an FDA decision day the record does not hold "
                         f"(only the sponsor's announcement of {lm.group(2)})")
    if fails:
        print(f"FAIL: {len(fails)} decided event page failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} decided event pages: decided title and descriptions, no Event schema, banners state only "
          "the days the record holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
