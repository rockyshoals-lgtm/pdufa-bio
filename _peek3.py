import csv,glob,collections
for pat in ("ODIN_MODEL_READY*.csv","enriched_gungnir_dataset_v3.csv","**/phase_readouts_h2.csv"):
    for p in glob.glob(pat,recursive=True)[:1]:
        with open(p,encoding="utf-8",errors="replace") as f:
            rd=csv.DictReader(f); rows=list(rd)
        cols=rows[0].keys() if rows else []
        dcol=[c for c in cols if "date" in c.lower()][:5]
        print(f"--- {p}  n={len(rows)}")
        print("   date cols:",dcol)
        tcol=[c for c in cols if c.lower() in ("ticker","symbol","tk")][:2]
        print("   ticker cols:",tcol)
        for c in dcol[:2]:
            vs=sorted(set(r[c][:7] for r in rows if r.get(c) and len(r[c])>=7))
            print(f"   {c}: {vs[-6:]}")
        recent=[r for r in rows if any((r.get(c) or "")[:7] in ("2026-07","2026-08") for c in dcol)]
        print("   rows in 2026-07/08:",len(recent))
        if recent:
            print("   sample:",{k:recent[0][k] for k in list(cols)[:9]})
