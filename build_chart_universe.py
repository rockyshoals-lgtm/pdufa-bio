# -*- coding: utf-8 -*-
"""
build_chart_universe.py  —  (re)generate the option-chart universe each crawl run.

ORATS is now 100K calls/month, so we chart ALL catalysts (PDUFAs + readouts), not just PDUFAs.
Sources: resolved 2025-present from pdufa_runup_bifrost.csv (PDUFA) + gungnir_readout_analysis.csv
(readout), plus fresh FUTURE catalysts from the latest crawl (catalysts_out/catalysts_public.csv).
Writes:
  option_chart_universe.csv        - everything (PDUFA + readout), nearest-to-today first
  option_chart_universe_pdufa.csv  - PDUFA subset (kept for optional PDUFA-only runs)
"""
import csv, os, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today()

def pdate(s):
    s = str(s)[:10]
    try: return dt.date.fromisoformat(s) if len(s) == 10 else dt.date(int(s[:4]), int(s[5:7]), 15)
    except Exception: return None

rows = []; seen = set()
def add(tk, d, kind):
    tk = (tk or "").upper().strip(); d = str(d)[:10]
    if not tk or not d or (tk, d) in seen: return
    seen.add((tk, d)); rows.append({"ticker": tk, "catalyst_date": d, "kind": kind})

# resolved 2025-present PDUFAs
hp = os.path.join(HERE, "pdufa_runup_bifrost.csv")
if os.path.exists(hp):
    for r in csv.DictReader(open(hp, encoding="utf-8", errors="ignore")):
        d = str(r.get("pdufa_date", ""))[:10]
        if "2025-01-01" <= d <= TODAY.isoformat(): add(r.get("ticker"), d, "PDUFA-resolved")

# resolved 2025-present readouts
hr = os.path.join(HERE, "gungnir_readout_analysis.csv")
if os.path.exists(hr):
    for r in csv.DictReader(open(hr, encoding="utf-8", errors="ignore")):
        d = str(r.get("date", ""))[:10]
        if "2025-01-01" <= d <= TODAY.isoformat(): add(r.get("ticker"), d, "readout-resolved")

# fresh FUTURE catalysts from the latest crawl
cp = os.path.join(HERE, "catalysts_out", "catalysts_public.csv")
if os.path.exists(cp):
    for r in csv.DictReader(open(cp, encoding="utf-8", errors="ignore")):
        cat = (r.get("category") or "")
        if cat not in ("drug", "readout"): continue
        d = str(r.get("catalyst_date") or "")
        if len(d) >= 10 and d[4] == "-" and d[7] == "-": dd = d[:10]
        elif len(d) == 7 and d[5:7].isdigit(): dd = d
        else: continue
        if dd >= TODAY.isoformat()[:len(dd)]:
            add(r.get("ticker"), dd, "PDUFA-future" if cat == "drug" else "readout-future")

rows.sort(key=lambda r: abs((pdate(r["catalyst_date"]) - TODAY).days) if pdate(r["catalyst_date"]) else 99999)

def write(path, subset=None):
    rs = [r for r in rows if (subset is None or subset in r["kind"])]
    w = csv.DictWriter(open(path, "w", newline=""), fieldnames=["ticker", "catalyst_date", "kind"])
    w.writeheader()
    for r in rs: w.writerow(r)
    return len(rs)

n_all = write(os.path.join(HERE, "option_chart_universe.csv"))
n_pd  = write(os.path.join(HERE, "option_chart_universe_pdufa.csv"), subset="PDUFA")
print(f"  [chart-universe] {n_all} catalysts (all) + {n_pd} PDUFA-only, nearest-first")
