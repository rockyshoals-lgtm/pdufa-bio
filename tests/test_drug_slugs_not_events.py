# -*- coding: utf-8 -*-
"""CI guard: a drug page is named for the drug, never for a trial stage or a study (2026-11-20, indexing round 3).

build_drug_pages.clean_name kept two words of a name, so "Brepocitinib Phase 3 trial" published /drug/brepocitinib-phase
("brepocitinib Phase: FDA Decision Dates") beside the real /drug/brepocitinib, and "VLU study" (a venous leg ulcer study)
and "12-week placebo-controlled" each got a drug page. 28 such pages sat in the sitemap: near-duplicates and junk titles
on a site where Google already declines to crawl 1,612 pages.

Checks:
  1. clean_name on planted names (stage tails cut, study acronyms and durations rejected, real names kept);
  2. no built /drug/ page has a slug ending -phase, -study or -trial, or starting with a duration;
  3. every page in _drug_slug_folds.json still redirects to its drug in vercel.json.

    python tests/test_drug_slugs_not_events.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_drug_pages as B  # noqa: E402

CASES = {
    "Brepocitinib Phase 3 trial": "Brepocitinib",
    "ARV-393 Phase 1": "ARV-393",
    "Lasofoxifene Phase 3 ELAINE-3": "Lasofoxifene",
    "OCU400 Phase 3 liMeliGhT": "OCU400",
    "12-week placebo-controlled study": None,
    "VLU study topline (Innovations in Wound Healing meeting)": None,
    "PhaseBio PB2452": "PhaseBio PB2452",
    "Deramiocel (CAP-1002) HOPE-3": "Deramiocel (CAP-1002)",
    "REGAL Phase 3 (galinpepimut-S) topline, event-driven": "galinpepimut-S",
    "Zanidatamab": "Zanidatamab",
    "IDOSE TR": "IDOSE TR",
    "zoldonrasib Earlier-phase CRC studies Clinical data update": "zoldonrasib",
}
BAD_SLUG = re.compile(r"-(?:phase|study|trial)$|^\d+-(?:week|day|month)s?\b")


def main():
    fails = []
    for raw, want in CASES.items():
        got = B.clean_name(raw)
        if got != want:
            fails.append(f"clean_name({raw!r}) = {got!r}, expected {want!r}")
    d = os.path.join(HERE, "pdufa_site_src", "drug")
    bad = sorted(s for s in (os.listdir(d) if os.path.isdir(d) else []) if BAD_SLUG.search(s))
    if bad:
        fails.append(f"{len(bad)} drug page(s) named for a trial stage or study: {bad[:8]}")
    # 3. every folded page still 301s to its drug (build_drug_pages.py rewrites all /drug/ redirects each run, which
    #    dropped them once, 2026-11-20).
    fp = os.path.join(HERE, "_drug_slug_folds.json")
    vj = os.path.join(HERE, "pdufa_site_src", "vercel.json")
    if os.path.exists(fp) and os.path.exists(vj):
        folds = json.load(open(fp, encoding="utf-8")).get("folds", {})
        have = {(r.get("source"), r.get("destination")) for r in json.load(open(vj, encoding="utf-8")).get("redirects", [])}
        lost = [o for o, n in folds.items() if os.path.isdir(os.path.join(d, n)) and not os.path.isdir(os.path.join(d, o))
                and ("/drug/" + o, "/drug/" + n) not in have]
        if lost:
            fails.append(f"{len(lost)} folded drug page(s) lost their redirect: {lost[:8]}")
    if fails:
        print("FAIL: drug pages named for events")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- {len(CASES)} planted names reduce to the drug; no /drug/ slug names a phase, study, trial or duration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
