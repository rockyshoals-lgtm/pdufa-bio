# -*- coding: utf-8 -*-
"""inject_goal_date_moves.py -- "Goal date moved {old} -> {new}" inline, from the row's own date_history (audit 2026-10-18, order 5).

date_history has been in the API since 09-15 but no page showed it; regardsofwallstreet shows "Was: {date}" and we
did not. For every PDUFA row whose date_history records a change of the goal DAY (a later entry whose date differs
from the first), the row's event page gets one marker-bounded sentence under the banner / sub line:

  Goal date moved: 2026-08-22 -> 2026-11-22 (recorded 2026-08-24). The FDA extended the goal date ...

and its /calendar row (the live grid and the month archive) gets a short tag after the drug text:
  "goal date moved from 2026-08-22"

WHY THE DATES ARE ISO, NOT "August 22, 2026" (2026-11-18, Bing date fix)
Bing printed "Aug 22, 2026" as the date of /calendar and /pdufa/CAPR, and "Jun 29, 2026" for
/pdufa/PRAX-relutrigine, although each page carries a fresh dateModified, og:updated_time,
article:modified_time and a visible "Page updated <date>" stamp, and Bing had recrawled /calendar
(its result shows the current title). The date Bing printed was, on each page, the one written
in prose beside a change verb in this block or tag: "goal date moved from Aug 22, 2026",
"(recorded June 29, 2026)". Google's guidance on result dates says the same thing: other dates
near the top that read like an update date compete with the real one. The facts stay; they are
written as data (the row itself already says "CAPR · 2026-11-22"), so the only prose date near
the top of the page is the page's own "Page updated" stamp.
Rows whose history only records a precision downgrade or a re-key (same day, or the first entry is a sentinel the
row never stated) are skipped; they are not moves. Idempotent.

    python inject_goal_date_moves.py [--dry-run]
"""
import argparse
import glob
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--DATEMOVE:BEGIN-->", "<!--DATEMOVE:END-->"
CB, CE = "<!--DM:", "-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def pretty(iso, short=False):
    try:
        y, m, d = (int(x) for x in str(iso)[:10].split("-"))
        return f"{MON[m][:3] if short else MON[m]} {d}, {y}"
    except Exception:  # noqa: BLE001
        return str(iso)


_PROSE_DATE = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December"
                         r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})\b")


def iso_dates(text):
    """'8-K of June 29, 2026' -> '8-K of 2026-06-29': same fact, written as data (see the docstring)."""
    def one(m):
        mon = next(i for i, n in enumerate(MON) if i and n[:3] == m.group(1)[:3])
        return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}"
    return _PROSE_DATE.sub(one, text)


def short_reason(why, old, new, limit=260):
    """First sentence of the row's note, dates written as data, cut at a word (never inside a date).

    A year-less mention of the old or new goal day ("from August 22 to ...") is the same date as old/new, so it is
    written as that ISO date too; red team 2026-11-18 found it left as prose beside "extended ... from".
    """
    t = iso_dates(re.split(r"(?<=[.!?])\s", why.strip())[0])
    for d in (old, new):
        try:
            y, m, dd = (int(x) for x in str(d)[:10].split("-"))
        except Exception:  # noqa: BLE001
            continue
        mon = MON[m]
        names = {mon, mon[:3]} | ({"Sept"} if m == 9 else set())
        alt = "|".join(sorted(names, key=len, reverse=True))
        t = re.sub(rf"\b(?:{alt})\.?\s+{dd}(?:st|nd|rd|th)?\b(?!,?\s*\d{{4}})", f"{y:04d}-{m:02d}-{dd:02d}", t)
    if len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "\u2026"
    return t


