# -*- coding: utf-8 -*-
"""A per-event PDUFA page whose event has been decided must say so.

Guards the gap the 2026-09-01b re-audit found: event pages are write-once (hand-grown
content), so /pdufa/REGN-garetosmab presented an approved drug as pending for 13 days on
a 33%-CTR page. mark_event_pages_decided.py now injects a DECBAN outcome banner daily;
this test fails the build if a decided event's page is missing one -- using the SAME
conservative matcher, so a page the injector would skip (ambiguous match) is not flagged.
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)


def toks(s):
    return set(re.findall(r"[a-z0-9]{4,}", str(s or "").lower()))


def test_decided_event_pages_carry_banner():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    decided = [r for r in rows if r.get("type") == "PDUFA"
               and str(r.get("st", "")).lower() == "decided" and r.get("dcd")]
    assert decided, "no decided PDUFA rows in dataset -- dataset parse broken?"

    bad = []
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(.+)$", slug)
        if not m:
            continue
        tk, drug_part = m.group(1), m.group(2).replace("-", " ")
        tk_cands = [r for r in decided if str(r.get("t", "")).upper() == tk]
        cands = [r for r in tk_cands if toks(drug_part) & toks(r.get("name"))]
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if not cands and tk_cands:
            tm = re.search(r"<title[^>]*>[A-Z]{1,6} PDUFA date:\s*(.+?),\s*[A-Z][a-z]{2}",
                           doc)
            if tm:
                cands = [r for r in tk_cands if toks(tm.group(1)) & toks(r.get("name"))]
        if len(cands) != 1:
            continue          # no match or ambiguous -- the injector skips these too
        if "<!--DECBAN:BEGIN-->" not in doc:
            bad.append(f"/pdufa/{slug} (event decided {cands[0].get('dcd')} "
                       f"{cands[0].get('oc')}, page has no outcome banner)")
        else:
            # the banner must carry the decision date the dataset carries
            ban = doc.split("<!--DECBAN:BEGIN-->", 1)[1].split("<!--DECBAN:END-->", 1)[0]
            import datetime as dt
            d = dt.date.fromisoformat(str(cands[0].get("dcd"))[:10])
            MON = ["", "January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"]
            if f"{MON[d.month]} {d.day}, {d.year}" not in ban:
                bad.append(f"/pdufa/{slug} (banner date disagrees with dataset "
                           f"dcd {cands[0].get('dcd')})")
    assert not bad, ("decided events with stale event pages -- run "
                     "mark_event_pages_decided.py:\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    test_decided_event_pages_carry_banner()
    print("OK")
