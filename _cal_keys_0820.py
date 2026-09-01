import csv, collections, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = list(csv.DictReader(open("readout_calendar.csv", encoding="utf-8-sig", errors="replace")))
cc = collections.Counter(r["confidence"] for r in R)
print("confidence:", dict(cc), "| disagree:",
      sum(1 for r in R if (r.get("disagree") or "").strip()))
for tk in ("ALT", "TENX", "APGE", "BHVN", "VERA", "IONS", "MIRM", "CAPR",
           "AMLX", "SLS", "WHWK", "OCGN"):
    r = next((x for x in R if x["ticker"] == tk), None)
    if r:
        print(f"{tk:<6} best={r['best_date']:<12} src={r['date_source']:<10} "
              f"conf={r['confidence']:<6} edgar={r['edgar_window']:<12} "
              f"pcd={r['ctgov_pcd']:<12} {r['imminence'][:30]}")
    else:
        print(tk, "NOT IN CALENDAR")
both = [r for r in R if r["confidence"] == "BOTH"
        and "2026-08-20" <= r["best_date"] <= "2026-10-15"]
both.sort(key=lambda r: r["best_date"])
print("\nBOTH-source, dated 8/20-10/15:", len(both))
for r in both[:18]:
    print(f"  {r['best_date']}  {r['ticker']:<7} edgar={r['edgar_window']:<10} "
          f"pcd={r['ctgov_pcd']:<12} sm={r.get('sm_signal') or '-'}")
