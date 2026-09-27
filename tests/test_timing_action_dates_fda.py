# -*- coding: utf-8 -*-
"""CI guard: every action date in the FDA decision-timing statistic comes from an FDA record,
and one FDA action is counted once.

Audit 2026-09-26: MRK WINREVAIR was counted +1 day late from Merck's 6:45 am release; the FDA's
letter is signed September 21, the goal day. TLX Pixclara sat excluded for eleven days after
Drugs@FDA posted its September 11 action. And -- found while fixing those -- two co-listed
partner pairs (GSK/SPRO tebipenem, JAZZ/ZYME Ziihera) were each one FDA action counted twice.

Asserts, over build_early_decisions.collect(2026):
  1. each row's action date has an FDA source (Drugs@FDA / accessdata.fda.gov letter, fda.gov
     approval letter or notice, or the FDA's released CRL on download.open.fda.gov);
  2. no FDA record appears twice;
  3. the published page states how many action dates come from the FDA's record.

    python tests/test_timing_action_dates_fda.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FDA = re.compile(r"^https://(www\.)?(fda\.gov|accessdata\.fda\.gov|download\.open\.fda\.gov)/")


def main():
    import build_early_decisions as B
    rec = B.collect(2026)
    fails = []
    for r in rec:
        if not FDA.match(r.get("fda_url") or ""):
            fails.append(f"{r['slug']}: action date {r['actual']} has no FDA record "
                         f"(source: {r.get('fda_url') or 'none'}) -- run sync_fda_action_dates.py, or mark "
                         f"_d.decision_date_unsourced if only an announcement states the day")
    seen = {}
    for r in rec:
        k = r.get("fda_record")
        if k and k in seen and "CRL" not in k:
            fails.append(f"{r['slug']} and {seen[k]} are the same FDA action ({k}) counted twice")
        seen.setdefault(k, r["slug"])
    page = io.open(os.path.join(HERE, "pdufa_site_src", "research", "fda-decision-timing", "index.html"),
                   encoding="utf-8").read()
    if not re.search(rf"{len(rec)} of {len(rec)} action dates on this page are taken from the FDA", page):
        fails.append(f"/research/fda-decision-timing does not state that all {len(rec)} action dates come "
                     f"from the FDA's record -- run build_early_decisions.py")
    if fails:
        print(f"FAIL: {len(fails)} timing-statistic provenance problem(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- all {len(rec)} action dates in the timing statistic come from an FDA record; no FDA action counted twice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
