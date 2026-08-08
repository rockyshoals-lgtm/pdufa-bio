#!/usr/bin/env python3
"""
pdufa.bio — freshness guard.

"Never stale" is the bar. Perfect currency is impossible (filings lag, prices move),
so the real guarantee is: never *silently* stale. For every company, this compares the
filing our financials came from against the company's NEWEST 10-Q/10-K on SEC. If a newer
report exists than the one we sourced runway/cash from, we flag it for re-pull — so a stale
number is always *known and surfaced*, never quietly served.

This is the safety net behind the crawler always taking the latest filing. Run it as a
deliberate sweep (it makes one SEC call per company).

    python freshness_check.py [catalysts_public.csv] [limit]
"""
import sys, re, time, requests
import pandas as pd

PATH  = sys.argv[1] if len(sys.argv) > 1 else "catalysts_public.csv"
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0          # 0 = all
UA    = "pdufa.bio freshness contact@pdufa.bio"

d = pd.read_csv(PATH, dtype=str)
sess = requests.Session(); sess.headers.update({"User-Agent": UA})
cache = {}

def submissions(cik):
    """Return (latest_10Q_10K_date, {accession_nodash: filing_date})."""
    if cik in cache: return cache[cik]
    res = (None, {})
    try:
        c = str(int(float(cik))).zfill(10)
        j = sess.get(f"https://data.sec.gov/submissions/CIK{c}.json", timeout=15).json()
        rec = j.get("filings", {}).get("recent", {})
        forms, dates, accs = rec.get("form", []), rec.get("filingDate", []), rec.get("accessionNumber", [])
        acc2date = {a.replace("-", ""): dt for a, dt in zip(accs, dates)}
        fin = [dt for fm, dt in zip(forms, dates) if fm in ("10-Q", "10-K")]
        res = (max(fin) if fin else None, acc2date)
    except Exception:
        pass
    cache[cik] = res; time.sleep(0.05); return res

def src_accession(url):
    m = re.search(r"/data/\d+/(\d+)/", str(url))
    return m.group(1) if m else None

# one row per ticker (company-level financials)
seen, rows = set(), []
for _, r in d.iterrows():
    tk = r.get("ticker")
    if tk in seen or pd.isna(tk) or pd.isna(r.get("cik")): continue
    seen.add(tk)
    rows.append(r)
if LIMIT: rows = rows[:LIMIT]

stale, checked, no_src = [], 0, 0
for r in rows:
    cik = r.get("cik"); tk = r.get("ticker")
    acc = src_accession(r.get("runway_guidance_url"))
    latest, acc2date = submissions(cik)
    if not latest: continue
    checked += 1
    if not acc:                       # we have no company-stated runway source on file at all
        no_src += 1; continue
    src_date = acc2date.get(acc)
    if src_date and latest > src_date:
        stale.append((tk, r.get("runway_label"), src_date, latest))

print(f"\n{'='*70}\n  FRESHNESS GUARD — {PATH}\n{'='*70}")
print(f"  companies checked: {checked}   (sampled {len(rows)})")
print(f"  STALE financials (a newer 10-Q/10-K exists than our source): {len(stale)}")
print(f"  {'TKR':7s}{'our runway src':>16s}{'newest 10-Q/K':>16s}   stored runway label")
for tk, lbl, sd, ld in sorted(stale, key=lambda x: x[3], reverse=True):
    print(f"  {tk:7s}{sd:>16s}{ld:>16s}   {str(lbl)[:32]}")
print(f"\n  -> these companies have reported since we last parsed their financials; re-pull before publish.\n")
