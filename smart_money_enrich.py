"""smart_money_enrich.py — add options + dark pool signals to readout_forward.csv.

David: "have the .bat populate the .csv with current option chain, dark pool, etc for catalysts,
that might tell us more on what smart money thinks."

For each ticker in readout_forward.csv, pulls from Unusual Whales (the same API the 9realms UW
addon uses) and appends columns describing how OPTIONS and DARK POOL are positioned into the
readout:

  sm_cp_ratio     call volume / put volume            (>1 = call-heavy = bullish lean)
  sm_unusual_x    today call vol / 30-day avg          (how unusual the options volume is)
  sm_bull_prem    bullish premium $ (ask-side calls)
  sm_bear_prem    bearish premium $
  sm_net_prem     net call premium $                   (+ = bullish money)
  sm_call_oi      call open interest
  sm_put_oi       put open interest
  sm_dp_prints    # dark pool block prints
  sm_dp_prem      total dark pool $ traded
  sm_dp_lean      ACCUM / DISTRIB / MIXED              (prints at ask vs at bid)
  sm_gex_sign     +GEX / -GEX                          (-GEX = dealer chase / squeeze regime)
  sm_signal       BULLISH / BEARISH / MIXED / QUIET    (composite; see below)

THE HONEST FRAME (this is a READ, not a signal):
  - Small/nano biotechs often have NO options and NO dark pool. Blank there means "no smart-money
    footprint to read", NOT bearish. David already knows dark pool won't exist for the tiny names.
  - Options flow is smart money AND dealer hedging AND retail lottery tickets, mixed together.
    A high call/put ratio pre-readout is suggestive, not proof. Our own UOA backtest found
    SCREAMING-bullish on large caps was mostly hedging noise; the gold signal was ELEVATED+MIXED.
  - Weekend runs show FRIDAY's close positioning. Fine for a watchlist; not live.
  Not investment advice.
"""
import csv
import datetime as dt
import os
import re
import socket
import sys
import time

# uw_live uses requests without an explicit timeout on every path; a slow/dead response hangs the
# whole enrich (it did, on the last ticker). A socket default timeout bounds every network call.
socket.setdefaulttimeout(12)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OP = os.path.join(HERE, "Odin Perfection")
sys.path.insert(0, OP)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(OP, ".env"))
except Exception:
    pass
try:
    import uw_live
except Exception as e:
    print(f"[smart_money] uw_live unavailable ({e}) — leaving CSV as-is.")
    sys.exit(0)

SM_COLS = ["sm_cp_ratio", "sm_unusual_x", "sm_bull_prem", "sm_bear_prem", "sm_net_prem",
           "sm_call_oi", "sm_put_oi", "sm_dp_prints", "sm_dp_prem", "sm_dp_lean",
           "sm_gex_sign", "sm_implied_date", "sm_implied_oi", "sm_implied_conf",
           "sm_signal", "sm_asof"]


def _f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def options_signal(tk):
    try:
        ov = uw_live.options_volume(tk)
    except Exception:
        return {}
    if not ov or not isinstance(ov, list):
        return {}
    o = ov[0]
    cv, pv = _f(o.get("call_volume")), _f(o.get("put_volume"))
    avg = _f(o.get("avg_30_day_call_volume"))
    # CAP the ratio. When put_volume==0 the true ratio is infinite; showing the raw call count
    # (STTK read "4011") looks like a nonsense ratio. Cap at 99 and let 99 mean "calls only /
    # essentially no puts". A capped 99 still scores call-heavy in the composite, correctly.
    if pv > 0:
        cp = round(min(cv / pv, 99.0), 2)
    else:
        cp = 99.0 if cv > 0 else 0
    return {
        "sm_cp_ratio": cp,
        "sm_unusual_x": round(cv / avg, 1) if avg > 0 else "",
        "sm_bull_prem": int(_f(o.get("bullish_premium"))),
        "sm_bear_prem": int(_f(o.get("bearish_premium"))),
        "sm_net_prem": int(_f(o.get("net_call_premium")) - _f(o.get("net_put_premium"))),
        "sm_call_oi": int(_f(o.get("call_open_interest"))),
        "sm_put_oi": int(_f(o.get("put_open_interest"))),
        "sm_asof": o.get("date", ""),
    }


