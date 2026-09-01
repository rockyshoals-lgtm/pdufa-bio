"""Which just_reported readouts filed 8/19-8/20, and how their tape looks right now."""
import csv, os, sys, json, time, datetime, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "Momentum Scanner"))
from momentum_radar import load_key

PK = load_key("POLYGON_API_KEY")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROWS = list(csv.DictReader(open(os.path.join(HERE, "readout_forward.csv"),
                                encoding="utf-8", errors="replace")))
fresh = [r for r in ROWS if (r.get("just_reported") or "").startswith("YES")
         and r["filed"] >= "2026-08-19"]
print(f"just_reported filed 8/19-8/20: {len(fresh)}")


def g(u, t=25):
    for _ in range(3):
        try:
            with urllib.request.urlopen(u, timeout=t) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.3)
    return None


def tape(tk):
    pv = g(f"https://api.polygon.io/v2/aggs/ticker/{tk}/prev?adjusted=true&apiKey={PK}") or {}
    pc = ((pv.get("results") or [{}])[0]).get("c")
    j = g(f"https://api.polygon.io/v2/aggs/ticker/{tk}/range/1/minute/2026-08-20/2026-08-20"
          f"?adjusted=true&sort=asc&limit=5000&apiKey={PK}") or {}
    dv, last, hi = 0.0, None, 0.0
    for x in j.get("results") or []:
        dv += (x.get("v") or 0) * (x.get("c") or 0)
        last = x.get("c")
        hi = max(hi, x.get("h") or 0)
    return tk, pc, last, hi, dv


with ThreadPoolExecutor(max_workers=10) as ex:
    T = {tk: v for tk, *v in ex.map(tape, sorted({r["ticker"] for r in fresh}))}

# board joins: did nest egg see them today?
FS = {}
p = os.path.join(HERE, "Momentum Scanner", "_DATA", "first_seen_2026-08-20.json")
if os.path.exists(p):
    FS = json.load(open(p))

out = []
for r in fresh:
    tk = r["ticker"]
    pc, last, hi, dv = T.get(tk, (None, None, None, 0))
    chg = ((last / pc - 1) * 100) if (last and pc) else None
    o2h = ((hi / pc - 1) * 100) if (hi and pc) else None
    out.append((dv or 0, tk, r, chg, o2h, dv))
out.sort(reverse=True)

print(f"{'tk':<7}{'filed':<12}{'chg%':>8}{'hi%':>8}{'$vol':>9}  {'board':<7} headline-snippet")
seen = set()
for _, tk, r, chg, o2h, dv in out:
    if tk in seen:
        continue
    seen.add(tk)
    jr = (r.get("just_reported") or "")[6:100].replace("&#8203;", "").strip()
    b = "SEEN" if tk in FS else "-"
    print(f"{tk:<7}{r['filed']:<12}"
          f"{(f'{chg:+.1f}%' if chg is not None else '-'):>8}"
          f"{(f'{o2h:+.1f}%' if o2h is not None else '-'):>8}"
          f"{(dv or 0)/1e6:>8.1f}M  {b:<7} {jr[:70]}")
