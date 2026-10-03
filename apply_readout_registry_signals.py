# -*- coding: utf-8 -*-
"""apply_readout_registry_signals.py -- the ruling for readout leads #52 (audit 2026-10-03, item 4.6).

watch_readouts.py raises a lead when ClinicalTrials.gov contradicts a pending readout (terminated, completed,
results posted, primary completion ACTUAL in the past): 20 leads on 09-04, 33 on 10-03. A further class, the
forward readouts whose whole window has passed, is "neither reported nor visibly upcoming" (13 on 09-14,
103 on 10-03). Both needed a treatment ruling. The builder's ruling, reversible and facts-only, following the
KYTX KYSA-1 exemplar of 09-04 (the row states what the registry states, sourced to it):

  1. The registry's own status is RECORDED on the row (`_d.registry`: overall status, primary completion date
     and whether it is ACTUAL, results-posted date, checked date, the study URL). No outcome is inferred:
     "completed" is not "positive", "terminated" is not "failed".
  2. The API serves it as the row's status at request time: "Terminated per registry", "Withdrawn per
     registry", "Suspended per registry", or "Completed per registry" (status COMPLETED or primary completion
     ACTUAL in the past). A sponsor-sourced result, when recorded, wins (st=Reported is never overridden).
  3. Rows whose attached NCT record is a DIFFERENT drug's trial (_readout_ta_manual.json "nct_mismatch", 20
     rows) are excluded: a registry fact about another trial is not a fact about this row. They are acked in
     the watcher with that reason and stay listed for a hand fix of the NCT.
  4. Forward rows whose window passed with no registry signal are served "Window passed" (api/v1/_lib.mjs).

Each lead the ruling records is acked in _readout_watch_ack.json with its reason, so the watcher shows only
NEW signals. RULE 1: registry dates are calendar dates. Facts only, not investment advice.

    python apply_readout_registry_signals.py
"""
import datetime as dt
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from watch_readouts import fetch, nct_of, BAD_STATUS  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
MAN = os.path.join(HERE, "_readout_ta_manual.json")


def main():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    mism = {m["id"]: m for m in json.load(io.open(MAN, encoding="utf-8")).get("nct_mismatch", [])} \
        if os.path.exists(MAN) else {}
    ackf = json.load(io.open(ACK, encoding="utf-8")) if os.path.exists(ACK) else {"acks": []}
    acked = {a.get("id") for a in ackf.get("acks", [])}
    today = dt.date.today().isoformat()
    rec_n = mis_n = 0
    for r in rows:
        if r.get("type") != "Readout" or str(r.get("st")) not in ("Guided", "Estimated") or not nct_of(r):
            continue
        rid, nct = r["id"], nct_of(r)
        if rid in mism:
            if rid not in acked:
                ackf["acks"].append({"id": rid, "reason": (f"Ruling 2026-10-03: the row's {nct} is a different trial "
                                                           f"('{mism[rid]['registry_title'][:90]}'), not {mism[rid]['row_drug']}; "
                                                           "registry signals on it are not facts about this row. NCT needs a hand fix.")})
                acked.add(rid)
                mis_n += 1
            r.setdefault("_d", {}).pop("registry", None)
            continue
        sm = fetch(nct)
        time.sleep(0.15)
        if not sm:
            continue
        status = str(sm.get("overallStatus") or "")
        pcd = sm.get("primaryCompletionDateStruct") or {}
        reg = {"overall_status": status, "primary_completion": pcd.get("date"),
               "primary_completion_type": pcd.get("type"),
               "results_first_submitted": sm.get("resultsFirstSubmitDate"),
               "checked": today, "source_url": f"https://clinicaltrials.gov/study/{nct}"}
        signal = (status in BAD_STATUS or bool(sm.get("resultsFirstSubmitDate"))
                  or (str(pcd.get("type")) == "ACTUAL" and str(pcd.get("date", "9999"))[:10] <= today))
        d = r.setdefault("_d", {})
        if signal:
            d["registry"] = reg
            rec_n += 1
            if rid not in acked:
                ackf["acks"].append({"id": rid, "reason": (f"Ruling 2026-10-03: recorded as the registry states it "
                                                           f"({status}, primary completion {pcd.get('type')} {pcd.get('date')}); "
                                                           "served as '... per registry'; no outcome inferred.")})
                acked.add(rid)
        else:
            d.pop("registry", None)
    io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    ackf["note"] = ackf.get("note") or "Reviewed readout-watcher signals. Shrink this list; never grow it silently."
    io.open(ACK, "w", encoding="utf-8", newline="\n").write(json.dumps(ackf, indent=1, ensure_ascii=False) + "\n")
    print(f"readout registry ruling: {rec_n} row(s) carry the registry's own status; {mis_n} NCT-mismatch row(s) acked "
          f"and excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
