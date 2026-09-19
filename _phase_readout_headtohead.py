"""PHASE READOUTS ONLY: us vs BiopharmaCatalyst. Quantity AND date quality.

Previous comparisons in this session mixed PDUFAs, filings and phase readouts together,
which flatters whichever source is heavier in one category. This isolates PHASE READOUTS
(Stage contains "Phase") and asks three separate questions:

  Q1 QUANTITY  — how many forward-dated phase readouts does each side carry, and how much
                 do the ticker sets actually overlap?
  Q2 PRECISION — of those, how many carry a date specific enough to act on?
  Q3 UNIQUE    — who has what the other does not, and is the difference real coverage or
                 just a different slice of the same universe?

Honest framing note: BPC's file is a curated commercial product covering the whole
catalyst landscape. Our readout set is assembled from EDGAR guidance + CT.gov primary
completion dates + our conference miner. These are not the same object, and "we have more
rows" would be a meaningless claim if the rows are different KINDS of thing. Reported
accordingly.
"""
import csv, collections, datetime as dt, io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today()
from openpyxl import load_workbook


def bpc_rows(path):
    ws = load_workbook(path, read_only=True).worksheets[0]
    hdr, out = None, []
    for r in ws.iter_rows(values_only=True):
        if hdr is None:
            hdr = [str(x or "").strip() for x in r]
            continue
        out.append(dict(zip(hdr, r)))
    return out


def ds(v):
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v or "")[:10]


def is_placeholder(iso):
    try:
        d = dt.date.fromisoformat(iso)
    except Exception:
        return None
    last = (dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
            - dt.timedelta(days=1)).day
    return d.day in (1, 15, last)


def load_csv(p):
    fp = os.path.join(HERE, p)
    return list(csv.DictReader(io.open(fp, encoding="utf-8-sig", errors="replace",
                                       newline=""))) if os.path.exists(fp) else []


import glob
snap = sorted(glob.glob(os.path.join(HERE, "bpc_data", "fda_*.xlsx")))[-1]
B = bpc_rows(snap)
print("=" * 94)
print(f"  PHASE READOUTS HEAD-TO-HEAD   (BPC snapshot: {os.path.basename(snap)})")
print("=" * 94)

# ---- BPC phase readouts, forward-dated
bp = []
for r in B:
    stage = str(r.get("Stage") or "")
    d = ds(r.get("Catalyst Date"))
    tk = str(r.get("Ticker") or "").strip().upper()
    if not tk or "PHASE" not in stage.upper():
        continue
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d) or d < TODAY.isoformat():
        continue
    bp.append({"tk": tk, "date": d, "stage": stage,
               "conf": str(r.get("Conference") or "").strip(),
               "ph": is_placeholder(d)})
bp_tk = {r["tk"] for r in bp}

# ---- our phase-readout-ish set
FWD = load_csv("readout_forward.csv")          # EDGAR: "a readout is coming"
CTG = load_csv("ctgov_readouts.csv")           # CT.gov primary completion dates
CONF = load_csv("conference_presenters.csv")   # our presenter miner
fwd_tk = {(r.get("ticker") or "").upper() for r in FWD if (r.get("window") or "").strip()}
ctg_tk = {(r.get("ticker") or "").upper() for r in CTG}
conf_tk = {(r.get("ticker") or "").upper() for r in CONF}
ours_tk = (fwd_tk | ctg_tk | conf_tk) - {""}

print(f"\n  Q1 — QUANTITY (forward-dated phase readouts)")
print(f"     BPC phase-readout rows            : {len(bp):>5}   ({len(bp_tk)} tickers)")
print(f"     OURS, EDGAR guidance windows      : {len(fwd_tk):>5} tickers")
print(f"     OURS, CT.gov completion dates     : {len(ctg_tk):>5} tickers")
print(f"     OURS, conference presenters       : {len(conf_tk):>5} tickers")
print(f"     OURS, union                       : {len(ours_tk):>5} tickers")
inter = bp_tk & ours_tk
print(f"\n     overlap (in BOTH)                 : {len(inter):>5} tickers"
      f"  = {100*len(inter)/max(1,len(bp_tk)):.0f}% of BPC's, "
      f"{100*len(inter)/max(1,len(ours_tk)):.0f}% of ours")
print(f"     BPC only                          : {len(bp_tk - ours_tk):>5}")
print(f"     OURS only                         : {len(ours_tk - bp_tk):>5}")

# ---- Q2 precision
print(f"\n  Q2 — DATE PRECISION on those phase readouts")
bph = [r for r in bp if r["ph"]]
print(f"     BPC: {len(bp)} rows, {len(bph)} placeholder-shaped "
      f"= {100*len(bph)/max(1,len(bp)):.0f}%   "
      f"(NYE: {sum(1 for r in bp if r['date'].endswith('-12-31'))})")
print(f"          -> genuinely specific days: {len(bp)-len(bph)} "
      f"= {100*(len(bp)-len(bph))/max(1,len(bp)):.0f}%")
cd = collections.Counter((r.get("pcd_precision") or "?") for r in CTG)
print(f"     OURS CT.gov pcd_precision: {dict(cd)}")
wp = collections.Counter((r.get("window_precision") or "(blank)") for r in FWD)
print(f"     OURS EDGAR window_precision: {dict(wp.most_common(6))}")
cp = collections.Counter((r.get("date_precision") or "?") + "/" +
                         (r.get("date_basis") or "?") for r in CONF)
print(f"     OURS conference: {dict(cp)}")

# ---- Q3 who has what
print(f"\n  Q3 — WHAT EACH SIDE UNIQUELY CARRIES (next 60 days)")
lim = (TODAY + dt.timedelta(days=60)).isoformat()
bonly = sorted({r["tk"] for r in bp if r["date"] <= lim} - ours_tk)
print(f"     BPC-only tickers with a phase readout inside 60d ({len(bonly)}):")
print("       " + ", ".join(bonly[:26]) + ("..." if len(bonly) > 26 else ""))
conf_only = sorted(conf_tk - bp_tk)
print(f"\n     OUR conference presenters BPC has no phase row for ({len(conf_only)}):")
print("       " + ", ".join(conf_only) if conf_only else "       (none)")
print("\n  Informational only — not investment advice.")
