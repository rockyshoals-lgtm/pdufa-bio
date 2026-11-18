# -*- coding: utf-8 -*-
"""test_event_page_currency.py -- nothing on a /pdufa/ event page is frozen at the day it was written.

Design red team 2026-11-18. Four days before Capricor's Nov 22 decision, /pdufa/CAPR showed a price chart that
ended 2026-06-19 under "last ~120 days", a chip to "All August 2026 PDUFA dates", three "related" decisions that
had all happened in July and August, and an unsourced "runway ~36 mo (estimated)". All 60 pages with that chart
had it ending 2026-06-19. refresh_event_page_currency.py now redraws or removes each of these every rebuild; this
fails if any comes back:

  1. no chart from the June one-off batch ("Price path to YYYY-MM-DD") remains, and every redrawn chart ends
     within 7 days of today and states its range;
  2. a page's "All <Month> <Year> PDUFA dates" chip names the month of the page's own target date;
  3. no "Same area" / "Same month" related row shows a date before today;
  4. no "Balance sheet: about N months of cash" sentence or runway risk badge remains.

    python tests/test_event_page_currency.py
"""
import datetime as dt
import glob
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
MON3 = {m[:3].capitalize(): i + 1 for i, m in enumerate(MONTHS)}

try:
    from zoneinfo import ZoneInfo
    TODAY = dt.datetime.now(ZoneInfo("America/New_York")).date()
except Exception:
    TODAY = dt.date.today()


def main():
    pages = sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")))
    bad = []
    charts = 0
    for p in pages:
        slug = "/pdufa/" + os.path.basename(os.path.dirname(p))
        doc = open(p, encoding="utf-8", errors="replace").read()

        if re.search(r'<div class="note">Price path to \d{4}-\d{2}-\d{2}\.', doc):
            bad.append(f"{slug}: still carries the one-off run-up chart ('Price path to ...')")
        for blk in re.findall(r"<!--EVRUNUP:B:[^>]*-->(.*?)<!--EVRUNUP:E-->", doc, re.S):
            if "<svg" not in blk:
                continue
            charts += 1
            m = re.search(r"the last \d+ trading sessions: ([A-Z][a-z]{2}) (\d{1,2}), (\d{4}) to "
                          r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4}), the latest close", blk)
            if not m:
                bad.append(f"{slug}: price chart does not state its date range")
                continue
            last = dt.date(int(m.group(6)), MON3[m.group(4)], int(m.group(5)))
            if (TODAY - last).days > 7:
                bad.append(f"{slug}: price chart ends {last}, more than 7 days ago")
            if 'aria-label="' not in blk:
                bad.append(f"{slug}: price chart has no text alternative")

        tg = re.search(r'FDA decision \(PDUFA\) target <b>(\d{4}-\d{2}-\d{2})</b>', doc)
        if tg:
            want = f"/calendar/{tg.group(1)[:4]}/{MONTHS[int(tg.group(1)[5:7]) - 1]}"
            for href in re.findall(r'<a href="(/calendar/\d{4}/[a-z]+)"[^>]*>All [A-Za-z]+ \d{4} PDUFA dates', doc):
                if href != want:
                    bad.append(f"{slug}: month chip links {href} but the page's target date is {tg.group(1)}")

        for d, why in re.findall(r'<span class="t">[^<]*? \. (\d{4}-\d{2}-\d{2})</span><span class="d">'
                                 r'(Same (?:area|month)[^<]*)</span>', doc):
            if d < TODAY.isoformat():
                bad.append(f"{slug}: related row '{why[:40]}' shows {d}, already past")

        if re.search(r"Balance sheet: about <b>\d+ months of cash</b>", doc) or "runway ends before" in doc:
            bad.append(f"{slug}: unsourced cash-runway sentence or runway badge")

    print(f"checked {len(pages)} /pdufa/ pages; {charts} current price chart(s)")
    if bad:
        for b in bad[:40]:
            print("  FAIL " + b)
        if len(bad) > 40:
            print(f"  ... and {len(bad) - 40} more")
        print("  fix: python refresh_event_page_currency.py")
        sys.exit(1)
    print("  PASS: event pages carry no frozen chart, month chip, related row or runway estimate")


if __name__ == "__main__":
    main()