def darkpool_signal(tk):
    try:
        dp = uw_live.darkpool_by_ticker(tk, 100)
    except Exception:
        return {}
    if not dp or not isinstance(dp, list):
        return {}
    prem = sum(_f(p.get("premium")) for p in dp)
    accum = distrib = 0
    for p in dp:
        px, ask, bid = _f(p.get("price")), _f(p.get("nbbo_ask")), _f(p.get("nbbo_bid"))
        if ask and px >= ask - 1e-9:
            accum += _f(p.get("premium"))
        elif bid and px <= bid + 1e-9:
            distrib += _f(p.get("premium"))
    lean = "MIXED"
    if accum > distrib * 1.5:
        lean = "ACCUM"
    elif distrib > accum * 1.5:
        lean = "DISTRIB"
    return {"sm_dp_prints": len(dp), "sm_dp_prem": int(prem), "sm_dp_lean": lean}


_OCC = re.compile(r"^[A-Z]+(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")


def _occ_expiry(sym):
    """OCC option symbol -> (expiry date, 'C'/'P'). e.g. HELP261218C00010000 -> (2026-12-18,'C')."""
    m = _OCC.match(sym or "")
    if not m:
        return None
    try:
        return dt.date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3))), m.group(4)
    except ValueError:
        return None


def implied_date(tk):
    """THE OPTIONS-IMPLIED CATALYST DATE (David's idea, 2026-07-19).

    Traders buy the nearest option expiry that safely COVERS a binary catalyst, so the expiry that
    holds the most forward CALL open interest is a crowd-sourced guess at when the readout lands.
    HELP's OI concentrates in Dec-2026 (its APPROACH Ph3 is guided Q4 2026); EYPT's in Oct-2026
    (LUGANO topline mid-2026). We report the max-call-OI expiry and its SHARE of all forward call OI
    as a confidence: a high share = the crowd agrees on a date; a low share = OI is smeared, weak signal.

    Guards: skip <10 DTE (front-month noise) and >15 months (LEAPs held for reasons unrelated to any
    one catalyst). It is a HEURISTIC, not a disclosure — the real event usually lands BEFORE the
    concentrated expiry (traders buy buffer), and one big spread can dominate a thin small-cap chain."""
    try:
        cons = uw_live.option_contracts(tk)
    except Exception:
        return {}
    if not cons or not isinstance(cons, list):
        return {}
    today = dt.date.today()
    by_exp = {}
    total = 0.0
    for c in cons:
        pe = _occ_expiry(c.get("option_symbol"))
        if not pe or pe[1] != "C":
            continue
        exp = pe[0]
        dte = (exp - today).days
        if dte < 10 or dte > 460:
            continue
        oi = _f(c.get("open_interest"))
        if oi <= 0:
            continue
        by_exp[exp] = by_exp.get(exp, 0.0) + oi
        total += oi
    if not by_exp or total <= 0:
        return {}
    # Prefer the EARLIEST expiry that is still "hot" (>= 60% of the peak expiry's OI), so an
    # imminent catalyst cluster is not masked by a bigger far-dated LEAP. On CAPR/REPL the raw max
    # was Jan-2027 (standing LEAP calls), hiding their August PDUFAs; the nearest-hot rule surfaces
    # the near cluster when one exists, and falls back to the peak when the peak stands alone.
    peak = max(by_exp.values())
    best_exp = min(e for e, oi in by_exp.items() if oi >= 0.60 * peak)
    return {"sm_implied_date": best_exp.isoformat(),
            "sm_implied_oi": int(by_exp[best_exp]),
            "sm_implied_conf": round(by_exp[best_exp] / total, 2)}


def gex_sign(tk):
    try:
        g = uw_live.greek_exposure(tk)
    except Exception:
        return {}
    if not g or not isinstance(g, list):
        return {}
    latest = g[-1] if g[-1].get("date", "") >= g[0].get("date", "") else g[0]
    net = _f(latest.get("call_gamma")) - _f(latest.get("put_gamma"))
    return {"sm_gex_sign": "+GEX" if net >= 0 else "-GEX"}


