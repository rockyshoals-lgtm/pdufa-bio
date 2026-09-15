# -*- coding: utf-8 -*-
"""CI guard: the readout therapeutic-area hubs stay current and stay honest about coverage.

Audit 09-14 item 7. These two pages exist because the auditor measured the grounding queries
behind them going 28 -> 77 citations at 66.38% share and 75 -> 102 at 32.59%, both rising in
share as well as volume, both answered off a generic hub.

Guarded because of what happened to the LAST set of therapeutic-area pages. /condition/* was
built once and never rebuilt, and two months later it was presenting past-dated events as
upcoming and labelling ACHV's cytisinicline PDUFA as "custirsen", a discontinued compound from
before the 2017 merger. A hub that is generated once is a hub that rots.

Four invariants:
  1. both pages exist and are non-trivial;
  2. no row on a page headed "upcoming" has a date in the past;
  3. the row count on the page equals the dataset's own count for that therapeutic area, so the
     page cannot drift from the data the way /condition did;
  4. the coverage sentence is present. 58% of forward readouts carry no therapeutic area, so a
     bare "37 oncology readouts" reads as a census it is not, and the page must say so.

    python tests/test_readout_ta_hubs.py
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
HUBS = {"oncology": {"oncology"}, "rare-disease": {"rare disease", "rare"}}
ROW = re.compile(r'<div class="t">([A-Z]{1,6}) (?:&middot;|·) ([^<]+)</div>')
MON = {m: i for i, m in enumerate(
    ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def main():
    ds = os.path.join(SITE, "api", "v1", "dataset.mjs")
    if not os.path.exists(ds):
        print("  SKIP dataset not found")
        return 0
    src = io.open(ds, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    today = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=4)).date().isoformat()

    fail = 0
    for slug, tas in HUBS.items():
        p = os.path.join(SITE, "readouts", slug, "index.html")
        if not os.path.isfile(p):
            print(f"  FAIL /readouts/{slug} does not exist -- run build_readout_ta_hubs.py")
            fail += 1
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if len(doc) < 4000:
            print(f"  FAIL /readouts/{slug} is only {len(doc)} bytes; it lost its rows")
            fail += 1
            continue

        want = [r for r in rows if r.get("type") == "Readout"
                and str(r.get("st") or "") in ("Guided", "Estimated")
                and str(r.get("ta") or "").strip().lower() in tas
                and str(r.get("d") or "") >= today]
        got = ROW.findall(doc)
        if len(got) != len(want):
            print(f"  FAIL /readouts/{slug}: page shows {len(got)} row(s), the dataset holds "
                  f"{len(want)} upcoming {slug} readout(s). This is the /condition/* failure -- "
                  f"a hub built once and never rebuilt. Run build_readout_ta_hubs.py.")
            fail += 1

        # nothing past-dated on a page headed "upcoming"
        for tk, lab in got:
            lab = lab.replace("(est.)", "").strip()
            m = re.match(r"^([A-Z][a-z]{2}) (\d{4})$", lab)
            if m:
                y, mo = int(m.group(2)), MON.get(m.group(1), 0)
                if f"{y:04d}-{mo:02d}" < today[:7]:
                    print(f"  FAIL /readouts/{slug}: {tk} {lab} has passed but sits on a page "
                          f"headed 'upcoming'")
                    fail += 1
            elif re.match(r"^\d{4}-\d{2}-\d{2}$", lab) and lab < today:
                print(f"  FAIL /readouts/{slug}: {tk} {lab} is past-dated")
                fail += 1

        if "floor, not a complete census" not in doc:
            print(f"  FAIL /readouts/{slug} lost its coverage sentence. 58% of forward readouts "
                  f"carry no therapeutic area; without that stated, the n reads as a complete "
                  f"census of the field and is not one.")
            fail += 1

    hub = os.path.join(SITE, "readouts", "index.html")
    if os.path.exists(hub):
        d = io.open(hub, encoding="utf-8", errors="replace").read()
        for slug in HUBS:
            if f"/readouts/{slug}" not in d:
                print(f"  FAIL /readouts does not link /readouts/{slug}")
                fail += 1

    if fail:
        print(f"\n{fail} readout-hub failure(s). DO NOT PUBLISH.")
        return 1
    print("OK -- both readout hubs match the dataset, carry no past-dated row, state their "
          "coverage limit, and are linked from /readouts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
