# -*- coding: utf-8 -*-
"""CI guard: a PDUFA the dataset records as Decided must be marked decided on every calendar
page that lists it -- never "Awaiting", never a bare live-looking date.

WHAT HAPPENED (2026-09-19). Pixclara (TLX, goal 2026-09-11) was approved after its goal date.
The dataset said Decided/Approved, the decision page was published, the API said Decided -- and
/calendar and /calendar/2026/september still showed "TLX · 2026-09-11 Awaiting", with the
September sentence saying the FDA was "due to decide on ... TLX101-Px". mark_calendar_awaiting.py
had badged the row on 09-14 (correctly, at the time); mark_calendar_decided.py's row pattern did
not allow the badge, so once a row went Awaiting it could never be marked decided. The mirror of
tests/test_awaiting_marked_on_calendar.py did not exist, so nothing noticed.

THE INVARIANT
For every day-precision PDUFA row with st == "Decided" (and an outcome), every calendar row
keyed by (any ticker in the label, goal date) must link its /fda-decision/ page and must not
carry the Awaiting badge.

    python tests/test_decided_rows_marked_on_calendar.py
"""
import glob
import io
import json
import os
import re
import sys

SITE = "pdufa_site_src"
ROW = re.compile(r'<a class="row"([^>]*)>\s*<div class="t">([A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})*)'
                 r'\s*(?:&middot;|·)\s*(\d{4}-\d{2}-\d{2})(.*?)</div>', re.S)


def main():
    ds = os.path.join(SITE, "api", "v1", "dataset.mjs")
    if not os.path.exists(ds):
        print(f"  SKIP {ds} not found")
        return 0
    src = io.open(ds, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    decided = {(str(r.get("t") or "").upper(), str(r.get("d") or ""))
               for r in rows
               if r.get("type") == "PDUFA" and r.get("dp") == "day"
               and str(r.get("st") or "") == "Decided" and r.get("oc")}

    fail = checked = 0
    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    for p in pages:
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        for m in ROW.finditer(doc):
            attrs, label, date, tail = m.groups()
            tks = [x.strip() for x in label.split("/")]
            if not any((tk, date) in decided for tk in tks):
                continue
            checked += 1
            # Two marked shapes exist: the script's (data-dec + outcome span) and a hand-restored
            # one from 09-05c (href to the decision page + <span class="ok|no">). Both tell the
            # reader the truth; the link to the decision page is the invariant.
            marked = 'href="/fda-decision/' in attrs
            if not marked or "awaiting" in tail.lower():
                how = "still says Awaiting" if "awaiting" in tail.lower() else "reads like a live date"
                print(f"  FAIL {rel}: {label} {date} -- the dataset records a decision with an "
                      f"outcome but the calendar row {how}. Run mark_calendar_decided.py.")
                fail += 1

    if fail:
        print(f"\n{fail} decided PDUFA row(s) not marked on the calendar. Two surfaces, one "
              f"truth: the API says Decided, the calendar must too. DO NOT PUBLISH.")
        return 1
    print(f"OK -- {len(decided)} decided day-precision PDUFA(s) in the dataset; all {checked} "
          f"calendar row(s) for them are marked decided and none says Awaiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
