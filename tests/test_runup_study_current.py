# -*- coding: utf-8 -*-
"""test_runup_study_current.py -- the run-up study must keep up with the decision archive.

The study went stale once already: it sat at PDUFA date 2026-02-21 while the archive kept growing,
and nobody noticed for months because nothing was checking. Automating the extension is only half
a fix; if the Action's study step starts failing, the number silently freezes again exactly as
before. This guard is the other half.

Checks:
  1. Every decision in the published archive older than GRACE days is present in the study.
     (New decisions get a grace window: post-decision price history has to exist before an event
     can be measured honestly.)
  2. runup_study_stats.json agrees with the CSV it claims to summarise. If these disagree, pages
     are quoting a statistic computed from a different dataset than the one we ship.
  3. Published pages quote the same event count as the dataset.

    python tests/test_runup_study_current.py
"""
import csv, json, os, re, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
STATS = os.path.join(HERE, "runup_study_stats.json")
DECISIONS = os.path.join(SITE, "decisions", "index.html")

GRACE_DAYS = 10          # a decision needs a few sessions of post-event prices to be measurable
ALLOW_UNMEASURABLE = 30  # tickers legitimately without usable price history (halted, delisted, ADR)


def main():
    ok = True
    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    have = {(r["ticker"].strip().upper(), r["pdufa_date"][:10]) for r in rows}
    print(f"study: {len(rows):,} events, latest {max(r['pdufa_date'][:10] for r in rows)}")

    html = open(DECISIONS, encoding="utf-8", errors="replace").read()
    arch = {(m.group(1), m.group(2))
            for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html)}
    cutoff = (dt.date.today() - dt.timedelta(days=GRACE_DAYS)).isoformat()
    due = {k for k in arch if k[1] <= cutoff}
    missing = sorted(due - have, key=lambda x: x[1])

    print(f"archive: {len(arch):,} decisions, {len(due):,} past the {GRACE_DAYS}-day grace window")
    if len(missing) > ALLOW_UNMEASURABLE:
        ok = False
        print(f"\nFAIL: {len(missing)} decided PDUFAs are missing from the study "
              f"(tolerance {ALLOW_UNMEASURABLE}). The study step is not keeping up.")
        for tk, d in missing[:15]:
            print(f"   {tk:6s} {d}")
        if len(missing) > 15:
            print(f"   ... and {len(missing) - 15} more")
        print("   fix: python extend_runup_study.py && python add_t120_baseline.py "
              "&& python runup_study_stats.py")
    else:
        print(f"  PASS: study current ({len(missing)} unmeasurable, within tolerance)")

    stats = json.load(open(STATS, encoding="utf-8"))
    if stats.get("n_events") != len(rows):
        ok = False
        print(f"\nFAIL: runup_study_stats.json says n_events={stats.get('n_events')} but the CSV "
              f"has {len(rows)}. Published figures were computed from a different dataset.")
        print("   fix: python runup_study_stats.py")
    else:
        print(f"  PASS: stats file agrees with the dataset ({len(rows):,} events)")

    # published pages must not quote a stale count
    n = f"{len(rows):,}"
    bad = []
    for page in ("index.html", os.path.join("runup-by-year", "index.html")):
        p = os.path.join(SITE, page)
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"([\d,]{4,9})(?=\s*(?:</b>)?\s*<?[^>]*>?\s*(?:PDUFA )?events in the run-up study|"
                             r"\s*PDUFA events</b>)", t):
            if m.group(1) != n:
                bad.append((page, m.group(1)))
    if bad:
        ok = False
        print(f"\nFAIL: page(s) quoting a stale study size (dataset has {n}):")
        for page, got in bad:
            print(f"   {page}: {got}")
        print("   fix: python build_home_board.py && python build_runup_by_year.py")
    else:
        print(f"  PASS: published pages quote {n} events")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
