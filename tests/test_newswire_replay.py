# -*- coding: utf-8 -*-
"""CI guard: the sponsor-feed watcher would have caught this month's three late approvals on
the day they were announced.

Audit 2026-09-26 item 6 acceptance: "a replay of September 14, 16 and 25 catches TLX, NUVB and
Atebrioz the same day." Feed history cannot be replayed live, so this replays the watcher's
MATCHER on the verbatim headline and opening line of each sponsor release, against the row as it
stood that morning (Upcoming). It also asserts the negatives that matter: an acceptance release
("FDA accepts sNDA", Pharming 09-25) and a trial readout must NOT raise a decision lead.

    python tests/test_newswire_replay.py
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

CASES = [
    # (row as it stood, item text verbatim from the sponsor release, expect lead?)
    ({"id": "pdufa_tlx_2026-09-11", "t": "TLX", "d": "2026-09-11", "type": "PDUFA", "st": "Upcoming",
      "name": "Pixclara (floretyrosine F 18; TLX101-Px)", "_d": {"brand": "Pixclara"}},
     "FDA Approves Telix's Brain Cancer Imaging Drug Pixclara \n Pixclara is the first FDA-approved FET-PET "
     "imaging drug for glioma (brain cancer).", True),                                  # Telix, Sep 14
    ({"id": "pdufa_nuvb_2027-01-04", "t": "NUVB", "d": "2027-01-04", "type": "PDUFA", "st": "Upcoming",
      "name": "IBTROZI (taletrectinib) sNDA", "_d": {}},
     "Nuvation Bio Announces FDA Approval of Supplemental New Drug Application for IBTROZI (taletrectinib) "
     "with Updated Duration of Response in TKI-Naive Advanced ROS1-Positive Non-Small Cell Lung Cancer", True),  # Sep 16
    ({"id": "pdufa_mirm_2026-09-26", "t": "MIRM", "d": "2026-09-26", "type": "PDUFA", "st": "Upcoming",
      "name": "zilurgisertib", "_d": {}},
     "Mirum Pharmaceuticals and Incyte Announce U.S. FDA Approval of Atebrioz (zilurgisertib) for Adult and "
     "Pediatric Patients with Fibrodysplasia Ossificans Progressiva", True),              # Sep 25
    ({"id": "pdufa_incy_2026-09-26", "t": "INCY", "d": "2026-09-26", "type": "PDUFA", "st": "Upcoming",
      "name": "Zilurgisertib (licensed to Mirum; MIRM holds the NDA)", "_d": {}},
     "Mirum Pharmaceuticals and Incyte Announce U.S. FDA Approval of Atebrioz (zilurgisertib) for Adult and "
     "Pediatric Patients with Fibrodysplasia Ossificans Progressiva", True),
    ({"id": "pdufa_phar_2027-01-30", "t": "PHAR", "d": "2027-01-30", "type": "PDUFA", "st": "Upcoming",
      "name": "Joenja (leniolisib) lower doses - APDS, ages 4+ from 13 kg (sNDA)", "_d": {}},
     "Pharming announces U.S. FDA acceptance and Priority Review of sNDA for lower doses of Joenja to treat "
     "children with APDS", False),                                                       # an acceptance, not a decision
    ({"id": "x", "t": "NUVB", "d": "2027-01-04", "type": "PDUFA", "st": "Upcoming",
      "name": "IBTROZI (taletrectinib) sNDA", "_d": {}},
     "Nuvation Bio presents taletrectinib TRUST-II data at ESMO", False),                # a readout, no FDA decision
]


def main():
    import watch_sponsor_newswire as W
    fails = []
    for row, text, want in CASES:
        got = bool(W.match(text, [row]))
        if got != want:
            fails.append(f"{row['id']}: expected {'a lead' if want else 'no lead'} for \"{text[:70]}...\"")
    if fails:
        print(f"FAIL: sponsor-feed matcher replay, {len(fails)} miss(es):")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- replay: TLX (Sep 14), NUVB (Sep 16), MIRM + INCY Atebrioz (Sep 25) each raise a lead from the "
          f"sponsor's own headline; an acceptance and a readout do not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
