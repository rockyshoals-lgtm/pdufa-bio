#!/usr/bin/env python3
"""LEADLAB — leading (pre-market) signal analysis with CONTROLS.
Join premarket_features to universe outcomes; measure P(surge25) by pre-market
signal, compare to open-gap, and quantify what fires EARLIER."""
import os, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except: return None
U = {(r["symbol"], r["date"]): r for r in csv.DictReader(open(os.path.join(HERE,"universe.csv")))}
PM = list(csv.DictReader(open(os.path.join(HERE,"premarket_features.csv"))))
M = []
for p in PM:
    u = U.get((p["symbol"], p["date"]))
    if not u: continue
    row = dict(u); row.update({k:p[k] for k in p if k not in ("symbol","date","prev_close")})
    M.append(row)
print("matched pre-market events (with outcomes):", len(M))
n=len(M); base=100*sum(int(r["surge25"]) for r in M)/n
print("sample base rate P(+25%%)=%.1f%%\n"%base)

def tbl(field, edges, label):
    print("--- P(intraday +25%%) by %s ---"%label)
    print("%-10s %7s %9s %11s"%(label,"n","P(+25%)","mean_relvol"))
    order=[]
    for i in range(len(edges)-1): order.append((edges[i],edges[i+1],"%g-%g"%(edges[i],edges[i+1])))
    order.append((edges[-1],1e9,"%g+"%edges[-1]))
    for lo,hi,lb in order:
        sub=[r for r in M if f(r[field]) is not None and lo<=f(r[field])<hi]
        if len(sub)<8: continue
        p25=100*sum(int(r["surge25"]) for r in sub)/len(sub)
        rv=[f(r["relvol"]) for r in sub if f(r["relvol"])]
        print("%-10s %7d %8.1f%% %11.1f"%(lb,len(sub),p25, sum(rv)/len(rv) if rv else 0))
    print()

# 1) pre-market move at 09:00 (fires ~30 min BEFORE the open)
tbl("pm_0900_pct",[3,5,10,20,40],"pm 09:00 move %")
# 2) pre-market move at 08:00 (fires ~90 min before open)
tbl("pm_0800_pct",[3,5,10,20,40],"pm 08:00 move %")
# 3) pre-market cumulative volume by 09:00 (volume-before-price)
tbl("pm_vol_0900",[10000,50000,200000,1000000],"pm vol by 09:00")

# EARLINESS: for events that DID surge, how big was the pre-market signal already?
sur=[r for r in M if int(r["surge25"])]
print("=== EARLINESS: of the %d events that hit +25%% intraday ==="%len(sur))
for cut,lbl in [("pm_0800_pct","08:00 (~90min pre-open)"),("pm_0900_pct","09:00 (~30min pre-open)")]:
    vals=[f(r[cut]) for r in sur if f(r[cut]) is not None]
    for thr in (5,10,20):
        got=sum(1 for v in vals if v>=thr)
        print("  by %s: %.0f%% were already >= +%d%% pre-market"%(lbl,100*got/len(vals),thr))
print()

# PRECISION comparison: pre-market 09:00 >=10% vs open-gap >=10%
def prec(cond):
    sub=[r for r in M if cond(r)]
    if not sub: return (0,0,0)
    tp=sum(int(r["surge25"]) for r in sub)
    return (100*tp/len(sub), len(sub), tp)
p9,n9,_=prec(lambda r: f(r["pm_0900_pct"]) is not None and f(r["pm_0900_pct"])>=10)
og,no,_=prec(lambda r: f(r["gap_pct"])>=10)
print("PRECISION @ >=10%% threshold:")
print("  pre-market 09:00 move >=10%% -> P(+25%%)=%.1f%% (n=%d) [fires ~30min earlier]"%(p9,n9))
print("  open gap >=10%%             -> P(+25%%)=%.1f%% (n=%d) [fires at 9:30]"%(og,no))
# combined confluence: pm 09:00 >=10% AND relvol context
pc,nc,_=prec(lambda r: f(r["pm_0900_pct"]) is not None and f(r["pm_0900_pct"])>=10 and f(r["relvol"]) and f(r["relvol"])>=3)
print("  pm 09:00>=10%% AND relvol>=3 -> P(+25%%)=%.1f%% (n=%d) [confluence]"%(pc,nc))