def composite(row):
    """BULLISH / BEARISH / MIXED / QUIET from the pieces. Directional AND has-a-footprint."""
    cp = _f(row.get("sm_cp_ratio"))
    bull, bear = _f(row.get("sm_bull_prem")), _f(row.get("sm_bear_prem"))
    dp = row.get("sm_dp_lean", "")
    has_flow = row.get("sm_cp_ratio", "") != "" or row.get("sm_dp_prem", "") != ""
    if not has_flow:
        return "QUIET"           # no options + no dark pool = nothing to read (often a nano)
    score = 0
    if cp >= 2.0: score += 1
    if cp and cp <= 0.5: score -= 1
    if bull > bear * 1.3 and bull > 0: score += 1
    if bear > bull * 1.3 and bear > 0: score -= 1
    if dp == "ACCUM": score += 1
    if dp == "DISTRIB": score -= 1
    return "BULLISH" if score >= 2 else "BEARISH" if score <= -2 else "MIXED"


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        # FRESHEST of {base, _new} (2026-08-13): when Excel holds readout_forward.csv open, the
        # scan writes readout_forward_new.csv instead -- enriching the stale base would put
        # yesterday's tickers under today's timestamps.
        cands = [c for c in (os.path.join(HERE, "readout_forward.csv"),
                             os.path.join(HERE, "readout_forward_new.csv"))
                 if os.path.exists(c)]
        path = max(cands, key=os.path.getmtime) if cands else \
            os.path.join(HERE, "readout_forward.csv")
        print(f"[smart_money] enriching {os.path.basename(path)}")
    if not os.path.exists(path):
        print(f"[smart_money] {path} not found."); return
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows:
        print("[smart_money] empty CSV."); return
    tickers = [r.get("ticker", "").strip() for r in rows]
    print(f"[smart_money] enriching {len(rows)} rows with UW options + dark pool...")

    # HARD PER-TICKER TIMEOUT via a DAEMON thread. uw_live's requests calls do not honor
    # socket.setdefaulttimeout on the read, so a hung ticker stalled the run at 40/51. A
    # ThreadPoolExecutor made it WORSE — 4 hung workers exhaust the pool and the next submit
    # blocks forever. A daemon thread per ticker is the fix: join with a timeout, and if it is
    # still stuck we ABANDON it — daemon threads are killed when the process exits, so a hung
    # network call can never block the final CSV write.
    import threading
    PER_TICKER = 20

    def one(tk, out):
        try:
            d = {}
            d.update(options_signal(tk))
            d.update(darkpool_signal(tk))
            d.update(gex_sign(tk))
            d.update(implied_date(tk))
            out.update(d)
        except Exception:
            pass

    enr = {}
    uniq = [t for t in dict.fromkeys(tickers) if t]
    for i, tk in enumerate(uniq):
        out = {}
        th = threading.Thread(target=one, args=(tk, out), daemon=True)
        th.start()
        th.join(PER_TICKER)
        out["sm_signal"] = composite(out)
        if th.is_alive():
            out["sm_signal"] = out.get("sm_signal") or "QUIET"   # abandoned, dies at exit
        enr[tk] = out
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(uniq)}", flush=True)

    hdr = list(rows[0].keys())
    for c in SM_COLS:
        if c not in hdr:
            hdr.append(c)
    for r in rows:
        d = enr.get(r.get("ticker", "").strip(), {})
        for c in SM_COLS:
            r[c] = d.get(c, "")
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)
    # LOCK-RESISTANT WRITE. The first run finished all 51 tickers, then os.replace threw
    # PermissionError [WinError 5] — the Documents folder is OneDrive-synced, which locks the
    # file mid-sync, and the bat's `start readout_forward.csv` can leave it open in a viewer.
    # Retry with backoff; if the target is still locked, DON'T lose the work — write a sibling
    # readout_forward_enriched.csv and tell the user. Never discard completed enrichment.
    ok = False
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            ok = True
            break
        except PermissionError:
            time.sleep(1.5 * (attempt + 1))
    if not ok:
        alt = os.path.splitext(path)[0] + "_enriched.csv"
        try:
            os.replace(tmp, alt)
            print(f"[smart_money] {os.path.basename(path)} was LOCKED (close it / OneDrive) — "
                  f"wrote {os.path.basename(alt)} instead. Your data is safe.")
            path = alt
        except Exception as e:
            print(f"[smart_money] could not write ({e}); enriched data left in {tmp}")

    sig = {}
    for tk, d in enr.items():
        s = d.get("sm_signal", "QUIET")
        sig[s] = sig.get(s, 0) + 1
    print(f"[smart_money] done. signal mix: {sig}")
    bull = [tk for tk, d in enr.items() if d.get("sm_signal") == "BULLISH"]
    if bull:
        print(f"[smart_money] BULLISH options/dark-pool lean into the readout: {sorted(bull)}")
    print("[smart_money] READ not signal — options flow mixes smart money, hedging, and retail. "
          "Not investment advice.")


if __name__ == "__main__":
    main()
