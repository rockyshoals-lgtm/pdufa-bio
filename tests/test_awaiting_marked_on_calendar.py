# -*- coding: utf-8 -*-
"""CI guard: a PDUFA whose date has passed with no decision must say "Awaiting" on the calendar.

WHAT HAPPENED (2026-09-14). CI had been red for three days -- the early-approval watcher was
correctly refusing to let the build proceed past unreviewed FDA approvals -- so nothing rebuilt.
In that window TLX's PDUFA goal date for TLX101-Px (Pixclara) passed. /api/v1 handled it: _lib.mjs
relabels a past-dated Upcoming PDUFA as "Awaiting", on the stated reasoning that "a PDUFA whose
date has passed with no outcome yet is not 'Upcoming'". The CALENDAR did not. So the site's
most-visited page showed "TLX - 2026-09-11" looking exactly like a live date, three days after
it had passed, while the API called the same row Awaiting.

That is the recurring shape here: two surfaces, one truth. The API's rule is the right one, so
the calendar has to follow it rather than the other way round.

THE INVARIANT
Every day-precision PDUFA in the dataset whose date is in the past and whose status is not
"Decided" must carry an Awaiting marker on every calendar page that lists it. Decided rows are
out of scope -- mark_calendar_decided.py owns those and gives them a checkmark instead.

    python tests/test_awaiting_marked_on_calendar.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys

SITE = "pdufa_site_src"
TODAY = dt.date.today().isoformat()
ROW = re.compile(r'<a class="row"[^>]*>\s*<div class="t">([A-Z]{1,6}) (?:&middot;|·) '
                 r'(\d{4}-\d{2}-\d{2})(.*?)</div>', re.S)


def main():
    ds = os.path.join(SITE, "api", "v1", "dataset.mjs")
    if not os.path.exists(ds):
        print(f"  SKIP {ds} not found")
        return 0
    src = io.open(ds, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

    awaiting = {(str(r.get("t") or "").upper(), str(r.get("d") or ""))
                for r in rows
                if r.get("type") == "PDUFA" and r.get("dp") == "day"
                and str(r.get("st") or "") != "Decided"
                and str(r.get("d") or "") and str(r.get("d") or "") < TODAY}

    fail = 0
    checked = 0
    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    for p in pages:
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        for m in ROW.finditer(doc):
            key = (m.group(1), m.group(2))
            if key not in awaiting:
                continue
            checked += 1
            tail = m.group(3)
            if "awaiting" not in tail.lower():
                print(f"  FAIL {rel}: {key[0]} {key[1]} -- the goal date passed and the dataset "
                      f"records no decision, but the row reads like a live date. The API calls "
                      f"this row Awaiting; the calendar must say the same. "
                      f"Run mark_calendar_awaiting.py.")
                fail += 1

    if fail:
        print(f"\n{fail} past-dated PDUFA row(s) presented as live. A countdown that has run "
              f"out is the worst row on the site. DO NOT PUBLISH.")
        return 1
    print(f"OK -- {len(awaiting)} PDUFA date(s) past with no decision; all {checked} calendar "
          f"row(s) for them carry the Awaiting marker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
