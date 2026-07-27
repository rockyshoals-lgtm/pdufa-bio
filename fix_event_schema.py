# -*- coding: utf-8 -*-
"""fix_event_schema.py -- make the PDUFA/readout schema.org Event objects valid for Google.

Google requires an Event to carry `startDate` and `location`. Conference Events already pass (real
venue). The /calendar Events had a real startDate but no location; the /readouts Events (and some
undated later-PDUFA calendar Events) had neither. This patches the BUILT pages (surgical, no page
regeneration, no regression) to add:
  * location  -> VirtualLocation at the event's own URL (honest: it's tracked online there)
  * eventAttendanceMode = OnlineEventAttendanceMode, eventStatus = EventScheduled
  * startDate (where missing) -> the REAL date for that catalyst, looked up from catalysts_public.csv
    (by trial/source URL, else by ticker+drug name) or dataset.mjs. No date is invented; an event that
    cannot be matched to a real date is left untouched (stays out of rich results rather than fabricate).

Also strips stray NUL bytes (encoding corruption found in readouts/index.html). Idempotent: an Event
that already has a location is skipped.

    python fix_event_schema.py [--dry-run]
"""
import argparse, csv, json, os, re

SITE = "pdufa_site_src"
CSVSRC = "catalysts_public.csv"
DS = os.path.join(SITE, "api", "v1", "dataset.mjs")
MODE = '"eventAttendanceMode":"https://schema.org/OnlineEventAttendanceMode"'
STAT = '"eventStatus":"https://schema.org/EventScheduled"'
PAGES = ["calendar/index.html", "readouts/index.html"]

EV_DATED = re.compile(r'\{"@type":"Event",("name":"(?:[^"\\]|\\.)*","url":"([^"]*)","startDate":"[^"]*")\}')
EV_BARE = re.compile(r'\{"@type":"Event",("name":"((?:[^"\\]|\\.)*)","url":"([^"]*)")\}')
DASH = "—"


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def loc(url):
    return f'"location":{{"@type":"VirtualLocation","url":"{url}"}}'


def load_dates():
    """Return (url2date, name2date, tickeridx). Dates are the same values the pages already display."""
    url2d, name2d, tickeridx = {}, {}, {}
    # dataset.mjs
    try:
        src = open(DS, encoding="utf-8", errors="replace").read().replace("\x00", "")
        arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
        for r in arr:
            d = r.get("d")
            if not d:
                continue
            if r.get("url"):
                url2d.setdefault(r["url"], d)
            nm = norm(str(r.get("t", "")) + str(r.get("name", "")))
            if nm:
                name2d.setdefault(nm, d)
    except Exception as e:
        print("  (dataset.mjs parse skipped:", e, ")")
    # catalysts_public.csv (the fuller source the pages were built from)
    if os.path.exists(CSVSRC):
        for r in csv.DictReader(open(CSVSRC, encoding="utf-8", errors="ignore")):
            d = (r.get("catalyst_date") or "").strip()
            if not d:
                continue
            u = (r.get("source_url") or "").strip()
            if u:
                url2d.setdefault(u, d)
            tk, drug = norm(r.get("ticker", "")), norm(r.get("drug", ""))
            if tk:
                name2d.setdefault(tk + drug, d)
                tickeridx.setdefault(tk, []).append((drug, d))
    return url2d, name2d, tickeridx


def lookup(url, name, url2d, name2d, tickeridx):
    if url in url2d:
        return url2d[url]
    m = re.search(r'(NCT\d+)', url or "")           # trial id inside a clinicaltrials URL
    if m:
        for k, v in url2d.items():
            if m.group(1) in k:
                return v
    left, _, right = (name or "").partition(DASH)   # "TICKER — DRUG"
    tk, drug = norm(left), norm(right.replace("…", ""))
    if tk + drug in name2d:
        return name2d[tk + drug]
    for cdrug, d in tickeridx.get(tk, []):           # tolerate truncated / code-prefixed names
        if drug and cdrug and (cdrug in drug or drug in cdrug):
            return d
    return None


def fix_page(path, url2d, name2d, tickeridx, dry):
    raw = open(path, encoding="utf-8", errors="replace").read()
    nul = raw.count("\x00")
    html = raw.replace("\x00", "")
    stats = {"loc_only": 0, "dated": 0, "unmatched": 0}

    def dated(m):  # has startDate, missing location
        body, url = m.group(1), m.group(2)
        if '"location"' in body:
            return m.group(0)
        stats["loc_only"] += 1
        return '{"@type":"Event",' + body + f',{MODE},{STAT},{loc(url)}}}'

    def bare(m):   # missing both startDate and location
        body, name, url = m.group(1), m.group(2), m.group(3)
        if '"location"' in body:
            return m.group(0)
        d = lookup(url, name, url2d, name2d, tickeridx)
        if not d:
            # No honest date available -> demote from Event to WebPage so it's not an INVALID Event
            # (a plain page link, valid schema, just not rich-result eligible). Never fabricate a date.
            stats["unmatched"] += 1
            return '{"@type":"WebPage",' + body + '}'
        stats["dated"] += 1
        return '{"@type":"Event",' + body + f',"startDate":"{d}",{MODE},{STAT},{loc(url)}}}'

    html = EV_DATED.sub(dated, html)
    html = EV_BARE.sub(bare, html)
    if (stats["loc_only"] or stats["dated"] or nul) and not dry:
        open(path, "w", encoding="utf-8").write(html)
    return stats, nul


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    url2d, name2d, tickeridx = load_dates()
    print(f"date sources: {len(url2d)} urls, {len(name2d)} name keys")
    for page in PAGES:
        p = os.path.join(SITE, page)
        if not os.path.exists(p):
            continue
        s, nul = fix_page(p, url2d, name2d, tickeridx, a.dry_run)
        print(f"{'DRY ' if a.dry_run else ''}{page:22s} +location(dated){s['loc_only']:4d}  "
              f"+startDate&location{s['dated']:4d}  unmatched(left){s['unmatched']:4d}  NUL_stripped{nul:6d}")


if __name__ == "__main__":
    main()
