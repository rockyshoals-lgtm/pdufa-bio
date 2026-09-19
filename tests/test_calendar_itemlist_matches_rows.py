# -*- coding: utf-8 -*-
"""The /calendar JSON-LD ItemList says exactly what the visible still-ahead rows say.

Audit 2026-09-06 (0840 slot) NEW-1: the ItemList "2026 FDA PDUFA Calendar" carried 54 Events
against 48 visible ahead rows -- 16 decided applications still EventScheduled to every schema
consumer, 9 live rows absent. No build step owned it. This asserts the RENDER: the set of
/pdufa/ URLs in the ItemList equals the set of hrefs on rows that are (a) not decided and
(b) dated today-Eastern or later, or quarter-only; and numberOfItems equals that count.

Proven 2026-09-06: 0 -> planted /pdufa/AZN-camizestrant back into the ItemList -> 1 ->
regenerated -> 0.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402


def _ahead_hrefs(doc, today):
    out = []
    for attrs, frag in re.findall(r'<a class="row"([^>]*)>(.*?)</a>', doc, re.S):
        href = re.search(r'href="([^"]+)"', attrs)
        if not href or not href.group(1).startswith("/pdufa/") or "data-dec" in attrs:
            continue
        t = re.sub(r"<[^>]+>", " ", frag)
        low = t.lower()
        if "✓" in t or "approved" in low or "crl" in low or "complete response" in low:
            continue
        iso = re.search(r"\d{4}-\d{2}-\d{2}", t)
        if iso and iso.group(0) < today:
            continue
        if not iso and not re.search(r"\bQ[1-4]\s+\d{4}", t):
            continue
        out.append(href.group(1))
    return out


def test_calendar_itemlist_matches_rows():
    doc = io.open(os.path.join(SITE, "calendar", "index.html"), encoding="utf-8",
                  errors="replace").read()
    m = re.search(r'<script type="application/ld\+json">(\{"@context":\s*"https://schema.org",\s*'
                  r'"@type":\s*"ItemList",\s*"name":\s*"2026 FDA PDUFA Calendar".*?)</script>',
                  doc, re.S)
    assert m, "no '2026 FDA PDUFA Calendar' ItemList on /calendar"
    il = json.loads(m.group(1))
    items = il["itemListElement"]
    urls = [re.sub(r"^https://www\.pdufa\.bio", "", it["item"]["url"]) for it in items]
    rows = _ahead_hrefs(doc, eastern_today().isoformat())
    assert rows, "0 ahead rows parsed from /calendar -- markup changed"
    assert il.get("numberOfItems") == len(items), \
        f"numberOfItems {il.get('numberOfItems')} != {len(items)} ListItems"
    extra = sorted(set(urls) - set(rows))
    missing = sorted(set(rows) - set(urls))
    assert not extra and not missing and len(urls) == len(rows), (
        f"ItemList ({len(urls)}) != ahead rows ({len(rows)}):\n"
        f"  in ItemList but not a live ahead row: {extra}\n"
        f"  live ahead row missing from ItemList: {missing}")
    for it in items:
        ev = it["item"]
        assert ev.get("startDate"), f"{ev.get('url')} has no startDate"
        assert ev.get("eventStatus", "").endswith("EventScheduled")


def test_month_itemlists_match_rows():
    """2026-09-19: the month pages carried an ItemList '<Month> <Year> FDA PDUFA dates' written
    once by seo_pass14_fixups.py and never updated -- June/July/August listed decided events as
    scheduled, September listed three decided (TLX, NUVL, RARE) and omitted the two ahead,
    August's numberOfItems (6) did not match its own 4 items. sync_calendar_itemlist.py owns
    them now; this asserts the render, same definition of 'ahead' as /calendar."""
    import glob
    today = eastern_today().isoformat()
    pages = sorted(glob.glob(os.path.join(SITE, "calendar", "20[0-9][0-9]", "*", "index.html")))
    assert pages, "no month pages"
    problems = []
    for p in pages:
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        rows = _ahead_hrefs(doc, today)
        found = re.findall(r'\{(?:"@context":\s*"https://schema\.org",\s*)?"@type":\s*"ItemList",\s*'
                           r'"name":\s*"[A-Z][a-z]+ 20\d\d FDA PDUFA dates".*?"itemListElement":\s*\[[^\]]*\]\}',
                           doc, re.S)
        if len(found) > 1:
            problems.append(f"{rel}: {len(found)} month ItemLists on one page"); continue
        if not found:
            if rows:
                problems.append(f"{rel}: {len(rows)} ahead rows but no month ItemList")
            continue
        il = json.loads(found[0])
        items = il["itemListElement"]
        if any("item" not in it for it in items):
            problems.append(f"{rel}: pass-14 url-only ItemList shape (never regenerated); run sync_calendar_itemlist.py")
            continue
        urls = [re.sub(r"^https://www\.pdufa\.bio", "", it["item"]["url"]) for it in items]
        if il.get("numberOfItems") != len(items):
            problems.append(f"{rel}: numberOfItems {il.get('numberOfItems')} != {len(items)} items")
        extra, missing = sorted(set(urls) - set(rows)), sorted(set(rows) - set(urls))
        if extra or missing:
            problems.append(f"{rel}: ItemList != ahead rows; extra={extra} missing={missing}")
    assert not problems, "month ItemLists out of step with their rows:\n  " + "\n  ".join(problems)


if __name__ == "__main__":
    test_calendar_itemlist_matches_rows()
    test_month_itemlists_match_rows()
    print("OK")
