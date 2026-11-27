# -*- coding: utf-8 -*-
"""test_home_card_names.py -- a phone card names the drug cleanly, not in fragments.

OMW round 2, 2026-11-27, checked live at 500px: the homepage "Next FDA decisions" cards showed
"Relacorilant - (...", "lorundrostat Do..." and "Anito-cel (anito...". The date shares the line, so
dataset names with trial or indication suffixes were cut mid-suffix, and a slate artifact
("lorundrostat Dose 1") read as a dosing claim. build_home_board.card_name() now gives the drug's own
name (a hand-verified calendar label wins for its page; a bare sponsor code keeps its gloss).

A sponsor that also has a Recently decided card (or a second next card) keeps its trial tag, so
"Bezuclastinib (SUMMIT)" never reads as the decided bezuclastinib beside it
(tests/test_board_no_double_listing.py checks the page). This fails if a card carries a " - " suffix or a "Dose N" artifact, two cards for one ticker read
alike, or card_name() stops handling the planted cases below.

    python tests/test_home_card_names.py
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

PLANTED = [  # (raw slate/dataset name, event href, what the card must show)
    ("Relacorilant - (GRACE resubmission)", "", "Relacorilant"),
    ("Relutrigine (PRAX-562) - (EMBOLD)", "", "Relutrigine"),
    ("Gazyva (obinutuzumab) - systemic lupus erythematosus (ALLEGORY)", "", "Gazyva"),
    ("Anito-cel (anitocabtagene autoleucel)", "", "Anito-cel"),
    ("lorundrostat Dose 1", "", "Lorundrostat"),
    ("MR-107A-02 (fast-acting meloxicam)", "", "MR-107A-02 (fast-acting meloxicam)"),
    ("mRNA-1283", "", "mRNA-1283"),
    ("Imsidolimab", "", "Imsidolimab"),
]
QUALIFIED = [  # the sponsor also has a decided card or a second card: the trial tag stays
    ("Bezuclastinib (CGT9486) - (SUMMIT)", "Bezuclastinib (SUMMIT)"),
    ("Gazyva (obinutuzumab) - systemic lupus erythematosus (ALLEGORY)", "Gazyva (ALLEGORY)"),
    ("Imsidolimab", "Imsidolimab"),
]


def main():
    from build_home_board import card_name
    bad = []
    for raw, href, want in PLANTED:
        got = card_name(raw, href)
        if got != want:
            bad.append(f"card_name({raw!r}) gave {got!r}, want {want!r}")
    for raw, want in QUALIFIED:
        got = card_name(raw, "", qualify=True)
        if got != want:
            bad.append(f"card_name({raw!r}, qualify) gave {got!r}, want {want!r}")
    doc = io.open(os.path.join(HERE, "pdufa_site_src", "index.html"), encoding="utf-8", errors="replace").read()
    lst = doc[doc.find('<div class="list">'):doc.find("Recently decided")]
    cards = re.findall(r'<a class="row" href="([^"]+)">.*?<span class="tk">([A-Z.]+) .*?<bdi class="dn">([^<]*)</bdi>', lst, re.S)
    if not cards:
        bad.append("home: no Next FDA decisions cards parsed -- markup changed?")
    seen = {}
    for href, tk, name in cards:
        if " - " in name or re.search(r"\bDose \d+$", name, re.I):
            bad.append(f"home: the {tk} card shows {name!r}, a suffix or slate artifact the phone cuts mid-word")
        if (tk, name) in seen and seen[(tk, name)] != href:
            bad.append(f"home: two {tk} cards both read {name!r} but open different pages")
        seen[(tk, name)] = href
    print(f"card_name: {len(PLANTED)} planted case(s); home: {len(cards)} next-decision card(s)")
    if bad:
        print("FAIL:\n  " + "\n  ".join(bad[:30]))
        return 1
    print("  PASS: next-decision cards name the drug cleanly and no two cards for one ticker read alike")
    return 0


if __name__ == "__main__":
    sys.exit(main())
