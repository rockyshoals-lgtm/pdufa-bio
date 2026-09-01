# -*- coding: utf-8 -*-
"""A published decision must never leave its dataset event marked Upcoming.

David's question (2026-09-01): do we catch approvals that land BEFORE the goal date?
The FDA deciding early is the NORM (16 of 28 sourced 2026 decisions came early; REGN
-12d, AZN -18d, TAK -56d, NUVL -58d, CORT -108d), but sync_api_from_pages matched only
within 14 days, so anything earlier depended on a human noticing. The sync now carries a
wide evidence-gated window; this guard asserts the RESULT, so the safeguard survives
even if the CI step is reordered or dropped -- the frozen-family lesson.

Uses the sync's own matcher functions (one source of the rule): for every Upcoming
day-precision PDUFA row, no published decision may match it.
"""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)

import sync_api_from_pages as sap  # noqa: E402


def test_no_upcoming_row_has_a_published_decision():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    decs = sap.published_decisions()
    assert len(decs) > 400, f"decisions archive parse broken ({len(decs)} rows)"

    bad = []
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() == "decided":
            continue
        tk, d = str(r.get("t", "")).upper(), str(r.get("d") or "")[:10]
        if not d:
            continue
        for (dtk, ddate), (oc, ddrug) in decs.items():
            if dtk != tk:
                continue
            try:
                sgap = (dt.date.fromisoformat(ddate) - dt.date.fromisoformat(d)).days
            except Exception:
                continue
            if abs(sgap) <= 14 or (
                    (-180 <= sgap <= 45 if oc == "Approved" else -14 <= sgap <= 45)
                    and sap._lead_match(r.get("name"), ddrug)):
                bad.append(f"{tk} goal {d} ({str(r.get('name'))[:40]}) is Upcoming but "
                           f"/fda-decision/{dtk}-{ddate} says {oc}"
                           + (f" ({ddrug[:40]})" if ddrug else ""))
    assert not bad, ("published decisions with Upcoming dataset rows -- run "
                     "sync_api_from_pages.py:\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    test_no_upcoming_row_has_a_published_decision()
    print("OK")
