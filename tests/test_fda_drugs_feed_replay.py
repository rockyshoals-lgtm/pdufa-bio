# -*- coding: utf-8 -*-
"""CI guard: the FDA "What's New: Drugs" watcher catches Atebrioz from the FDA's own 2:46 PM item.

Audit 2026-09-27 item 1 acceptance: "a replay of September 25 raises the Atebrioz lead at the
2:46 PM posting." Replays tests/fixtures/fda_drugs_whatsnew_2026-09-25.xml (a verbatim excerpt of
the FDA feed) against the MIRM and INCY rows as they stood that afternoon (Upcoming), and asserts:
  * both rows raise a lead from the 14:46:15 EDT item;
  * the Gazyva notice (no tracked row) is reported as untracked, not as a lead;
  * the AdComm announcement and the "Notable Approvals" index item raise nothing.

    python tests/test_fda_drugs_feed_replay.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

ROWS = [
    {"id": "pdufa_mirm_2026-09-26", "t": "MIRM", "d": "2026-09-26", "type": "PDUFA", "st": "Upcoming",
     "name": "zilurgisertib", "_d": {}},
    {"id": "pdufa_incy_2026-09-26", "t": "INCY", "d": "2026-09-26", "type": "PDUFA", "st": "Upcoming",
     "name": "Zilurgisertib (licensed to Mirum; MIRM holds the NDA)", "_d": {}},
    {"id": "pdufa_rhhby_2026-10-09", "t": "RHHBY", "d": "2026-10-09", "type": "PDUFA", "st": "Upcoming",
     "name": "Tecentriq (atezolizumab) adjuvant", "_d": {}},
]


def main():
    import watch_fda_drugs_feed as F
    xml = io.open(os.path.join(HERE, "tests", "fixtures", "fda_drugs_whatsnew_2026-09-25.xml"), encoding="utf-8").read()
    leads, untracked = F.leads_from(xml, ROWS)
    fails = []
    got = sorted((r["t"], it["title"][:30]) for r, _t, it, _k in leads)
    want = [("INCY", "FDA Approves Third Treatment f"), ("MIRM", "FDA Approves Third Treatment f")]
    if got != want:
        fails.append(f"leads {got}, expected {want}")
    if [it["title"][:30] for it in untracked] != ["FDA Approves Drug to Treat Idi"]:
        fails.append(f"untracked {[it['title'][:40] for it in untracked]}, expected only the Gazyva notice")
    if leads and str(leads[0][2]["date"]) != "2026-09-25":
        fails.append(f"lead dated {leads[0][2]['date']}, expected 2026-09-25")
    if fails:
        print("FAIL: FDA drugs-feed replay:")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- replay of 2026-09-25: the FDA's 14:46 EDT Atebrioz item raises leads on MIRM and INCY; "
          "Gazyva reported as untracked; the AdComm and index items raise nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
