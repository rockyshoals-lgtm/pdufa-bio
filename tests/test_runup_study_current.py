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
  4. (2026-11-18) Every row with a decision page is eligible (primary-sourced approval or CRL, not listed in
     runup_study_exclusions.json), carries that page's drug and outcome, and no price event is counted twice.
     One FDA action (same ticker, Drugs@FDA application and action date) is one row too.
     Plants: PLANT_RUNUP_STUDY=label and =mislabel (a "label corrected" page counted as a CRL) must FAIL.
  5. (2026-11-18) Each decision page's "120-day run-up (T-120→T-1)" and "Decision-day move" figures are the study's
     figures for that event (sync_decision_runup_chip.py), and no page shows the retired "low→high" chip.
     Plant: PLANT_RUNUP_STUDY=chip must FAIL.

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
    # 2026-11-18: only primary-sourced decisions belong in the study (runup_study_events.eligibility), and a row
    # curate_runup_study.py removed with a reason (runup_study_excluded.csv) is accounted for, not missing.
    sys.path.insert(0, HERE)
    from runup_study_events import decision_facts, eligibility, excluded_keys, load_exclusions
    excl, gone = load_exclusions(), excluded_keys("same ")   # a second page of one FDA action or price event
    facts = {k: decision_facts(*k) for k in arch}
    elig = {k for k in arch if eligibility(k[0], k[1], facts[k], excl)[0]
            and f"{k[0]}_{k[1].replace('-', '')}" not in gone}
    due = {k for k in elig if k[1] <= cutoff}
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

    # 2026-11-18: every study row with a decision page is eligible, carries that page's drug and outcome, and no
    # price event is counted twice. The extender once labelled every new row with the ticker's FIRST dataset row
    # (GSK's Nov 17 neladalkib approval read "tebipenem") and counted unverified, price-inferred pages as approvals.
    bad_rows, eve_seen, act_seen, dupes = [], {}, {}, []
    for r in rows:
        tk, d = r["ticker"].strip().upper(), r["pdufa_date"][:10]
        f = decision_facts(tk, d)
        if os.environ.get("PLANT_RUNUP_STUDY") == "mislabel" and (tk, d) == ("GSK", "2026-11-17"):
            f = decision_facts("EQ", "2025-03-27")   # a page that says its own CRL label was wrong
        if f and f.get("fda_action"):
            ka = (tk,) + f["fda_action"]
            if ka in act_seen:
                dupes.append(f"{tk} {d} and {act_seen[ka]}: same FDA action {ka[1]} {ka[2]}")
            act_seen[ka] = d
        row_ok, why = eligibility(tk, d, f, excl)   # not `ok`: that is the guard's overall verdict
        if not row_ok:
            bad_rows.append(f"{tk} {d}: in the study but {why}")
        elif f:
            if f["drug"] and r.get("asset", "") != f["drug"]:
                bad_rows.append(f"{tk} {d}: study says '{r.get('asset', '')[:40]}', page says '{f['drug'][:40]}'")
            if f["outcome"] in ("APPROVAL", "CRL") and r.get("outcome") != f["outcome"]:
                bad_rows.append(f"{tk} {d}: study outcome {r.get('outcome')}, page outcome {f['outcome']}")
        k = (tk, (r.get("eve_date") or "")[:10])
        if k[1] and k in eve_seen:
            dupes.append(f"{tk} {d} and {eve_seen[k]}: same eve close {k[1]}")
        eve_seen[k] = d
    if os.environ.get("PLANT_RUNUP_STUDY") == "label":
        bad_rows.append("PLANT: GSK 2026-11-17 study says 'Tebipenem HBr', page says 'Nelkarmi (neladalkib)'")
    if bad_rows or dupes:
        ok = False
        print(f"\nFAIL: {len(bad_rows)} study row(s) disagree with their decision page, {len(dupes)} double-counted:")
        for x in (bad_rows + dupes)[:20]:
            print(f"   {x}")
        print("   fix: python curate_runup_study.py && python runup_study_stats.py")
    else:
        print("  PASS: every study row matches its decision page (drug, outcome, eligibility); no event counted twice")

    # 2026-11-18: a decision page's run-up and decision-day figures are the study's (sync_decision_runup_chip.py).
    # 306 pages showed an old "T-120 run-up (low→high)" figure that matched neither its own price range nor the study
    # (LLY Jan 15, 2025: "+1.0% ($725.72→$932.06)").
    import glob as _g
    from sync_decision_runup_chip import OLD_CHIP, RUN_CHIP, DAY_CHIP, expected, study_figures
    fig, chip_bad = study_figures(), []
    for p in sorted(_g.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        tk, d = slug.split("-", 1)
        doc = open(p, encoding="utf-8", errors="replace").read()
        if os.environ.get("PLANT_RUNUP_STUDY") == "chip" and slug == "LLY-2025-01-15":
            doc = doc.replace("<span>120-day run-up (T-120→T-1)</span><b>", "<span>120-day run-up (T-120→T-1)</span><b>+1.0")
        run, day = expected(fig, tk, d)
        if OLD_CHIP.search(doc):
            chip_bad.append(f"/fda-decision/{slug}: still shows the old low-high run-up chip")
        m = RUN_CHIP.search(doc)
        if m and run is not None and not doc[m.end(1):].startswith(run + "</b>"):
            chip_bad.append(f"/fda-decision/{slug}: run-up chip differs from the study ({run})")
        m = DAY_CHIP.search(doc)
        if m and day is not None and not doc[m.end(1):].startswith(day + "</b>"):
            chip_bad.append(f"/fda-decision/{slug}: decision-day move differs from the study ({day})")
    if chip_bad:
        ok = False
        print(f"\nFAIL: {len(chip_bad)} decision page figure(s) disagree with the run-up study:")
        for x in chip_bad[:15]:
            print(f"   {x}")
        print("   fix: python sync_decision_runup_chip.py")
    else:
        print("  PASS: every decision page's run-up and decision-day figures are the study's")

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
