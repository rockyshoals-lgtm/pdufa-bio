# -*- coding: utf-8 -*-
"""record_date_check.py -- write one re-check of an open date into _date_checks.json.

Use it only after opening the source yourself (or reading an independent red-team verdict that did):

    python record_date_check.py <row id> <CONFIRMED|FIXED|RESOLVED|STOPPED|HELD> <newest source url> [note]

The entry is dated today (US Eastern). tests/test_date_checks_current.py reads the ledger.
"""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "_date_checks.json")
VERDICTS = ("CONFIRMED", "FIXED", "RESOLVED", "STOPPED", "HELD")


def eastern_today():
    try:
        from site_dates import eastern_today as et
        return et()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def load():
    if os.path.exists(LEDGER):
        return json.load(io.open(LEDGER, encoding="utf-8"))
    return {"_comment": "", "checks": {}}


def save(j):
    io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(j, indent=1, ensure_ascii=False, sort_keys=False) + "\n")


def record(j, rid, verdict, url, note="", checked=None, by="manual"):
    if verdict not in VERDICTS:
        raise SystemExit(f"verdict must be one of {VERDICTS}")
    e = {"checked": (checked or eastern_today().isoformat()), "verdict": verdict, "source": url, "by": by}
    if note:
        e["note"] = note
    j.setdefault("checks", {})[rid] = e
    return e


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    j = load()
    e = record(j, sys.argv[1], sys.argv[2].upper(), sys.argv[3], " ".join(sys.argv[4:]))
    save(j)
    print(sys.argv[1], e)
