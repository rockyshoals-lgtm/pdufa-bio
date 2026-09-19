"""Standalone false-GOLD audit — does not depend on _verify_gold_dates.py, which also reverted.

A GOLD row is what we tell people to preload a trade against. A GOLD row whose date lands on
the 1st / 15th / month-end is a vendor placeholder we promoted by mistake.
"""
import csv, collections, datetime as dt, io, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = list(csv.DictReader(io.open("readout_gold_dates.csv", encoding="utf-8-sig",
                                errors="replace", newline="")))
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
leak, gold_leak, nye_gold = [], [], []
for r in R:
    d = (r.get("date") or "").strip()
    if not DAY.match(d):
        continue
    try:
        dd = dt.date.fromisoformat(d)
    except Exception:
        continue
    last = (dt.date(dd.year + (dd.month == 12), dd.month % 12 + 1, 1)
            - dt.timedelta(days=1)).day
    if dd.day in (1, 15, last):
        leak.append(r)
        if (r.get("confidence") or "") == "GOLD":
            gold_leak.append(r)
            if d.endswith("-12-31"):
                nye_gold.append(r)
print(f"{len(R)} rows | placeholder-shaped days: {len(leak)} | of which GOLD: {len(gold_leak)}"
      f" | GOLD on New Year's Eve: {len(nye_gold)}")
print(f"tiers: {dict(collections.Counter(r['confidence'] for r in R))}")
print(f"precision: {dict(collections.Counter(r['precision'] for r in R))}")
if gold_leak:
    print("\nFALSE GOLD rows (a placeholder we told people to trade on):")
    for r in gold_leak[:14]:
        print(f"   {r['ticker']:<7}{r['date']}  {r['precision']:<6}{r['source'][:52]}")
sys.exit(1 if gold_leak else 0)
