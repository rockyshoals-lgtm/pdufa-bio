# -*- coding: utf-8 -*-
"""inject_conference_lede.py -- one fact-first sentence on every per-conference page (audit 2026-10-03, 3.4).

AASLD (45 Bing impressions, position 9.13) and SABCS queries arrive at the bottom of page one on pages
whose first text was "Nov 5-9, 2026 · Denver, US · Hepatology / MASH." The answer sentence goes first:
  "AASLD The Liver Meeting 2026 takes place November 5 to 9, 2026 in Denver, US."
built only from the page's own Dates and Location facts (sourced to the organiser by build_conferences.py),
with the tense set by the Eastern date (RULE 1): takes place / is under way, through ... / took place.
Idempotent, between markers.

    python inject_conference_lede.py
"""
import datetime as dt
import glob
import html
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--CONFFACT:BEGIN-->", "<!--CONFFACT:END-->"
OLD_B, OLD_E = "<!--CLEDE:BEGIN-->", "<!--CLEDE:END-->"
M3 = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def parse_span(s):
    s = s.strip()
    m = re.match(r"^([A-Z][a-z]{2}) (\d{1,2})\s*(?:-|to)\s*(\d{1,2}), (\d{4})$", s)
    if m:
        y, mo = int(m.group(4)), M3[m.group(1)]
        return dt.date(y, mo, int(m.group(2))), dt.date(y, mo, int(m.group(3)))
    m = re.match(r"^([A-Z][a-z]{2}) (\d{1,2})\s*(?:-|to)\s*([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$", s)
    if m:
        y = int(m.group(5))
        return dt.date(y, M3[m.group(1)], int(m.group(2))), dt.date(y, M3[m.group(3)], int(m.group(4)))
    m = re.match(r"^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$", s)
    if m:
        d = dt.date(int(m.group(3)), M3[m.group(1)], int(m.group(2)))
        return d, d
    return None


def span_words(a, b):
    if a == b:
        return f"{MON[a.month]} {a.day}, {a.year}"
    if a.month == b.month:
        return f"{MON[a.month]} {a.day} to {b.day}, {a.year}"
    return f"{MON[a.month]} {a.day} to {MON[b.month]} {b.day}, {b.year}"


def main():
    today = eastern_today()
    n = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "conference", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        dm = re.search(r"<span>Dates</span><b>([^<]+)</b>", doc)
        lm = re.search(r"<span>Location</span><b>([^<]+)</b>", doc)
        hm = re.search(r"<h1>(.*?)</h1>", doc, re.S)
        sp = parse_span(html.unescape(dm.group(1))) if dm else None
        if not (sp and hm):
            skipped += 1
            continue
        name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", hm.group(1)))).strip()
        a, b = sp
        loc = html.unescape(lm.group(1)).strip() if lm else ""
        where = f" in {loc}" if loc and loc.lower() not in ("tbd", "virtual", "") else ""
        if b < today:
            sent = f"{name} took place {span_words(a, b)}{where}."
        elif a <= today:
            sent = f"{name} is under way{where}, {span_words(a, b)}."
        else:
            sent = f"{name} takes place {span_words(a, b)}{where}."
        block = f'{B}<p class="sub fact" style="font-size:17px;color:#eef4fc">{html.escape(sent, quote=False)}</p>{E}'
        new = re.sub(re.escape(B) + r".*?" + re.escape(E), "", doc, flags=re.S)
        new = re.sub(re.escape(OLD_B) + r".*?" + re.escape(OLD_E), "", new, flags=re.S)   # marker migration
        j = new.find("<!--FRESH:END-->")
        if j < 0:
            j = new.find("</h1>")
            k = j + len("</h1>")
        else:
            k = j + len("<!--FRESH:END-->")
        if j < 0:
            skipped += 1
            continue
        new = new[:k] + block + new[k:]
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            n += 1
    print(f"conference ledes: {n} page(s) updated, {skipped} skipped (no parseable dates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
