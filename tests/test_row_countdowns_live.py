# -*- coding: utf-8 -*-
"""test_row_countdowns_live.py -- a ticker index's row countdowns are recounted at view time.

2026-11-19 (David: "Fix the countdowns"). The "in N days" on a /pdufa/{T} index row was baked at build time, so a page
served the day after a rebuild said "in 4 days" while the header above it, counted in the browser, said "in 3 days".
build_pdufa_ticker_index.py now puts the goal date on the countdown (data-due) and build_freshness_stamp.py's script
recounts every [data-due] when the page is viewed. This fails if:

  1. a row countdown on a /pdufa/{T} index has no data-due, or its data-due is not a calendar date, or is not the date
     the row shows beside it;
  2. the baked text is not in the script's own words ("today", "tomorrow", "in N days"), so it would flicker;
  3. a page with a row countdown does not carry the recount script (it rides in the FRESH block);
  4. the recount script is missing from build_freshness_stamp.SCRIPT, or its words differ from the builder's;
  5. build_sitemap.py hashes the countdown's words or its data-due (a passing day would move lastmod).

PLANT=nodue strips data-due from one row, PLANT=noscript drops the script from one page; each must FAIL.

    python tests/test_row_countdowns_live.py
"""
import datetime as dt
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ROW = re.compile(r'<span class="t">([A-Z][a-z]{2} \d{1,2}, \d{4}) (<span class="up"[^>]*>[^<]*</span>)')
UP = re.compile(r'<span class="up" data-due="(\d{4}-\d{2}-\d{2})">(today|tomorrow|in \d+ days)</span>$')


def main():
    plant = os.environ.get("PLANT", "")
    fails, rows, pages = [], 0, 0
    import build_freshness_stamp as F
    import build_sitemap as B

    if "querySelectorAll('[data-due]')" not in F.SCRIPT:
        fails.append("build_freshness_stamp.SCRIPT: no view-time recount of [data-due]")
    for w in ("'today'", "'tomorrow'", "'in '+n+' days'"):
        if w not in F.SCRIPT:
            fails.append(f"build_freshness_stamp.SCRIPT: recount words differ from the builder's (no {w})")
    a = B.content_hash('<p><span class="up" data-due="2026-11-22">in 3 days</span></p>')
    for alt in ('<span class="up" data-due="2026-11-22">tomorrow</span>', '<span class="up">in 4 days</span>'):
        if B.content_hash(f"<p>{alt}</p>") != a:
            fails.append(f"build_sitemap: hashes the countdown ({alt}); a passing day would move lastmod")

    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        t = os.path.basename(os.path.dirname(p))
        s = io.open(p, encoding="utf-8", errors="replace").read()
        found = ROW.findall(s)
        if not found:
            continue
        pages += 1
        if plant == "nodue" and pages == 1:
            found[0] = (found[0][0], re.sub(r' data-due="[^"]*"', "", found[0][1]))
        if plant == "noscript" and pages == 1:
            s = s.replace("querySelectorAll('[data-due]')", "")
        if "querySelectorAll('[data-due]')" not in s:
            fails.append(f"/pdufa/{t}: has a row countdown but no view-time recount script (python build_freshness_stamp.py)")
        for shown, span in found:
            rows += 1
            m = UP.match(span)
            if not m:
                fails.append(f"/pdufa/{t}: countdown {span!r} lacks data-due or is not in the script's words")
                continue
            try:
                d = dt.date.fromisoformat(m.group(1))
            except ValueError:
                fails.append(f"/pdufa/{t}: data-due {m.group(1)} is not a date")
                continue
            if f"{MON[d.month - 1]} {d.day}, {d.year}" != shown:
                fails.append(f"/pdufa/{t}: data-due {m.group(1)} is not the row's date ({shown})")

    print(f"row countdowns: {rows} rows on {pages} ticker indexes")
    for f in fails:
        print("  FAIL", f)
    if fails:
        print("  fix: python build_pdufa_ticker_index.py && python build_freshness_stamp.py")
        return 1
    print("  PASS: every row countdown carries its goal date and is recounted at view time")
    return 0


if __name__ == "__main__":
    sys.exit(main())
