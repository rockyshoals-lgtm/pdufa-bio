# -*- coding: utf-8 -*-
"""inject_event_page_source.py -- every upcoming PDUFA event page shows the document its date came from.

Audit 2026-11-05 (trust + AI citation). The event-page builder linked a source only when the dataset row's `url` was
an off-site link, a convention retired months ago: rows now carry `_d.source`, `_d.source_url` and `_d.source_quote`,
and the pages rendered none of it. /pdufa/QURE-amt-130 said "May 1, 2027" with no visible way to check it, on the
pages answer engines quote. This writes, under the page's one-line summary, a marker block:

    Source: <sponsor filing, linked>. "<the sentence that states the date>"

and, for a goal date beyond /calendar's window, points the calendar call-to-action at that year's hub and month page
instead of "the full 2026 calendar". Idempotent; only rows with a source_url are touched.

    python inject_event_page_source.py [--dry-run]
"""
import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--SRC:BEGIN-->", "<!--SRC:END-->"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def clean_quote(q, d):
    """The one sentence of the stored quote that states the date, or nothing.

    Some quotes were stored as a run of headline text from a release (CYTK's ran 400 characters through three bullet
    headlines and stopped mid-word); publishing that as a quotation misquotes the sponsor. Keep a sentence only if it
    names PDUFA/action date or the month of the goal, is whole, and is short enough to read as a quote."""
    q = re.sub(r"\s+", " ", str(q or "")).strip()
    if not q:
        return ""
    month = MONTHS[int(str(d)[5:7]) - 1] if str(d)[5:7].isdigit() else "PDUFA"
    parts = re.split(r"(?<=[.;])\s+|\s{2,}|(?<=\d{4})\s+(?=[A-Z][a-z]+ [A-Z])", q)
    best = [s.strip() for s in parts if re.search(r"PDUFA|action date|goal date|" + month, s)]
    best = [s for s in best if 20 <= len(s) <= 240]
    if not best:
        return ""
    s = min(best, key=len)
    # a headline run glued together without punctuation: cut at the clause that carries the date
    m = re.search(r"[^.;]{0,160}(?:PDUFA|action date|goal date)[^.;]{0,80}?" + r"\b\d{4}\b", s)
    if m and len(s) > 200:
        cut = m.group(0)
        if m.start() > 0 and not s[m.start() - 1].isspace():
            cut = cut.split(" ", 1)[1] if " " in cut else cut   # never start inside a word
        s = "…" + cut.strip(" ,;:(") if m.start() > 0 else cut.strip()
    # end the quotation at the date it is quoted for; anything after it (", following U.S.", a cash balance) is
    # another headline that happened to sit on the same line
    dm = re.search(r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
                   r"(?: \d{1,2},)? \d{4}", s)
    if dm and len(s) - dm.end() > 1:
        s = s[:dm.end()] + "…"   # cut, not ended: never add punctuation the sponsor did not write
    hd = re.search(r"(Financial Results|Corporate Update|Business Update)[^.]*?(?=PDUFA)", s)
    if hd:
        s = "…" + s[hd.end():]
    if len(s) > 240:
        return ""
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    n = ncta = 0
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("st") not in ("Upcoming", "Awaiting"):
            continue
        url = str(r.get("url") or "")
        if not url.startswith("/pdufa/"):
            continue
        p = os.path.join(SITE, url.strip("/").replace("/", os.sep), "index.html")
        if not os.path.exists(p):
            continue
        d = r.get("_d") or {}
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = doc
        su = str(d.get("source_url") or "")
        if su.startswith("http"):
            q = clean_quote(d.get("source_quote"), r.get("d"))
            block = (f'{B}<div class="note" style="margin:8px 0;font-size:13.5px;line-height:1.6">Source: '
                     f'<a href="{esc(su)}" rel="noopener">{esc(d.get("source") or "sponsor filing")}</a>.'
                     + (f' <span style="color:var(--mut2)">&ldquo;{esc(q)}&rdquo;</span>' if q else "") + f"</div>{E}")
            if B in new:
                new = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: block, new, flags=re.S)
            else:
                # under the one-line summary that follows the h1/freshness stamp; drop the legacy "Primary source"
                # line if the same page carries one, so the source is stated once
                m = re.search(r'(</h1>.*?<div class="sub">.*?</div>)', new, re.S)
                if m:
                    new = new[:m.end()] + block + new[m.end():]
            new = re.sub(r'<div class="note" style="margin:8px 0">Primary source: <a [^>]*>sponsor announcement</a></div>',
                         "", new)
        y, mo = str(r.get("d") or "")[:4], str(r.get("d") or "")[5:7]
        if y > "2026" and mo.isdigit():
            mname = MONTHS[int(mo) - 1]
            cta = (f'<a class="cta" href="/calendar/{y}"><b>See every {y} PDUFA date &rarr;</b></a>'
                   + (f'<a class="cta" href="/calendar/{y}/{mname.lower()}"><b>All {mname} {y} PDUFA dates &rarr;</b></a>'
                      if os.path.exists(os.path.join(SITE, "calendar", y, mname.lower(), "index.html")) else ""))
            new2 = new.replace('<a class="cta" href="/calendar"><b>See the full 2026 PDUFA calendar &rarr;</b></a>', cta, 1)
            if new2 != new:
                ncta += 1
            new = new2
        if new != doc:
            n += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    print(f"event-page sources: {n} page(s) written ({ncta} calendar link(s) pointed at a later year)"
          + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
