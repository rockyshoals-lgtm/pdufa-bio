# -*- coding: utf-8 -*-
"""
archive_run.py  —  snapshot + longitudinal index for each pdufa.bio crawl.

Makes every run self-documenting: copies the run's key outputs into runs/<date>/ (append-only
history) and writes/updates one summary row per run in runs/runs_index.csv, so over time we
accumulate a time series of catalyst counts, recall vs BPC, QA flags, and GUNGNIR tier mix —
the raw material for future model work (BIFROST/UOA backtests, drift monitoring).

Usage:  python archive_run.py [catalysts_out] [runs]
"""
import sys, os, csv, json, shutil, datetime as dt

OUT_DIR  = sys.argv[1] if len(sys.argv) > 1 else "catalysts_out"
RUNS_DIR = sys.argv[2] if len(sys.argv) > 2 else "runs"
DATE = (sys.argv[3] if len(sys.argv) > 3 else dt.date.today().isoformat())

dest = os.path.join(RUNS_DIR, DATE)
os.makedirs(dest, exist_ok=True)

# 1) copy the run's artifacts into the dated folder (only those that exist)
ARTIFACTS = ["catalysts_public.csv", "catalysts_scored.csv", "catalysts_primary.csv",
             "qa_diff.json", "coverage_gaps.csv", "universe_effective.txt"]
copied = []
for f in ARTIFACTS:
    src = os.path.join(OUT_DIR, f)
    if os.path.exists(src):
        try: shutil.copy2(src, os.path.join(dest, f)); copied.append(f)
        except Exception as e: print(f"  [archive] copy {f} failed: {e}")

def _rows(path):
    p = os.path.join(OUT_DIR, path)
    if not os.path.exists(p): return []
    try: return list(csv.DictReader(open(p, encoding="utf-8", errors="ignore")))
    except Exception: return []

# 2) compute a summary row
pub = _rows("catalysts_public.csv")
scored = _rows("catalysts_scored.csv")
import collections
cat = collections.Counter((r.get("category") or "").lower() for r in pub)
qa  = collections.Counter()
for r in pub:
    for f in (r.get("qa_flag") or "").split("|"):
        if f: qa[f] += 1
tier = collections.Counter((r.get("gungnir_est_tier") or "").upper() for r in scored if r.get("gungnir_est_tier"))
recall = overlap = ""
qp = os.path.join(OUT_DIR, "qa_diff.json")
if os.path.exists(qp):
    try:
        j = json.load(open(qp))
        pd_ = j.get("pdufa_only", {}); ov = j.get("overall", {})
        recall = pd_.get("recall_vs_bpc", ""); overlap = ov.get("overlap", "")
    except Exception: pass
gaps = len(_rows("coverage_gaps.csv"))

row = {"date": DATE, "total": len(pub),
       "drugs": cat.get("drug", 0), "readouts": cat.get("readout", 0),
       "devices": cat.get("device", 0), "earnings": cat.get("earnings", 0),
       "unique_tickers": len({(r.get("ticker") or "").upper() for r in pub if (r.get("ticker") or "").strip()}),
       "pdufa_recall_vs_bpc": recall, "bpc_overlap": overlap, "coverage_gaps": gaps,
       "stale_alias": qa.get("stale_alias", 0), "blank_drug": qa.get("blank_drug", 0),
       "scored_readouts": sum(tier.values()),
       "ALPHA": tier.get("ALPHA", 0), "BETA": tier.get("BETA", 0), "GAMMA": tier.get("GAMMA", 0),
       "DELTA": tier.get("DELTA", 0), "OMEGA": tier.get("OMEGA", 0),
       "archived_at": dt.datetime.now().isoformat(timespec="seconds")}

# 3) upsert into runs_index.csv (one row per date)
os.makedirs(RUNS_DIR, exist_ok=True)
idx_path = os.path.join(RUNS_DIR, "runs_index.csv")
cols = list(row.keys())
existing = []
if os.path.exists(idx_path):
    try: existing = [r for r in csv.DictReader(open(idx_path)) if r.get("date") != DATE]
    except Exception: existing = []
with open(idx_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for r in existing: w.writerow({c: r.get(c, "") for c in cols})
    w.writerow(row)

print(f"  [archive] {DATE}: snapshot -> {dest}/ ({len(copied)} files)")
print(f"  [archive] {row['total']} catalysts ({row['readouts']} readouts, {row['drugs']} PDUFA/drug, "
      f"{row['devices']} device), recall={recall}, tiers A/B/G/D/O="
      f"{row['ALPHA']}/{row['BETA']}/{row['GAMMA']}/{row['DELTA']}/{row['OMEGA']}")
print(f"  [archive] longitudinal index -> {idx_path}")
