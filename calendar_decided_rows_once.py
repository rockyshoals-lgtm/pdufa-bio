# -*- coding: utf-8 -*-
"""calendar_decided_rows_once.py -- one decision, one calendar row, and the row says when it was decided
(2026-11-17 currency audit).

What a real browser showed on /calendar on 2026-11-17:
  * five approvals listed twice: once on their decision day ("RHHBY · 2026-11-13 ✓ Gazyva") and again on the
    goal window the period marker matched them to ("RHHBY · Nov 2026 ✓ Gazyva"); same for ABBV tavapadon,
    BAYRY Kerendia, AZN Ultomiris and PFE Tukysa. A reader counts two events; an answer engine does too.
  * "PFE / ROIV · 2026-09-30 ✓ Brepocitinib" -- a quarter-end day withdrawn on 2026-09-10 (the sponsor said
    "third quarter") still shown, because fix_calendar_windowed_rows.py's ticker pattern does not read a
    two-ticker label. It duplicated the 2026-08-27 approval row on the same page.
  * decided rows sitting on their GOAL date with nothing saying the decision came on another day
    ("RHHBY · 2026-12-18 ✓ Wilserdly", approved 2026-11-16).

Rules, per calendar page:
  1. When several rows on one page with the same ticker label link the same /fda-decision page, keep one: the row whose shown date is the
     decision page's date, else a day-precision row, else the first. The others are removed. Rows of DIFFERENT
     tickers for one decision (a partner, a royalty holder: JAZZ / ZYME / RPRX for Ziihera) all stay; a reader
     of either ticker expects the row.
  2. A kept decided row whose shown date is not its decision date gains one span in its description stating the
     decision date: "FDA action Sep 9, 2026" when the dataset holds the FDA's own action date, otherwise
     "announced Nov 16, 2026" (the decision page's date, which is the announcement). Nothing is inferred.
Idempotent; --dry-run prints. Guard: tests/test_calendar_decision_once.py. Facts only; not investment advice.
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
ROW = re.compile(r'<a class="row"([^>]*)>\s*<div class="t">(.*?)</div>\s*<div class="d">(.*?)</div>\s*</a>', re.S)
DD = re.compile(r'\s*<span class="dd"[^>]*>.*?</span>', re.S)
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def pages():
    return [os.path.join(SITE, "calendar", "index.html")] + sorted(
        glob.glob(os.path.join(SITE, "calendar", "[0-9][0-9][0-9][0-9]", "*", "index.html")))


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month - 1]} {d.day}, {d.year}"


def action_dates():
    """/fda-decision/{TK}-{date} -> FDA action date, from Decided dataset rows that link the page."""
    s = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(s[s.index("["):s.rindex("]") + 1])
    out = {}
    for r in rows:
        u = str(r.get("url") or "")
        fad = str((r.get("_d") or {}).get("fda_action_date") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", fad):
            continue
        if u.startswith("/fda-decision/"):
            out[u] = fad
        dcd = str(r.get("dcd") or "")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", dcd):          # the decision page is named {TK}-{decision date}
            out.setdefault(f"/fda-decision/{str(r.get('t') or '').upper()}-{dcd}", fad)
    return out


def shown_date(t):
    m = re.search(r"\d{4}-\d{2}-\d{2}", re.sub(r"<[^>]+>", " ", t))
    return m.group(0) if m else None


def fix(doc, fad):
    rows = []
    for m in ROW.finditer(doc):
        h = re.search(r'href="(/fda-decision/[A-Z0-9./-]+-(\d{4}-\d{2}-\d{2}))"', m.group(1))
        if h and "data-dec" in m.group(1):
            rows.append((m, h.group(1), h.group(2)))
    by = {}
    for x in rows:
        label = re.sub(r"\s*(?:&middot;|·).*$", "", re.sub(r"<[^>]+>", "", x[0].group(2)), flags=re.S).strip()
        by.setdefault((x[1], label), []).append(x)
    drop, notes = set(), []
    for (href, _label), xs in by.items():
        if len(xs) > 1:
            keep = (next((x for x in xs if shown_date(x[0].group(2)) == x[2]), None)
                    or next((x for x in xs if shown_date(x[0].group(2))), None) or xs[0])
            for x in xs:
                if x is not keep:
                    drop.add(x[0].start())
                    notes.append(f"removed duplicate '{re.sub(r'<[^>]+>', '', x[0].group(2)).strip()}' of {href}")
    out, last = [], 0
    for m, href, pdate in rows:
        out.append(doc[last:m.start()])
        last = m.end()
        if m.start() in drop:
            continue
        seg = m.group(0)
        shown = shown_date(m.group(2))
        a = fad.get(href)
        if a:
            label = f"FDA action {pretty(a)}"
            same = shown == a
        else:
            label = f"announced {pretty(pdate)}"
            same = shown == pdate
        # The note sits in the date line (div.t), next to the date it qualifies: the drug line (div.d) is read by the
        # row-vs-dataset name check, and "FDA action" words there would read as part of the drug's name.
        t_new = DD.sub("", m.group(2))
        body = DD.sub("", m.group(3))
        if not same:
            t_new = t_new + f' <span class="dd" style="color:#94a9c9;font-size:12px;font-weight:400">&middot; {label}</span>'
        if (t_new, body) != (m.group(2), m.group(3)):
            seg = (seg[:m.start(2) - m.start()] + t_new + seg[m.end(2) - m.start():m.start(3) - m.start()] + body
                   + seg[m.end(3) - m.start():])
        out.append(seg)
    out.append(doc[last:])
    return "".join(out), notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fad = action_dates()
    total = 0
    for p in pages():
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new, notes = fix(doc, fad)
        for n in notes:
            print(f"  {os.path.relpath(p, SITE)}: {n}")
        total += len(notes)
        if new != doc and not a.dry_run:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            print(f"  wrote {os.path.relpath(p, SITE)}")
    print(f"duplicate decided rows removed: {total}{' [dry run]' if a.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
