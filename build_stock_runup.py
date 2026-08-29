# -*- coding: utf-8 -*-
"""build_stock_runup.py -- this stock's own T-120 numbers, measured, not modelled.

Every run-up figure on the site has until now been a cohort statistic: "across 1,827 decisions the
median peak was 17.8%". True, useful, and not what a reader looking at one ticker is asking. They
want to know what THIS stock did into its own catalysts, and where it stands right now.

Both are computable from public daily closes, so both stay inside the facts-only rule. Two blocks:

  RUN-UP SO FAR (upcoming catalysts). The stock's move from its own T-120 anchor to the latest
  close, plus the highest close since that anchor. This is a measurement of something that has
  already happened. It forecasts nothing.

  PAST CATALYSTS (history). Each prior decision for that ticker with its own measured T-120 figures
  and the outcome.

The honesty problem here is small n, and it is the whole reason this needed care. AZN has 81 events
in the study; most small caps have one or two. A "median" of one event is not a median, it is a
single number wearing a statistic's clothes, and it is exactly the kind of thing a reader would
reasonably act on. So: every event is listed individually with n always visible, and a per-ticker
median is computed ONLY at n >= 3. Below that the page shows the individual figures and points at
the cohort for the statistical base.

The T-120 definition is taken from the study itself (add_t120_baseline.py): the base is the close
120 trading sessions before the eve of the decision, and the peak is the highest close anywhere in
that window. Using a different anchor here would produce a per-stock number that is not comparable
to the cohort number printed beside it.

For an upcoming catalyst the eve has not happened, so the anchor is found by counting sessions back
from the future eve. Future sessions are counted as weekdays minus the NYSE holiday calendar
embedded below, which is stated so the anchor date is reproducible rather than approximate.

    python build_stock_runup.py [--dry-run] [--ticker MRNA] [--limit N]
"""
import argparse, csv, datetime as dt, json, os, re, statistics, sys, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
STUDY = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
STATS = os.path.join(HERE, "runup_study_stats.json")
CACHE = os.path.join(HERE, "stock_runup_cache.json")
BEGIN, END = "<!--STOCKRUNUP:BEGIN-->", "<!--STOCKRUNUP:END-->"

MIN_N_FOR_MEDIAN = 3          # below this a "median" would be theatre
WINDOW = 120

# NYSE closures. Stated explicitly so a reader can reproduce the anchor date rather than trust it.
HOLIDAYS = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
    "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18",
    "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
}


def sessions_between(a, b):
    """Trading sessions strictly after `a` up to and including `b`."""
    n, d = 0, a + dt.timedelta(days=1)
    while d <= b:
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
            n += 1
        d += dt.timedelta(days=1)
    return n


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("POLYGON_API_KEY")


def bars(ticker, key, cache):
    # A cache hit must still be CURRENT. The original unconditional return meant a series
    # fetched once was served forever: on 2026-08-29, 58 of 60 tickers ended at 2026-08-03,
    # so every hub's "run-up so far" figure was 26 days stale under a same-day freshness
    # stamp. Refresh when the newest cached close is more than 4 calendar days old (covers
    # weekends + a holiday); a failed refresh falls back to the stale series rather than
    # nothing, and says so.
    if ticker in cache:
        got = cache[ticker]
        newest = got[-1][0] if got else ""
        if newest >= (dt.date.today() - dt.timedelta(days=4)).isoformat():
            return got
    start = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    u = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/"
         f"{dt.date.today().isoformat()}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    try:
        res = json.loads(urllib.request.urlopen(u, timeout=30).read()).get("results") or []
    except Exception:
        res = []
    out = [(dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(), x["c"])
           for x in res]
    if not out and cache.get(ticker):
        # A failed refresh must not replace a stale-but-real series with nothing.
        print(f"  {ticker}: price refresh failed; serving cached series "
              f"(ends {cache[ticker][-1][0]})")
        return cache[ticker]
    cache[ticker] = out
    return out


def live_runup(series, decision_date):
    """Move from this stock's own T-120 anchor to the latest close. None if unmeasurable."""
    if len(series) < 5:
        return None
    try:
        dec = dt.date.fromisoformat(decision_date)
    except Exception:
        return None
    today = dt.date.fromisoformat(series[-1][0])
    if dec <= today:
        return None                                  # not upcoming
    eve = dec - dt.timedelta(days=1)
    remaining = sessions_between(today, eve)          # sessions still to run
    elapsed = WINDOW - remaining
    if elapsed < 5:
        return None                                  # window has barely opened; nothing to report
    if elapsed > len(series):
        return None                                  # not enough listed history to anchor honestly
    anchor_i = len(series) - elapsed
    if anchor_i < 0 or anchor_i >= len(series):
        return None
    a_date, a_close = series[anchor_i]
    if not a_close:
        return None
    closes = [c for _, c in series[anchor_i:] if c]
    last = series[-1][1]
    return {"anchor_date": a_date, "anchor": a_close, "last": last, "last_date": series[-1][0],
            "pct": (last / a_close - 1) * 100, "peak": (max(closes) / a_close - 1) * 100,
            "elapsed": elapsed, "remaining": remaining}


