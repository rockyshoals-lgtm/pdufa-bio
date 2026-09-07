"""WHY did we miss these 16 presenter rows BPC has? Three possible causes, three fixes.

  A. NO 8-K EXISTS — company announced by newswire only. Unfixable from EDGAR; BPC earns
     its keep here. Expected for mega-caps (ABBV, LLY, NKTR).
  B. 8-K EXISTS but our FTS phrases did not surface it — fixable by adding a phrase.
  C. 8-K EXISTS and FTS surfaced it, but the --max-fetch cap meant we never fetched the
     doc, or extract() rejected it — fixable by raising the cap / fixing the extractor.

Distinguishing A from B/C is the whole point: A is a real limit to publish honestly,
B and C are bugs. Queries EDGAR full-text search per ticker over the last 75 days and
reports what is actually there.
"""
import json, os, sys, time, urllib.parse, urllib.request, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from readout_scan import ua, _get, FTS

MISSES = [("GRI", "ERS"), ("INSM", "ERS"), ("BEAM", "ERS"), ("ABBV", "WCLC"),
          ("EYPT", "RETSOC"), ("OCGN", "RETSOC"), ("OCUL", "RETSOC"), ("CCCC", "IMS"),
          ("LLY", "EADV"), ("NKTR", "EADV"), ("SANA", "EASD"), ("ENTX", "ASBMR"),
          ("IMMP", "ESMO")]
agent = ua()


def fts_ticker(tk, days=75):
    """Every 8-K/6-K this ticker filed recently, with a crude presentation-word flag."""
    import datetime as dt
    end = dt.date.today()
    beg = end - dt.timedelta(days=days)
    q = urllib.parse.urlencode({"q": f'"{tk}"', "forms": "8-K,6-K",
                                "startdt": beg.isoformat(), "enddt": end.isoformat()})
    j = _get(f"{FTS}?{q}", agent)
    try:
        j = json.loads(j.decode()) if j else None
    except Exception:
        j = None
    return j


print(f"{'tkr':<6}{'conf':<8}{'EDGAR 8-K/6-K in 75d':<24}verdict")
print("-" * 78)
tally = collections.Counter()
for tk, conf in MISSES:
    j = fts_ticker(tk)
    time.sleep(0.2)
    n = 0
    if j:
        n = (j.get("hits", {}).get("total", {}) or {}).get("value", 0)
    # did OUR forward scan see this ticker at all?
    import csv, io
    seen = False
    try:
        for r in csv.DictReader(io.open(os.path.join(HERE, "readout_forward.csv"),
                                        encoding="utf-8-sig", errors="replace", newline="")):
            if (r.get("ticker") or "").upper() == tk:
                seen = True
                break
    except Exception:
        pass
    if n == 0:
        v, k = "A: no EDGAR filing at all — newswire only, BPC-only row", "A"
    elif seen:
        v, k = "C: we DID surface this ticker — extractor or fetch-cap dropped it", "C"
    else:
        v, k = "B: filings exist but our phrases never surfaced them", "B"
    tally[k] += 1
    print(f"{tk:<6}{conf:<8}{n:<24}{v}")
print("-" * 78)
print(f"A (unfixable, newswire-only): {tally['A']}   "
      f"B (phrase gap): {tally['B']}   C (fetch/extract gap): {tally['C']}")
