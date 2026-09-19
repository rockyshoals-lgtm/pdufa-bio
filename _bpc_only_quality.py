"""The 15 BPC-only near-term phase readouts: are they REAL dates or placeholders?

If BPC "has" a name we lack but the date is a New Year's Eve bucket, the coverage gap is
much less meaningful than a raw count suggests. Measure before treating it as a gap.
"""
import csv, datetime as dt, glob, io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today()
from openpyxl import load_workbook

MISS = ["ACAD", "ANIX", "CAMP", "CATX", "CNTB", "CRBP", "ENTX", "EVAX",
        "GALT", "IMMX", "KTTA", "LLY", "MNOV", "NBP", "NKTR"]


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


snap = sorted(glob.glob(os.path.join(HERE, "bpc_data", "fda_*.xlsx")))[-1]
ws = load_workbook(snap, read_only=True).worksheets[0]
hdr, rows = None, []
for r in ws.iter_rows(values_only=True):
    if hdr is None:
        hdr = [str(x or "").strip() for x in r]
        continue
    rows.append(dict(zip(hdr, r)))

lim = (TODAY + dt.timedelta(days=60)).isoformat()
print(f"{'tkr':<6}{'BPC date':<12}{'shape':<14}{'conference':<34}stage")
print("-" * 96)
real = ph = 0
for tk in MISS:
    for r in rows:
        if str(r.get("Ticker") or "").strip().upper() != tk:
            continue
        d = ds(r.get("Catalyst Date"))
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d) or not (TODAY.isoformat() <= d <= lim):
            continue
        if "PHASE" not in str(r.get("Stage") or "").upper():
            continue
        p = is_placeholder(d)
        shape = "PLACEHOLDER" if p else "real day"
        if p:
            ph += 1
        else:
            real += 1
        conf = str(r.get("Conference") or "").strip()
        print(f"{tk:<6}{d:<12}{shape:<14}{conf[:32]:<34}{str(r.get('Stage') or '')[:22]}")
        break
print("-" * 96)
print(f"{real} carry a genuinely specific day; {ph} are placeholder-shaped buckets.")
print("\nA placeholder-shaped 'miss' is a bucket we would have labelled Q4/2H anyway —")
print("the coverage gap that actually matters is the 'real day' rows.")
