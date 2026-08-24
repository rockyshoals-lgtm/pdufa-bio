# -*- coding: utf-8 -*-
"""update_capr_pdufa_extension.py -- CAPR deramiocel PDUFA extended 2026-08-22 -> 2026-11-22.

FACTS, from Capricor's own release (GlobeNewswire, 2026-08-24):
  * The FDA extended the PDUFA target action date for the deramiocel BLA from August 22, 2026
    to November 22, 2026.
  * Following the July 2026 advisory committee meeting, Capricor submitted a BLA AMENDMENT with
    24-month open-label extension data from the pivotal Phase 3 HOPE-3 study plus additional
    robustness analyses, asking the FDA to consider a REFINED PROPOSED INDICATION focused on
    upper limb function -- the primary endpoint of HOPE-3.
  * CBER accepted the amendment, classified it a MAJOR AMENDMENT, and extended the date by three
    months to allow time to review it.

This is an EXTENSION, not a Complete Response Letter and not a rejection: the application is
still under review. The site must say that precisely, because "delay" reads to a lot of people
as "turned down", and the two are different regulatory events with different consequences.

Both sources are updated together -- dataset.mjs (the API) and the data.js slate (the page) --
because they are separately consumed and test_calendar_two_sources compares them.

    python update_capr_pdufa_extension.py [--dry-run]
"""
import argparse, io, json, os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DATA_JS = os.path.join(SITE, "api", "data.js")

OLD, NEW = "2026-08-22", "2026-11-22"
SRC = ("https://www.globenewswire.com/news-release/2026/08/24/capricor-therapeutics-announces-"
       "extension-of-pdufa-target-action-date-as-fda-continues-review-of-deramiocel-bla.html")
NOTE = ("PDUFA target action date extended from August 22, 2026 to November 22, 2026. Capricor "
        "submitted a BLA amendment after the July 2026 advisory committee meeting containing "
        "24-month open-label extension data from the pivotal Phase 3 HOPE-3 study and additional "
        "robustness analyses, in support of a refined proposed indication focused on upper limb "
        "function (the HOPE-3 primary endpoint). CBER accepted it, classified it a major "
        "amendment, and added three months to review it. The application remains under review: "
        "this is an extension, not a Complete Response Letter.")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    # ---- dataset.mjs -------------------------------------------------------------------
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    j = src.find("[")
    arr, end = json.JSONDecoder().raw_decode(src[j:])
    n = 0
    for r in arr:
        if r.get("t") == "CAPR" and r.get("type") == "PDUFA" and str(r.get("d")) == OLD:
            r["d"] = NEW
            r["dp"] = "day"
            r["st"] = "Upcoming"
            r["name"] = "Deramiocel (CAP-1002) - (HOPE-3)"
            d = r.setdefault("_d", {})
            d["indication"] = ("Duchenne muscular dystrophy; refined proposed indication focused "
                               "on upper limb function")
            d["review"] = NOTE
            d["prior_pdufa_date"] = OLD
            r["url"] = SRC
            n += 1
    if n and not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:j] + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + src[j + end:])
    print(f"dataset.mjs: {n} CAPR row(s) moved {OLD} -> {NEW}")

    # ---- data.js slate -----------------------------------------------------------------
    s = io.open(DATA_JS, encoding="utf-8", errors="replace").read().replace("\x00", "")
    key = "const SLATE=" if "const SLATE=" in s else "SLATE="
    i = s.find(key)
    slate, send = json.JSONDecoder().raw_decode(s[i + len(key):])
    m = 0
    import datetime as dt
    today = dt.date.today()
    for c in slate.get("catalysts", []):
        if c.get("ticker") == "CAPR" and str(c.get("date"))[:10] == OLD:
            c["date"] = NEW
            c["t_minus"] = (dt.date.fromisoformat(NEW) - today).days
            c["drug"] = "Deramiocel (CAP-1002) - (HOPE-3)"
            c["indication"] = ("Duchenne muscular dystrophy; refined proposed indication "
                               "focused on upper limb function")
            m += 1
    if m and not a.dry_run:
        slate["catalysts"].sort(key=lambda c: str(c.get("date") or "9999"))
        io.open(DATA_JS, "w", encoding="utf-8").write(
            s[:i + len(key)] + json.dumps(slate, separators=(",", ":"), ensure_ascii=False)
            + s[i + len(key) + send:])
    print(f"data.js slate: {m} CAPR row(s) moved {OLD} -> {NEW}")
    if a.dry_run:
        print("DRY RUN -- nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
