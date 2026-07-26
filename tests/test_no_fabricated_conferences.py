"""CI guard: the conference feed must never contain a fabricated future event.

A page that renders perfectly and shows a conference that never happens is worse than a page
with a layout bug. /llms.txt is LIVE — a phantom here gets laundered into ChatGPT/Perplexity
answers at scale, where it cannot be clawed back.
"""
import csv, re, sys
import pandas as pd

FUTURE = re.compile(r"\b(will\s+(?:be\s+)?present\w*|to\s+be\s+presented|to\s+present|"
                    r"accepted\s+for|scheduled\s+to\s+present|upcoming)\b", re.I)
YEAR   = re.compile(r"\b(20[12]\d)\b")
CANON  = "catalysts_out/conference_presentations_history.csv"
fail = 0

def bad(msg):
    global fail
    print(f"  FAIL {msg}")
    fail += 1

# 1) the file must be READABLE. A file that cannot be parsed is not a file.
try:
    d = pd.read_csv(CANON)
except Exception as e:
    print(f"  FAIL {CANON} is UNREADABLE: {e}")
    sys.exit(1)

with open(CANON, newline="", encoding="utf-8") as f:
    rows = list(csv.reader(f))
hdr = len(rows[0])
ragged = [i for i, r in enumerate(rows) if len(r) != hdr]
if ragged:
    bad(f"{len(ragged)} ragged rows (first at {ragged[0]}) — unescaped quote in a snippet?")

# 2) NO FABRICATED FUTURE EVENTS
today = pd.Timestamp("today").normalize()
for _, r in d.iterrows():
    dt_ = str(r.get("catalyst_date", ""))
    sn = str(r.get("snippet", ""))
    try:
        when = pd.Timestamp(dt_ if len(dt_) == 10 else dt_ + "-01")
    except Exception:
        continue
    if when <= today:
        continue
    if not FUTURE.search(sn):
        bad(f"FABRICATION: {r.get('ticker')} {r.get('conference')} {dt_} — future date, no future cue")
    yrs = [int(y) for y in YEAR.findall(sn)]
    if yrs and max(yrs) < when.year:
        bad(f"FABRICATION: {r.get('ticker')} {r.get('conference')} {dt_} — snippet only mentions {max(yrs)}")

# 3) no duplicates
dup = int(d.duplicated(subset=["ticker", "catalyst_date", "conference"]).sum())
if dup:
    bad(f"{dup} duplicate rows on (ticker, date, conference)")

# 4) no known-bad labels
for junk in ("ANE", "PRE-RELEA"):
    n = int((d["conference"] == junk).sum())
    if n:
        bad(f'{n} rows carry the junk label "{junk}"')

if fail:
    print(f"\n{fail} conference-feed integrity failure(s). DO NOT PUBLISH.")
    sys.exit(1)
print(f"conference feed clean: {len(d)} rows, 0 fabrications, 0 dupes, 0 junk labels, 0 ragged rows.")
