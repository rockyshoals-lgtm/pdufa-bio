"""Improvement targets: unparseable windows, alt-window semantics, undated READOUT rows."""
import csv, os, re, json, sys, collections, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = list(csv.DictReader(open(os.path.join(HERE, "readout_forward.csv"),
                                encoding="utf-8", errors="replace")))

# 1) what do the alt windows look like vs the armed watchlist source
AW = json.load(open(os.path.join(HERE, "Momentum Scanner", "armed_watchlist.json"),
                    encoding="utf-8", errors="replace"))
aw = AW if isinstance(AW, dict) else {x.get("ticker"): x for x in AW}
for tk in ("ALT", "TENX", "APGE", "BHVN", "VERA", "IONS", "MIRM"):
    e = aw.get(tk) or {}
    r = next((x for x in ROWS if x["ticker"] == tk), {})
    print(f"{tk:<6} csv window='{r.get('window')}' alt='{r.get('window_alt')}' "
          f"| watchlist: {json.dumps({k: v for k, v in e.items() if k in ('window','date','lane','when','event')}, default=str)[:110]}")

# 2) primary window strings that exist but look vague/unparseable
pat = re.compile(r"^(\d{4}(-\d{2}){0,2}|[hq][1-4][- ]?\d{4}|[a-z]{3,9}[- ]?\d{4})$", re.I)
vague = collections.Counter()
for r in ROWS:
    w = (r.get("window") or "").strip()
    if w and not pat.match(w):
        vague[w.lower()[:40]] += 1
print(f"\nvague primary windows ({sum(vague.values())}):")
for w, n in vague.most_common(12):
    print(f"  {n}x  {w}")

# 3) fully undated rows by lane — the miss surface
und = [r for r in ROWS if not (r.get("window") or "").strip()
       and not (r.get("window_alt") or "").strip()]
lanes = collections.Counter((r.get("armed_lane") or "NONE") for r in und)
print(f"\nfully undated rows: {len(und)} by lane {dict(lanes)}")
for r in und[:12]:
    print(f"  {r['ticker']:<7}{r['filed']:<12}{(r.get('phrases') or '')[:60]}")
