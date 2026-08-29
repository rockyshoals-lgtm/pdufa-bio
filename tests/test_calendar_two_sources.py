# -*- coding: utf-8 -*-
"""test_calendar_two_sources.py -- the page's slate (data.js) and the API's dataset (dataset.mjs)
must agree on FORWARD PDUFA events.

Red team 2026-08-18, after four audits of the same count gap: "the page and the API are built
from two different files... No amount of row reconciliation will fix a two-source problem."
They're right about the mechanism: /calendar renders from the data.js SLATE, /api/v1/* serves
dataset.mjs, and nothing reconciled them. This is that reconciliation.

Scope is deliberate: FORWARD events only (today onward). The two files legitimately diverge on
the past -- the page shows decided events under their actual FDA action date while the dataset
keeps the goal date beside the outcome, and that difference is honest, not drift. The forward
window is where a divergence means a reader of the page and a consumer of the API are being told
different futures.

Match rule: exact (ticker, date) first; then same-date drug-token overlap (dual-listed events
carry one row per partner ticker: JAZZ+ZYME, PFE+ROIV); known review flags allowed. Same
family as test_calendar_matches_dataset, which reconciles the RENDERED page to the dataset --
this one reconciles the page's SOURCE to the dataset, so a divergence is caught even before a
page rebuild bakes it in.
"""
import datetime as dt, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.date.today().isoformat()


def toks(s):
    return set(re.findall(r"[a-z]{4,}", str(s or "").lower())) - {
        "with", "combination", "priority", "review", "oncology", "injection", "tablets"}


def main():
    src = open(os.path.join(SITE, "api", "data.js"), encoding="utf-8",
               errors="replace").read().replace("\x00", "")
    slate, _ = json.JSONDecoder().raw_decode(src[src.find("SLATE=") + 6:])
    cats = [c for c in slate.get("catalysts", [])
            if str(c.get("date", "")) >= TODAY]

    src2 = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                errors="replace").read().replace("\x00", "")
    ds, _ = json.JSONDecoder().raw_decode(src2[src2.find("["):])
    # "Forward" means the FDA has yet to act, not merely that the goal date is ahead. An
    # early approval leaves a decided event with a future goal date (NUVL approved 07-22
    # against a 09-18 goal; TAK 08-05 against 09-30), and the slate rightly drops those --
    # the 2026-08-29 slate sweep did exactly that and this guard, filtering on date alone,
    # demanded the page keep advertising two approved drugs as pending.
    events = [r for r in ds if r.get("type") == "PDUFA" and str(r.get("d", "")) >= TODAY
              and str(r.get("st", "")).lower() != "decided"]
    have = {(str(r.get("t", "")).upper(), str(r.get("d", ""))) for r in events}
    by_date = {}
    for r in events:
        by_date.setdefault(str(r.get("d", "")), []).append(
            (str(r.get("t", "")).upper(), toks(r.get("name"))))

    known = {(f["ticker"], f["date"]) for f in json.load(
        open(os.path.join(HERE, "_calendar_flags_known.json"), encoding="utf-8"))["flags"]}

    def covered(tk, d, drug):
        if (tk, d) in have or (tk, d) in known:
            return True
        dtoks = toks(drug)
        return any(dtoks & etoks for _, etoks in by_date.get(d, []) if etoks)

    bad = [f"data.js only: {c.get('ticker')} {c.get('date')} ({str(c.get('drug'))[:40]}) -- "
           f"the page will show an event the API denies"
           for c in cats
           if not covered(str(c.get("ticker", "")).upper(), str(c.get("date", "")),
                          c.get("drug"))]

    slate_dates = {(str(c.get("ticker", "")).upper(), str(c.get("date", ""))) for c in cats}
    slate_by_date = {}
    for c in cats:
        slate_by_date.setdefault(str(c.get("date", "")), []).append(toks(c.get("drug")))
    for r in events:
        tk, d = str(r.get("t", "")).upper(), str(r.get("d", ""))
        if (tk, d) in slate_dates or (tk, d) in known:
            continue
        if r.get("dp") and r.get("dp") != "day":
            continue                     # month/quarter placeholders never render as page rows
        ntoks = toks(r.get("name"))
        if any(ntoks & s for s in slate_by_date.get(d, []) if s):
            continue
        bad.append(f"dataset only: {tk} {d} ({str(r.get('name'))[:40]}) -- the API serves an "
                   f"event the page never shows (the dataset once LOST PFE Padcev; the reverse "
                   f"shape is a slate row the miner dropped)")

    if bad:
        print(f"FAIL: {len(bad)} forward event(s) exist in only ONE of data.js / dataset.mjs.")
        for b in bad[:10]:
            print(f"   {b}")
        print("\n   Two sources, one truth: fix the missing side (verify the event externally")
        print("   first) or add a reviewed entry to _calendar_flags_known.json.")
        return 1
    print(f"  PASS: {len(cats)} forward slate events and {len(events)} forward dataset events "
          f"reconcile ({len(known)} known flags)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
