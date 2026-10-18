# -*- coding: utf-8 -*-
"""Audit 09-15 ORDER 7: two pairs of /pdufa pages describe one event each and both members
index. Search engines pick one at random; AI engines cite both and count two events.

  /pdufa/ABBV-tavapadon-2  ->  /pdufa/ABBV-tavapadon   (one NDA, one goal window; the -2 slug is
                                                       a second generation of the same page)
  /pdufa/NVO-cagrisema     ->  /pdufa/NVO-am833        (AM833 IS CagriSema; the dataset row's own
                                                       name is "CagriSema (AM833)")

The MRK-trodelvy / GILD-trodelvy pair stays: the same sBLA, but two sponsors' tickers and two
pages a reader of either ticker hub expects ("David rules" -- auditor 09-15).

Treatment of the duplicate: its <link rel=canonical> points at the primary, its robots meta
becomes noindex,follow (a canonical alone is a hint; noindex is an instruction), every internal
link to it is rewritten to the primary, and it drops out of sitemap.xml. The page itself stays
so any inbound link still lands on the content. Idempotent; the guard
tests/test_duplicate_event_pages_canonical.py holds the map.

    python canonicalise_duplicate_event_pages.py
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DUPES = {"ABBV-tavapadon-2": "ABBV-tavapadon", "NVO-cagrisema": "NVO-am833",
         # Found by the guard's title census on its first run (2026-09-15), not by the audit:
         # seven decided events each had a bare-ticker page (the one the dataset, the drug
         # pages and the screener link) and a thinner drug-slug twin with zero inbound links.
         "BFRI-ameluz": "BFRI", "JAZZ-ziihera": "JAZZ", "PHAR-leniolisib": "PHAR",
         "PTGX-rusfertide": "PTGX", "ROIV-brepocitinib": "ROIV", "TAK-oveporexton": "TAK",
         "ZYME-ziihera": "ZYME",
         # a truncated-slug twin of the same decision (the title census missed it because the
         # truncation reached the title too)
         "GILD-bictegravir-and": "GILD-bictegravir-and-lenacapavi",
         # 2026-09-19: surfaced by the title census the day Pixclara decided; the bare page
         # carries 30 inbound links, the drug-slug twin none
         "TLX-tlx101-px": "TLX",
         # 2026-10-18: the RYZUMVI presbyopia event's two pre-canonical twins. Neither is linked from any page;
         # neither received the decided banner; both said "under FDA review" the day after the goal passed and
         # blocked both Sunday deploys (test_no_past_target_pending_pages). The partner page is the one we keep.
         "IRD": "IRD-phentolamine-ophthalmic", "VTRS-mr-141": "IRD-phentolamine-ophthalmic"}
SKIP = re.compile(r"[\\/]_pdufa_(x?bak\d*|bak\d*)[\\/]|[\\/]_[a-z]+bak")


def main():
    for dup, prim in DUPES.items():
        p = os.path.join(SITE, "pdufa", dup, "index.html")
        if not os.path.exists(os.path.join(SITE, "pdufa", prim, "index.html")):
            print(f"FAIL primary /pdufa/{prim} missing"); return 1
        t = io.open(p, encoding="utf-8").read()
        t, n1 = re.subn(r'<link rel="canonical" href="[^"]*"',
                        f'<link rel="canonical" href="https://www.pdufa.bio/pdufa/{prim}"', t)
        t, n2 = re.subn(r'<meta name="robots" content="[^"]*"',
                        '<meta name="robots" content="noindex,follow"', t)
        if "<!--DUPLICATE-OF-->" not in t:
            t = t.replace("<h1", f'<p class="sub" style="margin:0 0 8px"><!--DUPLICATE-OF-->This page duplicates '
                                 f'<a href="/pdufa/{prim}">/pdufa/{prim}</a>, which is the page we maintain.</p><h1', 1)
        # 2026-10-18: a twin must not contradict its primary. /pdufa/IRD still said "under FDA review" after the
        # primary was bannered Approved, and blocked both Sunday deploys. The primary's decision banner is copied
        # in (marker-bounded, idempotent), the pending story line rewritten, and the title made decided.
        pt = io.open(os.path.join(SITE, "pdufa", prim, "index.html"), encoding="utf-8", errors="replace").read()
        bm = re.search(r"<!--DECBAN:BEGIN-->.*?<!--DECBAN:END-->", pt, re.S)
        if bm:
            ban = "<!--DECIDED:BEGIN-->" + bm.group(0) + "<!--DECIDED:END-->"
            if "<!--DECIDED:BEGIN-->" in t:
                t = re.sub(r"<!--DECIDED:BEGIN-->.*?<!--DECIDED:END-->", lambda m: ban, t, flags=re.S)
            else:
                t = t.replace("</h1>", "</h1>" + ban, 1)
            word = "Approved" if "Approved</b>" in bm.group(0) else "Complete Response Letter"
            when = re.search(r"on <b>([^<]+)</b>", bm.group(0))
            day = when.group(1) if when else ""
            try:
                sys.path.insert(0, HERE)
                import mark_event_pages_decided as _M
                _tk = re.match(r"([A-Z]{1,6})", dup).group(1)
                _h = re.search(r'<h1>[A-Z]{1,6} PDUFA Date: <span class="g">(.+?)</span></h1>', t)
                _drug = _h.group(1) if _h else dup
                _iso = re.search(r"\d{4}-\d{2}-\d{2}", bm.group(0).replace(day, "")) if day else None
                import datetime as _dt
                _dcd = _dt.datetime.strptime(day, "%B %d, %Y").date().isoformat() if day else ""
                _goal = (re.search(r'<span>FDA PDUFA target date</span><b>(\d{4}-\d{2}-\d{2})</b>', t) or [None, ""])[1]
                if _dcd:
                    t = _M.decided_language(t, _tk, _drug, word, _dcd, _goal, False, goal_sourced=bool(_goal))
            except Exception as _e:  # noqa: BLE001
                print(f"  (decided_language on /pdufa/{dup} skipped: {_e})")
            t = re.sub(r"\bis under FDA review\b", f"{'was approved by the FDA' if word == 'Approved' else 'received a Complete Response Letter'}"
                       + (f" ({'announced' if 'announced on' in bm.group(0) else 'on'} {day})" if day else ""), t)
            t = re.sub(r"<title>([A-Z]{1,6}(?: / [A-Z]{1,6})?) PDUFA date: (.+?), [A-Z][a-z]{2} \d{1,2},? \d{4}( \| pdufa\.bio)?</title>",
                       lambda m: f"<title>{m.group(1)} FDA decision: {m.group(2)}, {word}{' ' + day if day else ''}{m.group(3) or ''}</title>", t)
        io.open(p, "w", encoding="utf-8").write(t)
        print(f"/pdufa/{dup}: canonical -> /pdufa/{prim} ({n1}), robots noindex,follow ({n2})"
              + (", decision copied from primary" if bm else ""))

    # internal links: every page except the duplicate itself
    changed = 0
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if SKIP.search(f):
            continue
        rel = os.path.relpath(f, SITE).replace("\\", "/")
        t = io.open(f, encoding="utf-8", errors="replace").read()
        o = t
        for dup, prim in DUPES.items():
            if rel == f"pdufa/{dup}/index.html":
                continue
            t = re.sub(rf'(href=")(?:https://www\.pdufa\.bio)?/pdufa/{re.escape(dup)}(["/#?])', rf"\g<1>/pdufa/{prim}\2", t)
        if t != o:
            io.open(f, "w", encoding="utf-8").write(t); changed += 1
    print(f"internal links rewritten on {changed} page(s)")

    sm = os.path.join(SITE, "sitemap.xml")
    if os.path.exists(sm):
        t = io.open(sm, encoding="utf-8").read()
        o = t
        for dup in DUPES:
            t = re.sub(rf"\s*<url>\s*<loc>https://www\.pdufa\.bio/pdufa/{re.escape(dup)}/?</loc>.*?</url>", "", t, flags=re.S)
        if t != o:
            io.open(sm, "w", encoding="utf-8").write(t); print("sitemap.xml: duplicates removed")
        else:
            print("sitemap.xml: duplicates already absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
