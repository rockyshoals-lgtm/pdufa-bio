# -*- coding: utf-8 -*-
"""CI guard: /fda-approval-letters is linked from every decision page and from /decisions (audit 2026-10-03, 3.2).

"fda approval letters" is a live Bing grounding query (13.04% share) and the hub shipped 09-27 with almost
no inbound links: 349 of 476 decision pages did not link it. Fails, on the rendered pages, when any
/fda-decision page or /decisions lacks a link to /fda-approval-letters.

    python tests/test_letters_hub_linked.py
"""
import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")


def main():
    miss = [os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))
            if 'href="/fda-approval-letters"' not in io.open(p, encoding="utf-8", errors="replace").read()]
    dec = 'href="/fda-approval-letters"' in io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8").read()
    if miss or not dec:
        print(f"FAIL: {len(miss)} decision page(s) without a link to /fda-approval-letters"
              + ("" if dec else "; /decisions does not link it") + (f": {miss[:8]}" if miss else ""))
        return 1
    print("OK -- every decision page and /decisions link /fda-approval-letters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
