# -*- coding: utf-8 -*-
"""test_event_page_currency.py -- nothing on a /pdufa/ event page is frozen at the day it was written.

Design red team 2026-11-18. Four days before Capricor's Nov 22 decision, /pdufa/CAPR showed a price chart that
ended 2026-06-19 under "last ~120 days", a chip to "All August 2026 PDUFA dates", three "related" decisions that
had all happened in July and August, and an unsourced "runway ~36 mo (estimated)". All 60 pages with that chart
had it ending 2026-06-19. refresh_event_page_currency.py now redraws or removes each of these every rebuild; this
fails if any comes back:

  1. no chart from the June one-off batch ("Price path to YYYY-MM-DD") remains; every redrawn chart ends within 7
     days of today and states its range, and only a page whose decision is still ahead carries one;
  2. a page's "All <Month> <Year> PDUFA dates" chip (either form the builders write) names the month of the page's
     own target date, whether the page writes it as 2026-11-22, Nov 22, 2026 or Nov 2026;
  3. no "Same area" / "Same month" related row shows a date before today, and a "Same month" row is in the page's
     own target month;
  4. no "Balance sheet: about N months of cash" sentence or runway risk badge remains.
Pages a watcher lead is holding at their last commit (quarantine_leads.py) are skipped: they are frozen on purpose,
and failing on them would turn one held row into a site-wide blockade.

    python tests/test_event_page_currency.py
"""
import datetime as dt
import glob
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
MON3 = {m[:3].capitalize(): i + 1 for i, m in enumerate(MONTHS)}
TARGET = re.compile(r'FDA decision \(PDUFA\) target <b>(?:(\d{4}-\d{2}-\d{2})|([A-Z][a-z]{2}) (?:(\d{1,2}), )?(\d{4}))</b>')
CHIP = re.compile(r'<a [^>]*?href="(/calendar/\d{4}/[a-z]+)"[^>]*>(?:<b>)?All [A-Za-z]+ \d{4} PDUFA dates')


def target_of(doc):
    m = TARGET.search(doc)
    if not m:
        return None, None
    if m.group(1):
        return m.group(1), m.group(1)[:7]
    if m.group(2) not in MON3:
        return None, None
    ym = f"{m.group(4)}-{MON3[m.group(2)]:02d}"
    return (f"{ym}-{int(m.group(3)):02d}" if m.group(3) else None), ym


def held_pages():
    """Pages quarantine_leads.py apply restores to their last commit while a lead is held."""
    try:
        import json
        sys.path.insert(0, HERE)
        import quarantine_leads as Q
        st = json.load(open(Q.STATE, encoding="utf-8")) if os.path.exists(Q.STATE) else {}
        ids = {l.get("row_id") for l in st.get("leads") or [] if l.get("row_id")}
        if not ids:
            return set()
        src = open(Q.DATASET, encoding="utf-8", errors="replace").read()
        rows = {r.get("id"): r for r in json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))}
        out = set()
        for rid in ids:
            for p in Q.held_paths(rows.get(rid) or {}, rid[5:] if rid.startswith("drug:") else None):
                out.add(os.path.normcase(os.path.abspath(p)))
        return out
    except Exception as ex:  # noqa: BLE001
        print(f"  note: could not read held leads ({ex.__class__.__name__}); checking every page")
        return set()

try:
    from zoneinfo import ZoneInfo
    TODAY = dt.datetime.now(ZoneInfo("America/New_York")).date()
except Exception:
    TODAY = dt.date.today()


def main():
    pages = sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html")))
    bad = []
    charts = skipped = 0
    held = held_pages()
    today = TODAY.isoformat()
    for p in pages:
        slug = "/pdufa/" + os.path.basename(os.path.dirname(p))
        if os.path.normcase(os.path.abspath(p)) in held:
            skipped += 1
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        day, ym = target_of(doc)
        pending = bool(ym) and (day >= today if day else ym >= today[:7])

        if re.search(r'<div class="note">Price path to \d{4}-\d{2}-\d{2}\.', doc):
            bad.append(f"{slug}: still carries the one-off run-up chart ('Price path to ...')")
        for blk in re.findall(r"<!--EVRUNUP:B:[^>]*-->(.*?)<!--EVRUNUP:E-->", doc, re.S):
            if "<svg" not in blk:
                continue
            charts += 1
            if not pending:
                bad.append(f"{slug}: price chart on a page with no decision still ahead")
            m = re.search(r"the last \d+ recorded daily closes: ([A-Z][a-z]{2}) (\d{1,2}), (\d{4}) to "
                          r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4}), the latest close", blk)
            if not m:
                bad.append(f"{slug}: price chart does not state its date range")
                continue
            last = dt.date(int(m.group(6)), MON3[m.group(4)], int(m.group(5)))
            if (TODAY - last).days > 7:
                bad.append(f"{slug}: price chart ends {last}, more than 7 days ago")
            if 'aria-label="' not in blk:
                bad.append(f"{slug}: price chart has no text alternative")

        if ym:
            want = f"/calendar/{ym[:4]}/{MONTHS[int(ym[5:7]) - 1]}"
            for href in CHIP.findall(doc):
                if href != want:
                    bad.append(f"{slug}: month chip links {href} but the page's target is {day or ym}")

        for d, why in re.findall(r'<span class="t">[^<]*? \. (\d{4}-\d{2}-\d{2})</span><span class="d">'
                                 r'(Same (?:area|month)[^<]*)</span>', doc):
            if d < today:
                bad.append(f"{slug}: related row '{why[:40]}' shows {d}, already past")
            elif why.startswith("Same month") and d[:7] != ym:
                bad.append(f"{slug}: 'Same month' row dated {d}, but the page's target is {day or ym or 'not stated'}")

        if re.search(r"Balance sheet: about <b>\d+ months of cash</b>", doc) or "runway ends before" in doc:
            bad.append(f"{slug}: unsourced cash-runway sentence or runway badge")

    print(f"checked {len(pages) - skipped} /pdufa/ pages ({skipped} held by a watcher lead, skipped); "
          f"{charts} current price chart(s)")
    if bad:
        for b in bad[:40]:
            print("  FAIL " + b)
        if len(bad) > 40:
            print(f"  ... and {len(bad) - 40} more")
        print("  fix: python refresh_event_page_currency.py")
        sys.exit(1)
    print("  PASS: event pages carry no frozen chart, month chip, related row or runway estimate")


if __name__ == "__main__":
    main()
