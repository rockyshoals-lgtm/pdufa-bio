# -*- coding: utf-8 -*-
"""CI guard: an Estimated readout row's month window equals the registry's primary-completion month that
the build itself recorded on the row (audit 2026-10-11, live P1).

/readouts defines an estimated date as "the registry's primary-completion window". On 10-11, 12 rows said
"Estimated {month}" for windows ClinicalTrials.gov had replaced weeks earlier (MBX May 2027 vs registry May
2028; GOSS Dec 2027 vs a trial terminated Sep 2026), because refresh_readout_registry.py was never in the
daily chain while apply_readout_registry_signals.py recorded the registry's status without moving the date.
Both now run in the chain, refresh first. This reads the dataset and fails when an Estimated row carries a
`_d.registry.primary_completion` whose month differs from the row's `dm`. Rows whose attached NCT is a
different drug's trial (_readout_ta_manual.json "nct_mismatch") are excluded, as both scripts exclude them.

Plant: PLANT_DRIFT=1 shifts one row's dm in memory and must produce a FAIL.

    python tests/test_readout_registry_synced.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MAN = os.path.join(HERE, "_readout_ta_manual.json")


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    mism = set()
    if os.path.exists(MAN):
        mism = {m["id"] for m in json.load(io.open(MAN, encoding="utf-8")).get("nct_mismatch", [])}
    fails, n = [], 0
    planted = os.environ.get("PLANT_DRIFT") == "1"
    for r in rows:
        if r.get("type") != "Readout" or str(r.get("st") or "") != "Estimated" or r.get("id") in mism:
            continue
        reg = (r.get("_d") or {}).get("registry") or {}
        pc = str(reg.get("primary_completion") or "")
        if len(pc) < 7 or str(r.get("dp") or "") not in ("month", "quarter", "year", ""):
            continue
        n += 1
        dm = str(r.get("dm") or str(r.get("d") or "")[:7])
        if planted and n == 1:
            dm = "1999-01"
            planted = False
        if dm != pc[:7]:
            fails.append(f"{r.get('id')}: dm {dm} but the registry's primary completion recorded on the row "
                         f"is {pc} ({reg.get('primary_completion_type')}, checked {reg.get('checked')})")
    if fails:
        print(f"FAIL: {len(fails)} Estimated readout row(s) whose window has drifted from the registry:")
        for f in fails[:25]:
            print("   " + f)
        return 1
    print(f"OK -- {n} Estimated readout rows carry the month their recorded registry primary-completion date states.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
