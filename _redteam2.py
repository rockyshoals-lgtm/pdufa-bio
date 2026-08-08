"""RED TEAM v2 — after my own phrase counter was wrong.

v1 used `^\\s*"([^"]+)"` and counted 9 phrases, because the list packs several per line. The real
count is ~26 and the .bat's arithmetic (1500/26=57, 6000/26=230) is CORRECT. I retracted.

So: count properly, then ask the question that actually matters — WHERE does the budget go?
"""
import ast, collections, datetime, json, os, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "phase_readout_miner.py"), encoding="utf-8").read()

# Parse the AST — no regex. The list is a literal; ask Python what is in it.
tree = ast.parse(src)
PH = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "GUIDANCE_PHRASES":
                PH = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
print("=" * 96)
print("  THE PHRASE LIST — counted by AST, not by a regex I can get wrong")
print("=" * 96)
print(f"  GUIDANCE_PHRASES: {len(PH)} phrases")
q1500, q6000 = max(30, 1500 // len(PH)), max(30, 6000 // len(PH))
print(f"    --max-docs 1500 -> quota {q1500}   (.bat claims 57)  {'OK' if q1500==57 else 'MISMATCH'}")
print(f"    --max-docs 6000 -> quota {q6000}   (.bat claims 230) {'OK' if q6000==230 else 'MISMATCH'}")
print(f"\n  -> the .bat's arithmetic is CORRECT. My v1 count of 9 was a regex bug in MY tool.")

UA = "David Moody rockyshoals@gmail.com"
FTS = "https://efts.sec.gov/LATEST/search-index"
FORMS = "8-K,6-K,10-Q,10-K,S-1,424B4,424B5,20-F"
until = datetime.date.today()
since = until - datetime.timedelta(days=450)


def total(ph):
    q = urllib.parse.urlencode({"q": f'"{ph}"', "startdt": since.isoformat(),
                                "enddt": until.isoformat(), "forms": FORMS})
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"{FTS}?{q}", headers={"User-Agent": UA}), timeout=25) as r:
            d = json.loads(r.read().decode())
        t = d.get("hits", {}).get("total", {})
        return t.get("value", 0)
    except Exception:
        return None


print("\n" + "=" * 96)
print("  WHERE DOES THE BUDGET ACTUALLY GO?  (the question the .bat does not ask)")
print("=" * 96)
print(f"  window {since}..{until}, forms {FORMS.split(',')[0]}+7 more\n")
print(f"  {'phrase':<34} {'available':>10} {'@57':>7} {'@230':>7}  {'saturates?':<12}")
rows = []
for ph in PH:
    v = total(ph)
    time.sleep(0.12)
    if v is None:
        continue
    rows.append((ph, v))
    sat57 = "YES" if v > 57 else "no (takes all)"
    print(f"  {ph[:34]:<34} {v:>10,} {min(57,v):>7} {min(230,v):>7}  {sat57:<12}")

rows.sort(key=lambda x: -x[1])
tot = sum(v for _, v in rows)
print(f"\n  TOTAL AVAILABLE: {tot:,} docs across {len(rows)} phrases")
print(f"  taken @1500 (quota 57):  {sum(min(57,v) for _,v in rows):,} = "
      f"{sum(min(57,v) for _,v in rows)/tot*100:.1f}%")
print(f"  taken @6000 (quota 230): {sum(min(230,v) for _,v in rows):,} = "
      f"{sum(min(230,v) for _,v in rows)/tot*100:.1f}%")

print("\n" + "=" * 96)
print("  THE CONCENTRATION PROBLEM")
print("=" * 96)
print(f"  {'phrase':<34} {'docs':>9} {'% of corpus':>12}")
for ph, v in rows[:6]:
    print(f"  {ph[:34]:<34} {v:>9,} {v/tot*100:>11.1f}%")
top3 = sum(v for _, v in rows[:3])
print(f"\n  top 3 phrases = {top3:,} docs = {top3/tot*100:.0f}% of the corpus")
sat = [r for r in rows if r[1] > 57]
nosat = [r for r in rows if r[1] <= 57]
print(f"  phrases that SATURATE at quota 57 : {len(sat)}/{len(rows)}")
print(f"  phrases that take EVERYTHING      : {len(nosat)}/{len(rows)}  "
      f"({sum(v for _,v in nosat):,} docs total — the quota never binds on these)")
print(f"\n  -> raising 1500->6000 spends {sum(min(230,v)-min(57,v) for _,v in rows):,} extra")
print(f"     doc-fetches, of which {sum(min(230,v)-min(57,v) for _,v in rows[:3]):,} "
      f"({sum(min(230,v)-min(57,v) for _,v in rows[:3])/max(1,sum(min(230,v)-min(57,v) for _,v in rows))*100:.0f}%) go to the top 3 phrases.")

print("\n" + "=" * 96)
print("  DAVID ALREADY FOUND THE ADJACENCY BUG — and solved it better than I did")
print("=" * 96)
i = src.find("EDGAR full-text search requires ADJACENCY")
print("  " + src[i-4:i+330].replace("\n    #", "\n ").strip()[:420])
print("\n  This is the SAME bug I hit an hour ago: my phrases_readout.txt scored 0 on")
print("  'Reports Positive TH103 Phase 1a SAD Results' because the drug name sits between")
print("  the words. My fix was a regex on the HEADLINE. His is better: search short universal")
print("  FRAGMENTS that FTS can actually match, then run the LEAD regexes on the FETCHED DOC.")
print("  That is why the list has 'Topline Results' and not 'positive topline results'.")
