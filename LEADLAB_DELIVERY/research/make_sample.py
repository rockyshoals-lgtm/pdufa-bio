#!/usr/bin/env python3
"""Stratified sample of gap-up ticker-days for the pre-market study.
Include winners AND losers across gap buckets so P(surge|pm-signal) has controls.
FMP has no rate limit, so we can afford a large sample."""
import os, csv, random
HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(7)
U = list(csv.DictReader(open(os.path.join(HERE, "universe.csv"))))
def f(x):
    try: return float(x)
    except: return None
# strata by gap bucket; cap each so small buckets (big gaps) are fully covered
buckets = {"3-5":[], "5-10":[], "10-20":[], "20+":[]}
for r in U:
    g = f(r["gap_pct"])
    if g is None: continue
    if g < 5: buckets["3-5"].append(r)
    elif g < 10: buckets["5-10"].append(r)
    elif g < 20: buckets["10-20"].append(r)
    else: buckets["20+"].append(r)
caps = {"3-5":300, "5-10":300, "10-20":300, "20+":400}
sample = []
for k, rs in buckets.items():
    random.shuffle(rs)
    sample += rs[:caps[k]]
random.shuffle(sample)
out = os.path.join(HERE, "sample_events.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(U[0].keys()))
    w.writeheader(); w.writerows(sample)
print("sample:", len(sample), "events")
for k,rs in buckets.items(): print("  gap %s: pool %d -> sampled %d" % (k, len(rs), min(len(rs),caps[k])))
