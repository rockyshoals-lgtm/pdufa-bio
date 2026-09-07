"""Verify the gold-date file is a usable calendar feed: every date parses to either an
ISO date/month or a canonical bucket label. Raw prose in the date column is a FAIL."""
import csv, io, re, collections, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = list(csv.DictReader(io.open("readout_gold_dates.csv", encoding="utf-8-sig",
                                errors="replace", newline="")))
ISO = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
BUCKET = re.compile(r"^(Q[1-4]|[12]H|MID)\s+20\d\d$", re.I)
good, bad = 0, collections.Counter()
for r in R:
    d = (r.get("date") or "").strip()
    if ISO.match(d) or BUCKET.match(d):
        good += 1
    else:
        bad[d] += 1
print(f"{len(R)} rows: {good} canonical, {sum(bad.values())} raw prose")
for k, v in bad.most_common(10):
    print(f"   {v:>3}x  {k[:60]}")

lbl = collections.Counter((r.get("date") or "") for r in R if not ISO.match(r.get("date") or ""))
print("\nbucket labels in use:")
for k, v in lbl.most_common(10):
    print(f"   {v:>3}x  {k}")
sys.exit(1 if bad else 0)
