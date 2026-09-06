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


if __name__ == "__main__":
    test_calendar_itemlist_matches_rows()
    print("OK")
