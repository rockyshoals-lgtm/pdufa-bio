# -*- coding: utf-8 -*-
"""CI guard: the EDGAR 8-K poll finds a real approval 8-K and ignores acceptance language (audit 2026-10-03, 2.4).

Replays sentences from Arvinas's 8-K EX-99.1 of 2026-05-01 (accession 0001628280-26-029210, the VEPPANU
approval, which reached pdufa.bio through a different path) against the row as it stood before the decision,
and two non-decision sentences shaped like every acceptance release. Also fails when an armed sponsor with a
goal in the next 60 days has neither an own channel (feed or EDGAR poll) nor a recorded reason in
_sponsor_coverage.json (the order's acceptance: "a working feed, an EDGAR poll, or a recorded reason").

    python tests/test_edgar_8k_replay.py
"""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import watch_edgar_8k as E  # noqa: E402

ROW = {"id": "pdufa_arvn_2026-06-05", "t": "ARVN", "type": "PDUFA", "st": "Upcoming", "d": "2026-06-05",
       "name": "Vepdegestrant - (VERITAC-2)", "_d": {"indication": "ESR1m ER+/HER2- advanced breast cancer"}}
REAL = ("Food and Drug Administration (FDA) has granted approval for VEPPANU (vepdegestrant) for the treatment of "
        "adults with estrogen receptor- positive (ER+)/human epidermal growth factor receptor 2-negative (HER2-), "
        "estrogen receptor 1 (ESR1)-mutated advanced or metastatic breast cancer.")
NOISE = ("The FDA has accepted the New Drug Application for vepdegestrant and assigned a PDUFA target action date of "
         "June 5, 2026. If approved, vepdegestrant would be the first PROTAC therapy.")


def main():
    fails = []
    hits = E.leads_in("Arvinas Announces. " + REAL, [ROW])
    if len(hits) != 1:
        fails.append(f"real approval sentence produced {len(hits)} lead(s), expected 1")
    if E.leads_in(NOISE, [ROW]):
        fails.append("acceptance / 'if approved' language produced a lead")
    p = os.path.join(HERE, "_sponsor_coverage.json")
    if not os.path.exists(p):
        fails.append("_sponsor_coverage.json missing (run watch_edgar_8k.py)")
    else:
        cov = json.load(io.open(p, encoding="utf-8"))
        for tk, c in cov.get("sponsors", {}).items():
            own = {"sponsor_feed", "edgar_8k"} & set(c.get("channels", []))
            if not own and not c.get("reason_no_own_channel"):
                fails.append(f"{tk}: armed goal {c.get('goals')} with no feed, no EDGAR poll and no recorded reason")
        if "MRK" in cov.get("sponsors", {}) and "edgar_8k" not in cov["sponsors"]["MRK"]["channels"]:
            fails.append("MRK is not covered by the EDGAR 8-K poll")
    if fails:
        print(f"FAIL: {len(fails)} EDGAR-poll failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- VEPPANU 8-K replays to 1 lead, acceptance language to 0; every armed sponsor has a channel or a reason.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
