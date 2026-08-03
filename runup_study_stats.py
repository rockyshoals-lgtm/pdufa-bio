# -*- coding: utf-8 -*-
"""runup_study_stats.py -- recompute the published run-up statistics from the dataset.

Single source of truth for every run-up number the site quotes, so page copy can never drift from
the data behind it. Prints the headline figures plus the by-year and by-market-cap-tier cuts.
"""
import csv, json, os, statistics as st, sys, collections
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))


def f(r, k):
    v = r.get(k)
    try:
        return float(v)
    except Exception:
        return None


def med(vals):
    vals = [v for v in vals if v is not None]
    return st.median(vals) if vals else None


def mean(vals):
    vals = [v for v in vals if v is not None]
    return st.mean(vals) if vals else None


dates = [r["pdufa_date"][:10] for r in rows if r.get("pdufa_date")]
appr = [r for r in rows if r.get("outcome") == "APPROVAL"]
crl = [r for r in rows if r.get("outcome") == "CRL"]

out = {
    "n_events": len(rows),
    "date_min": min(dates), "date_max": max(dates),
    "n_approval": len(appr), "n_crl": len(crl),
    "approval_rate": round(100 * len(appr) / len(rows), 1),
}

print("=" * 78)
print(f"  PDUFA RUN-UP STUDY  |  {len(rows)} events  |  {min(dates)} .. {max(dates)}")
print("=" * 78)
print(f"  approvals {len(appr)} ({out['approval_rate']}%)   CRLs {len(crl)}")

print("\n  RUN-UP INTO THE DECISION (median %, eve vs N trading days before)")
for k in ("runup_30d", "runup_21d", "runup_14d", "runup_7d", "runup_5d", "runup_3d"):
    m = med([f(r, k) for r in rows])
    out[k + "_median"] = round(m, 2) if m is not None else None
    print(f"    {k:11s} median {m:+6.2f}%" if m is not None else f"    {k:11s} n/a")

print("\n  DECISION-DAY / POST REACTION (median %, vs eve close)")
for k in ("post_1d", "post_2d", "post_5d"):
    m = med([f(r, k) for r in rows])
    ma = med([f(r, k) for r in appr])
    mc = med([f(r, k) for r in crl])
    out[k + "_median"] = round(m, 2) if m is not None else None
    out[k + "_median_approval"] = round(ma, 2) if ma is not None else None
    out[k + "_median_crl"] = round(mc, 2) if mc is not None else None
    print(f"    {k:8s} all {m:+7.2f}%   approval {ma:+7.2f}%   CRL {mc:+7.2f}%")

# absolute decision-day move by market-cap tier -- this is the "cohort move" the site quotes
print("\n  |DECISION-DAY MOVE| BY MARKET-CAP TIER (median absolute post_1d)")
tiers = collections.defaultdict(list)
for r in rows:
    v = f(r, "post_1d")
    if v is not None and r.get("mcap_tier"):
        tiers[r["mcap_tier"]].append(abs(v))
order = ["Nano (<$50M)", "Micro ($50M-$300M)", "Small ($300M-$2B)", "Mid ($2B-$10B)", "Large (>$10B)"]
out["cohort_abs_move"] = {}
for t in order:
    if tiers.get(t):
        m = st.median(tiers[t])
        out["cohort_abs_move"][t] = {"median_abs_pct": round(m, 2), "n": len(tiers[t])}
        print(f"    {t:22s} {m:5.1f}%   (n={len(tiers[t])})")

print("\n  BY YEAR")
byyr = collections.defaultdict(list)
for r in rows:
    byyr[r["pdufa_date"][:4]].append(r)
out["by_year"] = {}
for y in sorted(byyr):
    g = byyr[y]
    r30 = med([f(r, "runup_30d") for r in g])
    p1 = med([f(r, "post_1d") for r in g])
    ar = 100 * sum(1 for r in g if r.get("outcome") == "APPROVAL") / len(g)
    out["by_year"][y] = {"n": len(g),
                         "runup_30d_median": round(r30, 2) if r30 is not None else None,
                         "post_1d_median": round(p1, 2) if p1 is not None else None,
                         "approval_rate": round(ar, 1)}
    print(f"    {y}  n={len(g):4d}   runup30 median {r30:+6.2f}%   post1d median {p1:+6.2f}%   "
          f"approval {ar:4.1f}%")

json.dump(out, open(os.path.join(HERE, "runup_study_stats.json"), "w"), indent=1)
print(f"\nwrote runup_study_stats.json")
