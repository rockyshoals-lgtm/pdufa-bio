#!/usr/bin/env python3
"""LEADLAB — base-rate + leading-signal analysis on the UNBIASED universe.

Answers, with losers included (no survivorship bias):
  1) P(intraday surge to +25% | open-gap bucket, rel-vol bucket) at 9:30.
  2) Precision/recall tradeoff of an OPEN-based trigger vs the current 8%-move rule.
  3) (if premarket_features.csv present) how pre-market gap/rel-vol/velocity change
     the odds AND how much earlier they fire than the open.

Everything is a historical base rate, not a prediction. Educational only."""
import os, csv, statistics, collections

HERE = os.path.dirname(os.path.abspath(__file__))

def load(fn):
    p = os.path.join(HERE, fn)
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []

def f(x):
    try: return float(x)
    except: return None

def rate(rows, key):
    n = len(rows)
    return (100 * sum(int(r[key]) for r in rows) / n, n) if n else (0, 0)

def bucketize(rows, field, edges):
    out = collections.OrderedDict()
    labels = []
    for i in range(len(edges) - 1):
        labels.append("%g-%g" % (edges[i], edges[i+1]))
    labels.append("%g+" % edges[-1])
    for lb in labels: out[lb] = []
    for r in rows:
        v = f(r[field])
        if v is None: continue
        placed = False
        for i in range(len(edges) - 1):
            if edges[i] <= v < edges[i+1]:
                out[labels[i]].append(r); placed = True; break
        if not placed and v >= edges[-1]:
            out[labels[-1]].append(r)
    return out

def main():
    U = load("universe.csv")
    print("=" * 70)
    print("UNIVERSE: %d unbiased gap-up ticker-days (winners AND losers)" % len(U))
    br, _ = rate(U, "surge25")
    print("Overall base rate P(intraday +25%% | >=3%% gap-up) = %.1f%%" % br)
    print()

    print("--- P(intraday +25%) by OPEN GAP bucket (known at 9:30) ---")
    print("%-10s %8s %10s %12s %12s" % ("gap%", "n", "P(+25%)", "P(closeUp)", "P(close+15%)"))
    for lb, rs in bucketize(U, "gap_pct", [3,5,10,20,40,70]).items():
        if not rs: continue
        s25,_ = rate(rs, "surge25"); cu,_ = rate(rs, "close_up"); c15,_ = rate(rs, "close_up15")
        print("%-10s %8d %9.1f%% %11.1f%% %11.1f%%" % (lb, len(rs), s25, cu, c15))
    print()

    print("--- P(intraday +25%) by REL-VOL bucket (open-day vol / 20d ADV) ---")
    print("%-10s %8s %10s %12s" % ("relvol", "n", "P(+25%)", "P(close+15%)"))
    for lb, rs in bucketize(U, "relvol", [0.5,1,2,5,10,20]).items():
        if not rs: continue
        s25,_ = rate(rs, "surge25"); c15,_ = rate(rs, "close_up15")
        print("%-10s %8d %9.1f%% %11.1f%%" % (lb, len(rs), s25, c15))
    print()

    print("--- 2D: gap x relvol -> P(intraday +25%) ---")
    gaps = [3,5,10,20,40]; vols = [0.5,1,2,5,10]
    print("%-8s" % "gap\\rv", end="")
    vlabs = ["<1","1-2","2-5","5-10","10+"]
    for vl in vlabs: print("%8s" % vl, end="")
    print()
    for gi in range(len(gaps)):
        glo = gaps[gi]; ghi = gaps[gi+1] if gi+1 < len(gaps) else 999
        print("%-8s" % ("%g-%g" % (glo, ghi if ghi<999 else 0) if ghi<999 else "%g+"%glo), end="")
        for vi, (vlo, vhi) in enumerate([(0,1),(1,2),(2,5),(5,10),(10,999)]):
            sub = [r for r in U if f(r["gap_pct"]) and glo<=f(r["gap_pct"])<ghi
                   and r["relvol"] and vlo<=f(r["relvol"])<vhi]
            if len(sub) >= 15:
                s25,_ = rate(sub, "surge25")
                print("%7.0f%%" % s25, end="")
            else:
                print("%8s" % "-", end="")
        print()
    print()

    # ---- leading (pre-market) layer ----
    PM = load("premarket_features.csv")
    if not PM:
        print("(no premarket_features.csv yet — run pull_premarket.py after sampling)")
        return
    idx = {(r["symbol"], r["date"]): r for r in U}
    merged = []
    for p in PM:
        u = idx.get((p["symbol"], p["date"]))
        if u: merged.append({**u, **{"pm_"+k if not k.startswith("pm") else k: v for k,v in p.items()}})
    print("=" * 70)
    print("LEADING (pre-market) layer: %d events matched" % len(merged))
    print("--- P(intraday +25%) by 09:00 PRE-MARKET move (known 30min before open) ---")
    print("%-10s %8s %10s" % ("pm0900%", "n", "P(+25%)"))
    for lb, rs in bucketize(merged, "pm_0900_pct", [3,5,10,20,40]).items():
        if len(rs) < 10: continue
        s25,_ = rate(rs, "surge25")
        print("%-10s %8d %9.1f%%" % (lb, len(rs), s25))

main()
