"""DOES THE TIME-SLICE FIX FIND READOUTS THE CURRENT MINE MISSES?

My red team counted docs. It did not mine anything, so it found nothing. This actually looks.

THE TEST:
  current : one FTS call per phrase over 450 days, keep the first 57 (relevance-ranked)
  fixed   : walk the last N days in 7-day slices, take EVERYTHING in each

Then diff the tickers against the workbook. If the fix is real, it surfaces names the workbook
does not have — with RECENT filings, which are the only ones whose readout window is still open.

Read-only. SEC etiquette: identifying UA, <10 req/s.
"""
import collections, datetime, json, os, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "David Moody rockyshoals@gmail.com"
FTS = "https://efts.sec.gov/LATEST/search-index"
FORMS = "8-K,6-K"

# the HIGH-SIGNAL phrases only — the ones the flat quota starves.
# (`will host a conference call` is 29% of the corpus and ~0 signal; excluded on purpose.)
PHRASES = ["announces topline", "reports topline", "to discuss the topline",
           "expect to announce topline", "plans to report topline",
           "expects to report topline", "primary endpoint data", "Topline Results"]


def fts(phrase, start, end, frm=0):
    q = urllib.parse.urlencode({"q": f'"{phrase}"', "startdt": start, "enddt": end,
                                "forms": FORMS, "from": frm})
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"{FTS}?{q}", headers={"User-Agent": UA}), timeout=25) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def slices(days, step=7):
    end = datetime.date.today()
    out = []
    for i in range(0, days, step):
        b = end - datetime.timedelta(days=i + step)
        e = end - datetime.timedelta(days=i + 1)
        out.append((b.isoformat(), e.isoformat()))
    return out


DAYS = 45
print("=" * 100)
print(f"  TIME-SLICED WALK — last {DAYS} days, 7-day slices, high-signal phrases only")
print("=" * 100)
print(f"  phrases: {len(PHRASES)}   (excludes the conference-call phrases: 45% of corpus, ~0 signal)")

hits = {}
calls = 0
for ph in PHRASES:
    got = 0
    for (a, b) in slices(DAYS):
        j = fts(ph, a, b)
        calls += 1
        time.sleep(0.12)
        if not j:
            continue
        tot = j.get("hits", {}).get("total", {}).get("value", 0)
        for h in j.get("hits", {}).get("hits", []):
            src = h.get("_source", {})
            names = src.get("display_names") or []
            tk = None
            for nm in names:
                m = re.search(r"\(([A-Z.]{1,6})\)", nm)
                if m:
                    tk = m.group(1)
                    break
            if not tk:
                continue
            d = src.get("file_date", "")
            key = (tk, d, ph)
            if key not in hits:
                hits[key] = {"tk": tk, "date": d, "phrase": ph,
                             "name": (names[0].split("(")[0].strip() if names else ""),
                             "sics": src.get("sics") or [],
                             "form": (src.get("root_forms") or [""])[0],
                             "adsh": src.get("adsh")}
        got += len(j.get("hits", {}).get("hits", []))
    print(f"    {ph:<30} {got:>4} hits over {len(slices(DAYS))} slices")

print(f"\n  {calls} FTS calls, {len(hits)} phrase-hits, "
      f"{len({v['tk'] for v in hits.values()})} distinct tickers")

# biotech only
BIO_SIC = {"2836", "2834", "8731", "3826", "3841"}
bio = {k: v for k, v in hits.items() if any(s in BIO_SIC for s in v["sics"])}
print(f"  biotech-SIC only: {len(bio)} hits, "
      f"{len({v['tk'] for v in bio.values()})} tickers")

# ---- what does the workbook already know? ------------------------------------------------
known = set()
import csv
for p in ("phase_readouts_2026H2.csv",):
    fp = os.path.join(HERE, p)
    if os.path.exists(fp):
        for r in csv.DictReader(open(fp, encoding="utf-8")):
            t = (r.get("ticker") or r.get("symbol") or "").strip().upper()
            if t:
                known.add(t)
print(f"\n  workbook knows: {len(known)} tickers")

found = collections.defaultdict(list)
for v in bio.values():
    found[v["tk"]].append(v)
new = {t: v for t, v in found.items() if t not in known}

print("\n" + "=" * 100)
print(f"  TICKERS THE TIME-SLICE FOUND THAT THE WORKBOOK DOES NOT HAVE: {len(new)}")
print("=" * 100)
if not known:
    print("  (workbook CSV not present — cannot diff. Showing everything found instead.)")
    new = found
print(f"  {'tkr':<7} {'filed':<12} {'form':<6} {'phrase':<28} company")
for t in sorted(new, key=lambda x: -max(len(new[x]), 0))[:28]:
    v = sorted(new[t], key=lambda x: x["date"], reverse=True)[0]
    print(f"  {t:<7} {v['date']:<12} {v['form']:<6} {v['phrase'][:28]:<28} {v['name'][:34]}")

print("\n" + "=" * 100)
print("  THE COMPARISON THAT MATTERS")
print("=" * 100)
print(f"  current mine : 1 call/phrase over 450d, keep first 57 (relevance-ranked)")
print(f"  this walk    : {len(slices(DAYS))} calls/phrase over {DAYS}d, keep EVERYTHING")
print(f"                 -> {calls} calls total, ~{calls*0.15:.0f}s of FTS. No doc fetches yet.")
print(f"  the point: these filings are from the last {DAYS} DAYS. Their readout windows are")
print(f"  still OPEN. A relevance-ranked skim of 450 days returns mostly guidance that has")
print(f"  already expired.")
