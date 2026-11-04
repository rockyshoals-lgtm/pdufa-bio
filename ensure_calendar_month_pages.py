# -*- coding: utf-8 -*-
"""ensure_calendar_month_pages.py -- every month that holds a dated upcoming PDUFA has a /calendar/YYYY/month page.

2026-11-01 created March and May 2027 by hand; 2026-11-03 a sourced June 2027 goal (MRK sac-TMT) arrived with no
page to live on. ensure_calendar_rows.py only fills pages that exist, so a month with no page is invisible on the
calendar however well the date is sourced. This clones the nearest existing month page (rows emptied, names and
URLs swapped), seeds it with that month's dated rows, and rechains prev/next across the year. Idempotent.

    python ensure_calendar_month_pages.py [--dry-run]
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CAL = os.path.join(SITE, "calendar")
sys.path.insert(0, HERE)
from ensure_calendar_rows import row_html  # noqa: E402

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def existing():
    out = []
    for p in glob.glob(os.path.join(CAL, "20[0-9][0-9]", "*", "index.html")):
        y, m = p.split(os.sep)[-3], p.split(os.sep)[-2]
        if m in MONTHS:
            out.append((int(y), MONTHS.index(m) + 1))
    return sorted(out)


def path(y, m):
    return os.path.join(CAL, str(y), MONTHS[m - 1], "index.html")


def label(y, m):
    return f"{MONTHS[m - 1].capitalize()} {y}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    want = sorted({(int(r["d"][:4]), int(r["d"][5:7])) for r in rows
                   if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting") and r.get("dp", "day") == "day"})
    have = existing()
    made = []
    for y, m in want:
        if (y, m) in have:
            continue
        ty, tm = min(have, key=lambda k: abs((k[0] * 12 + k[1]) - (y * 12 + m)))
        tpl = io.open(path(ty, tm), encoding="utf-8").read()
        tname, tlow = MONTHS[tm - 1].capitalize(), MONTHS[tm - 1]
        doc = tpl.replace(f"{tname} {ty}", f"{MONTHS[m-1].capitalize()} {y}").replace(f"/{ty}/{tlow}", f"/{y}/{MONTHS[m-1]}")
        g = '<div class="grid" style="margin-top:12px">'
        gi = doc.index(g) + len(g)
        ge = doc.index('</div><div class="callout">', gi)
        mine = sorted([r for r in rows if r.get("type") == "PDUFA" and r.get("st") in ("Upcoming", "Awaiting")
                       and r["d"].startswith(f"{y}-{m:02d}") and r.get("dp", "day") == "day"], key=lambda r: r["d"])
        doc = doc[:gi] + "".join(row_html(r) for r in mine) + doc[ge:]
        tks = sorted({(r.get("t") or "").upper() for r in mine})
        chip = ('<a href="/ticker/{0}" style="display:inline-block;padding:3px 8px;margin:2px;border:1px solid '
                'var(--line);border-radius:7px;font-size:12.5px;text-decoration:none" class="lit">{0}</a>')
        doc = re.sub(r"(<!--TICKERIDX:BEGIN-->.*?<div>)(?:<a href=\"/ticker/[^\"]+\"[^>]*>[^<]*</a>)*(</div>)",
                     lambda mm: mm.group(1) + "".join(chip.format(t) for t in tks) + mm.group(2), doc, count=1, flags=re.S)
        if not a.dry_run:
            os.makedirs(os.path.dirname(path(y, m)), exist_ok=True)
            io.open(path(y, m), "w", encoding="utf-8").write(doc)
        have.append((y, m)); have.sort(); made.append((y, m))
        print(f"  + /calendar/{y}/{MONTHS[m-1]}: {len(mine)} row(s), cloned from {tname} {ty}")
    # rechain prev/next for every month page in order
    have = sorted(set(have))
    for i, (y, m) in enumerate(have):
        p = path(y, m)
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8").read()
        pn = '<div class="pn">'
        if i > 0:
            py, pm = have[i - 1]
            pn += f'<a href="/calendar/{py}/{MONTHS[pm-1]}">&larr; {label(py, pm)}</a>'
        else:
            pn += "<span></span>"   # keeps "next" right-aligned, as the original first-month page had it
        if i + 1 < len(have):
            ny, nm = have[i + 1]
            pn += f'<a href="/calendar/{ny}/{MONTHS[nm-1]}">{label(ny, nm)} &rarr;</a>'
        pn += "</div>"
        new = re.sub(r'<div class="pn">.*?</div>', pn, doc, count=1, flags=re.S)
        if new != doc and not a.dry_run:
            io.open(p, "w", encoding="utf-8").write(new)
            print(f"  ~ /calendar/{y}/{MONTHS[m-1]}: prev/next rechained")
    print(f"month pages created: {len(made)}" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
