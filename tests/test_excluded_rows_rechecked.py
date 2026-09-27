# -*- coding: utf-8 -*-
"""CI guard: a decision excluded from the timing statistic because only an announcement states
its date is re-checked against the FDA's record on every build.

Audit 2026-09-26 item 5: TLX Pixclara was excluded on 09-20 ("the filing does not state the day
the FDA acted") while Drugs@FDA had carried NDA 218592's September 11 approval since the 15th.
Nothing looked again. sync_fda_action_dates.py now re-queries every such row each run and
re-admits it when the record appears; it writes the check to _fda_action_state.json. This guard
fails if any excluded row was not checked within the last two days (Eastern), i.e. if the
re-check step stopped running.

    python tests/test_excluded_rows_rechecked.py
"""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def eastern_today():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=4)).date()


def main():
    src = io.open(os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    p = os.path.join(HERE, "_fda_action_state.json")
    state = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
    floor = (eastern_today() - dt.timedelta(days=2)).isoformat()
    fails, n = [], 0
    for r in rows:
        d = r.get("_d") or {}
        if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() != "decided" or not d.get("decision_date_unsourced"):
            continue
        n += 1
        chk = (state.get(r["id"]) or {}).get("checked", "")
        if chk < floor:
            fails.append(f"{r['id']}: excluded (announcement-only date) but last checked against the FDA's "
                         f"record on {chk or 'never'} -- run sync_fda_action_dates.py")
    if fails:
        print(f"FAIL: {len(fails)} excluded row(s) not re-checked:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {n} excluded row(s), each re-checked against the FDA's record since {floor}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
