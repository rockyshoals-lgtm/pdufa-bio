"""Why did the production newswire lane return 0 when the standalone test found 16?
Count the rows lost at EACH gate."""
import datetime as dt, glob, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import conference_presentations as CP
from conference_miner import NEWS_DIR, _NOT_A_CATALYST

reg = CP.load_registry()
print("NEWS_DIR =", NEWS_DIR, "exists:", os.path.isdir(NEWS_DIR))
files = sorted(glob.glob(os.path.join(NEWS_DIR, "news_mined_2026-*.jsonl")))
print("files:", len(files))

cutoff = (dt.date.today() - dt.timedelta(days=75)).isoformat()
print("cutoff:", cutoff)
n = no_title = no_tks = blocked = no_ev = ok = 0
samples = []
for p in files:
    day = os.path.basename(p)[11:21]
    if day < cutoff:
        continue
    try:
        fdt = dt.date.fromisoformat(day)
    except Exception:
        fdt = None
    for ln in io.open(p, encoding="utf-8", errors="replace"):
        if not ln.strip():
            continue
        try:
            o = json.loads(ln)
        except Exception:
            continue
        n += 1
        title = o.get("title") or ""
        tks = o.get("tickers") or []
        if not title:
            no_title += 1
            continue
        ev = CP.extract(title, filed_dt=fdt, registry=reg)
        if not ev:
            no_ev += 1
            continue
        # extraction SUCCEEDED — now which guard kills it?
        if not tks:
            no_tks += 1
            if len(samples) < 6:
                samples.append(("NO TICKERS", repr(o.get("tickers")), title[:80]))
            continue
        if _NOT_A_CATALYST.search(title):
            blocked += 1
            if len(samples) < 6:
                samples.append(("BLOCKED", _NOT_A_CATALYST.search(title).group(0), title[:80]))
            continue
        ok += 1
        if len(samples) < 6:
            samples.append(("OK", ",".join(tks), title[:80]))

print(f"\n{n:,} rows | no_title {no_title} | extract said no {no_ev} | "
      f"extracted-but-no-tickers {no_tks} | extracted-but-blocked {blocked} | PASSED {ok}")
print("\nsamples:")
for a, b, c in samples:
    print(f"  [{a}] ({b}) {c}")