def history(rows, ticker):
    ev = []
    for r in rows:
        if (r.get("ticker") or "").upper() != ticker:
            continue
        v = r.get("T-120_T-1")
        if v in (None, "", "nan"):
            continue
        try:
            ev.append({"date": r.get("pdufa_date") or r.get("eve_date"),
                       "outcome": (r.get("outcome") or "").strip(),
                       "t1": float(v) * 100,
                       "peak": (float(r["T-120_peak"]) * 100
                                if r.get("T-120_peak") not in (None, "", "nan") else None)})
        except (TypeError, ValueError):
            continue
    return sorted(ev, key=lambda x: x["date"] or "", reverse=True)


def pct(x, colour=True):
    c = "#46d17f" if x >= 0 else "#ff8f8f"
    return f'<b class="lit" style="color:{c if colour else "inherit"}">{x:+.1f}%</b>'


def render(ticker, live, ev, cohort):
    o = [BEGIN, '<section class="stockrunup" style="margin:24px 0">',
         f'<h2 style="font-size:18px;margin:0 0 4px">{ticker} run-up, measured</h2>',
         '<p style="font-size:12.5px;color:var(--mut2);line-height:1.65;margin:0 0 12px">'
         'Computed from this stock\'s own daily closing prices, on the same T-120 basis as the '
         '<a href="/runup-by-year">run-up study</a>: the baseline is the close 120 trading sessions '
         'before the eve of the decision. These are measurements of what already happened, not '
         'predictions.</p>']

    if live:
        o.append(
            f'<div style="background:var(--card);border:1px solid var(--line);border-radius:12px;'
            f'padding:14px 16px;margin:0 0 14px">'
            f'<div style="font-size:12px;color:var(--mut2);text-transform:uppercase;'
            f'letter-spacing:.5px">Run-up so far, this catalyst</div>'
            f'<div style="font-size:15px;color:#dce7f7;line-height:1.7;margin-top:6px">'
            f'Since its T-120 baseline on <span class="lit">{live["anchor_date"]}</span> '
            f'(${live["anchor"]:,.2f}), {ticker} is {pct(live["pct"])} to '
            f'<span class="lit">${live["last"]:,.2f}</span> at the close on '
            f'<span class="lit">{live["last_date"]}</span>. The highest close since that baseline is '
            f'{pct(live["peak"])} above it.</div>'
            f'<div style="font-size:12px;color:var(--mut2);margin-top:7px">'
            f'{live["elapsed"]} of 120 sessions elapsed, {live["remaining"]} to go. '
            f'Cohort context: across {cohort.get("n_events", 0):,} past decisions the median peak '
            f'from T-120 was {cohort.get("T-120_peak_median_pct", 0):.1f}% and the median move to '
            f'the day before the decision was {cohort.get("T-120_T-1_median_pct", 0):.1f}%.</div>'
            f'</div>')

    if ev:
        n = len(ev)
        rows = "".join(
            f'<tr><td class="lit" style="padding:7px 10px;white-space:nowrap">{e["date"]}</td>'
            f'<td style="padding:7px 10px;color:var(--mut2)">{e["outcome"] or "-"}</td>'
            f'<td style="padding:7px 10px;text-align:right">{pct(e["t1"])}</td>'
            f'<td style="padding:7px 10px;text-align:right">'
            f'{pct(e["peak"]) if e["peak"] is not None else "-"}</td></tr>' for e in ev[:12])
        o.append(
            f'<div style="font-size:12px;color:var(--mut2);text-transform:uppercase;'
            f'letter-spacing:.5px;margin:0 0 6px">{ticker}\'s past FDA decisions '
            f'(n={n})</div>'
            f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;'
            f'font-size:13px;border:1px solid var(--line);border-radius:10px">'
            f'<thead><tr style="color:var(--mut2);text-align:left;font-size:11.5px;'
            f'text-transform:uppercase;letter-spacing:.4px">'
            f'<th style="padding:8px 10px">Decision</th><th style="padding:8px 10px">Outcome</th>'
            f'<th style="padding:8px 10px;text-align:right">T-120 to eve</th>'
            f'<th style="padding:8px 10px;text-align:right">T-120 to peak</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')
        if n > 12:
            o.append(f'<div style="font-size:12px;color:var(--mut2);margin-top:6px">'
                     f'Showing the 12 most recent of {n}.</div>')

        if n >= MIN_N_FOR_MEDIAN:
            m1 = statistics.median([e["t1"] for e in ev])
            pk = [e["peak"] for e in ev if e["peak"] is not None]
            mp = statistics.median(pk) if pk else None
            o.append(
                f'<div style="font-size:13px;color:#dce7f7;line-height:1.7;margin-top:9px">'
                f'Median across these {n} decisions: {pct(m1)} from T-120 to the eve'
                + (f', {pct(mp)} to the peak' if mp is not None else '') + '. '
                f'<span style="color:var(--mut2)">A median over {n} events describes this stock\'s '
                f'past only. It is not a forecast, and the cohort figures on the '
                f'<a href="/runup-by-year">run-up study</a> are the larger statistical base.</span>'
                f'</div>')
        else:
            o.append(
                f'<div style="font-size:13px;color:var(--mut2);line-height:1.7;margin-top:9px">'
                f'With {"only one decision" if n == 1 else f"only {n} decisions"} on record, no '
                f'median is shown: an average of {n} event{"s" if n > 1 else ""} would not be a '
                f'meaningful statistic. The individual figures above are exact. For a statistical '
                f'base see the <a href="/runup-by-year">run-up study</a>, built on '
                f'{cohort.get("n_events", 0):,} decisions.</div>')
    elif not live:
        return ""

    o.append('</section>')
    o.append(END)
    return "".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ticker")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    key = load_key()
    cohort = json.load(open(STATS, encoding="utf-8")) if os.path.exists(STATS) else {}
    rows = list(csv.DictReader(open(STUDY, encoding="utf-8-sig", errors="replace")))

    # upcoming day-precision catalysts, by ticker
    upcoming = {}
    if os.path.exists(DATASET):
        m = re.search(r"export default (\[.*\])",
                      open(DATASET, encoding="utf-8", errors="replace").read(), re.S)
        for e in (json.loads(m.group(1)) if m else []):
            if e.get("dp") == "day" and e.get("d") and e.get("t") and e.get("type") == "PDUFA":
                t = str(e["t"]).upper()
                if t not in upcoming or e["d"] < upcoming[t]:
                    upcoming[t] = e["d"]

    tickers = sorted({os.path.basename(os.path.dirname(p))
                      for p in __import__("glob").glob(
                          os.path.join(SITE, "ticker", "*", "index.html"))})
    if a.ticker:
        tickers = [t for t in tickers if t.upper() == a.ticker.upper()]
    if a.limit:
        tickers = tickers[:a.limit]

    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            cache = {}

    n_live = n_hist = n_written = n_unblocked = 0
    for t in tickers:
        ev = history(rows, t)
        live = None
        if key and t in upcoming:
            live = live_runup(bars(t, key, cache), upcoming[t])
        if not ev and not live:
            continue
        block = render(t, live, ev, cohort)
        if not block:
            continue
        page = os.path.join(SITE, "ticker", t, "index.html")
        doc = open(page, encoding="utf-8", errors="replace").read()
        if BEGIN in doc:
            doc = doc.split(BEGIN, 1)[0] + block + doc.split(END, 1)[1]
        else:
            for anchor in ("<!--DEEPDIVE:BEGIN-->", '<div class="legal"', "<footer",
                           "</div></body>"):
                if anchor in doc:
                    doc = doc.replace(anchor, block + anchor, 1)
                    break
            else:
                continue
        # 92 hubs were noindexed for being thin, which was the right call when they held a ticker
        # symbol and nothing else. A page carrying a measured decision-history table (AMGN has 25
        # rows) or a live run-up is no longer thin, so the noindex is lifted where the content now
        # justifies it. The bar is deliberately the same one used for showing a median: three or
        # more decisions, or an in-flight catalyst. One or two rows stays noindexed, because a
        # two-row table is still a thin page and re-inviting Google to those was the original
        # mistake.
        if "noindex" in doc and (len(ev) >= MIN_N_FOR_MEDIAN or live):
            doc = doc.replace('<meta name="robots" content="noindex,follow">', "")
            n_unblocked += 1

        if not a.dry_run:
            open(page, "w", encoding="utf-8").write(doc)
        n_written += 1
        n_live += bool(live)
        n_hist += bool(ev)

    if not a.dry_run and cache:
        json.dump(cache, open(CACHE, "w"), separators=(",", ":"))

    print(f"stock run-up blocks: {n_written} page(s) written "
          f"({n_live} with a live run-up, {n_hist} with decision history, "
          f"{n_unblocked} lifted out of noindex)"
          + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
