# -*- coding: utf-8 -*-
"""sync_decision_runup_chip.py -- each decision page's run-up figures are the run-up study's figures for that event.

Found 2026-11-18: 306 of 336 /fda-decision pages carried a "T-120 run-up (low→high)" chip whose percentage did not
match its own price range (LLY Jan 15, 2025: "+1.0% ($725.72→$932.06)", a 28% range), and matched neither the study's
T-120-to-eve nor its T-120-to-peak figure. The chip came from the old app's whole-number field and was never
recomputed. The 159 newer pages carry "120-day run-up (T-120→T-1)" from build_decision_page.py's own price window,
anchored on the decision day rather than the eve, and 147 of them differ from the study by up to several points.
The run-up study (pdufa_runup_bifrost_v2.csv) is the one measurement of these events; this step writes its figures
onto every page, in one vocabulary:

    120-day run-up (T-120→T-1)   -15.2%   (study T-120_T-1: close 120 sessions before the eve, to the eve)
    Decision-day move            +0.2%    (study post_1d: first session on/after the decision vs the eve)

A page with the old chip whose event is not in the study (unverified, excluded, or not measurable) loses that chip
rather than keep a figure nobody measured; a newer page not in the study keeps its own measured figure. Runs after
runup_study_stats.py and before build_decision_faq.py (which quotes these chips), every rebuild. Idempotent.
tests/test_runup_study_current.py fails if a page's figures differ from the study.

    python sync_decision_runup_chip.py [--dry-run]
"""
import argparse
import csv
import glob
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")

OLD_CHIP = re.compile(r'<div class="kv"><span>T-120 run-up \(low→high\)</span><b>[^<]*</b></div>')
RUN_CHIP = re.compile(r'(<div class="kv"><span>120-day run-up \(T-120→T-1\)</span><b>)[^<]*(</b></div>)')
DAY_CHIP = re.compile(r'(<div class="kv"><span>Decision-day move</span><b>)[^<]*(</b></div>)')


def fnum(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def study_figures():
    out = {}
    for r in csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")):
        t1, pk, d1 = fnum(r.get("T-120_T-1")), fnum(r.get("T-120_peak")), fnum(r.get("post_1d"))
        out[(r["ticker"].strip().upper(), r["pdufa_date"][:10])] = (t1, pk, d1)
    return out


def run_text(t1):
    return f"{t1 * 100:+.1f}%"


def day_text(d1):
    return f"{d1:+.1f}%"


def expected(fig, tk, d):
    """(run-up chip value, decision-day value) the page must show, each None when the study has no figure."""
    t1, _pk, d1 = fig.get((tk, d), (None, None, None))
    return (run_text(t1) if t1 is not None else None), (day_text(d1) if d1 is not None else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fig = study_figures()
    changed = removed = day_fixed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        pid = os.path.basename(os.path.dirname(p))
        tk, d = pid.split("-", 1)
        doc = open(p, encoding="utf-8").read()
        new = doc
        run, day = expected(fig, tk, d)
        if OLD_CHIP.search(new):
            if run is None:
                new = OLD_CHIP.sub("", new)
                removed += 1
            else:
                new = OLD_CHIP.sub(f'<div class="kv"><span>120-day run-up (T-120→T-1)</span><b>{run}</b></div>', new)
        if run is not None and RUN_CHIP.search(new):
            new = RUN_CHIP.sub(lambda m: m.group(1) + run + m.group(2), new)
        if day is not None and DAY_CHIP.search(new):
            nd = DAY_CHIP.sub(lambda m: m.group(1) + day + m.group(2), new)
            day_fixed += nd != new
            new = nd
        if new != doc:
            changed += 1
            if not a.dry_run:
                with open(p, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new)
    print(f"decision pages: {changed} updated ({removed} old low-high chips removed: event not in the study; "
          f"{day_fixed} decision-day moves corrected){' DRY RUN' if a.dry_run else ''}")


if __name__ == "__main__":
    main()
