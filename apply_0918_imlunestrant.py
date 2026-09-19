# -*- coding: utf-8 -*-
"""FDA approved imlunestrant (Inluriyo) with abemaciclib (Verzenio) on 2026-09-18.

Read first-hand from the FDA's own approval notification before writing:

  "On September 18, 2026, the Food and Drug Administration approved imlunestrant (Inluriyo) in
   combination with abemaciclib (Verzenio), for adults with estrogen receptor (ER)-positive,
   human epidermal growth factor receptor 2 (HER2)-negative, estrogen receptor 1 (ESR1)-mutated
   advanced or metastatic breast cancer..."  -- based on EMBER-3.

We did not carry this as an upcoming PDUFA: Lilly never published a goal date for the supplement,
and our corpus had no row for it. So the row is recorded the way every other approval we did not
pre-track is recorded -- the action date is the sourced fact -- and it is explicitly marked
`goal_unsourced` so it cannot enter the decision-timing statistic as a punctuality measurement.
That is the rule written today after the same shape was found in the MRK and OTSKY rows.

`/drug/inluriyo` already exists for the September 2025 original approval and says "1 FDA decision
on record"; regenerating the drug pages picks this up as the second.

    python apply_0918_imlunestrant.py [--dry-run]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
FDA = ("https://www.fda.gov/drugs/resources-information-approved-drugs/"
       "fda-approves-imlunestrant-combination-abemaciclib-er-positive-her2-negative-esr1-mutated-advanced-or")
ROW_ID = "pdufa_lly_2026-09-18"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    # VERIFY BEFORE WRITING
    raw = urllib.request.urlopen(urllib.request.Request(FDA, headers=UA), timeout=70).read()
    t = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace"))))
    m = re.search(r"On September 18, 2026, the Food and Drug Administration approved imlunestrant[^.]*\.", t)
    if not m:
        print("FDA page does not carry the expected approval sentence -- NOTHING WRITTEN")
        return 1
    quote = m.group(0).strip()
    print("verified:", quote[:220], "...")

    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    if any(r["id"] == ROW_ID for r in rows):
        print(f"{ROW_ID} already present -- nothing to do")
        return 0

    row = {
        "id": ROW_ID, "t": "LLY", "company": "Eli Lilly and Company",
        "d": "2026-09-18", "dp": "day", "dm": "2026-09",
        "name": "Inluriyo (imlunestrant) + Verzenio (abemaciclib) - (EMBER-3)",
        "type": "PDUFA", "ta": "Oncology", "cap": "Large", "st": "Decided",
        "url": "/pdufa/LLY",
        "ua": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "_d": {
            "indication": ("ER-positive, HER2-negative, ESR1-mutated advanced or metastatic breast "
                           "cancer, in combination with abemaciclib"),
            "source": "FDA approval notification 2026-09-18 (CDER)",
            "source_url": FDA,
            "source_quote": quote[:400],
            "goal_unsourced": True,
            "goal_note": ("Lilly published no PDUFA goal date for this supplement and we carried no "
                          "row for it before the approval, so the date here is the FDA's action "
                          "date. It is excluded from the decision-timing statistic, which measures "
                          "action against a sponsor-stated goal."),
            "review": ("Label expansion for Inluriyo, originally approved 2025-09-25 as monotherapy "
                       "(NDA 218881). The combination approval with Verzenio (abemaciclib) rests on "
                       "the Phase 3 EMBER-3 trial."),
        },
        "oc": "Approved", "dcd": "2026-09-18",
    }
    rows.append(row)
    rows.sort(key=lambda r: (str(r.get("d") or ""), str(r.get("id"))))
    if not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    print(f"added {ROW_ID}  Approved 2026-09-18, goal_unsourced (no sponsor goal date published)"
          + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
