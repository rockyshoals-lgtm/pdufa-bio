# -*- coding: utf-8 -*-
"""CRL decision pages that cite FDA's letter must keep citing it.

Audit 09-02c item 3: 458 held FDA CRLs, zero cited -- fixed by link_crl_letters.py.
This floor guard keeps the fix from silently unshipping (the frozen-family lesson):
at least 10 decision pages must carry a CRLSRC card, and every card's link must point
at FDA's own host with a plausible letter filename. The count can only grow as new
CRLs land and the corpus refreshes; a drop below the floor means the CI step vanished
or a template rewrite flattened the cards.
"""
import glob
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def test_crl_letter_cards_present_and_valid():
    n, bad = 0, []
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "<!--CRLSRC:BEGIN-->" not in doc:
            continue
        n += 1
        card = doc.split("<!--CRLSRC:BEGIN-->", 1)[1].split("<!--CRLSRC:END-->", 1)[0]
        if not re.search(r'href="https://download\.open\.fda\.gov/crl/[\w.\-]+\.pdf"',
                         card):
            bad.append(os.path.basename(os.path.dirname(p)))
    assert not bad, f"CRLSRC cards without a valid FDA letter link: {bad}"
    assert n >= 10, (f"only {n} decision pages carry an FDA letter card (floor 10) -- "
                     f"did link_crl_letters.py drop out of CI, or did a rewrite "
                     f"flatten the cards?")


if __name__ == "__main__":
    test_crl_letter_cards_present_and_valid()
    print(f"OK")
