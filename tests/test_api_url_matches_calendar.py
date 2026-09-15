# -*- coding: utf-8 -*-
"""CI guard: for every upcoming PDUFA row that /calendar renders, the API's `url` is the page the
calendar links (audit 09-09b item 5 + 09-15 ORDER 1). One event, one page. Also: no upcoming
PDUFA row's `url` is an off-site document -- documents live in `source_url`.

    python tests/test_api_url_matches_calendar.py
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from sync_api_urls_to_calendar import calendar_rows, match, DATASET, SITE  # noqa: E402
import io, json  # noqa: E402,E401


def main():
    if not os.path.exists(os.path.join(SITE, "calendar", "index.html")):
        print("  SKIP no calendar"); return 0
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    cal = calendar_rows()
    fail = checked = 0
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("st") != "Upcoming":
            continue
        url = str(r.get("url") or "")
        if url.startswith("http"):
            print(f"  FAIL {r['id']}: url is an off-site document ({url[:70]}). Documents go in "
                  f"source_url; url is the event's page. Run sync_api_urls_to_calendar.py.")
            fail += 1
            continue
        c = match(r, cal)
        if not c:
            continue
        checked += 1
        if c["href"] != url:
            print(f"  FAIL {r['id']}: API url {url} but /calendar links {c['href']} for the same "
                  f"row. Run sync_api_urls_to_calendar.py.")
            fail += 1
    if fail:
        print(f"\n{fail} API-vs-calendar link disagreement(s). DO NOT PUBLISH."); return 1
    print(f"OK -- {checked} upcoming PDUFA rows link the same page in the API and on /calendar; "
          f"no upcoming row's url is an off-site document.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
