# -*- coding: utf-8 -*-
"""CI guard: the specialist-fund 13F block states only what the funds' own 13F filings say (audit 10-03, 4.1).

The file the order pointed at carried three wrong fund CIKs (venBio, Perceptive, Foresite mapped to other
filers). Fails when, on the RENDERED decision and drug pages:
  * a block names a fund that is not in _13f_specialists.json for that ticker, or a share count that differs;
  * a block names a fund whose CIK the sync did not verify against EDGAR's filer name;
  * a block lacks the quarter-end date or the SEC filing link;
  * _13f_specialists.json carries any of the rejected CIKs (0001603466, 0001224608, 0001540531).

    python tests/test_13f_block.py
"""
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
EXPECT = {"Baker Bros. Advisors": "BAKER BROS", "RA Capital Management": "RA CAPITAL", "Perceptive Advisors": "PERCEPTIVE",
          "OrbiMed Advisors": "ORBIMED", "Avoro Capital Advisors": "AVORO", "RTW Investments": "RTW",
          "EcoR1 Capital": "ECOR1", "BVF Inc.": "BVF", "Redmile Group": "REDMILE", "Cormorant Asset Management": "CORMORANT"}


def main():
    p = os.path.join(HERE, "_13f_specialists.json")
    if not os.path.exists(p):
        print("FAIL: _13f_specialists.json missing")
        return 1
    d = json.load(io.open(p, encoding="utf-8"))
    fails = []
    for f, meta in d.get("funds", {}).items():
        if f not in EXPECT or EXPECT[f] not in str(meta.get("edgar_name", "")).upper():
            fails.append(f"fund {f!r} not verified against its EDGAR filer name ({meta.get('edgar_name')!r})")
        if int(meta.get("cik", 0)) in (1603466, 1224608, 1540531):
            fails.append(f"fund {f!r} uses a rejected CIK {meta.get('cik')}")
    bt = d.get("by_ticker", {})
    n = 0
    for pg in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")) + glob.glob(os.path.join(SITE, "drug", "*", "index.html")):
        doc = io.open(pg, encoding="utf-8", errors="replace").read()
        m = re.search(r"<!--F13:BEGIN-->(.*?)<!--F13:END-->", doc, re.S)
        if not m:
            continue
        n += 1
        blk = m.group(1)
        if "quarter ended" not in blk or "sec.gov/Archives/edgar/data/" not in blk:
            fails.append(f"{pg}: block without the quarter-end date or SEC filing link")
        for fund, shares, tk in re.findall(r'rel="noopener"[^>]*>([^<]+)</a> reported ([\d,]+) shares of ([A-Z]{1,6})', blk):
            fund = html.unescape(fund)
            rec = next((h for h in bt.get(tk, []) if h["fund"] == fund), None)
            if not rec or rec["shares"] != int(shares.replace(",", "")):
                fails.append(f"{os.path.relpath(pg, SITE)}: {fund} {shares} {tk} not in the verified 13F data")
    if fails:
        print(f"FAIL: {len(fails)} 13F failure(s):")
        for f in fails[:20]:
            print("   " + f)
        return 1
    print(f"OK -- {n} pages carry 13F blocks; every fund and share count matches the EDGAR-verified filings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
