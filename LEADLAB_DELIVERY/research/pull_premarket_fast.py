#!/usr/bin/env python3
"""Threaded FMP 1-min extended pre-market puller; bounded batch per run (resumable)."""
import os, csv, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pull_premarket as P
HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "sample_events.csv"))))
    out = os.path.join(HERE, "premarket_features.csv")
    done = set()
    if os.path.exists(out):
        for r in csv.DictReader(open(out)):
            done.add((r["symbol"], r["date"]))
    todo = [r for r in rows if (r["symbol"], r["date"]) not in done]
    batch = todo[:int(os.environ.get("BATCH", "150"))]
    print("remaining %d; this run %d" % (len(todo), len(batch)))
    fields = ["symbol","date","prev_close","pm_bars","pm_vol","pm_high_pct",
              "pm_0800_pct","pm_0900_pct","pm_vol_0800","pm_vol_0900",
              "pm_last_pct","open_pct","r1_ret_pct","r5_ret_pct","r5_vol"]
    write_header = not os.path.exists(out)
    f = open(out, "a", newline="")
    w = csv.DictWriter(f, fieldnames=fields)
    if write_header: w.writeheader()
    n = 0; t0 = time.time()
    with ThreadPoolExecutor(max_workers=32) as ex:
        futs = [ex.submit(P.feats, r["symbol"], r["date"], float(r["prev_close"])) for r in batch]
        for fut in as_completed(futs):
            ft = fut.result()
            if ft:
                w.writerow(ft); n += 1
    f.flush()
    print("wrote %d in %.0fs" % (n, time.time()-t0))

main()
