# -*- coding: utf-8 -*-
"""test_decision_timing_current.py -- a decision page's timing facts stay current once the FDA's own day is on record.

2026-11-25 currency red team, CAPR-2026-11-20. Capricor announced its Complete Response Letter at 7:55 PM ET on
November 20 (GlobeNewswire time stamp), after the close. The FDA's letter, released later, is dated November 20 and the
goal date was November 22. When that letter put the FDA's day on record, two lines went stale at once:

  * the "after the close" note lived only in the announcement-only form of key facts, so the restore to canonical form
    dropped it, and the home card called the Nov 20 close "reaction day up 1%", a close taken before the news;
  * the page still said "The release does not state the letter's own date, so no early or late margin is given",
    while the site's own decision-timing study gave the margin as 2 days early.

This fails if:
  1. a decision in _announced_after_close.json has no "Announced | YYYY-MM-DD, after the close" row on its page;
  2. its "Move measured on" row measures the announcement day's own close without saying the news came after it;
  3. its home "Recently decided" card states a move measured on the announcement day itself;
  4. any decision page whose Verified line gives both the FDA's action day and the goal date still says no early or
     late margin is given.
PLANT=drop removes CAPR's after-close row in memory; PLANT=margin puts the old CAPR sentence back. Each must FAIL.

    python tests/test_decision_timing_current.py      (fix: python label_announcement_only_dates.py)
"""
import datetime as dt
import glob
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
LEDGER = os.path.join(HERE, "_announced_after_close.json")
NO_MARGIN = re.compile(r"no early or late margin|not state an early or late margin|no margin is (?:given|stated)|"
                       r"does not date the letter|letter's own date, so", re.I)
VDAY = r"([A-Z][a-z]+ \d{1,2}, \d{4}) \("
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment)))


def main():
    plant = os.environ.get("PLANT", "")
    bad = []
    led = json.load(io.open(LEDGER, encoding="utf-8")).get("after_close", {})
    home = io.open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()

    for slug, e in sorted(led.items()):
        day = e["announced"]
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(p):
            bad.append(f"{slug}: in _announced_after_close.json but has no decision page")
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if plant == "drop" and slug == "CAPR-2026-11-20":
            doc = re.sub(r"<!--ANNLATE-->.*?<!--/ANNLATE-->", "", doc, flags=re.S)
        if f"<span>Announced</span><b>{day}, after the close</b>" not in doc:
            bad.append(f"/fda-decision/{slug}: key facts do not say it was announced {day}, after the close")
        mm = re.search(r'<span>Move measured on</span><b>([^<]*)</b>', doc)
        if mm and mm.group(1).startswith(f"{day} close") and "news came after this close" not in mm.group(1):
            bad.append(f"/fda-decision/{slug}: the move is measured on the {day} close without saying the news came "
                       f"after it")
        card = re.search(rf'<a class="dec [a-z]+" href="/fda-decision/{re.escape(slug)}" title="([^"]*)"', home)
        d = dt.date.fromisoformat(day)
        if card and re.search(rf"move [+-]?\d+% on {MON[d.month]} {d.day},", html.unescape(card.group(1))):
            bad.append(f"home: the {slug} card measures the move on {day}, but the news came after that close")

    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if plant == "margin" and slug == "CAPR-2026-11-20":
            doc = doc.replace("so the FDA acted 2 days before the goal date",
                              "so no early or late margin is given", 1)
        v = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
        vt = text(v.group(1)) if v else ""
        fda, goal = re.search(r"FDA action day " + VDAY, vt), re.search(r"Goal date " + VDAY, vt)
        if not (fda and goal):
            continue
        body = text(re.sub(r"<(script|style)\b.*?</\1>", "", doc, flags=re.S))
        hit = NO_MARGIN.search(body)
        if hit:
            bad.append(f"/fda-decision/{slug}: the FDA acted {fda.group(1)} and the goal was {goal.group(1)}, but the "
                       f"page still says {body[max(0, hit.start() - 60):hit.end()].strip()!r}")

    print(f"{len(led)} after-close announcement(s) checked; decision pages with both FDA day and goal date scanned")
    if bad:
        print("FAIL")
        for b in bad[:20]:
            print("  " + b)
        return 1
    print("  PASS: after-close announcements keep their note, and every page with both dates states its margin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