def moves(r):
    """[(old_iso, new_iso, changed_iso, why)] for real day-to-day moves of the goal date."""
    hist = (r.get("_d") or {}).get("date_history") or []
    out, prev = [], None
    for h in hist:
        d = str(h.get("date") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            prev = None            # a month-precision entry ends the day-to-day chain
            continue
        note = str(h.get("why") or h.get("note") or "")
        sentinel = re.search(r"sentinel|not a stated|keyed on the FDA ACTION|withdrawn as unsourced", note, re.I)
        if prev and prev != d and h.get("changed") and not sentinel:
            out.append((prev, d, str(h.get("changed"))[:10], note))
        prev = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    n_pages = n_cal = 0
    cal_tags = {}
    for r in rows:
        if r.get("type") != "PDUFA":
            continue
        mv = moves(r)
        if not mv:
            continue
        old, new, changed, why = mv[-1]
        url = str(r.get("url") or "")
        p = os.path.join(SITE, url.strip("/").replace("/", os.sep), "index.html") if url.startswith("/pdufa/") else ""
        if p and os.path.exists(p):
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            why_s = html.escape(short_reason(why, old, new), quote=False)
            doc0 = re.sub(re.escape(B) + ".*?" + re.escape(E), "", doc, flags=re.S)
            # UX pass 2026-11-20: /pdufa/CAPR-deramiocel told the move twice, this note's reason and then the
            # "Date extended" box (EXTN) with the sponsor's own account, and the note's reason ended on an internal
            # pointer ("... and /pdufa-date-changes records it"). Where the page has its own extension box, the note
            # keeps the move as data and leaves the why to that box.
            ext = re.search(r"<!--EXTN:BEGIN-->(.*?)<!--EXTN:END-->", doc0, re.S)
            if ext and old[:10] in ext.group(1) and new[:10] in ext.group(1):   # the box tells this same move
                why_s = ""
            block = (f'{B}<p class="note" style="margin:6px 0 10px;font-size:13px;color:#f0c86a">'
                     f'<b>Goal date moved:</b> {old[:10]} &rarr; {new[:10]} (recorded {changed[:10]}).'
                     + (f' {why_s}' if why_s else '') + f'</p>{E}')
            m = (re.search(r"<!--DECBAN:END-->", doc0) or re.search(r'<div class="sub">.*?</div>', doc0, re.S)
                 or re.search(r"</h1>", doc0))
            if m:
                new_doc = doc0[:m.end()] + block + doc0[m.end():]
                if new_doc != doc:
                    n_pages += 1
                    if not a.dry_run:
                        io.open(p, "w", encoding="utf-8").write(new_doc)
        for tk in str(r.get("t") or "").split("/"):
            cal_tags[(tk.strip().upper(), str(r.get("d") or "")[:10])] = (old, r["id"])
    # calendar rows: a short tag after the drug text of the row keyed (ticker, current date)
    # 2026-11-18: the year pages (/calendar/2027) carry the same rows and tag; they were left out, so
    # they kept the old wording after the ISO change.
    for cp in ([os.path.join(SITE, "calendar", "index.html")]
               + sorted(glob.glob(os.path.join(SITE, "calendar", "20[0-9][0-9]", "index.html")))
               + sorted(glob.glob(os.path.join(SITE, "calendar", "20[0-9][0-9]", "*", "index.html")))):
        # 2026-11-01: was "2026" only, so a goal moved INTO 2027 (AGIO, EXEL) was tagged nowhere.
        doc = io.open(cp, encoding="utf-8", errors="replace").read()
        doc0 = re.sub(r' <span class="dm"><!--DM:[^>]*--><span[^>]*>[^<]*</span></span>', "", doc)
        changed_doc = doc0
        for (tk, iso), (old, rid) in cal_tags.items():
            rx = re.compile(r'(<a class="row"[^>]*>\s*<div class="t">' + re.escape(tk) + r'(?:\s*/\s*[A-Z]{1,6})*\s*(?:&middot;|·)\s*'
                            + re.escape(iso) + r'.*?<div class="d">)(.*?)(</div>)', re.S)
            changed_doc = rx.sub(lambda m: m.group(1) + m.group(2) + f' <span class="dm">{CB}{rid}{CE}'
                                 f'<span style="color:#f0c86a;font-size:11.5px">goal date moved from {old[:10]}</span></span>' + m.group(3),
                                 changed_doc, count=1)
        if changed_doc != doc:
            n_cal += 1
            if not a.dry_run:
                io.open(cp, "w", encoding="utf-8").write(changed_doc)
    print(f"goal-date moves: {len(cal_tags)} row(s) with a moved goal day; {n_pages} event page(s) and {n_cal} calendar page(s) updated"
          + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
