# -*- coding: utf-8 -*-
"""build_conference_runup_stats.py -- what biotech stocks have historically done into, on, and
after a medical-conference presentation. Ours, from our own study, not a vendor's.

SOURCE
conf_study/conference_runup_PUBLISHED.csv -- 1,425 presentation events, 2017-2026, each with the
stock's move over the 30/20/10/5 trading days BEFORE the presentation, the event day itself, and
5/10 days after. Cap tier is point-in-time (cap_tier_pit), so a company that was micro-cap in
2019 is measured as micro-cap, not by what it is worth today.

WHAT IT PRODUCES
_conference_runup_stats.json -- per conference and per cap tier: n, median, mean, and the share
of events that rose, for each window. Cells thinner than MIN_N are withheld rather than shown,
because a "typical run-up" computed from four events is not a typical anything.

HONESTY RULES BAKED IN
  * Median leads, not mean. Biotech returns are fat-tailed and the mean flatters.
  * Every published cell carries its n.
  * These are HISTORICAL DISTRIBUTIONS for a cohort, never a prediction for one company, and
    never advice. The renderer repeats that where a reader will see it.

    python build_conference_runup_stats.py [--min-n 12]
"""
import argparse, csv, io, json, os, statistics as st, sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "conf_study", "conference_runup_PUBLISHED.csv")
OUT = os.path.join(HERE, "_conference_runup_stats.json")
WINDOWS = ["runup_30d", "runup_20d", "runup_10d", "runup_5d", "event_day",
           "post_5d", "post_10d"]
TIERS = ["nano", "micro", "small", "mid", "large"]


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    # guard against sentinel/blow-up rows: a 10x move over 30 days is a data error far more
    # often than a real conference reaction, and one such row moves a mean permanently.
    return f if -95 <= f <= 900 else None


def summarize(rows, min_n):
    out = {}
    for w in WINDOWS:
        vals = [x for x in (num(r.get(w)) for r in rows) if x is not None]
        if len(vals) < min_n:
            continue
        out[w] = {"n": len(vals),
                  "median": round(st.median(vals), 2),
                  "mean": round(st.mean(vals), 2),
                  "pct_up": round(100.0 * sum(1 for v in vals if v > 0) / len(vals), 1)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-n", type=int, default=12)
    a = ap.parse_args()

    if not os.path.exists(SRC):
        print(f"SKIP: {os.path.relpath(SRC, HERE)} not found")
        return 0
    rows = list(csv.DictReader(io.open(SRC, encoding="utf-8-sig")))
    print(f"study rows: {len(rows)}")

    stats = {"_source": "conf_study/conference_runup_PUBLISHED.csv",
             "_events": len(rows), "_min_n": a.min_n,
             "overall": summarize(rows, a.min_n), "by_conference": {}, "by_cap": {},
             "by_conference_cap": {}}

    by_conf = defaultdict(list)
    for r in rows:
        c = (r.get("conf") or "").strip().upper()
        if c and c != "UNKNOWN":
            by_conf[c].append(r)
    for c, rs in by_conf.items():
        s = summarize(rs, a.min_n)
        if s:
            stats["by_conference"][c] = s

    by_cap = defaultdict(list)
    for r in rows:
        t = (r.get("cap_tier_pit") or "").strip().lower()
        if t in TIERS:
            by_cap[t].append(r)
    for t, rs in by_cap.items():
        s = summarize(rs, a.min_n)
        if s:
            stats["by_cap"][t] = s

    # conference x cap is where the signal actually lives (a micro-cap at ASCO is not a large-cap
    # at ASCO), but it thins out fast -- hence the same MIN_N gate.
    cc = defaultdict(list)
    for r in rows:
        c = (r.get("conf") or "").strip().upper()
        t = (r.get("cap_tier_pit") or "").strip().lower()
        if c and c != "UNKNOWN" and t in TIERS:
            cc[f"{c}|{t}"].append(r)
    for k, rs in cc.items():
        s = summarize(rs, a.min_n)
        if s:
            stats["by_conference_cap"][k] = s

    json.dump(stats, io.open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"wrote {os.path.basename(OUT)}: {len(stats['by_conference'])} conference(s), "
          f"{len(stats['by_cap'])} cap tier(s), {len(stats['by_conference_cap'])} pairs "
          f"(min n={a.min_n})")

    o = stats["overall"]
    print("\n  ALL CONFERENCE PRESENTATIONS (median move, share that rose)")
    for w in WINDOWS:
        if w in o:
            print(f"    {w:10s} n={o[w]['n']:<5d} median {o[w]['median']:+6.2f}%   "
                  f"{o[w]['pct_up']:.0f}% rose")
    print("\n  BY CAP TIER (10-day run-up -> event day -> 5 days after, medians)")
    for t in TIERS:
        s = stats["by_cap"].get(t)
        if s and "runup_10d" in s:
            ed = s.get("event_day", {}).get("median")
            p5 = s.get("post_5d", {}).get("median")
            print(f"    {t:6s} n={s['runup_10d']['n']:<5d} "
                  f"{s['runup_10d']['median']:+6.2f}%  ->  "
                  f"{('%+.2f%%' % ed) if ed is not None else '   n/a'}  ->  "
                  f"{('%+.2f%%' % p5) if p5 is not None else '   n/a'}")
    print("\n  Historical distributions for a cohort, not a prediction. Not investment advice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
