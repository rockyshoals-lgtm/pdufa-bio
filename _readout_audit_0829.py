"""Grade the 2026-08-28 readout miner run on ONE question: how close are the dates?

The whole point of the precision work was to stop treating a bucket ("Q4 2026", stored by
BPC as 2026-12-31) as if it were a day. So the scorecard is not "how many rows" -- it is
"how many rows carry a date we could actually preload a trade against."

Tiers, strictest first:
  GOLD   a real calendar day: CT.gov primary completion date, or an EDGAR/company-stated
         day that survived the placeholder screen
  FIRM   a month ("September 2026") -- tradeable as a window, not a day
  SOFT   a quarter/half/year bucket -- a watchlist entry, not a calendar entry
  NONE   no window at all
"""
import os, sys, csv, json, collections, datetime, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = r"C:\Users\dcmoo\Documents\Python\9realms"
TODAY = datetime.date(2026, 8, 29)


def rd(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


FWD = rd(os.path.join(R, "readout_forward.csv"))
CTG = rd(os.path.join(R, "ctgov_readouts.csv"))
CAL = rd(os.path.join(R, "readout_calendar.csv"))
print(f"readout_forward  {len(FWD):>5} rows   cols={len(FWD[0]) if FWD else 0}")
print(f"ctgov_readouts   {len(CTG):>5} rows   cols={len(CTG[0]) if CTG else 0}")
print(f"readout_calendar {len(CAL):>5} rows   cols={len(CAL[0]) if CAL else 0}")
if CAL:
    print(f"\ncalendar columns: {list(CAL[0])}")
if FWD:
    print(f"forward columns : {list(FWD[0])}")
if CTG:
    print(f"ctgov columns   : {list(CTG[0])}")

# ---------------------------------------------------------------- precision census
print("\n" + "=" * 92)
print("  PRECISION CENSUS -- readout_forward.csv (the EDGAR pass)")
print("=" * 92)
for col in ("window_precision", "window_alt_precision", "conference"):
    if FWD and col in FWD[0]:
        c = collections.Counter((r.get(col) or "").strip() or "(blank)" for r in FWD)
        print(f"  {col}:")
        for k, n in c.most_common(12):
            print(f"      {k:<16}{n:>5}  {100*n/len(FWD):>5.1f}%")
    else:
        print(f"  {col}: COLUMN MISSING")

# unique tickers, and how many have a DAY
if FWD:
    tk = collections.Counter(r.get("ticker") or r.get("tk") for r in FWD)
    print(f"\n  {len(tk)} unique tickers across {len(FWD)} filing rows "
          f"(median {sorted(tk.values())[len(tk)//2]} rows/ticker)")
    day = [r for r in FWD if (r.get("window_precision") or "").strip() == "DAY"]
    dtk = {r.get("ticker") for r in day}
    print(f"  DAY-precision: {len(day)} rows across {len(dtk)} tickers")

# ---------------------------------------------------------------- ct.gov specificity
print("\n" + "=" * 92)
print("  CT.GOV -- the specific-date source")
print("=" * 92)
if CTG:
    pc = collections.Counter((r.get("pcd_precision") or "").strip() or "(blank)" for r in CTG)
    for k, n in pc.most_common(10):
        print(f"      {k:<16}{n:>5}  {100*n/len(CTG):>5.1f}%")
    # how many pcd are real days vs month-end placeholders
    ends, firsts, mids, other = 0, 0, 0, 0
    fut = []
    for r in CTG:
        s = (r.get("pcd") or "").strip().lstrip("~")
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", s)
        if not m:
            continue
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        try:
            dt = datetime.date(y, mo, d)
        except ValueError:
            continue
        nxt = datetime.date(y + (mo == 12), (mo % 12) + 1, 1)
        last = (nxt - datetime.timedelta(days=1)).day
        if d == last:
            ends += 1
        elif d == 1:
            firsts += 1
        elif d == 15:
            mids += 1
        else:
            other += 1
        if dt >= TODAY:
            fut.append((dt, r))
    tot = ends + firsts + mids + other
    print(f"\n  shape of the {tot} parseable primary-completion dates:")
    print(f"      month-END (1st/15th/last = bucket placeholder): {ends+firsts+mids:>4} "
          f"= {100*(ends+firsts+mids)/max(1,tot):.0f}%   "
          f"[last {ends} / 1st {firsts} / 15th {mids}]")
    print(f"      genuine arbitrary day                        : {other:>4} "
          f"= {100*other/max(1,tot):.0f}%   <-- the only truly GOLD dates")
    print(f"\n  {len(fut)} of {tot} are still in the FUTURE (>= {TODAY})")

# ---------------------------------------------------------------- the merged calendar
print("\n" + "=" * 92)
print("  readout_calendar.csv -- THE MASTER VIEW, graded")
print("=" * 92)
if CAL:
    for col in ("confidence", "source", "precision", "best_precision", "status"):
        if col in CAL[0]:
            c = collections.Counter((r.get(col) or "").strip() or "(blank)" for r in CAL)
            print(f"  {col}: " + ", ".join(f"{k}={n}" for k, n in c.most_common(10)))
    # imminence
    up = []
    for r in CAL:
        for k in ("best_date", "date", "pcd", "window"):
            s = (r.get(k) or "").strip().lstrip("~")
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", s)
            if m:
                try:
                    dt = datetime.date(int(m[1]), int(m[2]), int(m[3]))
                except ValueError:
                    break
                if TODAY <= dt <= TODAY + datetime.timedelta(days=75):
                    up.append((dt, r, k))
                break
    up.sort(key=lambda x: x[0])
    print(f"\n  {len(up)} rows dated inside the next 75 days:")
    for dt, r, k in up[:35]:
        tkr = r.get("ticker") or r.get("tk") or "?"
        conf = (r.get("confidence") or r.get("source") or "")[:18]
        drug = (r.get("drug") or r.get("asset") or "")[:22]
        print(f"    {dt}  ({(dt-TODAY).days:>3}d)  {tkr:<7}{conf:<19}{drug:<24}"
              f"{(r.get('phase') or '')[:10]}")
