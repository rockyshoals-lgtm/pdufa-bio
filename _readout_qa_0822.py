"""QA the 8/22 readout run: coverage, DATE PRECISION, and what is still blocking preload.

The bar has moved. It is no longer "did we find a window" — 82% of rows had one on 8/20.
It is "is the date SHARP ENOUGH to preload and to publish on pdufa.bio". A row saying
'Q4 2026' cannot arm a board on a given morning and should not be shown as a date to a
reader. So this grades every row into precision buckets and reports what would actually
be publishable.
"""
import csv, os, re, sys, json, collections, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date(2026, 8, 22)


def load(p):
    fp = os.path.join(HERE, p)
    return list(csv.DictReader(open(fp, encoding="utf-8-sig", errors="replace"))) \
        if os.path.exists(fp) else []


F = load("readout_forward.csv")
C = load("readout_calendar.csv")
G = load("ctgov_readouts.csv")
print(f"forward {len(F)} rows | calendar {len(C)} rows | ctgov {len(G)} rows\n")


def precision(s):
    """DAY | MONTH | QUARTER | HALF | YEAR | none — how sharp is this label?"""
    t = (s or "").strip()
    if not t:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
        return "DAY"
    if re.match(r"^(January|February|March|April|May|June|July|August|September|October|"
                r"November|December)\s+\d{1,2},?\s+\d{4}$", t, re.I):
        return "DAY"
    if re.match(r"^\d{4}-\d{2}$", t):
        return "MONTH"
    if re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}$", t, re.I):
        return "MONTH"
    if re.match(r"^Q[1-4]\s+\d{4}$", t, re.I):
        return "QUARTER"
    if re.match(r"^[12]H\s+\d{4}$", t, re.I) or re.match(r"^MID\s+\d{4}$", t, re.I):
        return "HALF"
    if re.match(r"^\d{4}$", t):
        return "YEAR"
    return "OTHER"


print("=" * 92)
print("  DATE PRECISION — the preload/publish bar")
print("=" * 92)
for name, rows, col in (("forward.window", F, "window"),
                        ("forward.window_alt", F, "window_alt"),
                        ("calendar.best_date", C, "best_date")):
    c = collections.Counter(precision(r.get(col)) for r in rows)
    tot = sum(v for k, v in c.items() if k)
    sharp = c.get("DAY", 0) + c.get("MONTH", 0)
    print(f"  {name:<22} dated {tot:>4}/{len(rows):<4}  "
          f"DAY {c.get('DAY',0):>3}  MONTH {c.get('MONTH',0):>3}  Q {c.get('QUARTER',0):>3}  "
          f"H {c.get('HALF',0):>3}  YR {c.get('YEAR',0):>3}  other {c.get('OTHER',0):>3}"
          f"   -> sharp(DAY+MONTH) {sharp} ({100*sharp/max(1,len(rows)):.0f}%)")

# best available precision per ticker, across ALL sources
best = {}
RANK = {"DAY": 4, "MONTH": 3, "QUARTER": 2, "HALF": 1, "YEAR": 0}
for r in F:
    for col in ("window", "window_alt"):
        p = precision(r.get(col))
        if p in RANK:
            tk = r["ticker"]
            if tk not in best or RANK[p] > RANK[best[tk][0]]:
                best[tk] = (p, r.get(col), "EDGAR" if col == "window" else "armed")
for r in C:
    p = precision(r.get("best_date"))
    if p in RANK:
        tk = r["ticker"]
        if tk not in best or RANK[p] > RANK[best[tk][0]]:
            best[tk] = (p, r.get("best_date"), r.get("date_source") or "cal")
for r in G:
    p = precision(r.get("pcd"))
    if p in RANK:
        tk = r.get("ticker")
        if tk and (tk not in best or RANK[p] > RANK[best[tk][0]]):
            best[tk] = (p, r.get("pcd"), "CTGOV")

c = collections.Counter(v[0] for v in best.values())
sharp = c.get("DAY", 0) + c.get("MONTH", 0)
print(f"\n  BEST-OF-ALL-SOURCES, per ticker ({len(best)} tickers):")
print(f"    DAY {c.get('DAY',0)}  MONTH {c.get('MONTH',0)}  QUARTER {c.get('QUARTER',0)}  "
      f"HALF {c.get('HALF',0)}  YEAR {c.get('YEAR',0)}")
print(f"    PUBLISHABLE (day or month precision): {sharp}/{len(best)} "
      f"({100*sharp/max(1,len(best)):.0f}%)")

print("\n" + "=" * 92)
print("  HARD DATES (day precision) — what can go straight onto pdufa.bio and prearm")
print("=" * 92)
day = [(v[1], tk, v[2]) for tk, v in best.items() if v[0] == "DAY"]


def key(s):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return s
    try:
        return datetime.datetime.strptime(s.replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
    except Exception:
        return "9999"


day.sort(key=lambda x: key(x[0]))
fwd = [d for d in day if key(d[0]) >= TODAY.isoformat()]
print(f"  {len(day)} day-precision rows, {len(fwd)} still in the future:")
for d, tk, src in fwd[:30]:
    print(f"    {key(d)}  {tk:<7} ({src})   raw='{d}'")

print("\n" + "=" * 92)
print("  STILL VAGUE — armed READOUT names with only quarter/half/year precision")
print("=" * 92)
vague = [(tk, v) for tk, v in best.items() if v[0] in ("QUARTER", "HALF", "YEAR")]
arm = {r["ticker"]: r.get("armed_lane") for r in F if r.get("armed_lane")}
va = [(tk, v) for tk, v in vague if arm.get(tk)]
print(f"  {len(vague)} vague total, {len(va)} of them on an armed lane (the ones that matter):")
for tk, v in sorted(va, key=lambda x: x[1][1])[:25]:
    print(f"    {tk:<7} {v[1]:<12} {arm.get(tk,''):<8} (from {v[2]})")

# where CT.gov could sharpen an EDGAR-vague row but has no entry
gt = {r.get("ticker") for r in G if r.get("ticker")}
gap = [tk for tk, v in va if tk not in gt]
print(f"\n  of those, {len(gap)} have NO CT.gov row at all — the sharpening gap:")
print("   ", ", ".join(sorted(gap)[:40]))
