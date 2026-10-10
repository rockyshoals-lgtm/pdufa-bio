# -*- coding: utf-8 -*-
"""sync_event_urls.py -- every pending PDUFA row's `url`, and its calendar row, point at ITS event page.

Audit 2026-10-10 item 3: the API sent 33 of 35 upcoming rows to a hub (/ticker/{T} or /pdufa/{T}) while
an event page with the date in its title existed. The loop: ensure_calendar_rows followed the row's url,
sync_api_urls_to_calendar followed the calendar, and nothing ever asked event_pages.resolve(). Now:

  1. dataset.mjs: for each pending PDUFA row (day or window) that resolves to an event page, `url`
     becomes that page (an external url is first preserved in _d.source_url if that is empty);
  2. calendar pages: a row for (ticker, date) whose href is a hub is repointed to the same page.

Runs before ensure_calendar_rows.py and sync_api_urls_to_calendar.py, so both follow. Idempotent.

    python sync_event_urls.py [--dry-run]
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
sys.path.insert(0, HERE)
import event_pages as EP  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    changed, target, by_label = 0, {}, {}
    pend = EP.pending_rows(rows)
    from site_windows import window_label
    for r in pend:
        u = EP.resolve(r)
        if not u:
            continue
        target[r["id"]] = u          # keyed by row, not (ticker, date): two NVO rows share one sentinel date
        tk, d = str(r.get("t") or "").upper(), str(r.get("d") or "")[:10]
        # the calendar writes a window row as "REGN · Nov 2026" and a day row as "REGN · 2026-11-30"
        by_label[(tk, d if str(r.get("dp") or "day") == "day" else window_label(r))] = u
    # ONE EVENT, ONE PAGE: partner tickers of one DAY-dated application (IRD / VTRS MR-141) share a
    # calendar row, which can link one page; every partner row's url is that page (it states the date).
    for r in pend:
        if r["id"] not in target or str(r.get("dp") or "day") != "day":
            continue
        tk, d = str(r.get("t") or "").upper(), str(r.get("d") or "")[:10]
        for x in pend:
            if x is r or x["id"] not in target or str(x.get("dp") or "day") != "day":
                continue
            xt, xd = str(x.get("t") or "").upper(), str(x.get("d") or "")[:10]
            if xd != d or xt == tk or target[x["id"]] == target[r["id"]]:
                continue
            toks = lambda y: set(re.findall(r"[a-z]{5,}", str(y.get("name") or "").lower()))  # noqa: E731
            if EP.drug_token(x) == EP.drug_token(r) or (toks(x) & toks(r)):
                prim = min(target[r["id"]], target[x["id"]])     # deterministic: the alphabetically first page
                target[r["id"]] = target[x["id"]] = prim
                by_label[(tk, d)] = by_label[(xt, d)] = prim
    for r in pend:
        u = target.get(r["id"])
        if not u:
            continue
        if str(r.get("url") or "") != u:
            old = str(r.get("url") or "")
            if old.startswith("http") and not (r.get("_d") or {}).get("source_url"):
                r.setdefault("_d", {})["source_url"] = old
            r["url"] = u
            changed += 1
            print(f"  {r['id']}: url {old or '(none)'} -> {u}")
    if changed and not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    # calendar rows
    rx = re.compile(r'(<a class="row"(?![^>]*data-dec)[^>]*href=")([^"]+)("[^>]*>\s*<div class="t">)([A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})*)\s*(?:&middot;|·)\s*(\d{4}-\d{2}-\d{2}|Q[1-4] \d{4}|[A-Z][a-z]{2} \d{4}|\d{4})(?=<)')
    n_cal = 0
    for p in [os.path.join(SITE, "calendar", "index.html")] + sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html"))):
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()

        def fix(m):
            tks = [x.strip() for x in m.group(4).split("/")]
            for tk in tks:
                u = by_label.get((tk, m.group(5)))
                if u and m.group(2) != u and re.match(r"^/(ticker|pdufa)/[A-Z]{1,6}$", m.group(2)):
                    return m.group(1) + u + m.group(3) + m.group(4) + " &middot; " + m.group(5)
            return m.group(0)
        doc2 = rx.sub(fix, doc)
        if doc2 != doc:
            n_cal += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="\n").write(doc2)
    print(f"event urls: {changed} dataset row(s) repointed, {n_cal} calendar page(s) updated; "
          f"{len(target)} pending rows resolve to an event page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
