#!/usr/bin/env python3
"""
MOMENTUM / MEME / NEWS-EXPLOSION + UOA SCANNER  v1.1
=====================================================
A modern rebuild of hype_stock*.py (+ odin_options_scanner) on robust APIs.

WHAT IT DOES
  Scans the WHOLE US market for stocks exploding right now and for unusual
  options activity across ALL sectors, scores each 0-100, classifies it, and
  tags biotech names for the ODIN / HEIMDALL engine.

  UNIVERSE = FMP price-movers (gainers + most-actives)  UNION  the Unusual
  Whales market-wide flow-alert firehose (all sectors). The UOA union means a
  name with big options flow is scanned even if the STOCK hasn't moved yet --
  options often lead price.

SIGNAL STACK  (primary = market microstructure; social = SECONDARY, never proof)
  PRIMARY
    - Price surge          FMP  (1d % move)
    - Relative volume      FMP  (today vol vs avg)
    - Per-name options     UW   (call/put vol vs 30d avg, call skew, sweeps)
    - Market-wide UOA       UW   (whole-tape flow-alert firehose, ALL sectors:
                           premium-sized prints, sweeps, vol>>OI, ask-side
                           direction -> a separate 0-100 uoa_score + bias)
    - Short-squeeze fuel   UW   (% float short, days-to-cover)
    - News / catalyst      FMP  (fresh PR/headline + keyword classifier)
    - Analyst change       FMP  (upgrades in the last week)
  SECONDARY -- WEIGHTED BLEND (capped):
    - LunarCrush 0.40 / Reddit 0.35 / StockTwits 0.25, re-normalized over
      whichever sources are live.

OUTPUT  momentum_scan_<ts>.json + momentum_scan_latest.json + .js twin + console.
        Pairs with momentum_meme_dashboard.html.

KEYS (env vars -- never hard-code secrets)
    FMP_API_KEY (required) · UW_API_KEY (options/short/UOA) ·
    REDDIT_CLIENT_ID/SECRET/USER_AGENT (opt) · LUNARCRUSH_API_KEY (opt, paid)

DISCLAIMER: Informational and educational only -- NOT investment advice.
Owned and operated by Odin Catalyst LLC.
"""

import os, sys, json, time, re, datetime as dt
import requests

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
FMP_KEY = os.getenv("FMP_API_KEY", "")
UW_KEY  = os.getenv("UW_API_KEY", os.getenv("UNUSUAL_WHALES_TOKEN", ""))
LC_KEY  = os.getenv("LUNARCRUSH_API_KEY", "")
RDT_ID  = os.getenv("REDDIT_CLIENT_ID", "")
RDT_SEC = os.getenv("REDDIT_CLIENT_SECRET", "")
RDT_UA  = os.getenv("REDDIT_USER_AGENT", "MomentumMemeScanner/1.0")

FMP_BASE = "https://financialmodelingprep.com/stable"
UW_BASE  = "https://api.unusualwhales.com"
LC_BASE  = "https://lunarcrush.com/api4"
ST_BASE  = "https://api.stocktwits.com/api/2"

MIN_PRICE, MAX_PRICE = 0.50, 5000.0
MIN_AVG_VOLUME       = 150_000
MIN_DAY_CHANGE_PCT   = 5.0
MAX_MARKET_CAP       = 300_000_000     # micro/nano only (<= $300M, the rocket zone). Set None to include all.
TOP_N_PER_LIST       = 60
ENRICH_LIMIT         = 70
REQUEST_PAUSE        = 0.15

VOL_SPIKE_HIGH   = 5.0
OPT_SPIKE_HIGH   = 4.0
SHORT_FLOAT_HIGH = 0.20
DTC_HIGH         = 5.0
NEWS_LOOKBACK_DAYS = 2
REDDIT_SUBS = ["wallstreetbets","stocks","pennystocks","options",
               "smallstreetbets","superstonk","robinhoodpennystocks"]
REDDIT_POST_LIMIT = 200
MENTION_HIGH        = 25
STOCKTWITS_MSG_HIGH = 20

# market-wide UOA firehose (Unusual Whales flow-alerts, ALL sectors)
UW_FLOW_ALERTS_PATH = "api/option-trades/flow-alerts"
UOA_FIREHOSE_LIMIT  = 200
UOA_MIN_PREMIUM     = 150_000     # ignore single alerts below this
UOA_TICKER_MIN_PREM = 300_000     # aggregated premium for a UOA-only name to qualify
UOA_PREM_HIGH       = 2_000_000   # aggregated premium that maxes the uoa_score

