# -*- coding: utf-8 -*-
"""CI guard: every pending PDUFA row resolves to an event page whose TITLE carries the row's date, the
row's `url` is that page, its calendar row links it, and the page's Event schema states the same date
(audit 2026-10-10 items 2 and 3).

Giredestrant evERA (Dec 18) and bezuclastinib SUMMIT (Dec 30) resolved to their siblings' Nov 30 pages,
and the API sent 33 of 35 upcoming rows to a hub. Fails, on the rendered pages and the dataset, when:
  1. a pending row (day or window precision) has no page whose title states its date;
  2. the row's url is not that page;
  3. a calendar row for (ticker, date) links a bare hub while an event page exists;
  4. the event page carries an Event startDate that is not the row's date (day rows).

    python tests/test_event_page_titles_carry_date.py
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import event_pages as EP  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    from site_dates import eastern_today
    today = eastern_today().isoformat()
    pend = EP.pending_rows(rows, today)
    fails, n_day = [], 0
    cal = ""
    for p in [os.path.join(SITE, "calendar", "index.html")] + sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html"))):
        if os.path.exists(p):
            cal += io.open(p, encoding="utf-8", errors="replace").read()
    for r in pend:
        rid, tk, d = r["id"], str(r.get("t") or "").upper(), str(r.get("d") or "")[:10]
        u = EP.resolve(r)
        if not u:
            fails.append(f"{rid}: no /pdufa/ page states its date ({EP.date_forms(r)[:2]}); "
                         f"candidates {EP.candidate_slugs(r)[:3]}")
            continue
        if str(r.get("dp") or "day") == "day":
            n_day += 1
        url = str(r.get("url") or "")
        if url != u:
            # a partner ticker's row (IRD / VTRS) may share the sibling's page, if that page states the date
            ok = False
            if url.startswith("/pdufa/"):
                t2, doc2 = EP.page_title(url[len("/pdufa/"):])
                ok = t2 is not None and EP.page_carries_date(r, doc2, t2)
            if not ok:
                fails.append(f"{rid}: url is {url!r}, event page is {u}")
            else:
                u = url
        doc = io.open(os.path.join(SITE, u.strip("/").replace("/", os.sep), "index.html"), encoding="utf-8", errors="replace").read()
        if str(r.get("dp") or "day") == "day":
            for m in re.finditer(r'"startDate":\s*"(\d{4}-\d{2}-\d{2})', doc):
                if m.group(1) != d:
                    fails.append(f"{rid}: {u} Event startDate {m.group(1)} != {d}")
                    break
            for m in re.finditer(r'<a class="row"(?![^>]*data-dec)[^>]*href="([^"]+)"[^>]*>\s*<div class="t">([A-Z /]+?)\s*(?:&middot;|·)\s*' + re.escape(d) + r'(?=<)', cal):
                if tk in [x.strip() for x in m.group(2).split("/")] and re.match(r"^/(ticker|pdufa)/[A-Z]{1,6}$", m.group(1)):
                    fails.append(f"{rid}: calendar row links hub {m.group(1)}, event page is {u}")
                    break
    if fails:
        print(f"FAIL: {len(fails)} pending row(s) without a dated event page of their own:")
        for f in fails[:25]:
            print("   " + f)
        return 1
    print(f"OK -- {len(pend)} pending PDUFA rows ({n_day} day-dated) each resolve to a page whose title states "
          f"the row's date; urls, calendar rows and Event schema agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
