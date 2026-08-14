# -*- coding: utf-8 -*-
"""reconcile_calendar_table.py -- the calendar's rows must say what the dataset says. Daily.

Red team 2026-08-12: /calendar published '67 dates, 52 ahead' inside FAQPage schema while the
API answered 64/46 for the same window. Chasing the delta found worse than a count: PRAX's
relutrigine row still said September 27 six weeks after the FDA extended it to December 27
(major amendment, announced June 29, sponsor 8-K) -- a stale DATE on the site's #1-ranked page,
while the weekly heatmap on the SAME page, which reads the dataset, already showed PRAX in
late December. The page contradicted itself and nothing noticed, because rows are inserted and
marked decided but never re-checked against the dataset they came from.

This is that re-check. For every upcoming row on /calendar and the month pages:

  1. The row's event is matched to the dataset by drug-name token (+ticker), not by date --
     a date change is exactly what must not break the join.
  2. Date drift -> the row's date is rewritten and the row re-sorted into place.
  3. An upcoming row whose event no longer exists in the dataset at all is removed and
     reported loudly (month-page removals let ensure_calendar_rows re-insert at the new date).

Decided rows are never touched; they are history and mark_calendar_decided owns them.
Runs before ensure_calendar_rows in CI, so a moved event is deleted from the wrong month and
re-inserted into the right one within the same run.

    python reconcile_calendar_table.py [--dry-run]
"""
import argparse, datetime as dt, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()

STOP = {"the", "and", "with", "plus", "for", "cream", "oral", "tablet", "injection", "acid",
        "sodium", "dose", "low", "high", "gene", "therapy", "cell", "immunotherapy"}
ROW = re.compile(r'<a class="row" href="(/pdufa/[^"]+)">'
                 r'<div class="t">([A-Z]+) (?:&middot;|·) (\d{4}-\d{2}-\d{2})</div>'
                 r'<div class="d">(.*?)</div></a>', re.S)


def toks(s):
    """Name tokens, hyphenated forms AND their parts: the dataset says 'zanidatamab-hrii'
    where the row says 'zanidatamab', and treating the hyphenated form as one token made the
    first dry run flag a perfectly matched ZYME row for removal."""
    out = set()
    for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(s or "").lower()):
        parts = [w] + w.split("-")
        for p in parts:
            if len(p) >= 4 and p not in STOP and not p.isdigit():
                out.add(p)
    return out


def load_events():
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
               encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    out = []
    for r in rows:
        if (r.get("type") == "PDUFA" and r.get("dp") == "day"
                and re.match(r"^\d{4}-\d{2}-\d{2}$", str(r.get("d", "")))
                and str(r.get("st", "")).lower() != "decided"):
            out.append({"t": str(r.get("t", "")).upper(), "d": r["d"],
                        "name": re.sub(r"\s+", " ", str(r.get("name") or "")).strip(),
                        "toks": toks(r.get("name"))})
    return out


def match(events, tk, date, row_toks):
    """The dataset event this row means. Same-date candidates win outright (a row that
    already agrees must never be 'moved' to a sibling event -- the first dry run moved
    NUVL's zidesamtinib row onto its neladalkib sibling), then same-ticker by overlap."""
    cands = [(len(e["toks"] & row_toks), e) for e in events if e["toks"] & row_toks]
    if not cands:
        return None
    key = lambda c: c[0]
    same_date_tk = [c for c in cands if c[1]["d"] == date and c[1]["t"] == tk]
    if same_date_tk:
        return max(same_date_tk, key=key)[1]
    # cross-ticker overlap VALIDATES a row at the same date (dual-ticker events: the ABEO row
    # is the dataset's RARE row) but must never MOVE one -- AZN's datopotamab row shares the
    # 'deruxtecan' token with MRK's I-DXd, and the first version relocated it onto MRK's date.
    same_date_any = [c for c in cands if c[1]["d"] == date]
    if same_date_any:
        return max(same_date_any, key=key)[1]
    same_tk = [c for c in cands if c[1]["t"] == tk]
    if not same_tk:
        return "ambiguous"
    best = max(same_tk, key=key)
    # a weak single-token overlap must not relocate a row across months
    if best[0] < 2 and best[1]["d"] != date:
        return "ambiguous"
    return best[1]


