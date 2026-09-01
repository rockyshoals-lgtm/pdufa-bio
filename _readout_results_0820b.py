"""Post-run analysis: fill-rate deltas vs the 07:53 run + the near-term master calendar."""
import csv, os, sys, collections, datetime, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date(2026, 8, 20)


def load(p):
    fp = os.path.join(HERE, p)
    return list(csv.DictReader(open(fp, encoding="utf-8-sig", errors="replace"))) \
        if os.path.exists(fp) else []


# freshest forward file
fwd_p = max((p for p in ("readout_forward.csv", "readout_forward_new.csv")
             if os.path.exists(os.path.join(HERE, p))),
            key=lambda p: os.path.getmtime(os.path.join(HERE, p)))
F = load(fwd_p)
n = len(F)
w = sum(1 for r in F if (r.get("window") or "").strip())
alt = sum(1 for r in F if not (r.get("window") or "").strip()
          and (r.get("window_alt") or "").strip())
canon = sum(1 for r in F if re.match(r"^(Q[1-4]|[12]H|MID)\s+20\d{2}$|^20\d{2}",
                                     (r.get("window") or "").strip()))
print(f"FORWARD ({fwd_p}): {n} rows | window {w} ({100*w/n:.0f}%) | +alt {alt} "
      f"| dated {w+alt} ({100*(w+alt)/n:.0f}%) | canonical labels {canon}")
print("   (07:53 run was: 197 rows, 58 window (29%), 139 dated (71%))")

C = load("ctgov_readouts.csv")
print(f"CTGOV: {len(C)} tickers with a specific-dated trial (was pre-widening universe ~374)")

CAL = load("readout_calendar.csv")
print(f"CALENDAR: {len(CAL)} rows | cols: {list(CAL[0].keys()) if CAL else '-'}\n")

# near-term: best_date within 45 days (or pending/overdue)
def pd(s):
    m = re.match(r"^(20\d{2})-(\d{2})(?:-(\d{2}))?", (s or "").strip())
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 15))
    return None


datecols = [c for c in (CAL[0].keys() if CAL else []) if "date" in c.lower()]
near = []
for r in CAL:
    d = None
    for c in datecols:
        d = d or pd(r.get(c))
    if d and TODAY - datetime.timedelta(days=30) <= d <= TODAY + datetime.timedelta(days=45):
        near.append((d, r))
near.sort(key=lambda x: x[0])
print(f"NEAR-TERM (best date -30d..+45d): {len(near)}")
for d, r in near[:30]:
    vals = " | ".join(f"{k}={v}" for k, v in list(r.items())[:7] if v)
    print(f"  {d}  {vals[:130]}")
