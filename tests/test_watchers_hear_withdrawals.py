# -*- coding: utf-8 -*-
"""CI guard: the sponsor watchers hear withdrawals, goal-date extensions and refusals to file (audit 2026-10-08).

Merck withdrew the I-DXd BLA on 2026-09-25 and no watcher listened for the word. This plants the real
Merck headline against every armed (Upcoming) PDUFA row plus an Upcoming copy of the MRK row as it stood
before the withdrawal, and requires that it arms the MRK row and ONLY the MRK row. It also requires that
extension and refuse-to-file headlines are classified, and that look-alikes ("withdraws guidance",
a trial readout) are not.

    python tests/test_watchers_hear_withdrawals.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import watch_sponsor_newswire as W  # noqa: E402

MERCK = ("Ifinatamab Deruxtecan Biologics License Application for Certain Patients with Previously Treated "
         "Extensive-Stage Small Cell Lung Cancer Voluntarily Withdrawn \n The Biologics License Application (BLA) "
         "seeking accelerated approval in the U.S. for Daiichi Sankyo and Merck's ifinatamab deruxtecan (I-DXd) "
         "for the treatment of adult patients with extensive-stage small cell lung cancer has been voluntarily "
         "withdrawn.")
KINDS = [("FDA Extends PDUFA Target Action Date for Deramiocel BLA by Three Months", "extension"),
         ("Company Receives Major Amendment Notice; FDA Extends Review of NDA", "extension"),
         ("FDA Issues Refuse to File Letter for the Company's NDA", "refuse to file"),
         ("Ifinatamab Deruxtecan Biologics License Application Voluntarily Withdrawn", "withdrawal")]
DECOYS = ["Merck Withdraws 2026 Revenue Guidance Range", "Merck Announces Positive Phase 3 Results for KEYNOTE-B15",
          "Daiichi Sankyo Presents IDeate-Lung02 Enrollment Update at ESMO"]


def main():
    src = io.open(os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    mrk = next((r for r in rows if r["id"] == "pdufa_mrk_2026-10-10"), None)
    fails = []
    if not mrk:
        fails.append("dataset has no pdufa_mrk_2026-10-10 row to plant against")
    else:
        planted = dict(mrk, st="Upcoming")
        armed = [r for r in W.armed_rows(rows, None) if r["id"] != mrk["id"]] + [planted]
        hits = {r["id"] for r, _t in W.match(MERCK, armed)}
        if hits != {mrk["id"]}:
            fails.append(f"planted Merck withdrawal armed {sorted(hits) or 'nothing'}; expected only {mrk['id']}")
    for title, kind in KINDS:
        got = W.outcome_kind(title)
        if got != kind:
            fails.append(f"{title!r} classified {got!r}, expected {kind!r}")
    for title in DECOYS:
        if W.outcome_kind(title):
            fails.append(f"decoy {title!r} classified {W.outcome_kind(title)!r}")
    if fails:
        print("FAIL: the watchers do not hear the other outcomes:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- planted Merck withdrawal arms only pdufa_mrk_2026-10-10; {len(KINDS)} outcome headlines "
          f"classified, {len(DECOYS)} decoys ignored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
