# -*- coding: utf-8 -*-
"""make_decisions_join_slim.py -- the 4 public columns CI needs, without the model dataset.

2026-08-14: the daily rebuild failed four consecutive runs because verify_decisions.py and its
appliers read ODIN_MODEL_READY_*.csv -- which lives only on the workstation, deliberately: it is
the research model's training data and the site repo is public. But the verification chain only
needs (ticker, date, drug name, indication) to join a decision page to its drug -- facts the
site itself already publishes on every sourced decision page. This emits exactly those columns
to _decisions_join_slim.csv, which IS committed; the verification scripts prefer the full CSV
when present (workstation) and fall back to the slim file (CI), then to an empty join rather
than crashing.

Run whenever the ODIN dataset gains events:  python make_decisions_join_slim.py
"""
import csv, os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
DST = os.path.join(HERE, "_decisions_join_slim.csv")

if not os.path.exists(SRC):
    print("full ODIN csv not present (CI?) -- nothing to do")
    sys.exit(0)

with open(SRC, encoding="utf-8", errors="replace") as f:
    rows = list(csv.DictReader(f))
with open(DST, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["ticker", "catalyst_date", "asset", "indication"])
    for r in rows:
        w.writerow([r.get("ticker", ""), r.get("catalyst_date", ""),
                    r.get("asset", ""), r.get("indication", "")])
print(f"wrote {DST}: {len(rows)} rows, 4 public columns")
