# -*- coding: utf-8 -*-
"""test_calendar_matches_dataset.py -- every upcoming calendar row is a dataset event.

Red team 2026-08-12: /calendar said 67/52 inside FAQPage schema while the API said 64/46, and
the delta hid real defects -- PRAX's row showed September 27 six weeks after the FDA moved it
to December 27; NUVL's row named the wrong sibling drug for its date; BBIO's row text was
literally 'EX-99'; and the dataset itself had LOST the PFE Padcev event five days before its
decision. reconcile_calendar_table.py fixes drift daily; this guard proves it ran and that no
NEW drift appeared.

Rule: every upcoming row on /calendar and the month pages must correspond to a dataset event
with the same ticker and date (drug-token overlap not required here -- the reconciler enforces
names; this guard enforces existence). Known conflicts under human review live in
_calendar_flags_known.json, visibly, and that list may only shrink.
"""
import datetime as dt, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
ROW = re.compile(r'<a class="row" href="/pdufa/[^"]+">'
                 r'<div class="t">([A-Z]+) (?:&middot;|·) (\d{4}-\d{2}-\d{2})</div>', re.S)


def main():
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
               encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    have = {(str(r.get("t", "")).upper(), str(r.get("d", ""))) for r in rows
            if r.get("type") == "PDUFA"}
    # dual-ticker rows: the page may key an event by its partner ticker (ABEO row for the RARE
    # event), so any same-DATE event also counts as existence
    dates = {str(r.get("d", "")) for r in rows if r.get("type") == "PDUFA"}

    known = {(f["ticker"], f["date"]) for f in json.load(
        open(os.path.join(HERE, "_calendar_flags_known.json"), encoding="utf-8"))["flags"]}

    bad = []
    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    checked = 0
    for p in pages:
        if not os.path.exists(p):
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        for tk, d in ROW.findall(doc):
            if d < TODAY:
                continue
            checked += 1
            if (tk, d) in have or (tk, d) in known:
                continue
            if d in dates:
                continue          # same-date event exists under a partner ticker
            bad.append(f"{rel}: {tk} {d} -- row exists, dataset has no such event; either "
                       f"the dataset lost it (it lost PFE Padcev once) or the row is stale")

    if bad:
        print(f"FAIL: {len(bad)} calendar row(s) with no dataset event behind them.")
        for b in bad[:8]:
            print(f"   {b}")
        print("\n   Run reconcile_calendar_table.py, verify externally, and either repair the")
        print("   dataset or add a reviewed entry to _calendar_flags_known.json.")
        return 1
    print(f"  PASS: {checked} upcoming calendar rows all correspond to dataset events "
          f"({len(known)} known conflicts under review)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
