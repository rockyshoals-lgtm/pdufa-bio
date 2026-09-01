import csv, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = list(csv.DictReader(open("readout_gold_dates.csv", encoding="utf-8-sig", errors="replace")))
g = [r for r in R if r["confidence"] in ("GOLD", "FIRM")]
n = [r for r in g if "2026-08-22" <= r["date"] <= "2026-10-05"]
print(f"{len(g)} GOLD+FIRM total | {len(n)} between Aug 22 and Oct 5\n")
for r in sorted(n, key=lambda r: r["date"]):
    src = ("CONF" if "conference" in r["source"]
           else ("PDUFA" if "PDUFA" in r["source"] else "FILING"))
    cf = "  *CONFLICT " + r["conflict"] if r["conflict"] else ""
    print(f"  {r['date']}  {r['ticker']:<7}{src:<7}{r['drug'][:34]:<36}{cf}")
