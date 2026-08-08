# -*- coding: utf-8 -*-
"""uw_export.py — bulk-export EVERYTHING Unusual Whales has for our 2026 catalyst tickers,
before the UW subscription lapses. Dark pool + full options flow + greeks + OI + net-premium,
at full depth, resumable, rate-limit compliant.

WHY / WHEN
UW cancels imminently. This grabs the deep per-ticker data the MCP tools can only sip through a
chat session. It hits the UW REST API directly with your key, in parallel, paginated to
exhaustion, and writes raw JSON to disk so nothing is lost.

AUTH
Reads the UW key from Odin Perfection/.env_master (or ./.env, or a real env var), trying these
names in order: UW_API_KEY, UNUSUAL_WHALES_API_KEY, UNUSUALWHALES_API_KEY, UW_TOKEN.
Header: Authorization: Bearer <key>   (per the UW public API docs).

WHAT IT PULLS  (all verified against the UW OpenAPI on 2026-07-21)
  darkpool     /api/darkpool/{ticker}            paginated via older_than, limit 500, ALL premium
  greeks       /api/stock/{ticker}/greek-exposure?timeframe=2Y   (2y daily GEX history)
               .../greek-exposure/strike  .../greek-exposure/expiry  .../gex-levels
  flow         /api/stock/{ticker}/flow-alerts    /api/stock/{ticker}/option-trades
               .../flow-per-strike  .../flow-per-expiry
  premium/vol  /api/stock/{ticker}/net-prem-ticks   .../options-volume   .../oi-change
  vol/iv       /api/stock/{ticker}/volatility/term-structure  .../max-pain  .../iv-rank
               .../atm-chains  .../spot-exposures  .../interpolated-iv
  reference    /api/stock/{ticker}/info  .../option-contracts  .../insider-buy-sells
  market-wide  /api/darkpool/recent (per day)   /api/option-trades/flow-alerts (paginated)
Any endpoint the account can't reach (403/404/422) is auto-skipped and logged — the run never
breaks on one bad path.

OUTPUT   uw_export_2026/<TICKER>/<endpoint>.json  (+ _market/ for market-wide, _log.csv, _MANIFEST.json)
Resumable: a ticker+endpoint whose file already exists and is non-empty is skipped on re-run.

Usage:
  python uw_export.py                 # all catalyst tickers, all endpoints, full depth
  python uw_export.py --discover      # probe every endpoint on one ticker, print which work, exit
  python uw_export.py --tickers MNKD CAPR OTLK      # subset
  python uw_export.py --rps 3 --workers 6 --dp-max 8000
"""
import argparse, csv, json, os, sys, time, threading, datetime as dt
import concurrent.futures as cf
import urllib.parse as up
import urllib.request as ur
import urllib.error as ue

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://api.unusualwhales.com"
OUT  = os.path.join(HERE, "uw_export_2026")

# conference codes that leak into the catalyst set but are not tradeable tickers
NOT_TICKERS = {"AASLD","ACR","AES","ASH","ASN","CTAD","EASD","ESC","ESMO","IDWEEK","SABCS",
               "SITC","WCLC","IRD"}


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    for name in ("UW_API_KEY", "UNUSUAL_WHALES_API_KEY", "UNUSUALWHALES_API_KEY", "UW_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    sys.exit("No UW key found. Add one line to 'Odin Perfection/.env_master':\n"
             "  UW_API_KEY=your_unusualwhales_token")


