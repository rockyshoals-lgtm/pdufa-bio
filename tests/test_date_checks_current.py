# -*- coding: utf-8 -*-
"""CI guard: open dates are re-checked against their sources before they matter, and after the sponsor
says something newer.

WHY (red team 2026-11-17)
A date that was right when we wrote it goes stale silently: the sponsor's next quarterly release moves
"Q4 2026" to "Q1 2027", the FDA extends a goal by three months, a trial is stopped. The row still
quotes the old release word for word, so every format guard passes. The only defence is to re-read
the sponsor before the date matters, and to re-read every row of a company when that company
publishes something newer. _date_checks.json is the ledger of those re-reads (one entry per row:
date checked, verdict, the newest source looked at).

THE INVARIANTS (open PDUFA rows and company-Guided readouts whose window has not ended)
  1. IMMINENT: a row dated within the next 14 days must have been checked within the last 30 days.
  2. NEWER DISCLOSURE: when the same company has another open row sourced to a document dated after
     this row's last check (and after this row's own source), this row must be re-checked against it.
     That is the "Q3 release moved one program but we only updated the other" failure.
  3. A ledger entry may not be dated in the future, and its verdict must be one of the known ones.

Clearing a failure means opening the sources again and recording the result in the ledger
(`record_date_check.py <row id> <verdict> <source url> [note]`), never editing dates in the ledger by
hand to make the guard pass.

    python tests/test_date_checks_current.py
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
LEDGER = os.path.join(HERE, "_date_checks.json")
IMMINENT_DAYS = 14
MAX_AGE_DAYS = 30
VERDICTS = {"CONFIRMED", "FIXED", "RESOLVED", "STOPPED", "HELD"}


def eastern_today():
    try:
        from site_dates import eastern_today as et
        return et()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def source_date(d):
    v = d.get("guided_filed")
    if v and re.match(r"\d{4}-\d{2}-\d{2}", str(v)):
        return dt.date.fromisoformat(str(v)[:10])
    m = re.search(r"(20\d\d-\d\d-\d\d)", str(d.get("source") or ""))
    return dt.date.fromisoformat(m.group(1)) if m else None


def open_rows(rows, today):
    for r in rows:
        d = r.get("_d") or {}
        if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Under review"):
            yield r
        elif r.get("type") == "Readout" and r.get("st") == "Guided" and r.get("d", "") >= today.isoformat():
            yield r


def check(rows, ledger, today):
    fails = []
    rows = list(open_rows(rows, today))
    newest = {}
    for r in rows:
        sd = source_date(r.get("_d") or {})
        if sd and sd <= today:
            k = r.get("t")
            if k not in newest or sd > newest[k][0]:
                newest[k] = (sd, r["id"])
    for rid, e in ledger.items():
        try:
            cd = dt.date.fromisoformat(e.get("checked", ""))
        except Exception:
            fails.append(f"{rid}: ledger entry has no valid 'checked' date")
            continue
        if cd > today:
            fails.append(f"{rid}: ledger entry dated in the future ({cd})")
        if e.get("verdict") not in VERDICTS:
            fails.append(f"{rid}: ledger verdict {e.get('verdict')!r} not one of {sorted(VERDICTS)}")
    for r in rows:
        rid = r["id"]
        e = ledger.get(rid)
        cd = None
        if e:
            try:
                cd = dt.date.fromisoformat(e.get("checked", ""))
            except Exception:
                cd = None
        try:
            due = dt.date.fromisoformat(r["d"])
        except Exception:
            continue
        if 0 <= (due - today).days <= IMMINENT_DAYS and (cd is None or (today - cd).days > MAX_AGE_DAYS):
            fails.append(f"{rid} [{r['t']}] due {r['d']}: not checked against its source in the last "
                         f"{MAX_AGE_DAYS} days (last: {cd or 'never'})")
        own = source_date(r.get("_d") or {})
        nd = newest.get(r.get("t"))
        if cd and nd and nd[1] != rid and nd[0] > cd and (own is None or nd[0] > own):
            fails.append(f"{rid} [{r['t']}]: {r['t']} published something newer ({nd[0]}, cited by {nd[1]}) "
                         f"after this row was last checked ({cd}); re-check this row against it")
    return fails


def load_ledger():
    if not os.path.exists(LEDGER):
        return {}
    return json.load(io.open(LEDGER, encoding="utf-8")).get("checks", {})


def self_test():
    t = dt.date(2026, 11, 18)
    rows = [
        {"id": "a", "t": "X", "type": "PDUFA", "st": "Upcoming", "d": "2026-11-25", "_d": {"source": "8-K 2026-08-01"}},
        {"id": "b", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-03-31", "_d": {"guided_filed": "2026-08-05"}},
        {"id": "c", "t": "Y", "type": "Readout", "st": "Guided", "d": "2027-06-30", "_d": {"guided_filed": "2026-11-05"}},
    ]
    stale = {"a": {"checked": "2026-09-01", "verdict": "CONFIRMED"}, "b": {"checked": "2026-10-01", "verdict": "CONFIRMED"},
             "c": {"checked": "2026-11-06", "verdict": "CONFIRMED"}}
    fresh = {"a": {"checked": "2026-11-18", "verdict": "CONFIRMED"}, "b": {"checked": "2026-11-18", "verdict": "CONFIRMED"},
             "c": {"checked": "2026-11-18", "verdict": "CONFIRMED"}}
    f1, f2 = check(rows, stale, t), check(rows, fresh, t)
    ok = len(f1) == 2 and not f2
    if not ok:
        print("SELF-TEST FAILED:", f1, f2)
    return ok


def main():
    if not self_test():
        return 1
    src = io.open(DATASET, encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    fails = check(rows, load_ledger(), eastern_today())
    if fails:
        print(f"FAIL: {len(fails)} open date(s) need re-checking against their sources "
              f"(re-open the source, then record_date_check.py):")
        for f in fails[:60]:
            print("   " + f)
        return 1
    print("OK -- imminent dates were checked in the last 30 days, and no row predates a newer disclosure "
          "from its own company unchecked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
