# -*- coding: utf-8 -*-
"""
build_option_charts.py  —  per-ticker option-contract-PRICE charts across a catalyst window.

For each catalyst it tracks a FIXED ladder of DISTINCT strikes (anchored ~ATM, +/-10%, +/-20% of the
window-start spot) on the first expiry AFTER the catalyst, and plots each strike's CALL and PUT mid
price daily across the window (resolved: T-60 -> T+15 ; future: T-120 -> today). Shows the runup, the
IV ramp, and the post-event crush per strike.

Data: ORATS datav2 hist/strikes (one call per ticker per trade date returns the whole chain).
CONCURRENT: pulls each event's window in parallel (--workers, default 12) to use the ORATS
1,000-calls/min headroom (~12 workers ~= 900/min). Budget-aware + resumable: every event is cached
to opt_charts/cache/<TICKER>_<DATE>.json; re-running skips cached events; --max-calls stops cleanly.

Usage:
  python build_option_charts.py --universe option_chart_universe.csv --max-calls 90000   # full clear
  python build_option_charts.py --tickers CELC,UNCY,VRDN --stride 1
  python build_option_charts.py --render
"""
import os, sys, csv, json, time, argparse, threading, datetime as dt
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "opt_charts")
CACHE = os.path.join(OUT, "cache"); PNG = os.path.join(OUT, "png")
for d in (OUT, CACHE, PNG): os.makedirs(d, exist_ok=True)

def orats_key():
    try:
        for l in open(os.path.join(HERE, "Odin Perfection", ".env_master")):
            if l.startswith("ORATS"): return l.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception: pass
    return os.environ.get("ORATS_API_KEY", "cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d")
KEY = orats_key()

CALLS = 0; _lock = threading.Lock()
def hist_strikes(ticker, tradedate):
    global CALLS
    with _lock: CALLS += 1
    u = f"https://api.orats.io/datav2/hist/strikes?token={KEY}&ticker={ticker}&tradeDate={tradedate}"
    try:
        with urllib.request.urlopen(u, timeout=25) as r:
            return json.loads(r.read().decode()).get("data") or []
    except Exception:
        return None

def trading_days(start, end, stride=1):
    out = []; d = start; i = 0
    while d <= end:
        if d.weekday() < 5:
            if i % stride == 0: out.append(d.isoformat())
            i += 1
        d += dt.timedelta(days=1)
    return out

def parse_date(s):
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-": return dt.date.fromisoformat(s[:10])
    if len(s) >= 7 and s[4] == "-" and s[5:7].isdigit(): return dt.date(int(s[:4]), int(s[5:7]), 15)
    return None

def nearest(strikes, target):
    return min(strikes, key=lambda k: abs(k - target)) if strikes else None

def build_event(ticker, cat_date, kind, pre, post, stride, today, max_calls, workers):
    cd = parse_date(cat_date)
    if not cd: return None
    start = cd - dt.timedelta(days=int(pre * 1.45))
    end   = min(cd + dt.timedelta(days=int(post * 1.45)), today)
    days  = trading_days(start, end, stride)
    if not days: return None
    # anchor (serial) - need ladder + expiry before parallel pulls
    ref = None
    for d in days:
        if CALLS >= max_calls: return "BUDGET"
        ch = hist_strikes(ticker, d)
        if ch:
            ref = (d, ch); break
    if not ref: return None
    d0, ch0 = ref
    try: spot0 = float(ch0[0].get("stockPrice"))
    except (TypeError, ValueError): return None
    if not spot0 or spot0 != spot0: return None   # guard None/0/NaN/str stockPrice
    exps = sorted({r["expirDate"] for r in ch0 if r.get("expirDate", "") >= cd.isoformat()})
    if not exps: return None
    expiry = exps[0]
    avail = sorted({r["strike"] for r in ch0 if r["expirDate"] == expiry})
    if len(avail) < 3: return None
    ladder = []; seen_k = set()
    for mult, lbl in [(0.8, "-20%"), (0.9, "-10%"), (1.0, "ATM"), (1.1, "+10%"), (1.2, "+20%")]:
        k = nearest(avail, spot0 * mult)
        if k is None or k in seen_k: continue
        seen_k.add(k); ladder.append((k, lbl))
    # remaining dates IN PARALLEL (cap to remaining budget)
    rest = [d for d in days if d != d0]
    budget_left = max(0, max_calls - CALLS)
    if len(rest) > budget_left: rest = rest[:budget_left]
    chains = {d0: ch0}
    if rest:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(hist_strikes, ticker, d): d for d in rest}
            for f in futs:
                ch = f.result()
                if ch: chains[futs[f]] = ch
    series = []
    for d in days:
        ch = chains.get(d)
        if not ch: continue
        sub = {r["strike"]: r for r in ch if r.get("expirDate") == expiry}
        row = {"date": d, "stock": ch[0].get("stockPrice"), "v": {}}
        for k, lbl in ladder:
            r = sub.get(k)
            if r: row["v"][lbl] = {"K": k, "c": r.get("callValue"), "p": r.get("putValue")}
        if row["v"]: series.append(row)
    if not series: return None
    return {"ticker": ticker, "cat_date": cd.isoformat(), "kind": kind, "expiry": expiry,
            "spot0": spot0, "ladder": [{"K": k, "label": l} for k, l in ladder], "series": series}