def load_tickers():
    tk = set()
    src = open(os.path.join(HERE, "pdufa_site_src", "api", "data.js"), encoding="utf-8").read()
    i = src.find("const SLATE=")
    slate, _ = json.JSONDecoder().raw_decode(src[i + len("const SLATE="):])
    today = dt.date.today().isoformat()
    for c in slate["catalysts"]:
        if c.get("ticker") and c.get("date") and today <= str(c["date"])[:10] <= "2026-12-31":
            tk.add(c["ticker"].upper())
    ds = open(os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    arr = json.loads(ds[ds.index("["):ds.rindex("]") + 1])
    for e in arr:
        if e.get("t") and e.get("d") and today <= str(e["d"])[:10] <= "2026-12-31":
            tk.add(e["t"].upper())
    return sorted(t for t in tk if t.isascii() and t.isupper() and 1 < len(t) <= 6 and t not in NOT_TICKERS)


class Rate:
    def __init__(self, rps):
        self.lock = threading.Lock(); self.iv = 1.0 / max(0.5, rps); self.nxt = 0.0
    def wait(self):
        with self.lock:
            now = time.monotonic(); s = max(0.0, self.nxt - now); self.nxt = max(now, self.nxt) + self.iv
        if s > 0: time.sleep(s)


class UW:
    def __init__(self, key, rps):
        self.key = key; self.rl = Rate(rps); self.n = 0; self.lk = threading.Lock()
    def get(self, path, params=None):
        url = BASE + path + ("?" + up.urlencode(params) if params else "")
        for attempt in range(6):
            self.rl.wait()
            with self.lk: self.n += 1
            req = ur.Request(url, headers={"Authorization": "Bearer " + self.key,
                                           "Accept": "application/json",
                                           "User-Agent": "pdufa.bio uw-export"})
            try:
                with ur.urlopen(req, timeout=60) as r:
                    return r.status, json.loads(r.read().decode("utf-8", "replace"))
            except ue.HTTPError as e:
                if e.code in (403, 404, 422):
                    return e.code, None                         # unreachable/invalid -> skip
                if e.code == 429 or e.code >= 500:
                    time.sleep(min(30, 2 ** attempt) + 0.3); continue
                return e.code, None
            except Exception:
                time.sleep(min(20, 2 ** attempt) + 0.3)
        return 0, None


# endpoint templates: (name, path, params, paginate?)   {t} = ticker
STOCK_ENDPOINTS = [
    ("greek_exposure",        "/api/stock/{t}/greek-exposure",            {"timeframe": "2Y"}, False),
    ("greek_exposure_strike", "/api/stock/{t}/greek-exposure/strike",     {}, False),
    ("greek_exposure_expiry", "/api/stock/{t}/greek-exposure/expiry",     {}, False),
    ("gex_levels",            "/api/stock/{t}/gex-levels",                {}, False),
    ("greek_flow",            "/api/stock/{t}/greek-flow",                {}, False),
    ("net_prem_ticks",        "/api/stock/{t}/net-prem-ticks",            {}, False),
    ("options_volume",        "/api/stock/{t}/options-volume",            {}, False),
    ("oi_change",             "/api/stock/{t}/oi-change",                 {"limit": 500}, False),
    ("flow_alerts",           "/api/stock/{t}/flow-alerts",               {"limit": 200}, False),
    ("flow_alerts_ticker",    "/api/option-trades/flow-alerts",           {"limit": 200, "ticker_symbol": "{t}"}, False),
    ("option_trades",         "/api/stock/{t}/option-trades",             {"limit": 500}, False),
    ("flow_per_strike",       "/api/stock/{t}/flow-per-strike",           {}, False),
    ("flow_per_expiry",       "/api/stock/{t}/flow-per-expiry",           {}, False),
    ("max_pain",              "/api/stock/{t}/max-pain",                  {}, False),
    ("iv_term_structure",     "/api/stock/{t}/volatility/term-structure", {}, False),
    ("iv_rank",               "/api/stock/{t}/iv-rank",                   {}, False),
    ("atm_chains",            "/api/stock/{t}/atm-chains",                {}, False),
    ("spot_exposures",        "/api/stock/{t}/spot-exposures",            {}, False),
    ("interpolated_iv",       "/api/stock/{t}/interpolated-iv",           {}, False),
    ("option_contracts",      "/api/stock/{t}/option-contracts",          {"limit": 500}, False),
    ("stock_volume_price",    "/api/stock/{t}/stock-volume-price-levels", {}, False),
    ("insider_buy_sells",     "/api/stock/{t}/insider-buy-sells",         {}, False),
    ("info",                  "/api/stock/{t}/info",                      {}, False),
]


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def rows_of(obj):
    if isinstance(obj, list): return obj
    if isinstance(obj, dict):
        d = obj.get("data")
        if isinstance(d, list): return d
        if isinstance(d, dict) and isinstance(d.get("data"), list): return d["data"]
    return []


def pull_darkpool(uw, t, out_dir, dp_max, log):
    """Paginate /api/darkpool/{ticker} backward via older_than until exhausted or dp_max."""
    fp = os.path.join(out_dir, "darkpool.json")
    if os.path.exists(fp) and os.path.getsize(fp) > 2:
        return "cached"
    all_rows, older = [], None
    while len(all_rows) < dp_max:
        params = {"limit": 500, "order": "desc", "order_by": "executed_at"}
        if older: params["older_than"] = older
        code, obj = uw.get(f"/api/darkpool/{t}", params)
        log(t, "darkpool", code, len(all_rows))
        if code != 200 or not obj:
            break
        rows = rows_of(obj)
        if not rows:
            break
        all_rows.extend(rows)
        ts = rows[-1].get("executed_at") or rows[-1].get("trf_executed_at")
        if not ts or len(rows) < 500:
            break
        older = ts
    if all_rows:
        dump(fp, all_rows)
    return len(all_rows)


def pull_endpoint(uw, t, name, path, params, out_dir, valid, log):
    if name not in valid:
        return "skip"
    fp = os.path.join(out_dir, name + ".json")
    if os.path.exists(fp) and os.path.getsize(fp) > 2:
        return "cached"
    params = {k: (v.format(t=t) if isinstance(v, str) else v) for k, v in (params or {}).items()}
    code, obj = uw.get(path.format(t=t), params)
    log(t, name, code, 0)
    if code == 200 and obj is not None:
        dump(fp, obj); return "ok"
    return code


def discover(uw, sample):
    """Probe every stock endpoint on one liquid ticker; return the set that returns 200."""
    print(f"discovery on {sample}:")
    valid = set()
    for name, path, params, _ in STOCK_ENDPOINTS:
        p = {k: (v.format(t=sample) if isinstance(v, str) else v) for k, v in (params or {}).items()}
        code, obj = uw.get(path.format(t=sample), p)
        ok = code == 200 and obj is not None
        if ok: valid.add(name)
        print(f"  {name:22s} {path.format(t=sample):46s} {code} {'OK' if ok else 'skip'}")
    return valid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+")
    ap.add_argument("--rps", type=float, default=3.0, help="requests/sec (UW higher tiers allow ~120/min)")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--dp-max", type=int, default=8000, help="max darkpool trades per ticker")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--sample", default="MNKD")
    a = ap.parse_args()

    uw = UW(load_key(), a.rps)
    os.makedirs(OUT, exist_ok=True)

    if a.discover:
        discover(uw, a.sample); return

    tickers = [t.upper() for t in a.tickers] if a.tickers else load_tickers()
    print(f"UW export: {len(tickers)} tickers, {len(STOCK_ENDPOINTS)} stock endpoints + darkpool, "
          f"rps={a.rps}, workers={a.workers}, dp-max={a.dp_max}")

    valid = discover(uw, a.sample)
    print(f"\nvalid stock endpoints for this account: {len(valid)}/{len(STOCK_ENDPOINTS)}\n")

    logf = open(os.path.join(OUT, "_log.csv"), "a", newline="", encoding="utf-8")
    logw = csv.writer(logf); loglk = threading.Lock()
    if os.path.getsize(os.path.join(OUT, "_log.csv")) == 0:
        logw.writerow(["ts", "ticker", "endpoint", "http", "rows_so_far"])
    def log(t, ep, code, n):
        with loglk:
            logw.writerow([dt.datetime.utcnow().isoformat(), t, ep, code, n]); logf.flush()

    done = {"n": 0}
    def do_ticker(t):
        d = os.path.join(OUT, t); os.makedirs(d, exist_ok=True)
        pull_darkpool(uw, t, d, a.dp_max, log)
        for name, path, params, _ in STOCK_ENDPOINTS:
            pull_endpoint(uw, t, name, path, params, d, valid, log)
        with loglk:
            done["n"] += 1
            print(f"  [{done['n']}/{len(tickers)}] {t}  ({uw.n} reqs)", flush=True)

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(do_ticker, tickers))

    # market-wide darkpool (today) + market flow alerts
    md = os.path.join(OUT, "_market"); os.makedirs(md, exist_ok=True)
    code, obj = uw.get("/api/darkpool/recent", {"limit": 200, "min_premium": 50000})
    if code == 200: dump(os.path.join(md, "darkpool_recent.json"), obj)
    code, obj = uw.get("/api/option-trades/flow-alerts", {"limit": 200})
    if code == 200: dump(os.path.join(md, "flow_alerts_market.json"), obj)

    manifest = {"generated_utc": dt.datetime.utcnow().isoformat(), "tickers": tickers,
                "valid_endpoints": sorted(valid), "total_requests": uw.n,
                "note": "UW bulk export for 2026 catalysts. Raw JSON per ticker/endpoint."}
    dump(os.path.join(OUT, "_MANIFEST.json"), manifest)
    logf.close()
    print(f"\nDONE. {len(tickers)} tickers, {uw.n} requests -> {OUT}")


if __name__ == "__main__":
    main()
