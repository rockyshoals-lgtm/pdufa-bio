"""Audit the fresh readout_forward.csv (8/20 run): fill rates, near-term calendar, gaps."""
import csv, re, json, os, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = list(csv.DictReader(open(os.path.join(HERE, "readout_forward.csv"),
                                encoding="utf-8", errors="replace")))
TODAY = datetime.date(2026, 8, 20)

MON = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_win(w):
    """Return (start, end) dates for a window string, or None."""
    if not w:
        return None
    w = w.strip().lower()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", w)
    if m:
        d = datetime.date(int(m[1]), int(m[2]), int(m[3]))
        return d, d
    m = re.match(r"^(\d{4})-(\d{2})$", w)
    if m:
        y, mo = int(m[1]), int(m[2])
        nd = (datetime.date(y + (mo == 12), (mo % 12) + 1, 1) - datetime.timedelta(days=1))
        return datetime.date(y, mo, 1), nd
    m = re.match(r"^([hq])([12349])[- ]?(\d{4})$", w)
    if m:
        y = int(m[3])
        if m[1] == "h":
            s = datetime.date(y, 1 if m[2] == "1" else 7, 1)
            e = datetime.date(y, 6, 30) if m[2] == "1" else datetime.date(y, 12, 31)
        else:
            q = int(m[2])
            s = datetime.date(y, 3 * q - 2, 1)
            e = (datetime.date(y + (q == 4), (3 * q % 12) + 1, 1) - datetime.timedelta(days=1))
        return s, e
    m = re.match(r"^(\d{4})$", w)
    if m:
        return datetime.date(int(m[1]), 1, 1), datetime.date(int(m[1]), 12, 31)
    m = re.match(r"^([a-z]{3})[a-z]*[- ]?(\d{4})$", w)
    if m and m[1] in MON:
        y, mo = int(m[2]), MON[m[1]]
        nd = (datetime.date(y + (mo == 12), (mo % 12) + 1, 1) - datetime.timedelta(days=1))
        return datetime.date(y, mo, 1), nd
    return None


n = len(ROWS)
kinds = collections.Counter(r["kind"] for r in ROWS)
just = sum(1 for r in ROWS if (r.get("just_reported") or "").startswith("YES"))
winfill = sum(1 for r in ROWS if (r.get("window") or "").strip())
altonly = sum(1 for r in ROWS if not (r.get("window") or "").strip()
              and (r.get("window_alt") or "").strip())
lanes = collections.Counter((r.get("armed_lane") or "NONE") for r in ROWS)
print(f"rows {n} | kinds {dict(kinds)} | just_reported {just}")
print(f"window filled {winfill} ({100*winfill/n:.0f}%) | alt-only rescue {altonly} "
      f"| total dated {winfill+altonly} ({100*(winfill+altonly)/n:.0f}%)")
print(f"armed lanes: {dict(lanes)}")

# near-term calendar: windows that start within 45d or already open and end ahead
cal = []
for r in ROWS:
    w = (r.get("window") or "").strip() or (r.get("window_alt") or "").strip()
    p = parse_win(w)
    if not p:
        continue
    s, e = p
    if e < TODAY or s > TODAY + datetime.timedelta(days=60):
        continue
    span = (e - s).days
    cal.append((s, e, span, r))

cal.sort(key=lambda x: (x[1], x[2]))          # soonest END first, tightest window first
print(f"\nNEAR-TERM (window open now or opening <=60d): {len(cal)}")
print(f"{'tk':<7}{'win':<16}{'span':>5} {'lane':<9}{'kind':<9}{'filed':<12} phrases")
seen = set()
for s, e, span, r in cal[:40]:
    tk = r["ticker"]
    if tk in seen:
        continue
    seen.add(tk)
    w = (r.get("window") or "").strip() or (r.get("window_alt") or "").strip() + "*"
    ph = (r.get("phrases") or "")[:38]
    print(f"{tk:<7}{w:<16}{span:>4}d {(r.get('armed_lane') or '-'):<9}"
          f"{r['kind']:<9}{r['filed']:<12} {ph}")

# hard dates (single-day windows) anywhere forward
hard = [(s, r) for s, e, sp, r in cal if sp == 0]
print(f"\nHARD DATES in the near window: {len(hard)}")
for s, r in sorted(hard):
    print(f"  {s}  {r['ticker']:<7} {(r.get('armed_lane') or '-'):<8} {(r.get('phrases') or '')[:60]}")

# unparseable window strings (improvement target)
bad = collections.Counter()
for r in ROWS:
    for w in ((r.get("window") or "").strip(), (r.get("window_alt") or "").strip()):
        if w and not parse_win(w):
            bad[w.lower()] += 1
print(f"\nUNPARSEABLE window strings ({sum(bad.values())} rows): {dict(bad.most_common(15))}")
