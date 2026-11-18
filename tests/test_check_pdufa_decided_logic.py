# -*- coding: utf-8 -*-
"""CI guard: the 'already decided' scan ties an approval headline to a row only when it is about that row.

check_pdufa_decided.py flagged four open PDUFAs on 2026-11-18 that were all still pending: a generic word
('treatment') tied Merck KGaA's PIMJETMI approval to Merck & Co.'s IDVYNSO row, and three approvals of
other applications (Joenja's earlier indication, Bixlenvo, WILSERDLY in evERA) matched by drug name. This
runs the matcher's offline self-test so those stay fixed and a real approval of the row's drug still flags.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import check_pdufa_decided as C  # noqa: E402

if __name__ == "__main__":
    if not C.self_test():
        sys.exit(1)
    print("OK -- decided-PDUFA matcher skips generic words, older releases and hand-checked other "
          "products; a newer approval of the row's drug still flags.")
