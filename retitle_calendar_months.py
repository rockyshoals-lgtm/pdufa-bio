# -*- coding: utf-8 -*-
"""retitle_calendar_months.py -- month calendar pages say in their title how many FDA decision dates they hold.

Audit 2026-10-24 (Bing). For "upcoming PDUFA dates November 2026" Bing ranks /calendar and /calendar/2026/november
first and third, but the month page's title was "November 2026 FDA PDUFA Calendar" with a generic description, while
the competing results lead with a count ("PDUFA Dates November 2026: 17 FDA Decisions"). The count we can state is the
number of dated rows the page itself lists, so that is the number used: title, description, og:title,
og:description, twitter:title. Idempotent; pages without rows are left alone.

    python retitle_calendar_months.py [--dry-run]
"""
import argparse
import glob
import html
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def sub_meta(doc, attr, name, value):
    v = html.escape(value, quote=True)
    return re.sub(r'(<meta ' + attr + r'="' + re.escape(name) + r'" content=")[^"]*(")',
                  lambda m: m.group(1) + v + m.group(2), doc, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    changed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "calendar", "20[0-9][0-9]", "*", "index.html"))):
        month, year = os.path.basename(os.path.dirname(p)), os.path.basename(os.path.dirname(os.path.dirname(p)))
        if month not in MONTHS:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        n = len(re.findall(r'<a class="row"', doc))
        if not n:
            continue
        mname = month.capitalize()
        title = f"{mname} {year} PDUFA Calendar: {n} FDA Decision Date{'s' if n != 1 else ''} | pdufa.bio"
        desc = (f"{n} FDA PDUFA decision date{'s' if n != 1 else ''} in {mname} {year}, each with company, ticker, drug "
                f"and indication and a link to its primary source. Updated daily.")
        new = re.sub(r"<title>[^<]*</title>", f"<title>{html.escape(title, quote=False)}</title>", doc, count=1)
        new = sub_meta(new, "name", "description", desc)
        new = sub_meta(new, "property", "og:title", title)
        new = sub_meta(new, "property", "og:description", desc)
        new = sub_meta(new, "name", "twitter:title", title)
        new = sub_meta(new, "name", "twitter:description", desc)
        if new != doc:
            changed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
            print(f"  /calendar/{year}/{month}: {title}")
    print(f"calendar month titles: {changed} page(s) written" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
