"""RED TEAM the 'day precision' claim before anything gets published.

Suspicion: 11 names share 2026-08-31 and 12+ share 2026-09-15. Real company guidance does
not cluster like that. Those are MONTH markers rendered as a date -- armed_watchlist writes
'Readout 2026-09-15 [month]' for "sometime in September", and CT.gov month-only primary
completion dates parse to the month END. Both LOOK like a day and are not one.

Publishing a placeholder as a hard date is worse than publishing nothing: a reader (or our
own prearm) would sit on the wrong morning. So classify every 'day' date as REAL or
PLACEHOLDER and recount.
"""
import csv, os, re, sys, collections, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    fp = os.path.join(HERE, p)
    return list(csv.DictReader(open(fp, encoding="utf-8-sig", errors="replace"))) \
        if os.path.exists(fp) else []


F, C, G = load("readout_forward.csv"), load("readout_calendar.csv"), load("ctgov_readouts.csv")

# 1. how do the "day" dates cluster? A real calendar is spread out.
allday = collections.Counter()
for r in F:
    d = (r.get("window_alt") or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        allday[d] += 1
print("MOST COMMON 'day-precision' dates in window_alt (a real calendar does NOT clump):")
for d, n in allday.most_common(12):
    dd = datetime.date.fromisoformat(d)
    lastday = (datetime.date(dd.year + (dd.month == 12), dd.month % 12 + 1, 1)
               - datetime.timedelta(days=1)).day
    tag = ("MONTH-END placeholder" if dd.day == lastday
           else "MID-MONTH placeholder" if dd.day == 15
           else "looks real")
    print(f"   {d}  x{n:<3}  {tag}")

# 2. classify
def is_placeholder(d):
    try:
        dd = datetime.date.fromisoformat(d)
    except Exception:
        return False
    lastday = (datetime.date(dd.year + (dd.month == 12), dd.month % 12 + 1, 1)
               - datetime.timedelta(days=1)).day
    return dd.day in (1, 15, lastday)


real, ph = [], []
seen = set()
for r in F:
    tk, d = r["ticker"], (r.get("window_alt") or "").strip()
    if tk in seen or not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        continue
    seen.add(tk)
    (ph if is_placeholder(d) else real).append((d, tk, "armed"))

# EDGAR hard dates ('August 22, 2026') are company-stated -> genuinely real
edgar_real = []
for r in F:
    w = (r.get("window") or "").strip()
    if re.match(r"^[A-Z][a-z]+ \d{1,2},? \d{4}$", w):
        edgar_real.append((w, r["ticker"], "EDGAR-stated"))

# CT.gov: month-end PCDs are month precision, everything else is a real locked date
ct_real, ct_ph = [], []
for r in G:
    d = (r.get("pcd") or "").strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        continue
    (ct_ph if is_placeholder(d) else ct_real).append((d, r.get("ticker"), "CTGOV"))

print(f"\nRECOUNT")
print(f"  armed window_alt : {len(real)} real-looking, {len(ph)} PLACEHOLDER "
      f"(1st / 15th / month-end)")
print(f"  EDGAR stated day : {len(edgar_real)} (company said an actual date -- trustworthy)")
print(f"  CT.gov PCD       : {len(ct_real)} real-looking, {len(ct_ph)} month-end placeholder")

trust = {}
for d, tk, s in ct_real + real + edgar_real:      # weakest first, strongest wins
    if tk:
        trust[tk] = (d, s)
print(f"\n  GENUINELY DAY-PRECISE, deduped by ticker: {len(trust)}")
print(f"  (vs the 278 the naive count claimed)")

today = datetime.date(2026, 8, 22).isoformat()


def norm(d):
    try:
        return datetime.datetime.strptime(d.replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
    except Exception:
        return d


fwd = sorted([(norm(d), tk, s) for tk, (d, s) in trust.items() if norm(d) >= today])
print(f"\n  FORWARD and genuinely dated: {len(fwd)}")
for d, tk, s in fwd[:30]:
    print(f"    {d}  {tk:<7} {s}")

print(f"\n  PLACEHOLDER-ONLY tickers (month precision, must NOT be published as a day): "
      f"{len(ph)+len(ct_ph)}")
months = collections.Counter(d[:7] for d, tk, s in ph + ct_ph)
print("   by month:", dict(sorted(months.items())))
