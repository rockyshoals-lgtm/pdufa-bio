# -*- coding: utf-8 -*-
"""CI guard: an upcoming "Estimated" readout date must come from a named ClinicalTrials.gov record.

WHY (red team 2026-11-17)
/readouts calls an Estimated date "the trial's registry window" -- ClinicalTrials.gov's primary
completion month. On 2026-11-17, 60 of 154 upcoming Estimated rows had no trial at all: no NCT
number, no source link, a bare drug name ("Nivolumab", "Pembrolizumab", "Clinical readout") and a
month that nobody could trace (rows created 2026-07-11). A reader cannot check such a date, and a
red-team search of the registry found no company-sponsored trial completing in that month for most
of them. A date with no source is not a fact, so it does not get published.

THE INVARIANT. Every Readout row with st "Estimated" whose date has not passed:
  1. carries `_d.nct_id.nct` (NCT + 8 digits);
  2. links that record (`_d.source_url` or `url` is clinicaltrials.gov/study/<that NCT>);
  3. is dated in the registry's primary-completion month (`d[:7] == _d.nct_id.pcd[:7]`).
Registry drift (the registry moved, we did not) is test_readout_registry_synced's job; this guard is
about having a registry record at all.

    python tests/test_estimated_readouts_registry_backed.py
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")


def eastern_today():
    try:
        from site_dates import eastern_today as et
        return et()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def check(rows, today):
    fails = []
    for r in rows:
        if r.get("type") != "Readout" or r.get("st") != "Estimated" or r.get("d", "") < today.isoformat():
            continue
        d = r.get("_d") or {}
        n = d.get("nct_id") or {}
        nct = n.get("nct") if isinstance(n, dict) else None
        why = []
        if not (nct and re.fullmatch(r"NCT\d{8}", nct)):
            why.append("no ClinicalTrials.gov record (no NCT)")
        else:
            links = " ".join(str(x or "") for x in (d.get("source_url"), r.get("url")))
            if f"clinicaltrials.gov/study/{nct}" not in links:
                why.append(f"does not link clinicaltrials.gov/study/{nct}")
            pcd = str(n.get("pcd") or "")
            if pcd[:7] != str(r.get("d"))[:7]:
                why.append(f"dated {r.get('d')} but the registry's primary completion is {pcd or 'missing'}")
        if why:
            fails.append(f"{r['id']} [{r.get('t')}] {r.get('name')!r} {r.get('d')}: " + "; ".join(why))
    return fails


def self_test():
    t = dt.date(2026, 11, 18)
    bad = [{"id": "a", "t": "X", "type": "Readout", "st": "Estimated", "d": "2026-12-15", "name": "Nivolumab",
            "_d": {"nct_id": None}},
           {"id": "b", "t": "X", "type": "Readout", "st": "Estimated", "d": "2026-12-15", "url": "/ticker/X",
            "_d": {"nct_id": {"nct": "NCT01234567", "pcd": "2027-02"}}}]
    good = [{"id": "c", "t": "X", "type": "Readout", "st": "Estimated", "d": "2026-12-15",
             "url": "https://clinicaltrials.gov/study/NCT01234567",
             "_d": {"nct_id": {"nct": "NCT01234567", "pcd": "2026-12"}}}]
    ok = len(check(bad, t)) == 2 and not check(good, t)
    if not ok:
        print("SELF-TEST FAILED")
    return ok


def main():
    if not self_test():
        return 1
    src = io.open(DATASET, encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    fails = check(rows, eastern_today())
    if fails:
        print(f"FAIL: {len(fails)} upcoming Estimated readout(s) not backed by a ClinicalTrials.gov record "
              f"(add the NCT the date comes from, or take the row out):")
        for f in fails[:80]:
            print("   " + f)
        return 1
    print("OK -- every upcoming Estimated readout is dated from a linked ClinicalTrials.gov record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
