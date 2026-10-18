# -*- coding: utf-8 -*-
"""inject_goal_date_moves.py -- "Goal date moved {old} -> {new}" inline, from the row's own date_history (audit 2026-10-18, order 5).

date_history has been in the API since 09-15 but no page showed it; regardsofwallstreet shows "Was: {date}" and we
did not. For every PDUFA row whose date_history records a change of the goal DAY (a later entry whose date differs
from the first), the row's event page gets one marker-bounded sentence under the banner / sub line:

  Goal date moved: August 22, 2026 -> November 22, 2026 (changed August 24, 2026). The FDA extended the goal date ...

and its /calendar row (the live grid and the month archive) gets a short tag after the drug text:
  "goal date moved from Aug 22, 2026"
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
            why_s = html.escape(re.split(r"(?<=[.!?])\s", why.strip())[0][:220], quote=False)
            block = (f'{B}<p class="note" style="margin:6px 0 10px;font-size:13px;color:#f0c86a">'
                     f'<b>Goal date moved:</b> {pretty(old)} &rarr; {pretty(new)} (recorded {pretty(changed)}). '
                     f'{why_s}</p>{E}')
            doc0 = re.sub(re.escape(B) + ".*?" + re.escape(E), "", doc, flags=re.S)
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
    for cp in [os.path.join(SITE, "calendar", "index.html")] + sorted(glob.glob(os.path.join(SITE, "calendar", "2026", "*", "index.html"))):
        doc = io.open(cp, encoding="utf-8", errors="replace").read()
        doc0 = re.sub(r' <span class="dm"><!--DM:[^>]*--><span[^>]*>[^<]*</span></span>', "", doc)
        changed_doc = doc0
        for (tk, iso), (old, rid) in cal_tags.items():
            rx = re.compile(r'(<a class="row"[^>]*>\s*<div class="t">' + re.escape(tk) + r'(?:\s*/\s*[A-Z]{1,6})*\s*(?:&middot;|·)\s*'
                            + re.escape(iso) + r'.*?<div class="d">)(.*?)(</div>)', re.S)
            changed_doc = rx.sub(lambda m: m.group(1) + m.group(2) + f' <span class="dm">{CB}{rid}{CE}'
                                 f'<span style="color:#f0c86a;font-size:11.5px">goal date moved from {pretty(old, True)}</span></span>' + m.group(3),
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
