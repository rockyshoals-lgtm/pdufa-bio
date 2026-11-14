# -*- coding: utf-8 -*-
"""CI guard: every stock price the site publishes comes from FMP via price_source.py (David, 2026-11-13).

Polygon was removed on 2026-11-13; Yahoo/yfinance was ruled out for the pipeline (audit 2026-11-09 §4b: no official
API, blocks datacenter IPs, terms forbid redistribution). This scans the rebuild workflow and every Python script it
runs (plus the chain bats and price_source.py) and fails on any reference to Polygon's API or key, yfinance, or Yahoo's
chart endpoints. Research scripts outside the site pipeline are not scanned.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD = re.compile(r"api\.polygon\.io|POLYGON_API_KEY|\byfinance\b|query[12]\.finance\.yahoo\.com|stooq\.com|alphavantage")


def main():
    wf = open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    scripts = set(re.findall(r"python\s+([\w/]+\.py)", wf))
    for b in ("_chain_0919.bat",):
        p = os.path.join(HERE, b)
        if os.path.exists(p):
            scripts |= set(re.findall(r"([A-Za-z_0-9]+\.py)", open(p, encoding="utf-8", errors="replace").read()))
    scripts |= {"price_source.py", "add_decision_chart.py", "refresh_pxcache.py"}
    bad = []
    if BAD.search(wf):
        bad += [f".github/workflows/pdufa-rebuild.yml: {m.group(0)}" for m in BAD.finditer(wf)][:3]
    for s in sorted(scripts):
        p = os.path.join(HERE, s)
        if not os.path.exists(p):
            continue
        for n, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
            code = line.split("#", 1)[0]
            if BAD.search(code):
                bad.append(f"{s}:{n}: {line.strip()[:110]}")
    if bad:
        print(f"FAIL: {len(bad)} non-FMP price reference(s) in the site pipeline (prices must come from price_source/FMP):")
        for b in bad[:20]:
            print("   " + b)
        return 1
    print(f"OK -- {len(scripts)} pipeline scripts and the workflow reference no Polygon, yfinance or Yahoo price endpoint; "
          "prices come from FMP via price_source.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
