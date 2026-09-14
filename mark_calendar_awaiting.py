# -*- coding: utf-8 -*-
"""A PDUFA date that has passed with no decision must SAY so on the calendar.

/api/v1 already does this. _lib.mjs relabels a past-dated Upcoming PDUFA as "Awaiting", with the
reasoning that "a PDUFA whose date has passed with no outcome yet is not 'Upcoming'". The
calendar never learned the same rule, so on 2026-09-14 the TLX row for TLX101-Px (Pixclara) sat
on /calendar reading "TLX - 2026-09-11" exactly like a live date three days after its goal date
had passed. The API said Awaiting and the page said nothing: two surfaces, one truth, again.

This is deliberately NOT a claim that anything went wrong. Telix's own half-year report of
August 20, 2026 confirms the September 11 goal date, and as of today no Telix filing and no FDA
record shows a decision either way. "Awaiting" is the honest word for that, and it is the word
the API already uses.

Rows that are Decided are untouched -- mark_calendar_decided.py owns those.

    python mark_calendar_awaiting.py [--dry-run]
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = "pdufa_site_src"
TODAY = dt.date.today().isoformat()
BADGE = ('<span class="awaiting" style="color:#e3ba5e;font-weight:700" '
         'title="The PDUFA goal date has passed and no decision has been announced">'
         'Awaiting</span>')
ROW = re.compile(r'(<a class="row"[^>]*>\s*<div class="t">([A-Z]{1,6}) (?:&middot;|·) '
                 r'(\d{4}-\d{2}-\d{2}))(.*?)(</div>)', re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
                  encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

    awaiting = set()
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("dp") != "day":
            continue
        if str(r.get("st") or "") in ("Decided",):
            continue
        d = str(r.get("d") or "")
        if d and d < TODAY:
            awaiting.add((str(r.get("t") or "").upper(), d))

    if not awaiting:
        print("no past-dated undecided PDUFA rows; nothing to mark")
        return 0
    print("awaiting: " + ", ".join(f"{t} {d}" for t, d in sorted(awaiting)))

    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    marked = 0
    for p in pages:
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        orig = doc

        def rep(m):
            global marked  # noqa: PLW0603
            key = (m.group(2), m.group(3))
            if key not in awaiting or "awaiting" in m.group(4).lower():
                return m.group(0)
            return m.group(1) + m.group(4) + " " + BADGE + m.group(5)

        # re.sub can't see a nonlocal counter cleanly, so count by diffing
        doc = ROW.sub(lambda m: (m.group(1) + m.group(4) + " " + BADGE + m.group(5))
                      if ((m.group(2), m.group(3)) in awaiting
                          and "awaiting" not in m.group(4).lower())
                      else m.group(0), doc)
        n = doc.count('class="awaiting"') - orig.count('class="awaiting"')
        if doc != orig:
            marked += n
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(doc)
            print(f"  {os.path.relpath(p, SITE)}: +{n} awaiting badge(s)")

    print(f"\n{marked} calendar row(s) marked Awaiting"
          + ("  (--dry-run, nothing written)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
