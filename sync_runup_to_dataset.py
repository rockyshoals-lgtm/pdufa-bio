# -*- coding: utf-8 -*-
"""sync_runup_to_dataset.py -- every PDUFA row's `runup_summary` is that event's own measured run-up (David, 2026-11-13).

Found 2026-11-13: of 122 PDUFA rows in the public dataset, 54 had no run-up and 68 carried one of five repeated value
sets ({"t30": 0.38, "t7": -0.01, "t1": 0.0} on 31 rows, {"t30": 2.19, ...} on 21): placeholders by cohort, written once,
published in /api/v1 as if each event's own. This rewrites the field from measured daily closes:

  Decided rows   from the run-up study row for the same ticker within 45 days of the FDA action (pdufa_runup_bifrost_v2.csv,
                 the 1,885-event study): percent change into the eve close over 120 / 30 / 14 / 7 / 3 sessions, and the
                 move 1 and 5 sessions after. basis "decided".
  Upcoming rows  day-dated goals still ahead: the stock's run-up so far, last close versus 120 / 30 / 7 sessions earlier
                 (FMP closes via price_source.py), with the date of that close. basis "so far".
  Otherwise      null, with `runup_note` saying why (no listed ticker, no price history, a window-only goal).

Units are percent, stated in the field (`unit: "pct"`). Facts only, not investment advice.

    python sync_runup_to_dataset.py [--dry-run]
"""
import argparse
import collections
import csv
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

P = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")


def f2(x, scale=1.0):
    try:
        return round(float(x) * scale, 2) if str(x).strip() not in ("", "nan", "None") else None
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    import price_source as ps
    today = eastern_today()
    study = collections.defaultdict(list)
    for r in csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")):
        study[r["ticker"]].append(r)
    s = io.open(P, encoding="utf-8").read(); i, j = s.index("["), s.rindex("]") + 1
    rows = json.loads(s[i:j])
    n = collections.Counter()
    for r in rows:
        if r.get("type") != "PDUFA":
            continue
        d = r.setdefault("_d", {})
        t = str(r.get("t") or "").upper()
        st = str(r.get("st") or "")
        summ, note = None, None
        if st == "Decided":
            key = str(r.get("dcd") or r.get("d") or "")[:10]
            best = None
            for x in study.get(t, []):
                try:
                    gap = abs((dt.date.fromisoformat(x["pdufa_date"][:10]) - dt.date.fromisoformat(key)).days)
                except ValueError:
                    continue
                if gap <= 45 and (best is None or gap < best[0]):
                    best = (gap, x)
            if best:
                x = best[1]
                summ = {"basis": "decided", "unit": "pct", "eve_date": x.get("eve_date") or None,
                        "t120": f2(x.get("T-120_T-1"), 100), "t30": f2(x.get("runup_30d")), "t14": f2(x.get("runup_14d")),
                        "t7": f2(x.get("runup_7d")), "t3": f2(x.get("runup_3d")),
                        "post_1d": f2(x.get("post_1d")), "post_5d": f2(x.get("post_5d")),
                        "source": "pdufa.bio run-up study (split-adjusted daily closes)"}
                n["decided"] += 1
            else:
                note = ("No run-up record: " + ("device PMA decision, not a PDUFA event" if "approvable" in str(r.get("oc", "")).lower()
                                               else "no usable daily closes around the decision"))
                n["decided_none"] += 1
        elif st in ("Upcoming", "Awaiting") and str(r.get("dp") or "day") == "day" and str(r.get("d") or "") >= today.isoformat():
            b = ps.daily(t, (today - dt.timedelta(days=200)).isoformat(), today.isoformat()) if t else []
            if len(b) >= 31:
                last_d, last_c = b[-1][0], b[-1][1]
                pct = lambda k: round((last_c / b[-1 - k][1] - 1) * 100, 2) if len(b) > k and b[-1 - k][1] else None
                summ = {"basis": "so far", "unit": "pct", "as_of": last_d, "t120": pct(120), "t30": pct(30), "t7": pct(7),
                        "source": "FMP split-adjusted daily closes"}
                n["upcoming"] += 1
            else:
                note = "No run-up yet: no daily price history for this ticker" if t else "No listed ticker"
                n["upcoming_none"] += 1
        else:
            note = "Run-up is measured for day-dated goals and decided events only"
            n["other"] += 1
        d["runup_summary"] = summ
        if note:
            d["runup_note"] = note
        else:
            d.pop("runup_note", None)
    print(f"runup_summary: {n['decided']} decided rows measured from the study, {n['upcoming']} upcoming rows measured so far; "
          f"null: {n['decided_none']} decided, {n['upcoming_none']} upcoming, {n['other']} window-only or other | {ps.summary()}")
    if not a.dry_run:
        io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
