# -*- coding: utf-8 -*-
"""CI guard: the page an upcoming day-precision PDUFA row links states THAT row's date.

Found 2026-09-15: /pdufa/PRAX told readers relutrigine's goal date was September 27, 2026 for
78 days after the FDA moved it to December 27 (the refresher skipped tickers with two live
events), and two rows on two-event tickers linked the page describing the OTHER event (COGT PEAK
-> the SUMMIT page; PRAX ulixacaltamide -> the relutrigine page). The dataset was right every
time; the link or the page was not. Rendered output is what is asserted.

    python tests/test_event_page_states_row_date.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    fail = checked = 0
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("st") != "Upcoming" or r.get("dp") != "day":
            continue
        url = str(r.get("url") or "")
        if not url.startswith("/pdufa/"):
            continue
        p = os.path.join(SITE, url.strip("/"), "index.html")
        if not os.path.exists(p):
            print(f"  FAIL {r['id']}: url {url} has no page.")
            fail += 1
            continue
        t = io.open(p, encoding="utf-8", errors="replace").read()
        kv = re.search(r"PDUFA target date</span><b>(\d{4}-\d{2}-\d{2})</b>", t)
        sd = re.search(r'"startDate":"(\d{4}-\d{2}-\d{2})', t)
        stated = {x.group(1) for x in (kv, sd) if x}
        if not stated:
            continue                       # ticker history pages state no single date
        checked += 1
        if r["d"] not in stated:
            print(f"  FAIL {r['id']}: dataset date {r['d']} but {url} states {sorted(stated)}. "
                  f"Either the page is stale (refresh_moved_pdufa_pages.py) or the row links the "
                  f"wrong event's page.")
            fail += 1
    if fail:
        print(f"\n{fail} event page(s) disagree with their row. DO NOT PUBLISH.")
        return 1
    print(f"OK -- {checked} upcoming day-precision PDUFA rows link a page that states their date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