MEME_KEYWORDS = ['moon','diamond hands','apes','hodl','tendies','squeeze','yolo','rocket','short','gamma']
CATALYST_KEYWORDS = ['fda','approval','pdufa','breakthrough','phase 3','topline','data','partnership',
                     'buyout','merger','acquisition','acquire','activist','upgrade','contract','award',
                     'beats','earnings beat','guidance','positive','grant','authorization','clearance']
BIOTECH_SECTORS = ['healthcare','biotechnology','pharmaceutical','drug','life sciences']

W = dict(price=25, volume=20, options=15, short=15, news=15, social=10)
SOCIAL_WEIGHTS = {"lunarcrush": 0.40, "reddit": 0.35, "stocktwits": 0.25}

# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------
def _get(url, params=None, headers=None, timeout=15):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        time.sleep(REQUEST_PAUSE)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None
def fmp(path, **params):
    if not FMP_KEY: return None
    params["apikey"] = FMP_KEY
    return _get(f"{FMP_BASE}/{path}", params=params)
def uw(path, **params):
    if not UW_KEY: return None
    return _get(f"{UW_BASE}/{path}", params=params,
                headers={"Authorization": f"Bearer {UW_KEY}", "Accept": "application/json"})
def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))
def mcap_tier(mc):
    mc = float(mc) if mc else 0
    if mc <= 0:     return "?"
    if mc < 50e6:   return "nano"
    if mc < 300e6:  return "micro"
    if mc < 2e9:    return "small"
    if mc < 10e9:   return "mid"
    return "large"

# ----------------------------------------------------------------------------
# UNIVERSE  (movers)  +  market-wide UOA firehose
# ----------------------------------------------------------------------------
def build_movers():
    seen, uni = set(), []
    for path in ("biggest-gainers", "most-actives"):
        for row in (fmp(path) or [])[:TOP_N_PER_LIST]:
            s = (row.get("symbol") or "").upper()
            if not s or s in seen or any(c in s for c in ".^/") or len(s) > 5: continue
            seen.add(s); uni.append(s)
    return uni

def uw_market_uoa():
    """Whole-tape flow-alert firehose across ALL sectors -> {ticker: agg}."""
    if not UW_KEY: return {}
    d = uw(UW_FLOW_ALERTS_PATH, limit=UOA_FIREHOSE_LIMIT,
           min_premium=str(UOA_MIN_PREMIUM), vol_greater_oi="true")
    rows = (d.get("result") or d.get("data") if isinstance(d, dict) else d) or []
    agg = {}
    for a in rows:
        if (a.get("issue_type") or "Common Stock") not in ("Common Stock", "ADR"): continue
        t = (a.get("ticker") or "").upper()
        if not t: continue
        prem = float(a.get("total_premium", 0) or 0)
        ask  = float(a.get("total_ask_side_prem", 0) or 0)
        typ  = a.get("type", "")
        g = agg.setdefault(t, {"prem":0.0,"call_ask":0.0,"put_ask":0.0,"sweeps":0,"max_voi":0.0,
                               "sector":a.get("sector",""),"mcap":a.get("marketcap"),"n":0})
        g["prem"] += prem; g["n"] += 1
        if typ == "call": g["call_ask"] += ask
        elif typ == "put": g["put_ask"] += ask
        if a.get("has_sweep"): g["sweeps"] += 1
        g["max_voi"] = max(g["max_voi"], float(a.get("volume_oi_ratio", 0) or 0))
    return agg

# ----------------------------------------------------------------------------
# FMP / UW per-name enrichment
# ----------------------------------------------------------------------------
def get_quote(sym):
    q = fmp("quote", symbol=sym)
    return q[0] if isinstance(q, list) and q else (q if isinstance(q, dict) else None)
def get_profile(sym):
    p = fmp("profile", symbol=sym); return p[0] if isinstance(p, list) and p else None
def get_news(sym):  return fmp("news/stock", symbols=sym, limit=15) or []
def get_grades(sym): return fmp("grades", symbol=sym, limit=20) or []
def _unwrap(d):
    if isinstance(d, dict) and "data" in d: d = d["data"]
    if isinstance(d, list) and d: return d[0]
    return d if isinstance(d, dict) else None