def reconcile(path, events, dry):
    doc = open(path, encoding="utf-8", errors="replace").read()
    orig = doc
    moved, flagged, renamed = [], [], []
    month_scoped = bool(re.search(r"calendar[\\/]\d{4}[\\/]", path))

    def fix(m):
        href, tk, date, dtext = m.groups()
        if date < TODAY:
            return m.group(0)                      # past/decided-pending rows: not ours
        ev = match(events, tk, date, toks(re.sub(r"<[^>]+>", " ", dtext)))
        if ev is None or ev == "ambiguous":
            # Same ticker+date in the dataset but a DIFFERENT drug named on the row: the row
            # text is wrong, not the event. Found live: BBIO's row said literally 'EX-99' (a
            # filing exhibit name), NUVL's Sep 18 row named neladalkib (its Nov sibling)
            # where the dataset says zidesamtinib, INO's named the superseded VGX-3100. The
            # maintained dataset wins; the rename is reported loudly.
            samecell = [e for e in events if e["t"] == tk and e["d"] == date]
            if samecell:
                nm = samecell[0]["name"][:70]
                renamed.append(f"{tk} {date}: row said "
                               f"'{re.sub(r'<[^>]+>', '', dtext)[:40]}' -> '{nm}'")
                return (m.group(0)[:m.group(0).index('<div class="d">')]
                        + f'<div class="d">{nm}</div></a>')
            # Otherwise: page shows an event the dataset does not hold at all. Not removed --
            # the dataset may have LOST it (that is a dataset bug, not a page bug) or the
            # page may be stale; either way a human decides, loudly, not a regex.
            flagged.append(f"{tk} {date} "
                           f"({'no dataset match' if ev is None else 'ambiguous match'})")
            return m.group(0)
        if ev["d"] != date:
            # month pages are month-scoped: a cross-month move DELETES the row here and
            # ensure_calendar_rows (which runs right after in CI) re-inserts it on the right
            # month page. Same-month moves and the main /calendar page just rewrite the date.
            if month_scoped and ev["d"][:7] != date[:7]:
                moved.append(f"{tk} {date} -> {ev['d']} (moved to its new month page)")
                return ""
            moved.append(f"{tk} {date} -> {ev['d']}")
            return re.sub(rf"((?:&middot;|·) ){date}", rf"\g<1>{ev['d']}", m.group(0))
        return m.group(0)

    doc = ROW.sub(fix, doc)

    # MAIN PAGE ONLY (2026-08-13): INSERT dataset events that have no row at all. Found live:
    # the MRK/RHHBY/VTRS catalysts verified real and re-added to the dataset appeared on month
    # pages (ensure_calendar_rows) and the board, but the MAIN calendar table -- the flagship
    # surface -- gains rows from nothing. Same row markup; date order; upcoming only.
    if not month_scoped:
        # PRESENCE is markup-agnostic (2026-08-13, second attempt): row markup varies across
        # builder generations -- decorated .t divs escape the strict ROW regex, and the first
        # insert pass duplicated LNTH/JAZZ/RARE rows it claimed were absent. An event is
        # present if its ticker and date co-occur within 60 chars anywhere in the BODY (JSON-LD
        # stripped -- schema mirrors rows, it does not prove one). Inserts also respect the
        # page's own date scope: this table covers a stated window, and dumping 2027 events
        # into it re-titles the flagship page.
        body = re.sub(r"<script.*?</script>", " ", doc, flags=re.S)
        row_dates = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", body)
        max_d = max(row_dates) if row_dates else "9999"
        for ev in sorted(events, key=lambda e: e["d"]):
            if ev["d"] > max_d:
                continue                     # outside the page's stated window
            if re.search(rf"\b{ev['t']}\b[^<>]{{0,60}}{ev['d']}"
                         rf"|{ev['d']}[^<>]{{0,60}}\b{ev['t']}\b", body):
                continue                     # already on the page, whatever the markup
            if any((ev["toks"] & toks(seg)) for seg in
                   re.findall(rf"{ev['d']}</div><div class=\"d\">(.{{0,90}}?)</div>", body)):
                continue                     # dual-ticker row already covers this event
            href = f"/pdufa/{ev['t']}"
            row_html = (f'<a class="row" href="{href}"><div class="t">{ev["t"]} &middot; '
                        f'{ev["d"]}</div><div class="d">{ev["name"][:70]}</div></a>')
            # insert before the first row with a later date, else after the last row
            anchor = None
            for mrow in ROW.finditer(doc):
                if mrow.group(3) > ev["d"]:
                    anchor = mrow.start()
                    break
            if anchor is not None:
                doc = doc[:anchor] + row_html + doc[anchor:]
            else:
                last = None
                for mrow in ROW.finditer(doc):
                    last = mrow
                if last is None:
                    continue
                doc = doc[:last.end()] + row_html + doc[last.end():]
            moved.append(f"{ev['t']} {ev['d']} INSERTED (dataset event had no row)")
            body = re.sub(r"<script.*?</script>", " ", doc, flags=re.S)

    # re-sort rows inside each list container so a moved date sits in order
    def sort_container(m):
        blocks = ROW.findall(m.group(0))
        if len(blocks) < 2:
            return m.group(0)
        full = re.findall(r'<a class="row" href="/pdufa/[^"]*">.*?</a>', m.group(0), re.S)
        keyed = sorted(zip([b[2] for b in blocks], full))
        inner = m.group(0)
        for f in full:
            inner = inner.replace(f, "\x00", 1)
        for _, f in keyed:
            inner = inner.replace("\x00", f, 1)
        return inner

    doc = re.sub(r'<div class="list">(?:\s*<a class="row" href="/pdufa/.*?</a>)+',
                 sort_container, doc, flags=re.S)

    if doc != orig and not dry:
        open(path, "w", encoding="utf-8").write(doc)
    return moved, flagged, renamed


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    events = load_events()
    print(f"dataset day-precision upcoming PDUFAs: {len(events)}")

    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    tot_m = tot_r = 0
    for p in pages:
        if not os.path.exists(p):
            continue
        moved, flagged, renamed = reconcile(p, events, a.dry_run)
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        for x in moved:
            print(f"  MOVED   {rel}: {x}")
        for x in renamed:
            print(f"  RENAMED {rel}: {x}")
        for x in flagged:
            print(f"  FLAG    {rel}: {x}  (left in place -- needs a human read)")
        tot_m += len(moved) + len(renamed); tot_r += len(flagged)
    print(f"rows corrected: {tot_m}; rows flagged for review: {tot_r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
