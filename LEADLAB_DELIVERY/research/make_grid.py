#!/usr/bin/env python3
"""Export the empirical, unbiased P(surge) scoring grids the new engine embeds.
Grids: open-session (gap x relvol) and pre-market (pm09:00 move x relvol).
Every cell carries its sample size; sparse cells fall back to the 1-D marginal."""
import os, csv, json
HERE=os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except: return None
U=list(csv.DictReader(open(os.path.join(HERE,"universe.csv"))))
GAP_EDGES=[3,5,10,20,40]          # >=40 top bucket
RV_EDGES=[0,1,2,5,10]             # >=10 top bucket
def gi(g):
    for i in range(len(GAP_EDGES)-1):
        if GAP_EDGES[i]<=g<GAP_EDGES[i+1]: return i
    return len(GAP_EDGES)-1 if g>=GAP_EDGES[-1] else None
def vi(v):
    for i in range(len(RV_EDGES)-1):
        if RV_EDGES[i]<=v<RV_EDGES[i+1]: return i
    return len(RV_EDGES)-1 if v>=RV_EDGES[-1] else None
def rate(rows,key="surge25"):
    return (sum(int(r[key]) for r in rows)/len(rows), len(rows)) if rows else (0,0)

# open grid
grid=[[None]*len(RV_EDGES) for _ in range(len(GAP_EDGES))]
for gj in range(len(GAP_EDGES)):
    for vj in range(len(RV_EDGES)):
        sub=[r for r in U if f(r["gap_pct"]) is not None and gi(f(r["gap_pct"]))==gj
             and r["relvol"] and vi(f(r["relvol"]))==vj]
        p,n=rate(sub)
        grid[gj][vj]={"p":round(p,3),"n":n} if n>=12 else None
# gap marginal fallback
gap_marg=[]
for gj in range(len(GAP_EDGES)):
    sub=[r for r in U if f(r["gap_pct"]) is not None and gi(f(r["gap_pct"]))==gj]
    p,n=rate(sub); gap_marg.append({"p":round(p,3),"n":n})
rv_marg=[]
for vj in range(len(RV_EDGES)):
    sub=[r for r in U if r["relvol"] and vi(f(r["relvol"]))==vj]
    p,n=rate(sub); rv_marg.append({"p":round(p,3),"n":n})

out={
  "meta":{"events":len(U),"label":"P(intraday +25% vs prev close) | small/micro gap-up",
          "source":"Polygon whole-market grouped-daily (incl. delisted) — unbiased",
          "gap_edges":GAP_EDGES,"rv_edges":RV_EDGES,"min_gap":3},
  "open_grid":grid,"gap_marginal":gap_marg,"rv_marginal":rv_marg,
  "base_rate":round(rate(U)[0],3),
}
# pre-market grid (from premarket_features joined to outcomes)
pmf=os.path.join(HERE,"premarket_features.csv")
if os.path.exists(pmf):
    Ui={(r["symbol"],r["date"]):r for r in U}
    PM=[]
    for p in csv.DictReader(open(pmf)):
        u=Ui.get((p["symbol"],p["date"]))
        if u: PM.append({**u,**{k:p[k] for k in p if k not in("symbol","date")}})
    PM_EDGES=[3,5,10,20,40]
    def pmi(x):
        for i in range(len(PM_EDGES)-1):
            if PM_EDGES[i]<=x<PM_EDGES[i+1]: return i
        return len(PM_EDGES)-1 if x>=PM_EDGES[-1] else None
    pm_grid=[]
    for j in range(len(PM_EDGES)):
        sub=[r for r in PM if f(r["pm_0900_pct"]) is not None and pmi(f(r["pm_0900_pct"]))==j]
        p,n=rate(sub); pm_grid.append({"p":round(p,3),"n":n})
    # pm move x relvol
    pm2=[[None]*len(RV_EDGES) for _ in range(len(PM_EDGES))]
    for j in range(len(PM_EDGES)):
        for vj in range(len(RV_EDGES)):
            sub=[r for r in PM if f(r["pm_0900_pct"]) is not None and pmi(f(r["pm_0900_pct"]))==j
                 and r["relvol"] and vi(f(r["relvol"]))==vj]
            p,n=rate(sub); pm2[j][vj]={"p":round(p,3),"n":n} if n>=8 else None
    out["pm_edges"]=PM_EDGES
    out["pm0900_marginal"]=pm_grid
    out["pm0900_x_relvol_grid"]=pm2
    out["pm_sample"]=len(PM)
json.dump(out,open(os.path.join(HERE,"scoring_grid.json"),"w"),indent=2)
print("wrote scoring_grid.json | open events=%d pm sample=%d base=%.3f"%(len(U),out.get("pm_sample",0),out["base_rate"]))
