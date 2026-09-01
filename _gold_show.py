import csv, collections, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = list(csv.DictReader(open("readout_gold_dates.csv", encoding="utf-8-sig", errors="replace")))
con = [r for r in R if r["conflict"]]
print(f"{len(R)} rows | {len(con)} true conflicts (same drug, two dates)\n")
for r in con:
    print(f"  {r['date']}  {r['ticker']:<7}{r['drug'][:26]:<28}{r['source'][:26]:<28}"
          f"vs {r['conflict']}")
print("\nGOLD by month:")
g = [r for r in R if r["confidence"] == "GOLD"]
m = collections.Counter(r["date"][:7] for r in g)
print(" ", dict(sorted(m.items())))
print(f"\nGOLD rows Aug 22 - Sep 30 ({sum(1 for r in g if '2026-08-22'<=r['date']<='2026-09-30')}):")
for r in g:
    if "2026-08-22" <= r["date"] <= "2026-09-30":
        src = "CONF" if "conference" in r["source"] else "PDUFA"
        print(f"  {r['date']}  {r['ticker']:<7}{src:<7}{r['event'][:14]:<16}{r['drug'][:30]}")
