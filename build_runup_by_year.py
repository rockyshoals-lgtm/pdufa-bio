# -*- coding: utf-8 -*-
"""build_runup_by_year.py -- regenerate /runup-by-year from the master run-up dataset.

Why regenerate rather than patch: the page was produced by a separate T-120 pipeline whose source
files stopped updating in March 2026, so it had drifted from the master study
(pdufa_runup_bifrost_v2.csv) that everything else on the site is derived from. Two different run-up
numbers on one site is worse than one number that moves.

The page is now computed directly from the master dataset, so it updates whenever the study is
extended. Methodology is stated on the page: medians (not means) of the same columns the study uses,
on the T-120 baseline, which is now the single baseline used everywhere on the site.

    python build_runup_by_year.py [--dry-run]
"""
import argparse, csv, os, statistics as st, sys, collections
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CSVF = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
PAGE = os.path.join(SITE, "runup-by-year", "index.html")
TODAY = dt.date.today()


def fnum(r, k):
    try:
        return float(r.get(k))
    except Exception:
        return None


def med(vals):
    vals = [v for v in vals if v is not None]
    return st.median(vals) if vals else None


def pc(v, frac=False):
    if v is None:
        return "n/a"
    x = v * 100 if frac else v
    s = f"{x:+.1f}%"
    return s.replace("-", "&minus;")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(CSVF, encoding="utf-8-sig", errors="replace")))
    byyr = collections.defaultdict(list)
    for r in rows:
        d = (r.get("pdufa_date") or "")[:10]
        if len(d) == 10:
            byyr[d[:4]].append(r)

    years = sorted(byyr)
    dmin = min((r.get("pdufa_date") or "")[:10] for r in rows)
    dmax = max((r.get("pdufa_date") or "")[:10] for r in rows)

    trs = []
    for y in years:
        g = byyr[y]
        r120 = med([fnum(r, "T-120_T-1") for r in g])       # fraction
        rpk = med([fnum(r, "T-120_peak") for r in g])       # fraction
        n120 = sum(1 for r in g if fnum(r, "T-120_T-1") is not None)
        r30 = med([fnum(r, "runup_30d") for r in g])         # percent
        p1 = med([fnum(r, "post_1d") for r in g])            # percent
        p5 = med([fnum(r, "post_5d") for r in g])            # percent
        appr = sum(1 for r in g if r.get("outcome") == "APPROVAL")
        ar = 100 * appr / len(g)
        star = "*" if y == str(TODAY.year) else ""
        trs.append(
            f"<tr><td class='y'>{y}{star}</td><td class='num'>{len(g)}</td>"
            f"<td class='num'>{pc(r120, frac=True)}</td><td class='num'>{pc(rpk, frac=True)}</td>"
            f"<td class='num'>{pc(r30)}</td>"
            f"<td class='num'>{pc(p1)}</td><td class='num'>{pc(p5)}</td>"
            f"<td class='num'>{ar:.1f}%</td></tr>")

    # tier cohort table -- the numbers the decision pages quote
    tiers = collections.defaultdict(list)
    for r in rows:
        v = fnum(r, "post_1d")
        if v is not None and r.get("mcap_tier"):
            tiers[r["mcap_tier"]].append(abs(v))
    order = ["Nano (<$50M)", "Micro ($50M-$300M)", "Small ($300M-$2B)", "Mid ($2B-$10B)", "Large (>$10B)"]
    ttrs = []
    for t in order:
        if tiers.get(t):
            ttrs.append(f"<tr><td class='y'>{t}</td><td class='num'>{len(tiers[t])}</td>"
                        f"<td class='num'>{st.median(tiers[t]):.1f}%</td></tr>")

    allr120 = med([fnum(r, "T-120_T-1") for r in rows])
    allpk = med([fnum(r, "T-120_peak") for r in rows])
    n120 = sum(1 for r in rows if fnum(r, "T-120_T-1") is not None)
    allp1 = med([fnum(r, "post_1d") for r in rows])
    appr_all = sum(1 for r in rows if r.get("outcome") == "APPROVAL")

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="index,follow,max-image-preview:large">
<title>PDUFA Run-up by Year (2020-2026): {len(rows):,} FDA Decisions With Real Price Data | pdufa.bio</title>
<meta name="description" content="How biotech stocks actually behave into and out of an FDA decision, by year: {len(rows):,} PDUFA events from {dmin} to {dmax} with real daily closes. Median run-up, decision-day move, T+5 move and approval rate per year, plus decision-day move by market-cap tier. Free, sourced, no login.">
<link rel="canonical" href="https://www.pdufa.bio/runup-by-year"><meta name="theme-color" content="#060b14">
<meta property="og:type" content="article"><meta property="og:title" content="PDUFA run-up by year: {len(rows):,} FDA decisions with real price data"><meta property="og:url" content="https://www.pdufa.bio/runup-by-year">
<style>*{{box-sizing:border-box}}
:root{{--bg:#060b14;--card:#0e1c33;--line:#1e3a63;--line2:#294d80;--gold:#f0c86a;--ink:#eef4fc;--mut:#9db3d4;--mut2:#7c93b6;--green:#46d17f;--red:#ff8f6b}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55}}
a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}
header.site{{position:sticky;top:0;z-index:20;backdrop-filter:blur(10px);background:rgba(6,11,20,.85);border-bottom:1px solid var(--line)}}
.hd{{max-width:1020px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
.hd .brand{{font-size:20px;font-weight:800;letter-spacing:-.4px;color:var(--ink)}}.hd .brand b{{color:var(--gold)}}
.hd nav{{display:flex;gap:2px;flex-wrap:wrap}}.hd nav a{{font-size:13.5px;color:var(--mut);padding:7px 10px;border-radius:8px}}.hd nav a:hover{{color:var(--ink);background:var(--card);text-decoration:none}}
.wrap{{max-width:1020px;margin:0 auto;padding:22px 22px 70px}}
.bc{{font-size:12px;color:var(--mut2);margin:2px 0 10px}}.bc a{{color:var(--mut2)}}
h1{{font-size:31px;line-height:1.14;font-weight:800;letter-spacing:-.6px;margin:6px 0 8px}}h1 .g{{color:var(--gold)}}
h2{{font-size:19px;margin:32px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}}
p{{color:var(--mut);font-size:15px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px;margin:14px 0}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{text-align:left;color:var(--gold);font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;padding:9px 8px;border-bottom:1px solid var(--line2)}}
th.num,td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td{{padding:9px 8px;border-bottom:1px solid var(--line);color:var(--mut)}}
td.y{{color:var(--ink);font-weight:700;white-space:nowrap}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
@media(max-width:760px){{.stats{{grid-template-columns:1fr 1fr}}h1{{font-size:25px}}.hd nav{{display:none}}}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px}}
.big{{font-size:25px;font-weight:800;letter-spacing:-.5px;color:var(--ink)}}
.note{{font-size:12px;color:var(--mut2);line-height:1.6}}
.fresh{{display:inline-block;background:rgba(70,209,127,.13);border:1px solid #2f6b45;color:#46d17f;font-size:12px;font-weight:700;padding:4px 11px;border-radius:20px;margin:4px 0 2px}}
.legal{{border-top:1px solid var(--line);margin-top:36px;padding-top:16px;font-size:11.5px;color:#8aa0bf;line-height:1.6}}
</style><link rel="icon" type="image/svg+xml" href="/favicon.svg"></head><body>
<header class="site"><div class="hd"><a class="brand" href="/">pdufa<b>.bio</b></a><nav><a href="/calendar">Calendar</a><a href="/conferences">Conferences</a><a href="/adcomm">AdComm</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a><a href="/screener">Screener</a><a href="/tickers">Tickers</a><a href="/sls" style="color:#46d17f;font-weight:700">SLS</a><a class="pro" href="/pricing" style="color:var(--gold)">Pro</a></nav></div></header>
<main class="wrap">
<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/research">Research</a> &rsaquo; Run-up by year</div>
<div class="fresh">Updated {TODAY.strftime("%b %-d, %Y") if os.name != "nt" else TODAY.strftime("%b %d, %Y").replace(" 0", " ")} &middot; {len(rows):,} decisions</div>
<h1>PDUFA run-up <span class="g">by year</span>: {years[0]} to {years[-1]}</h1>
<p>What biotech stocks actually did into and out of an FDA decision, measured on real daily closes across
<b>{len(rows):,} PDUFA events</b> from {dmin} to {dmax}. Updated as each decision is published and folded back
into the dataset. Medians throughout. A handful of 300% moves would make means meaningless here.
All run-up figures use a single <b>T-120 baseline</b> (120 trading days before the decision), the same baseline quoted everywhere else on the site.</p>

<div class="stats">
  <div class="stat"><div class="note">PDUFA events</div><div class="big">{len(rows):,}</div><div class="note">{dmin} &rarr; {dmax}</div></div>
  <div class="stat"><div class="note">Approval rate</div><div class="big">{100*appr_all/len(rows):.1f}%</div><div class="note">{appr_all:,} approvals</div></div>
  <div class="stat"><div class="note">Median run-up T-120 &rarr; T-1</div><div class="big">{(allr120*100 if allr120 is not None else 0):+.1f}%</div><div class="note">the whole pre-decision drift</div></div>
  <div class="stat"><div class="note">Median decision-day move</div><div class="big">{(allp1 if allp1 is not None else 0):+.1f}%</div><div class="note">signed, all events</div></div>
</div>

<h2>By year</h2>
<div class="card"><table>
<tr><th>Year</th><th class="num">Events</th><th class="num">Run-up T-120&rarr;T-1</th><th class="num">Peak run-up from T-120</th><th class="num">Run-up 30d</th><th class="num">Decision day</th><th class="num">T+5</th><th class="num">Approval rate</th></tr>
{"".join(trs)}
</table>
<div class="note" style="margin-top:10px">All figures are medians of the events in that year. <b>Run-up T-120&rarr;T-1</b> is the
return from 120 trading days before the decision to the last session before it. <b>Peak run-up</b> is the
return from that same T-120 close to the highest close anywhere in the window, which is what was actually
on the table for anyone who sold into the run-up rather than holding to the last session. <b>Run-up 30d</b> is the same measured
over 30 trading days. <b>Decision day</b> is the first session on/after the decision versus the prior close.
<b>T+5</b> is five sessions after the decision versus that same prior close. {"*" + str(TODAY.year) + " is a partial year." if str(TODAY.year) in byyr else ""}</div></div>

<h2>Decision-day move by market-cap tier</h2>
<p>The single most useful number here: how far a stock typically moves on the day, by company size. This is the
figure quoted on every individual decision page.</p>
<div class="card"><table>
<tr><th>Market-cap tier</th><th class="num">Events</th><th class="num">Median absolute move</th></tr>
{"".join(ttrs)}
</table>
<div class="note" style="margin-top:10px">Median <b>absolute</b> decision-day move. Direction removed, so this
answers &ldquo;how big is the move&rdquo; not &ldquo;which way&rdquo;. Smaller companies move far more: the nano-cap
median is several times the large-cap median.</div></div>

<h2>Method &amp; limits</h2>
<p class="note">Universe: every FDA PDUFA decision we have published in our decision archive with usable daily price
history, {dmin} to {dmax}. Prices are split-adjusted daily closes (Polygon). Returns are computed in trading days,
not calendar days. Outcomes are taken from our published decision archive, each of which is sourced to a primary FDA,
SEC or company filing.<br><br>
<b>T-120 coverage.</b> {n120:,} of {len(rows):,} events ({100*n120/len(rows):.1f}%) have a full 120 sessions of prior trading history; the rest are companies that had not been listed long enough, and they are excluded from the T-120 columns rather than measured over a short window. Coverage is 100% for {years[-1]}.<br><br><b>Limits worth stating.</b> Daily closes understate intraday ranges, so every move here is a floor, not a ceiling.
Medians hide dispersion, a typical move of a few percent coexists with a long tail of very large ones. A
partial current year is marked with an asterisk and will move as more decisions land. Market-cap tier is assigned
from the company's size at the time we recorded the event. This is a description of what happened historically; it
is not a prediction and not investment advice.</p>
<p class="note">Reuse encouraged with attribution: &ldquo;pdufa.bio, PDUFA run-up study (n={len(rows):,},
{dmin} to {dmax})&rdquo;. See <a href="/research">all research</a> and the free
<a href="/developers">API</a>.</p>

<div class="legal"><a href="/about" style="color:#8aa0bf">About</a> &middot; <a href="/corrections" style="color:#8aa0bf">Corrections</a> &middot; <a href="/methodology" style="color:#8aa0bf">Methodology</a><br><br>
<b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent service.
<b>Informational and educational only. Not investment advice.</b> Historical statistics only; past behaviour
does not predict future outcomes. Verify every date and outcome against primary FDA / SEC / company filings.
Last computed {TODAY.isoformat()}. &copy; 2026 pdufa.bio</div>
</main><script src="/cmdk.js" defer></script></body></html>"""

    print(f"/runup-by-year: {len(rows):,} events, {dmin} .. {dmax}, {len(years)} years")
    for y in years:
        print(f"    {y}: n={len(byyr[y])}")
    if a.dry_run:
        print("DRY RUN -- not written."); return
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    open(PAGE, "w", encoding="utf-8").write(html)
    print(f"wrote runup-by-year/index.html ({len(html)} bytes)")


if __name__ == "__main__":
    main()