def render(ev):
    import matplotlib
    matplotlib.use("Agg"); import matplotlib.pyplot as plt
    cd = ev["cat_date"]; t0 = dt.date.fromisoformat(cd)
    xs = [dt.date.fromisoformat(r["date"]) for r in ev["series"]]
    fig, (axc, axp) = plt.subplots(1, 2, figsize=(13, 4.6), sharex=True)
    colors = {"-20%": "#c0392b", "-10%": "#e67e22", "ATM": "#2c3e50", "+10%": "#2980b9", "+20%": "#16a085"}
    seen_k = set(); ladder = []
    for lad in ev["ladder"]:
        if lad["K"] in seen_k: continue
        seen_k.add(lad["K"]); ladder.append(lad)
    for which, ax, title in [("c", axc, "CALL mid"), ("p", axp, "PUT mid")]:
        for lad in ladder:
            lbl = lad["label"]
            ys = [(r["v"].get(lbl) or {}).get(which) for r in ev["series"]]
            pts = [(x, y) for x, y in zip(xs, ys) if y is not None]
            if len(pts) > 1:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], label=f"${lad['K']:g} ({lbl})",
                        color=colors.get(lbl, "#888"), lw=1.6)
        ax.axvline(t0, color="#999", ls="--", lw=1)
        ax.set_title(title, fontsize=10); ax.grid(alpha=.25); ax.set_ylabel("$ / contract-share")
        ax.legend(fontsize=7, ncol=2)
    fig.suptitle(f"{ev['ticker']}  —  catalyst {cd} ({ev['kind']})  exp {ev['expiry']}  | strikes fixed at entry spot ${ev['spot0']:.0f}",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(PNG, f"{ev['ticker']}_{cd}.png")
    fig.savefig(p, dpi=96); plt.close(fig)
    return p

def gallery():
    evs = []
    for f in sorted(os.listdir(CACHE)):
        if f.endswith(".json"):
            try:
                e = json.load(open(os.path.join(CACHE, f)))
                if e.get("series"): evs.append(e)
            except Exception: pass
    rows = []
    for ev in sorted(evs, key=lambda e: (e["kind"], e["cat_date"])):
        png = f"png/{ev['ticker']}_{ev['cat_date']}.png"
        if os.path.exists(os.path.join(OUT, png)):
            rows.append(f'<div class=card><div class=h>{ev["ticker"]} &middot; {ev["cat_date"]} '
                        f'&middot; {ev["kind"]}</div><img loading=lazy src="{png}"></div>')
    html = ("<!doctype html><meta charset=utf-8><title>Option-price charts</title>"
            "<style>body{background:#0b0f17;color:#e8eef7;font-family:-apple-system,Segoe UI,Arial;margin:18px}"
            ".card{background:#121a28;border:1px solid #24344d;border-radius:10px;margin:0 0 16px;padding:8px}"
            ".h{font-weight:700;margin:4px 6px 8px;color:#e3ba5e}img{width:100%;border-radius:6px}h1{font-size:20px}</style>"
            f"<h1>Option-contract price charts — {len(rows)} catalysts</h1>"
            "<p style=color:#9fb1cc>Distinct strikes near ATM/&plusmn;10/20% (anchored at entry spot); "
            "CALL mid (left) &amp; PUT mid (right); dashed = catalyst. Source: ORATS hist/strikes.</p>"
            + "".join(rows))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    return len(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default=os.path.join(HERE, "option_chart_universe.csv"))
    ap.add_argument("--tickers", default="")
    ap.add_argument("--pre", type=int, default=60); ap.add_argument("--post", type=int, default=15)
    ap.add_argument("--future-pre", type=int, default=120)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--workers", type=int, default=12)      # ~12 -> ~900/min, under the 1000/min cap
    ap.add_argument("--max-calls", type=int, default=3000)
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    today = dt.date.today()
    if a.render:
        for f in os.listdir(CACHE):
            if f.endswith(".json"):
                try:
                    e = json.load(open(os.path.join(CACHE, f)))
                    if e.get("series"): render(e)
                except Exception as ex: print("  render err", f, ex)
        print(f"gallery: {gallery()} charts -> {OUT}/index.html"); return
    only = {t.strip().upper() for t in a.tickers.split(",") if t.strip()}
    uni = list(csv.DictReader(open(a.universe, encoding="utf-8", errors="ignore")))
    done = budget = 0; t0 = time.time()
    for r in uni:
        tk = (r.get("ticker") or "").upper()
        if not tk or (only and tk not in only): continue
        cd = r.get("catalyst_date", ""); kind = r.get("kind", r.get("category", "catalyst"))
        cache_f = os.path.join(CACHE, f"{tk}_{(parse_date(cd) or '').__str__()}.json")
        if os.path.exists(cache_f): continue
        is_future = (parse_date(cd) or today) >= today
        pre = a.future_pre if is_future else a.pre
        post = 0 if is_future else a.post
        try:
            ev = build_event(tk, cd, kind, pre, post, a.stride, today, a.max_calls, a.workers)
        except Exception as _be:
            print(f"  [skip] {tk}: {_be}"); ev = None   # one bad ticker never kills the batch
        if ev == "BUDGET": budget = 1; break
        if ev:
            json.dump(ev, open(cache_f, "w"))
            try: render(ev)
            except Exception as e: print("  render err", tk, e)
            done += 1
            print(f"  {tk} {ev['cat_date']} exp{ev['expiry']} {len(ev['series'])}d strikes={[l['K'] for l in ev['ladder']]} [{CALLS} calls]")
        else:
            json.dump({"ticker": tk, "cat_date": str(parse_date(cd)), "kind": kind, "skip": "no_options_or_data"},
                      open(cache_f, "w"))
        if CALLS >= a.max_calls: budget = 1; break
    n = gallery()
    rate = CALLS / max(1e-9, (time.time() - t0) / 60)
    print(f"\nDONE this run: {done} new charts, {CALLS} ORATS calls (~{rate:.0f}/min)"
          + (" (HIT --max-calls; re-run to continue)" if budget else "")
          + f". Gallery: {n} charts -> {OUT}/index.html")

if __name__ == "__main__":
    main()
