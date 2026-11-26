# -*- coding: utf-8 -*-
"""test_archive_month_target.py -- an event page with a month-only target never takes an old archive approval.

Red team 2026-11-26: the 19:22Z rebuild failed two guards because mark_event_pages_decided.py stamped
/pdufa/RHHBY-gazyva (the pending Gazyva lupus application, target "Dec 2026") "Approved 2025-10-20": the Oct 2025
lupus nephritis approval. The page states no day, so archive_candidates() skipped its date window, and once
/decisions named that approval "Gazyva" (it read "price-only" before) the brand token matched. This fails if:
  1. a "Mon YYYY" target lets through an archive approval far older than ARCHIVE_EARLY_WINDOW before that month;
  2. a "Mon YYYY" target blocks a recent approval inside the window (the fix must not hide real decisions);
  3. a day-dated target or a "Not announced" page changes behaviour.
PLANT=nomonth removes the month parse; it must FAIL.

    python tests/test_archive_month_target.py
"""
import datetime as dt
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import mark_event_pages_decided as K  # noqa: E402

MON = K._MONTHS[:]


def page(target):
    return ('<title>ZZQ PDUFA date: Widgetmab (widgetmab), Dec 2026 | pdufa.bio</title>'
            f'<div class="kv"><span>FDA PDUFA target date</span><b>{target}</b></div>')


def main():
    if os.environ.get("PLANT") == "nomonth":
        K._MONTHS = []
    today = dt.date.today()
    tgt = today + dt.timedelta(days=60)
    month = f"{MON[tgt.month - 1]} {tgt.year}"
    old = (today - dt.timedelta(days=400)).isoformat()
    recent = (today - dt.timedelta(days=10)).isoformat()
    arch = {"ZZQ": [(old, "ap", "Widgetmab lupus nephritis"), (recent, "ap", "Widgetmab")]}

    def got(target):
        return sorted(c["dcd"] for c in K.archive_candidates(arch, "ZZQ", "widgetmab", page(target)))

    cases = [
        (f"month target {month}", month, [recent]),
        (f"day target {tgt.isoformat()}", tgt.isoformat(), [recent]),
        ("Not announced", "Not announced", sorted([old, recent])),
    ]
    bad = []
    for name, target, want in cases:
        g = got(target)
        if g != want:
            bad.append(f"{name}: candidates {g}, want {want}")
    print(f"archive month target: {len(cases)} cases")
    if bad:
        print("FAIL")
        for b in bad:
            print("  " + b)
        return 1
    print("  PASS: a month-only target bounds the archive window by its month")
    return 0


if __name__ == "__main__":
    sys.exit(main())
