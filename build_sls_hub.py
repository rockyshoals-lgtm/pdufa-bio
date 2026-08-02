# -*- coding: utf-8 -*-
"""build_sls_hub.py -- the canonical SLS (SELLAS Life Sciences) hub at /sls.

Facts only, every claim traceable to a primary source (SEC filing / company release) or computed
here from market data with the method stated. No opinions, no targets, no recommendation.

The hub answers the three questions the biotech community is actually asking:
  1. Where does the REGAL 80th event stand, and what does reaching it mechanically trigger?
  2. What did the June 24 2026 executive-agreement amendment ACTUALLY say (vs. what it was read as)?
  3. Has "company amends change-of-control terms" historically preceded a buyout?
"""
import json, os, time
import datetime as dt
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUTDIR = os.path.join(SITE, "sls")
TODAY = dt.date(2026, 8, 1)
BASE78 = dt.date(2026, 5, 11)          # as-of date of the 78-event disclosure
DAYS_SINCE = (TODAY - BASE78).days


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("POLYGON_API_KEY")


def daily(t, start, end, key):
    url = (f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{end}"
           f"?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                rows = (json.loads(r.read().decode()) or {}).get("results") or []
                return [(dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(), x["c"])
                        for x in rows if x.get("c")]
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** i); continue
            return []
        except Exception:
            time.sleep(1)
    return []


