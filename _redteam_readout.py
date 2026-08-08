"""RED TEAM the MAX READOUT MINE — check every claim in run_readout_max.bat against the code
and against EDGAR itself.

The .bat makes six specific, falsifiable claims. Good. Falsifiable claims are the only kind
worth making, and they are the only kind you can be wrong about. So: check them.

  C1  quota = max(30, max_docs // len(GUIDANCE_PHRASES))
  C2  26 phrases, --max-docs 1500 -> quota 57  (the "wall of 57s")
  C3  "topline results" has 2,337 docs available; we take 57 = 2.4%
  C4  10 phrases: 12,900 available -> 570 taken = 4.4% coverage
  C5  6000 -> quota 230, "~4x the coverage"
  C6  "only 17% of workbook rows are company-stated"

And the question the .bat does NOT ask: is the sample we take BIASED?
"""
import json, os, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

src = open(os.path.join(HERE, "phase_readout_miner.py"), encoding="utf-8").read()

print("=" * 96)
print("  C1/C2 — THE QUOTA FORMULA AND THE 'WALL OF 57s'")
print("=" * 96)
m = re.search(r"quota\s*=\s*max\(30,\s*max_docs\s*//\s*max\(1,\s*len\(GUIDANCE_PHRASES\)\)\)", src)
print(f"  formula in code: {'CONFIRMED' if m else 'NOT FOUND — the .bat describes code that is not there'}")

# count the phrases for real
blk = src[src.find("GUIDANCE_PHRASES = ["):]
blk = blk[:blk.find("\n]")]
phrases = re.findall(r'^\s*"([^"]+)"', blk, re.M)
n = len(phrases)
print(f"  GUIDANCE_PHRASES counted: {n}")
for docs in (1500, 6000):
    q = max(30, docs // max(1, n))
    print(f"    --max-docs {docs:>5} -> quota {q:>4} per phrase   (pool cap {docs})")
print(f"\n  .bat claims 26 phrases -> quota 57 at 1500. Actual: {n} -> "
      f"{max(30, 1500 // max(1, n))}")
if n != 26:
    print(f"  *** the .bat's arithmetic is based on 26 phrases; the file now has {n}. ***")

print("\n" + "=" * 96)
print("  C3/C4 — HOW MANY DOCS ACTUALLY EXIST? (ask EDGAR, do not trust the comment)")
print("=" * 96)
UA = "David Moody rockyshoals@gmail.com"
FTS = "https://efts.sec.gov/LATEST/search-index"
import datetime
until = datetime.date.today()
since = until - datetime.timedelta(days=450)


def fts_total(phrase):
    q = urllib.parse.urlencode({"q": f'"{phrase}"', "startdt": since.isoformat(),
                                "enddt": until.isoformat(), "forms": "8-K"})
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"{FTS}?{q}", headers={"User-Agent": UA}), timeout=25) as r:
            d = json.loads(r.read().decode())
        t = d.get("hits", {}).get("total", {})
        return t.get("value", 0), t.get("relation", "eq")
    except Exception as e:
        return None, str(e)


print(f"  window: {since} .. {until}  (450d, 8-K only)\n")
print(f"  {'phrase':<40} {'available':>10} {'we take':>8} {'coverage':>9}")
q1500 = max(30, 1500 // max(1, n))
q6000 = max(30, 6000 // max(1, n))
tot_av = 0
rows = []
import time
for ph in phrases[:10]:
    v, rel = fts_total(ph)
    time.sleep(0.15)
    if v is None:
        print(f"  {ph[:40]:<40} {'ERR':>10}")
        continue
    tot_av += v
    rows.append((ph, v))
    cov = q1500 / v * 100 if v else 0
    print(f"  {ph[:40]:<40} {v:>10,} {q1500:>8} {cov:>8.1f}%")
if rows:
    print(f"\n  {'TOTAL (10 phrases)':<40} {tot_av:>10,} {q1500*len(rows):>8} "
          f"{q1500*len(rows)/tot_av*100:>8.1f}%")
    print(f"  .bat claims: 12,900 available -> 570 taken = 4.4%")
    print(f"\n  AT --max-docs 6000: quota {q6000} -> "
          f"{q6000*len(rows)/tot_av*100:.1f}% coverage")
    print(f"  .bat calls 6000 '~4x the coverage'. True — but "
          f"{q6000*len(rows)/tot_av*100:.1f}% still MISSES "
          f"{100 - q6000*len(rows)/tot_av*100:.0f}% of the corpus.")

print("\n" + "=" * 96)
print("  THE QUESTION THE .bat DOES NOT ASK: is the sample BIASED?")
print("=" * 96)
print("  Taking the first `quota` hits is only safe if EDGAR's order is RANDOM w.r.t. what")
print("  we want. It is not — FTS returns by RELEVANCE by default. So the 57 (or 230) we keep")
print("  are the 57 EDGAR thinks match best, which correlates with... nothing we care about.")
mm = re.search(r'"sort"|sort=|dateRange|&dateRange', src)
print(f"  does the miner request a sort order?  {'yes' if mm else 'NO — it takes EDGAR default order'}")
print("\n  THE FIX IS NOT A BIGGER QUOTA. It is to SLICE BY TIME:")
print("    for each phrase, walk the 450d window in 30-day slices and take everything in each.")
print("    Same total docs, but a COMPLETE census of recent filings instead of an arbitrary")
print("    relevance-ranked skim of the whole period. Recent filings are the ones with live")
print("    readout dates; a 14-month-old 'topline results' mention is nearly worthless.")

print("\n" + "=" * 96)
print("  C6 — IS 17% OF THE WORKBOOK COMPANY-STATED?")
print("=" * 96)
import csv
p = os.path.join(HERE, "phase_readouts_2026H2.csv")
if os.path.exists(p):
    rr = list(csv.DictReader(open(p, encoding="utf-8")))
    print(f"  rows: {len(rr):,}")
    cols = rr[0].keys() if rr else []
    srcc = [c for c in cols if "source" in c.lower() or "src" in c.lower()]
    print(f"  source-ish columns: {srcc}")
    import collections
    for c in srcc[:2]:
        cnt = collections.Counter(x.get(c) or "-" for x in rr)
        for k, v in cnt.most_common(8):
            print(f"    {c}={k!r:<28} {v:>5} ({v/len(rr)*100:.0f}%)")
else:
    print(f"  {p} not found — run the miner first")
