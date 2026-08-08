"""RED TEAM readout_forward.csv — grade MY OWN scanner's output before David trades it.

The scan ran clean: 105 FTS calls, 69 rows, no errors. That says NOTHING about whether the
rows are TRUE. Three failure modes visible on inspection, so measure all three.
"""
import csv, datetime as dt, os, re, sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = sys.argv[1] if len(sys.argv) > 1 else "readout_forward.csv"
rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
print(f"{len(rows)} rows from {os.path.basename(SRC)}\n")

MON = ("january february march april may june july august september october november december"
       .split())


def as_date(s):
    """Parse 'July 15, 2026' / 'JULY 6, 2026' -> date. None if it is a vague period."""
    m = re.match(r"\s*([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\s*$", s or "")
    if not m:
        return None
    try:
        mo = MON.index(m.group(1).lower()[:20]) + 1
    except ValueError:
        return None
    try:
        return dt.date(int(m.group(3)), mo, int(m.group(2)))
    except ValueError:
        return None


# a window is only USEFUL if it points FORWARD from the filing. Vague periods (1H 2027,
# Q4 2026) are real guidance. A hard date equal to the filing date is the 8-K's own dateline.
PAST_RX = re.compile(
    r"\b(reports?|reported|announces?|announced|presents?|presented|shows?|showed|"
    r"demonstrat\w+|achiev\w+|met\b|update)\b.{0,60}\b(positive|results?|data|readout)\b|"
    r"\b(positive|topline|top-line)\b.{0,40}\b(results?|data)\b", re.I)
FWD_RX = re.compile(
    r"\b(expects?|expected|anticipat\w+|plans?|on track|will report|to report|upcoming|"
    r"guidance|projected)\b", re.I)
BIO_RX = re.compile(
    r"\b(phase\s*[123ib]|clinical|patients?|therapeut|pharma|biotech|trial|dose|efficacy|"
    r"endpoint|oncolog|FDA|IND\b|NDA\b|BLA\b|cohort|placebo|mg/kg|biolog)\b", re.I)

buck = collections.Counter()
echo, past_win, real_fwd, no_win = [], [], [], []
mis_fwd, non_bio = [], []

for r in rows:
    tk = r.get("ticker", "?")
    w = (r.get("window") or "").strip()
    ctx = re.sub(r"\s+", " ", (r.get("context") or ""))
    try:
        filed = dt.date(*map(int, r["filed"].split("-")))
    except Exception:
        filed = None

    # --- FAILURE 1: the window is the filing's own dateline -----------------------------
    d = as_date(w)
    if not w:
        buck["blank"] += 1
        no_win.append(tk)
    elif d and filed and abs((d - filed).days) <= 3:
        buck["ECHO (window == filed date)"] += 1
        echo.append((tk, r["filed"], w))
    elif d and filed and d < filed:
        buck["PAST (window before the filing)"] += 1
        past_win.append((tk, r["filed"], w))
    elif d:
        buck["hard date, forward"] += 1
        real_fwd.append((tk, r["filed"], w))
    else:
        buck["VAGUE PERIOD (1H 2027, Q4 26)"] += 1
        real_fwd.append((tk, r["filed"], w))

    # --- FAILURE 2: labeled FORWARD but the context is a PAST readout -------------------
    if PAST_RX.search(ctx) and not FWD_RX.search(ctx):
        mis_fwd.append((tk, ctx[:86]))

    # --- FAILURE 3: not biotech at all --------------------------------------------------
    if not BIO_RX.search(ctx + " " + (r.get("company") or "")):
        non_bio.append((tk, (r.get("company") or "?")[:28], ctx[:64]))

print("=" * 92)
print("  FAILURE 1 — THE `window` COLUMN")
print("=" * 92)
for k, v in buck.most_common():
    print(f"  {v:>3}  {k}")
bad = buck["ECHO (window == filed date)"] + buck["PAST (window before the filing)"]
got = len(rows) - buck["blank"]
print(f"\n  {bad} of {got} extracted windows ({bad/max(got,1)*100:.0f}%) are NOT a readout window.")
print("\n  ECHO — the LEAD regex grabbed the 8-K dateline / slide cover date:")
for tk, f, w in echo[:9]:
    print(f"    {tk:<6} filed {f}  ->  window '{w}'")
print("\n  PAST — a fiscal-period reference (10-Q boilerplate), not guidance:")
for tk, f, w in past_win[:6]:
    print(f"    {tk:<6} filed {f}  ->  window '{w}'")

print("\n" + "=" * 92)
print("  FAILURE 2 — LABELED `FORWARD`, BUT THE CONTEXT IS A READOUT THAT ALREADY PRINTED")
print("=" * 92)
for tk, c in mis_fwd[:12]:
    print(f"    {tk:<6} {c}")
print(f"\n  {len(mis_fwd)} of {len(rows)} FORWARD rows ({len(mis_fwd)/max(len(rows),1)*100:.0f}%) "
      f"read as PAST tense.")

print("\n" + "=" * 92)
print("  FAILURE 3 — NOT BIOTECH")
print("=" * 92)
for tk, co, c in non_bio[:10]:
    print(f"    {tk:<6} {co:<28} {c}")
print(f"\n  {len(non_bio)} of {len(rows)} rows have no biotech vocabulary anywhere.")

print("\n" + "=" * 92)
print("  WHAT SURVIVES — genuine forward guidance, and WHEN")
print("=" * 92)
today = dt.date(2026, 7, 17)


def near(w):
    """Does this window plausibly OPEN within ~90 days? Vague periods -> earliest day."""
    s = (w or "").lower()
    y = re.search(r"20(2[6-9]|3\d)", s)
    if not y:
        return None
    yr = int(y.group(0))
    if re.search(r"\b(1h|first half|early)\b", s): start = dt.date(yr, 1, 1)
    elif re.search(r"\b(2h|second half|late|latter)\b", s): start = dt.date(yr, 7, 1)
    elif re.search(r"\bq1|first quarter\b", s): start = dt.date(yr, 1, 1)
    elif re.search(r"\bq2|second quarter\b", s): start = dt.date(yr, 4, 1)
    elif re.search(r"\bq3|third quarter\b", s): start = dt.date(yr, 7, 1)
    elif re.search(r"\bq4|fourth quarter\b", s): start = dt.date(yr, 10, 1)
    elif re.search(r"\bmid-?\b", s): start = dt.date(yr, 6, 1)
    else: return None
    return (start - today).days


live = []
for tk, f, w in real_fwd:
    dd = near(w)
    live.append((dd if dd is not None else 9999, tk, f, w))
for dd, tk, f, w in sorted(live):
    when = "OPEN NOW" if dd <= 0 else (f"opens in ~{dd}d" if dd < 9999 else "unparsed")
    print(f"    {tk:<6} {w:<26} {when}")
print(f"\n  {len(real_fwd)} rows carry a real forward window. "
      f"{sum(1 for d,_,_,_ in live if d <= 0)} are OPEN NOW.")
print("\n  NOTE: not one of these is a DATE. Forward guidance is quarters and halves — a PLAN,")
print("  not a commitment. This scan cannot tell you 'KLRS prints Tuesday'. Nothing can.")
