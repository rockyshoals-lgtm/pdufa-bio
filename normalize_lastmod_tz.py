"""One-time (idempotent) migration: re-express legacy UTC `ts` values in _sitemap_lastmod.json
in Eastern, the zone every rendered date on the site uses (2026-09-08, auditor N2).

build_sitemap.py has recorded new `ts` values in Eastern since 2026-09-07; entries written before
that carry `+00:00`, and build_date_modified.py copies `ts` verbatim into og:updated_time, so an
unchanged page (e.g. /pdufa/SRRK-apitegromab, last content change 2026-09-06) published a UTC
stamp while every page that changed since published Eastern. Same instant, different zone label.

This converts the label only. The instant is unchanged; the page does not become "fresher".
If the Eastern calendar day differs from the stored `date` (a UTC ts between 00:00 and 04:00),
the ts is dropped and the page keeps its bare date -- exactly what build_sitemap.py's own
repair rule does to a ts whose day disagrees with its date. No `date` is moved: the sitemap
day a page has claimed for weeks does not shift because of a zone relabel.
"""
import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

STATE = "_sitemap_lastmod.json"
EASTERN = ZoneInfo("America/New_York")


def main():
    raw = json.load(open(STATE, encoding="utf-8"))
    converted = date_moved = 0
    for k, v in raw.items():
        ts = v.get("ts")
        if not ts or not (ts.endswith("+00:00") or ts.endswith("Z")):
            continue
        t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(EASTERN)
        if v.get("date") and v["date"] != t.strftime("%Y-%m-%d"):
            del v["ts"]                       # day disagrees: keep the date, drop the clock
            date_moved += 1
            continue
        v["ts"] = t.replace(microsecond=0).isoformat()
        converted += 1
    if "--dry-run" not in sys.argv:
        json.dump(raw, open(STATE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        open(STATE, "a", encoding="utf-8").write("\n")
    print(f"ts converted UTC->Eastern: {converted}; ts dropped (Eastern day != date): {date_moved}"
          + ("  (DRY RUN)" if "--dry-run" in sys.argv else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