def uw_options_volume(sym): return _unwrap(uw(f"api/stock/{sym}/options-volume"))
def uw_short(sym):          return _unwrap(uw(f"api/shorts/{sym}/data"))
def uw_flow_alerts(sym):
    d = uw(f"api/stock/{sym}/flow-alerts", limit=50)
    if isinstance(d, dict) and "data" in d: return d["data"]
    return d if isinstance(d, list) else []

# ----------------------------------------------------------------------------
# SOCIAL (three sources -> normalized 0..1 each)
# ----------------------------------------------------------------------------
_REDDIT = _VADER = None
def _init_reddit():
    global _REDDIT, _VADER
    if not (RDT_ID and RDT_SEC): return False
    try:
        import praw
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        _REDDIT = praw.Reddit(client_id=RDT_ID, client_secret=RDT_SEC, user_agent=RDT_UA)
        _VADER  = SentimentIntensityAnalyzer(); return True
    except Exception as e:
        print(f"[reddit] disabled ({e})"); return False

def reddit_pass(universe):
    raw = {s: {"mentions":0,"sent":0.0,"meme":0} for s in universe}
    if not _init_reddit(): return {}
    uset, pat = set(universe), re.compile(r'\$?\b([A-Z]{2,5})\b')
    for sub in REDDIT_SUBS:
        try:
            posts = list(_REDDIT.subreddit(sub).hot(limit=REDDIT_POST_LIMIT//2)) + \
                    list(_REDDIT.subreddit(sub).new(limit=REDDIT_POST_LIMIT//2))
        except Exception:
            continue
        for p in posts:
            text = f"{p.title} {getattr(p,'selftext','')}"
            hits = set(pat.findall(text.upper())) & uset
            if not hits: continue
            sc = _VADER.polarity_scores(text)["compound"]
            mm = sum(1 for k in MEME_KEYWORDS if k in text.lower())
            for h in hits:
                raw[h]["mentions"] += 1; raw[h]["sent"] += sc; raw[h]["meme"] += mm
    sub = {}
    for s, d in raw.items():
        if d["mentions"] <= 0: continue
        m = clamp(d["mentions"]/MENTION_HIGH)
        sent = clamp((d["sent"]/max(d["mentions"],1) + 1)/2)
        meme = clamp(d["meme"]/5.0)
        sub[s] = 0.5*m + 0.3*sent + 0.2*meme
    return sub

def stocktwits_one(sym):
    j = _get(f"{ST_BASE}/streams/symbol/{sym}.json")
    if not j or "messages" not in j: return None
    msgs = j["messages"]; n = len(msgs)
    bull = sum(1 for m in msgs if ((m.get("entities") or {}).get("sentiment") or {}).get("basic") == "Bullish")
    bear = sum(1 for m in msgs if ((m.get("entities") or {}).get("sentiment") or {}).get("basic") == "Bearish")
    t = bull + bear; br = (bull/t) if t else 0.5
    return {"score": round(0.6*clamp(n/STOCKTWITS_MSG_HIGH) + 0.4*clamp((br-0.4)/0.5),3),
            "msgs": n, "bull_ratio": round(br,2)}

def lunarcrush_one(sym):
    if not LC_KEY: return None
    j = _get(f"{LC_BASE}/public/stocks/{sym}/v1", headers={"Authorization": f"Bearer {LC_KEY}"})
    d = (j or {}).get("data") or {}
    if not d: return None
    gx = clamp(float(d.get("galaxy_score",0) or 0)/100.0)
    sent = float(d.get("sentiment", d.get("average_sentiment",0)) or 0)
    if sent > 1: sent /= 100.0
    return {"score": round(clamp(0.6*gx + 0.4*clamp(sent)),3),
            "galaxy": d.get("galaxy_score"), "sentiment": d.get("sentiment")}

# ----------------------------------------------------------------------------
# SCORING
# ----------------------------------------------------------------------------
def score_name(sym, quote, profile, news, grades, optv, short, flow, rsub, st, lc, uoa=None):
    comp, flags = {}, []
    chg = float(quote.get("changePercentage", quote.get("changesPercentage", 0)) or 0)
    comp["price"] = round(W["price"] * clamp(chg/30.0), 2)
    if chg >= 20: flags.append("PRICE_PARABOLIC")

    vol  = float(quote.get("volume", 0) or 0)
    avgv = float(quote.get("avgVolume", quote.get("averageVolume", 0)) or 0)
    if avgv <= 0 and profile:  # FIX: /stable/quote omits avgVolume; /stable/profile carries averageVolume
        avgv = float(profile.get("averageVolume", profile.get("volAvg", 0)) or 0)
    relv = (vol/avgv) if avgv > 0 else 0
    comp["volume"] = round(W["volume"] * clamp(relv/VOL_SPIKE_HIGH), 2)
    if relv >= VOL_SPIKE_HIGH: flags.append("VOLUME_EXPLOSION")

    osc = 0.0
    if optv:
        cv = float(optv.get("call_volume",0) or 0); pv = float(optv.get("put_volume",0) or 0)
        a30 = float(optv.get("avg_30_day_call_volume",0) or 0)
        spike = (cv/a30) if a30 > 0 else 0
        cpr = (cv/(cv+pv)) if (cv+pv) > 0 else 0.5
        osc = 0.7*clamp(spike/OPT_SPIKE_HIGH) + 0.3*clamp((cpr-0.5)/0.4)
        if spike >= OPT_SPIKE_HIGH: flags.append("OPTIONS_SPIKE")
    if flow and sum(1 for f in flow if f.get("has_sweep")) >= 3:
        osc = min(1.0, osc + 0.15); flags.append("CALL_SWEEPS")
    comp["options"] = round(W["options"]*osc, 2)

    # --- market-wide UOA (all sectors; can LEAD price) -> separate 0-100 score ---
    uoa_score, uoa_bias, uoa_prem = 0.0, "", 0.0
    if uoa:
        uoa_prem = uoa["prem"]; netd = uoa["call_ask"] - uoa["put_ask"]
        uoa_bias = "BULLISH" if netd > 0 else ("BEARISH" if netd < 0 else "MIXED")
        conv = clamp(abs(netd)/uoa_prem) if uoa_prem > 0 else 0
        uoa_score = round(min(100.0, 40*clamp(uoa_prem/UOA_PREM_HIGH) + 20*clamp(uoa["sweeps"]/4)
                              + 20*clamp(uoa["max_voi"]/10) + 20*conv), 1)
        comp["options"] = round(max(comp["options"], W["options"]*clamp(uoa_score/100)), 2)
        tag = f"${uoa_prem/1e6:.1f}M" if uoa_prem >= 1e6 else f"${uoa_prem/1e3:.0f}K"
        flags.append(f"UOA_{tag}_{uoa_bias}")
        if uoa["sweeps"] >= 3: flags.append("SWEEP_CLUSTER")
        if uoa["max_voi"] >= 10: flags.append("VOL>>OI")

    ssc = 0.0
    if short:
        pfs = float(short.get("short_percent_of_float", short.get("short_float_pct",0)) or 0)
        if pfs > 1: pfs /= 100.0
        dtc = float(short.get("days_to_cover", short.get("dtc",0)) or 0)
        ssc = 0.6*clamp(pfs/SHORT_FLOAT_HIGH) + 0.4*clamp(dtc/DTC_HIGH)
        if pfs >= SHORT_FLOAT_HIGH: flags.append("HIGH_SHORT_INTEREST")
    comp["short"] = round(W["short"]*ssc, 2)

    nsc, headline = 0.0, ""
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=NEWS_LOOKBACK_DAYS)
    for n in news:
        ds = (n.get("publishedDate") or n.get("date") or "")[:19]
        try: nd = dt.datetime.strptime(ds, "%Y-%m-%d %H:%M:%S")
        except Exception: continue
        if nd < cutoff: continue
        txt = f"{n.get('title','')} {n.get('text','')}".lower()
        hk = [k for k in CATALYST_KEYWORDS if k in txt]
        if hk: nsc = max(nsc, 0.6 + 0.1*len(hk)); headline = headline or n.get("title","")[:140]
        elif not headline: headline = n.get("title","")[:140]; nsc = max(nsc, 0.3)
    comp["news"] = round(W["news"]*clamp(nsc), 2)
    if nsc >= 0.6: flags.append("FRESH_CATALYST")
    wk = dt.datetime.utcnow() - dt.timedelta(days=7); upg = 0
    for g in grades:
        try: gd = dt.datetime.strptime((g.get("date") or "")[:10], "%Y-%m-%d")
        except Exception: continue
        act = f"{g.get('action','')}{g.get('newGrade','')}".lower()
        if gd >= wk and ("up" in act or "buy" in act or "outperform" in act): upg += 1
    if upg: comp["news"] = round(min(W["news"], comp["news"]+2*upg), 2); flags.append(f"ANALYST_UPGRADE_x{upg}")

    subs, wts, sdet = {}, {}, {}
    if rsub is not None and sym in rsub:
        subs["reddit"] = rsub[sym]; wts["reddit"] = SOCIAL_WEIGHTS["reddit"]; flags.append("REDDIT_BUZZ")
    if st:
        subs["stocktwits"] = st["score"]; wts["stocktwits"] = SOCIAL_WEIGHTS["stocktwits"]; sdet["stocktwits"] = st
        if st.get("msgs",0) >= STOCKTWITS_MSG_HIGH and st.get("bull_ratio",0) >= 0.65: flags.append("STOCKTWITS_BULLISH")
    if lc:
        subs["lunarcrush"] = lc["score"]; wts["lunarcrush"] = SOCIAL_WEIGHTS["lunarcrush"]; sdet["lunarcrush"] = lc
        if lc.get("galaxy") and float(lc["galaxy"] or 0) >= 65: flags.append("LUNARCRUSH_HIGH_GALAXY")
    soc = (sum(subs[k]*wts[k] for k in subs)/sum(wts.values())) if subs else 0.0
    comp["social"] = round(W["social"]*clamp(soc), 2)

    total = round(sum(comp.values()), 1)

    # ROCKET = abnormal VOLUME *and* abnormal OPTIONS at the same time (the real movers)
    vol_hot = relv >= VOL_SPIKE_HIGH
    opt_hot = (comp["options"] >= 0.6*W["options"]) or uoa_score >= 50 \
              or ("OPTIONS_SPIKE" in flags) or ("CALL_SWEEPS" in flags) or ("SWEEP_CLUSTER" in flags)
    rocket = bool(vol_hot and opt_hot)
    if rocket: flags.insert(0, "ROCKET")

    sector = f"{(profile or {}).get('sector','')} {(profile or {}).get('industry','')}".lower()
    if not sector.strip() and uoa: sector = (uoa.get("sector","") or "").lower()
    is_bio = any(b in sector for b in BIOTECH_SECTORS)
    if is_bio: flags.append("BIOTECH")

    pv = comp["price"] + comp["volume"]
    if uoa_score >= 60 and pv < 20:                                        kind = "UOA_LEADER"
    elif comp["short"] >= 9 and comp["social"] >= 5 and comp["volume"] >= 10: kind = "MEME_SQUEEZE"
    elif comp["news"] >= 9 and pv >= 22:                                   kind = "NEWS_EXPLOSION"
    elif pv >= 24:                                                         kind = "MOMENTUM"
    elif total >= 35 or uoa_score >= 50:                                   kind = "WATCH"
    else:                                                                  kind = "NOISE"

    return dict(ticker=sym, score=total, uoa_score=uoa_score, uoa_bias=uoa_bias, rocket=rocket,
                uoa_premium=round(uoa_prem,0), kind=kind, biotech=is_bio,
                price=round(float(quote.get("price",0) or 0),2), day_change_pct=round(chg,2),
                rel_volume=round(relv,2), components=comp, flags=flags, headline=headline,
                sector=(profile or {}).get('sector','') or (uoa or {}).get('sector',''),
                market_cap=quote.get("marketCap"),
                mcap_tier=mcap_tier(quote.get("marketCap") or (uoa or {}).get("mcap")),
                social_sources=list(subs.keys()), social_detail=sdet)

# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def run_once():
    if not FMP_KEY:
        print("ERROR: set FMP_API_KEY (universe + price/volume/news needs it)."); sys.exit(1)
    t0 = time.time()
    print("Universe: FMP movers + UW market-wide UOA firehose (all sectors)...")
    movers = build_movers()
    uoa_map = uw_market_uoa()
    universe = list(dict.fromkeys(movers + list(uoa_map)))
    print(f"  {len(movers)} movers + {len(uoa_map)} UOA names -> {len(universe)} union")

    cands = []
    for s in universe:
        q = get_quote(s)
        if not q: continue
        price = float(q.get("price",0) or 0)
        avgv  = float(q.get("avgVolume", q.get("averageVolume",0)) or 0)
        chg   = float(q.get("changePercentage", q.get("changesPercentage",0)) or 0)
        if price < MIN_PRICE or price > MAX_PRICE: continue
        mc = float(q.get("marketCap") or (uoa_map.get(s) or {}).get("mcap") or 0)
        if MAX_MARKET_CAP and mc > MAX_MARKET_CAP: continue   # nano/micro/small only
        _liq = avgv if avgv > 0 else float(q.get("volume",0) or 0)  # FIX: quote lacks avgVolume; use today's volume as liquidity floor
        mover   = (_liq >= MIN_AVG_VOLUME and abs(chg) >= MIN_DAY_CHANGE_PCT)
        has_uoa = (s in uoa_map and uoa_map[s]["prem"] >= UOA_TICKER_MIN_PREM)
        if mover or has_uoa: cands.append((s, q))
    cands = cands[:ENRICH_LIMIT]
    print(f"  {len(cands)} candidates (movers or UOA>=${UOA_TICKER_MIN_PREM/1e3:.0f}K)")

    rsub = reddit_pass([s for s,_ in cands]) if (RDT_ID and RDT_SEC) else {}
    print(f"Social: reddit={'on' if (RDT_ID and RDT_SEC) else 'off'}  "
          f"lunarcrush={'on' if LC_KEY else 'off'}  stocktwits=on(best-effort)")

    print("Enriching...")
    results = [score_name(s, q, get_profile(s), get_news(s), get_grades(s),
                          uw_options_volume(s), uw_short(s), uw_flow_alerts(s),
                          rsub, stocktwits_one(s), lunarcrush_one(s), uoa_map.get(s))
               for s, q in cands]
    results.sort(key=lambda r: max(r["score"], r["uoa_score"]), reverse=True)

    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    payload = dict(generated=stamp, n=len(results), weights=W, social_weights=SOCIAL_WEIGHTS,
                   disclaimer="Informational/educational only - not investment advice.", results=results)
    here = os.path.dirname(os.path.abspath(__file__))
    for fn in (f"momentum_scan_{stamp}.json", "momentum_scan_latest.json"):
        with open(os.path.join(here, fn), "w") as f: json.dump(payload, f, indent=2, default=str)
    with open(os.path.join(here, "momentum_scan_latest.js"), "w") as f:
        f.write("window.MOMENTUM_DATA = " + json.dumps(payload, default=str) + ";")

    print(f"\n{'#':>2} {'TICKER':7} {'MOM':>4} {'UOA':>4} {'BIAS':8} {'CHG%':>7} {'RVOL':>5}  {'KIND':13} {'BIO':3} FLAGS")
    print("-"*112)
    for i, r in enumerate(results[:30], 1):
        print(f"{i:>2} {r['ticker']:7} {r['score']:>4} {r['uoa_score']:>4} {r['uoa_bias'][:8]:8} "
              f"{r['day_change_pct']:>7} {r['rel_volume']:>5} {r['kind']:13} {'Y' if r['biotech'] else ' ':3} "
              f"{','.join(r['flags'][:4])}")
    print(f"\nDone in {time.time()-t0:.0f}s. Wrote momentum_scan_latest.json. Open the dashboard. "
          f"Informational/educational only - not investment advice.")

def market_open_now():
    try:
        from zoneinfo import ZoneInfo
        now = dt.datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now = dt.datetime.utcnow() - dt.timedelta(hours=4)   # rough ET fallback
    if now.weekday() >= 5: return False
    mins = now.hour*60 + now.minute
    return 9*60+30 <= mins <= 16*60

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Momentum/Meme/UOA scanner")
    ap.add_argument("--loop", type=int, default=0,
                    help="re-run every N minutes and rewrite the dashboard data (0 = run once)")
    ap.add_argument("--market-hours", action="store_true",
                    help="in loop mode, only scan during US market hours (Mon-Fri 9:30-16:00 ET)")
    a = ap.parse_args()
    if a.loop <= 0:
        run_once(); return
    print(f"LOOP MODE: every {a.loop} min"
          + (" (market hours only)" if a.market_hours else "") + ".  Ctrl+C to stop.")
    while True:
        if (not a.market_hours) or market_open_now():
            try: run_once()
            except SystemExit: raise
            except Exception as e: print("scan error:", e)
        else:
            print(dt.datetime.now().strftime("%H:%M"), "market closed - skipping")
        time.sleep(a.loop * 60)

if __name__ == "__main__":
    main()