def chart(rows, marks):
    if len(rows) < 3:
        return ""
    W, H, PAD = 900, 250, 28
    ds = [d for d, c in rows]; cs = [c for d, c in rows]
    lo, hi = min(cs), max(cs); rng = (hi - lo) or 1; n = len(cs)
    X = lambda i: PAD + i * (W - 2 * PAD) / (n - 1)
    Y = lambda c: H - PAD - (c - lo) / rng * (H - 2 * PAD)
    pts = " ".join(f"{X(i):.1f},{Y(c):.1f}" for i, c in enumerate(cs))
    idx = {d: i for i, d in enumerate(ds)}
    p = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;display:block">',
         f'<line x1="{PAD}" y1="{H-PAD}" x2="{W-PAD}" y2="{H-PAD}" stroke="#1e3a63"/>',
         f'<polyline points="{pts}" fill="none" stroke="#6fb6ff" stroke-width="1.8"/>']
    for md, lbl, col in marks:
        i = idx.get(md) or next((j for j, d in enumerate(ds) if d >= md), None)
        if i is None:
            continue
        p.append(f'<line x1="{X(i):.1f}" y1="{PAD}" x2="{X(i):.1f}" y2="{H-PAD}" stroke="{col}" '
                 f'stroke-width="1" stroke-dasharray="3 3" opacity=".55"/>')
        p.append(f'<circle cx="{X(i):.1f}" cy="{Y(cs[i]):.1f}" r="4.5" fill="{col}" stroke="#02060d" '
                 f'stroke-width="1"><title>{lbl} ({ds[i]}) ${cs[i]:.2f}</title></circle>')
    for f in (0, .25, .5, .75, 1):
        v = lo + rng * f
        p.append(f'<text x="3" y="{Y(v)+4:.1f}" font-size="10" fill="#7c93b6">${v:.0f}</text>')
    for i in (0, n // 3, 2 * n // 3, n - 1):
        p.append(f'<text x="{X(i):.1f}" y="{H-9}" font-size="10" fill="#7c93b6" text-anchor="middle">{ds[i][:7]}</text>')
    p.append("</svg>")
    return "".join(p)


NAV = ('<nav><a href="/calendar">Calendar</a><a href="/conferences">Conferences</a>'
       '<a href="/adcomm">AdComm</a><a href="/decisions">Decisions</a>'
       '<a href="/runup-by-year">Run-up</a><a href="/readouts">Readouts</a>'
       '<a href="/screener">Screener</a><a href="/sls" style="color:#46d17f;font-weight:700">SLS</a>'
       '<a class="pro" href="/pricing" style="color:var(--gold)">Pro</a></nav>')


def main():
    key = load_key()
    rows = daily("SLS", "2024-10-01", TODAY.isoformat(), key)
    last = rows[-1][1] if rows else 0
    lastd = rows[-1][0] if rows else ""
    w52 = [c for d, c in rows if d >= (TODAY - dt.timedelta(days=365)).isoformat()]
    lo52, hi52 = (min(w52), max(w52)) if w52 else (0, 0)
    marks = [("2024-12-10", "60th event: interim analysis triggered", "#e3ba5e"),
             ("2025-01-23", "Interim analysis passed", "#e3ba5e"),
             ("2025-08-07", "IDMC: continue without modification", "#e3ba5e"),
             ("2025-12-29", "72 events disclosed", "#e3ba5e"),
             ("2026-05-12", "78 events disclosed", "#e3ba5e"),
             ("2026-06-25", "Exec change-of-control amendment", "#46d17f")]
    ch = chart(rows, marks)

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="index,follow,max-image-preview:large">
<title>SLS (SELLAS Life Sciences) Tracker &mdash; REGAL 80th Event, the Change-of-Control Amendment, and the Facts | pdufa.bio</title>
<meta name="description" content="The canonical SELLAS Life Sciences (NASDAQ: SLS) tracker: live REGAL 80th-event status (78 of 80 as of May 11, 2026), exactly what the June 24 2026 executive change-of-control amendment says, whether such amendments have historically preceded buyouts, and every dated catalyst with its measured stock reaction. Primary sources only.">
<link rel="canonical" href="https://www.pdufa.bio/sls"><meta name="theme-color" content="#060b14">
<meta property="og:type" content="article"><meta property="og:title" content="SLS Tracker: REGAL 80th event + the change-of-control amendment, in facts"><meta property="og:url" content="https://www.pdufa.bio/sls">
<style>*{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
:root{{--bg:#060b14;--card:#0e1c33;--cardh:#132745;--line:#1e3a63;--line2:#294d80;--gold:#f0c86a;--ink:#eef4fc;--mut:#9db3d4;--mut2:#7c93b6;--green:#46d17f;--red:#ff8f6b}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.58;-webkit-font-smoothing:antialiased}}
a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}
header.site{{position:sticky;top:0;z-index:20;backdrop-filter:blur(10px);background:rgba(6,11,20,.85);border-bottom:1px solid var(--line)}}
.hd{{max-width:1080px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
.hd .brand{{font-size:20px;font-weight:800;letter-spacing:-.4px;color:var(--ink)}}.hd .brand b{{color:var(--gold)}}
.hd nav{{display:flex;gap:2px;flex-wrap:wrap}}.hd nav a{{font-size:13.5px;color:var(--mut);padding:7px 10px;border-radius:8px}}.hd nav a:hover{{color:var(--ink);background:var(--card);text-decoration:none}}
.wrap{{max-width:1080px;margin:0 auto;padding:22px 22px 70px}}
.bc{{font-size:12px;color:var(--mut2);margin:2px 0 10px}}.bc a{{color:var(--mut2)}}
h1{{font-size:33px;line-height:1.13;font-weight:800;letter-spacing:-.7px;margin:6px 0 8px}}h1 .g{{color:var(--gold)}}
h2{{font-size:21px;margin:36px 0 8px;letter-spacing:-.3px;border-bottom:1px solid var(--line);padding-bottom:7px}}
h3{{font-size:15px;margin:20px 0 6px;color:var(--gold)}}
p{{color:var(--mut);font-size:15px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px;margin:14px 0}}
.kv{{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}}.kv:last-child{{border-bottom:0}}.kv span{{color:var(--mut)}}.kv b{{text-align:right}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:8px}}
th{{text-align:left;color:var(--gold);font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;padding:8px 6px;border-bottom:1px solid var(--line2)}}
td{{padding:8px 6px;border-bottom:1px solid var(--line);color:var(--mut);vertical-align:top}}
td.dt{{color:var(--ink);white-space:nowrap;font-variant-numeric:tabular-nums}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media(max-width:820px){{.grid4{{grid-template-columns:1fr 1fr}}.grid2{{grid-template-columns:1fr}}h1{{font-size:26px}}.hd nav{{display:none}}}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px}}
.big{{font-size:27px;font-weight:800;color:var(--ink);letter-spacing:-.5px}}
.note{{font-size:12px;color:var(--mut2);line-height:1.6}}
.fact{{font-size:13.5px;color:var(--mut);padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05)}}.fact:last-child{{border-bottom:0}}
.bull{{border-color:#2f6b45}}.bear{{border-color:#7a3a2b}}.bull h3{{color:var(--green)}}.bear h3{{color:var(--red)}}
.quote{{border-left:3px solid var(--gold);padding:8px 0 8px 14px;margin:12px 0;color:var(--ink);font-size:14.5px;background:rgba(240,200,106,.05)}}
.myth{{background:#081426;border:1px solid var(--line2);border-radius:10px;padding:13px 15px;margin:10px 0}}
.myth .r{{color:var(--red);font-weight:800;font-size:13px;text-transform:uppercase;letter-spacing:.4px}}
.myth .f{{color:var(--green);font-weight:800;font-size:13px;text-transform:uppercase;letter-spacing:.4px;margin-top:8px}}
.legal{{border-top:1px solid var(--line);margin-top:38px;padding-top:16px;font-size:11.5px;color:#8aa0bf;line-height:1.6}}
ol,ul{{color:var(--mut);font-size:14px}}li{{margin:5px 0}}
.pill{{display:inline-block;font-size:11.5px;font-weight:800;padding:3px 9px;border-radius:20px;background:rgba(70,209,127,.14);color:var(--green);border:1px solid #2f6b45}}
</style><link rel="icon" type="image/svg+xml" href="/favicon.svg"></head><body>
<header class="site"><div class="hd"><a class="brand" href="/">pdufa<b>.bio</b></a>{NAV}</div></header>
<main class="wrap">
<div class="bc"><a href="/">Home</a> &rsaquo; SLS tracker</div>
<h1>SELLAS Life Sciences <span class="g">(SLS)</span> &mdash; the facts, tracked</h1>
<p>SELLAS is at a rare juncture: a Phase 3 survival trial sitting two deaths from its final analysis, and an
executive-compensation filing that a large part of the retail market read as merger preparation. Both are
knowable from primary documents. This page states exactly what has been filed and disclosed &mdash; the
REGAL event mechanics, the full text and terms of the June 24 2026 amendment, whether such amendments have
historically preceded buyouts, and how the stock has actually reacted to every dated catalyst. There are no
forecasts, price targets, or recommendations anywhere on this page.</p>

<div class="grid4">
  <div class="stat"><div class="note">REGAL events (deaths)</div><div class="big">78 / 80</div><div class="note">as of May 11, 2026 &middot; {DAYS_SINCE}d ago</div></div>
  <div class="stat"><div class="note">80th event announced?</div><div class="big" style="color:var(--gold)">Not yet</div><div class="note">company says it will announce it</div></div>
  <div class="stat"><div class="note">Cash &amp; equivalents</div><div class="big">$107.1M</div><div class="note">Mar 31, 2026 (+$7.5M warrants)</div></div>
  <div class="stat"><div class="note">Last close</div><div class="big">${last:.2f}</div><div class="note">52w ${lo52:.2f}&ndash;${hi52:.2f} &middot; {lastd}</div></div>
</div>

<div class="card">{ch}
<div class="note" style="margin-top:9px">SLS daily closes, Oct 2024 &ndash; Aug 2026 (Polygon, split-adjusted). Gold markers = REGAL
milestone disclosures. Green marker = the June 24 2026 executive change-of-control amendment. Hover any marker for the date and close.</div></div>

<h2>1. The 80th event: what it is and where it stands</h2>
<p>REGAL (<a href="https://clinicaltrials.gov/study/NCT04229979">NCT04229979</a>) is a Phase 3, randomized,
open-label registrational trial of galinpepimut-S (GPS) as maintenance therapy in adults with AML in second
complete remission (CR2) after second-line salvage, who are ineligible for allogeneic stem-cell transplant.
Patients are randomized 1:1 to GPS versus investigator's choice of best available therapy, and the
<b>primary endpoint is overall survival</b>.</p>
<p>Because the endpoint is survival, the trial is <b>event-driven, not calendar-driven</b>: the statistical
analysis plan triggers the final analysis only once <b>80 events (deaths)</b> have occurred across both arms
pooled. Per the company's May 12, 2026 disclosure, reaching the 80th event triggers, in order: database lock
&rarr; blinded data review &rarr; statistical analysis &rarr; unblinding &rarr; disclosure of topline results.</p>
<p>Two facts govern how the running count should be read. <b>SELLAS states it remains blinded</b> to all
efficacy and survival outcomes, so the disclosed counts are pooled totals that cannot distinguish the GPS arm
from the control arm. And the company stated that because no outcomes analyses were performed, the one-time
aggregate update <b>incurred no statistical penalty</b>.</p>

<h3>Measured pace of event accrual</h3>
<div class="card"><table>
<tr><th>Interval</th><th class="num">Days</th><th class="num">Events</th><th class="num">Days per event</th></tr>
<tr><td class="dt">Dec 10, 2024 (60) &rarr; Dec 26, 2025 (72)</td><td class="num">381</td><td class="num">12</td><td class="num">31.8</td></tr>
<tr><td class="dt">Dec 26, 2025 (72) &rarr; May 11, 2026 (78)</td><td class="num">136</td><td class="num">6</td><td class="num">22.7</td></tr>
<tr><td class="dt"><b>Overall: 60 &rarr; 78</b></td><td class="num"><b>517</b></td><td class="num"><b>18</b></td><td class="num"><b>28.7</b></td></tr>
</table>
<div class="note" style="margin-top:10px">Applying each observed pace to the 2 remaining events from the 78-event as-of date
(May 11, 2026) implies arrival around <b>Jun 25</b>, <b>Jul 7</b> and <b>Jul 14, 2026</b> respectively. As of
<b>Aug 1, 2026</b> &mdash; <b>{DAYS_SINCE} days</b> after that as-of date &mdash; the 80th event has not been announced. This is
arithmetic on company-disclosed counts, not a projection model.</div></div>
<p>Context in the company's own words. After the IDMC's August 2025 recommendation, the 80th event had been
expected before year-end 2025; it did not occur. In the December 29, 2025 release CEO Angelos Stergiou stated
that survival times "appear longer than expected," and REGAL steering-committee member Dr. Yair Levy stated that
for non-transplant patients in this setting standard treatment carries "an expected median overall survival of
around eight months."</p>

<h2>2. The June 24, 2026 amendment &mdash; what it actually says</h2>
<p>On June 25, 2026 SELLAS shares rose roughly 15% and hit a 52-week high, on volume near double the 65-day
average. Widely-read coverage attributed the move substantially to a Form 8-K filed that week amending
executive severance terms, which was interpreted as preparation for a sale. Here is the filing itself.</p>
<p>The 8-K was filed under <b>Item 5.02(e) &mdash; Compensatory Arrangements of Certain Officers</b>, covering three
agreements: an amendment to CEO Dr. Angelos Stergiou's employment agreement, and amended-and-restated severance
and change-of-control letter agreements with CFO John Burns and Chief Development Officer Dr. Dragan Cicic.</p>

<div class="quote">"The Agreements were approved by the Board of Directors&hellip; upon recommendation of the
Compensation Committee of the Board, <b>following a review with the Company's independent compensation
consulting firm of certain market and competitive practices relating to executive severance agreements</b>."
<div class="note" style="margin-top:6px">&mdash; SELLAS Form 8-K, filed June 24, 2026 (Item 5.02(e))</div></div>

<h3>The actual terms</h3>
<div class="card">
<div class="kv"><span>CEO (Stergiou) &mdash; what changed</span><b>Only that certain change-of-control severance payments are paid as a <u>lump sum</u></b></div>
<div class="kv"><span>CEO &mdash; everything else</span><b>"The terms&hellip; remain unchanged in all other respects"</b></div>
<div class="kv"><span>CFO/CDO &mdash; non-CoC severance</span><b>9 months base salary + pro-rata target bonus + 9 months COBRA</b></div>
<div class="kv"><span>CFO/CDO &mdash; CoC severance</span><b>Lump sum = 15 months base salary; lump sum = target bonus; 18 months COBRA; full acceleration of unvested equity</b></div>
<div class="kv"><span>Change-of-Control Period</span><b>1 month before &rarr; 12 months after a change of control</b></div>
<div class="kv"><span>Trigger structure</span><b style="color:var(--green)">DOUBLE trigger &mdash; requires a change of control <u>AND</u> termination without Cause / resignation for Good Reason</b></div>
<div class="kv"><span>Conditioned on</span><b>Effective separation and general release agreement</b></div>
</div>

<h3>Five things the filing shows that the popular reading skipped</h3>
<div class="myth">
<div class="r">Read as</div>"They're locking in golden parachutes because a buyer is at the table."
<div class="f">What the document says</div>The benefits are <b>double-trigger</b>: a change of control alone pays nothing. An
executive must also be terminated without Cause or resign for Good Reason inside the window. Single-trigger
(vesting on the deal alone) is the structure that pays out on simply completing a sale. Double-trigger is also
the <b>majority market structure</b>, not an unusual one: Meridian Compensation Partners' 2023 study of
change-in-control severance arrangements found <b>91% of companies vest time-based equity on a double trigger</b>
&mdash; i.e. a qualifying termination following a change of control. SELLAS adopted the prevailing structure.
</div>
<div class="myth">
<div class="r">Read as</div>"A sudden, unexplained restructuring of executive contracts."
<div class="f">What the document says</div>The filing states its own rationale: Compensation Committee recommendation to the
Board, <b>following review with an independent compensation consulting firm of market and competitive practices</b>.
That is the standard description of routine benchmarking, and it is stated on the face of the filing.
</div>
<div class="myth">
<div class="r">Read as</div>"Massive payouts were added."
<div class="f">What the document says</div>The change-of-control cash benefit for the CFO and CDO is <b>15 months of
base salary</b> (1.25&times;) plus target bonus, with COBRA for up to 18 months. For scale, Meridian's 2023 study
found a <b>3&times; cash multiple is the plurality practice for CEOs (47%)</b>, with 2&times; also common. We note
explicitly that this is <b>not a like-for-like comparison</b> &mdash; that benchmark is for chief executives, while
the 15-month figure here applies to a CFO and a CDO, and non-CEO officers customarily carry lower multiples than
the CEO. The defensible statement is the narrow one: these are the disclosed terms, and they are cash multiples
of roughly one year's salary rather than multi-year packages.
</div>
<div class="myth">
<div class="r">Read as</div>"The CEO's package was overhauled."
<div class="f">What the document says</div>For the CEO the <b>only</b> change is the <b>form of payment</b> &mdash; certain
change-of-control severance is now paid as a lump sum rather than over time. The filing states the agreement is
otherwise unchanged. Converting instalments to a lump sum is a common administrative/tax-timing change.
</div>
<div class="myth">
<div class="r">Read as</div>"This is a merger-related filing."
<div class="f">What the document says</div>On the 8-K cover page, the boxes for <b>written communications under Rule 425</b>,
<b>soliciting material under Rule 14a-12</b>, and <b>pre-commencement tender-offer communications under Rules 14d-2(b)
and 13e-4(c)</b> are all <b>unchecked</b>. Those are the boxes a filer checks when a communication relates to a
merger or tender offer.
</div>
<p class="note">None of the above establishes that a transaction is <i>not</i> occurring. Companies do amend
compensation ahead of deals, and boards are not required to disclose negotiations. It establishes only what this
particular document does and does not say &mdash; and this document describes benchmarking with a double-trigger structure.</p>

<h2>3. Has this pattern historically preceded a buyout?</h2>
<p>The inference "change-of-control amendment &rarr; imminent acquisition" is testable. We searched SEC EDGAR
full-text for 8-K filings containing comparable change-of-control severance language over the trailing 12 months
(Aug 1, 2025 &ndash; Aug 1, 2026), kept filers in pharma/biotech SIC codes (2834, 2836, 8731), deduplicated to one
row per company, and then checked whether each ticker still trades independently today.</p>
<div class="card"><table>
<tr><th>Company</th><th>Ticker</th><th>Comparable CoC 8-K filed</th><th>Status as of Aug 1, 2026</th></tr>
<tr><td>Ardelyx, Inc.</td><td class="dt">ARDX</td><td class="dt">2025-08-04</td><td>Still trading independently</td></tr>
<tr><td>Stoke Therapeutics, Inc.</td><td class="dt">STOK</td><td class="dt">2025-10-06</td><td>Still trading independently</td></tr>
<tr><td>Xenon Pharmaceuticals Inc.</td><td class="dt">XENE</td><td class="dt">2025-12-01</td><td>Still trading independently</td></tr>
<tr><td>Imunon, Inc.</td><td class="dt">IMNN</td><td class="dt">2026-05-04</td><td>Still trading independently</td></tr>
<tr><td>SELLAS Life Sciences Group, Inc.</td><td class="dt">SLS</td><td class="dt">2026-06-25</td><td>Still trading independently</td></tr>
</table>
<div class="note" style="margin-top:10px"><b>Result: of the 5 comparable biotech/pharma filers identified in the window,
0 have been acquired or taken private as of Aug 1, 2026.</b></div></div>
<p class="note"><b>Stated limits of this measurement.</b> EDGAR full-text search matches exact phrases in the filing
body, and many companies describe these arrangements in other words or incorporate them by reference to an exhibit;
this search therefore <b>undercounts</b> the true population, and 5 is a small sample rather than a census. The
"still trading" check is also a proxy &mdash; a ticker can stop quoting for reasons other than acquisition
(bankruptcy, reverse merger, ticker change, delisting). Treat this as a directional check on a popular inference,
not a precise base rate. Readers can reproduce it: the filings are public and the tickers are named above.</p>
<p>The academic literature addresses a related but distinct question. Studies of <i>golden parachutes</i> find that
firms whose executives hold such arrangements are associated with a <b>greater likelihood of acquisition</b> and a
<b>lower acquisition premium</b>, and that adoption is generally received as a negative event, more so for more
generous agreements. Note the distinction that matters here: that research concerns <b>having</b> change-of-control
protection, not <b>amending its payment mechanics</b>, and it describes population-level associations rather than
a signal about any single company.</p>

<h2>4. Every dated catalyst and its measured stock reaction</h2>
<p>Day-of move is the close on the first trading day on or after the announcement versus the prior close; +5d is
five sessions later versus that same prior close. Computed from Polygon split-adjusted daily closes. The full
21-event table, including volume multiples, is in the companion study.</p>
<div class="card">
<div class="fact">Across 21 dated events since Nov 2024, the <b>mean absolute day-of move was 6.1%</b>; only <b>8 of 21 (38%)</b> closed higher on the day.</div>
<div class="fact">Mean signed day-of move was <b>&minus;1.1%</b>, while the mean move five sessions later was <b>+9.5%</b> &mdash; the drift after these events was consistently larger and more positive than the day-of reaction.</div>
<div class="fact">The two most positive-sounding REGAL headlines were sold on the day: the 60th-event interim-analysis trigger (Dec 10, 2024) closed <b>&minus;4.6%</b> and fell a further 17.8% the next session; the positive interim-analysis outcome (Jan 23, 2025) closed <b>&minus;13.3%</b> on <b>17.4&times;</b> average volume &mdash; then was +16.7% five sessions later.</div>
<div class="fact">The Dec 29, 2025 release disclosing that the 80th event had <b>not</b> arrived on schedule closed <b>+16.7%</b> on 4.3&times; volume, and was <b>+42.9%</b> five sessions later.</div>
<div class="fact">REGAL/IDMC events (n=5) averaged a 7.2% absolute day-of move and <b>+16.5%</b> at +5d; SLS009 and conference-data events (n=9) averaged 4.0% day-of and +3.1% at +5d.</div>
<div style="margin-top:12px"><a href="/research/sls-deep-dive" style="font-weight:700">Full event-by-event table with volume multiples &rarr;</a></div>
</div>

<h2>5. Documented bull and bear facts</h2>
<p>Both columns contain only statements traceable to a primary source or computed from market data, presented
without weighting. Neither column is a recommendation.</p>
<div class="grid2">
<div class="card bull"><h3>Cited by the bull case</h3>
<div class="fact">The pre-specified <b>60-event interim analysis was passed</b> (futility, efficacy, safety) &mdash; announced Jan 23, 2025.</div>
<div class="fact">At that analysis, <b>pooled median survival appeared to be at least 13.5 months</b> against an expected ~6 months in a comparable population.</div>
<div class="fact">The <b>IDMC recommended continuation without modification</b> in August 2025, with no safety concerns identified.</div>
<div class="fact"><b>Event accrual has run slower than projected</b>, which the company attributes to survival times appearing longer than expected (pooled, blinded).</div>
<div class="fact"><b>FDA and EMA orphan drug designation</b> for GPS in AML, plus <b>FDA Fast Track</b> in AML.</div>
<div class="fact"><b>$107.1M cash</b> at Mar 31, 2026 plus $7.5M of Q2 warrant proceeds; total liabilities $6.8M; no debt disclosed.</div>
<div class="fact">A <b>$150M ATM is established and entirely unused</b> &mdash; the company states it has not sold any shares through it.</div>
<div class="fact">Q1 2026 R&amp;D rose to $5.1M from $3.2M, attributed partly to <b>preparation for a potential BLA</b> for GPS following the final analysis.</div>
<div class="fact">SLS009 at ASH 2025: <b>46% ORR</b> across cohorts, 58% in patients with one prior line, median OS 8.9 months in the least pre-treated cohort vs a stated ~2.5-month historical benchmark.</div>
<div class="fact">A second, independent catalyst: 80-patient <b>Phase 2 of SLS009 in first-line AML, topline expected Q4 2026</b>.</div>
</div>
<div class="card bear"><h3>Cited by the bear case</h3>
<div class="fact"><b>The timeline has slipped repeatedly.</b> The 80th event was expected before year-end 2025; as of Aug 1, 2026 it is unannounced &mdash; {DAYS_SINCE} days past the 78-event as-of date and beyond all three windows implied by the company's own disclosed pace.</div>
<div class="fact"><b>Blinded pooled counts cannot distinguish the arms.</b> Longer pooled survival could reflect the control arm, the GPS arm, or both; SELLAS is blinded and cannot say.</div>
<div class="fact"><b>REGAL is open-label</b>, a 1:1 randomized comparison against investigator's choice, not a blinded placebo-controlled design.</div>
<div class="fact"><b>Share count roughly doubled year over year</b> &mdash; weighted-average shares 87.8M (Q1 2025) to 172.5M (Q1 2026); shares outstanding 153.1M to 181.3M between Dec 31, 2025 and Mar 31, 2026.</div>
<div class="fact">The <b>unused $150M ATM</b> represents authorized future dilution on top of that increase.</div>
<div class="fact"><b>Losses are widening</b>: net loss $8.4M in Q1 2026 vs $5.8M in Q1 2025; accumulated deficit $283.4M.</div>
<div class="fact"><b>The interim analysis was a continuation decision, not a success declaration</b> &mdash; it permitted the trial to continue; it did not establish the primary endpoint will be met.</div>
<div class="fact"><b>Positive REGAL headlines have historically been sold</b> (see the reaction record above).</div>
<div class="fact"><b>Part of the mid-2026 move was not clinical</b> &mdash; coverage attributed the June 25 surge substantially to the change-of-control amendment being read as merger preparation, and to retail/WallStreetBets momentum.</div>
<div class="fact"><b>Expectations are elevated</b>: the stock closed at ${last:.2f} on {lastd} against a 52-week range of ${lo52:.2f}&ndash;${hi52:.2f}, having risen roughly 503% over the trailing year.</div>
</div>
</div>

<h2>Program reference</h2>
<div class="card">
<div class="kv"><span>Lead asset</span><b>Galinpepimut-S (GPS) &mdash; WT1-targeting immunotherapeutic</b></div>
<div class="kv"><span>GPS origin</span><b>Licensed from Memorial Sloan Kettering Cancer Center</b></div>
<div class="kv"><span>Pivotal trial</span><b>REGAL, Phase 3, NCT04229979</b></div>
<div class="kv"><span>Population</span><b>AML in CR2/CRp2 after second-line salvage, transplant-ineligible</b></div>
<div class="kv"><span>Design / endpoint</span><b>1:1 randomized, open-label, GPS vs best available therapy / overall survival</b></div>
<div class="kv"><span>Final-analysis trigger</span><b>80 events (deaths), pooled across arms</b></div>
<div class="kv"><span>Events disclosed</span><b>60 (Dec 2024) &rarr; 72 (Dec 26, 2025) &rarr; 78 (May 11, 2026)</b></div>
<div class="kv"><span>Second asset</span><b>SLS009 (tambiciclib) &mdash; selective CDK9 inhibitor</b></div>
<div class="kv"><span>SLS009 next catalyst</span><b>Phase 2 first-line AML, 80 patients &mdash; topline expected Q4 2026</b></div>
</div>

<h2>Primary sources</h2>
<ul>
<li><a href="https://www.sec.gov/Archives/edgar/data/1390478/000110465926077556/tm2618927d1_8k.htm">SEC Form 8-K, filed June 24, 2026 (Item 5.02(e))</a> &mdash; the executive change-of-control amendments, in full.</li>
<li><a href="https://www.sec.gov/Archives/edgar/data/1390478/000110465926077556/tm2618927d1_ex10-1.htm">Exhibit 10.1</a> &middot; <a href="https://www.sec.gov/Archives/edgar/data/1390478/000110465926077556/tm2618927d1_ex10-2.htm">Exhibit 10.2</a> &mdash; the underlying agreements.</li>
<li><a href="https://www.sec.gov/Archives/edgar/data/1390478/000139047826000009/sls-202605128xkexhibit991.htm">SEC 8-K Exhibit 99.1 &mdash; Q1 2026 results (May 12, 2026)</a> &mdash; 78 events as of May 11; 80th-event trigger sequence; $107.1M cash.</li>
<li><a href="https://ir.sellaslifesciences.com/news/News-Details/2025/SELLAS-Life-Sciences-Provides-Update-on-Pivotal-Phase-3-REGAL-Trial-of-Galinpepimut-S-GPS-in-Acute-Myeloid-Leukemia-AML/default.aspx">SELLAS &mdash; REGAL update (Dec 29, 2025)</a> &mdash; 72 events as of Dec 26, 2025; no statistical penalty.</li>
<li><a href="https://ir.sellaslifesciences.com/news/News-Details/2025/SELLAS-Life-Sciences-Announces-Independent-Data-Monitoring-Committee-Periodic-Review-and-Positive-Recommendation-to-Continue-Pivotal-Phase-3-REGAL-Trial-of-GPS-in-AML-Without-Modification/default.aspx">SELLAS &mdash; IDMC periodic review (Aug 7, 2025)</a></li>
<li><a href="https://clinicaltrials.gov/study/NCT04229979">ClinicalTrials.gov &mdash; REGAL (NCT04229979)</a></li>
<li><a href="https://www.meridiancp.com/app/uploads/2024/01/Meridian_2023-Study-of-CIC-Severance-Arrangements-1.pdf">Meridian Compensation Partners &mdash; 2023 Study of Change-in-Control Severance Arrangements</a> &mdash; market prevalence of double-trigger vesting (91%) and CEO cash multiples.</li>
<li><a href="/research/sls-deep-dive">pdufa.bio &mdash; SLS event-reaction study</a> (full 21-event table)</li>
</ul>
<p class="note">Stock-reaction figures are computed by pdufa.bio from Polygon split-adjusted daily closes; daily closes
understate intraday ranges. Where an announcement fell on a non-trading day, the first following session is used.
Page compiled {TODAY.isoformat()} and updated as new filings are published.</p>

<div class="legal"><a href="/about" style="color:#8aa0bf">About</a> &middot; <a href="/corrections" style="color:#8aa0bf">Corrections</a> &middot; <a href="/methodology" style="color:#8aa0bf">Methodology</a><br><br>
<b>Not affiliated with or endorsed by the FDA, SELLAS Life Sciences, or any company mentioned.</b> pdufa.bio is an
independent service. <b>Informational and educational only &mdash; not investment advice.</b> This page contains factual
statements, filed document text, and historical price statistics only; it makes no forecast and no recommendation
about any security. Event-driven readout timing, interim results and corporate transactions are inherently uncertain.
Verify every figure against primary FDA, SEC and company filings before acting. &copy; 2026 pdufa.bio</div>
</main><script src="/cmdk.js" defer></script></body></html>"""

    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "index.html"), "w", encoding="utf-8").write(html)
    print(f"wrote sls/index.html ({len(html)} bytes, chart={'yes' if ch else 'no'}, "
          f"days since 78-event as-of = {DAYS_SINCE})")


if __name__ == "__main__":
    main()
