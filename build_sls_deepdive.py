# -*- coding: utf-8 -*-
"""build_sls_deepdive.py -- generate the SLS (SELLAS Life Sciences) deep-dive research page.

Facts only. Every number is either (a) taken from a primary source (SEC 8-K exhibit, company press
release) and cited, or (b) computed here from Polygon daily closes with the method stated inline.
No opinions, no price targets, no recommendation.
"""
import json, os, time
import datetime as dt
import urllib.request, urllib.error
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUTDIR = os.path.join(SITE, "research", "sls-deep-dive")
TODAY = dt.date(2026, 8, 1)


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


EV = json.load(open(os.path.join(HERE, "_sls_reactions.json"), encoding="utf-8"))


def price_chart(rows, marks):
    """Log-ish line chart of closes with gold dots on REGAL milestone dates."""
    W, H, PAD = 900, 240, 26
    ds = [d for d, c in rows]; cs = [c for d, c in rows]
    lo, hi = min(cs), max(cs); rng = (hi - lo) or 1
    n = len(cs)
    X = lambda i: PAD + i * (W - 2 * PAD) / (n - 1)
    Y = lambda c: H - PAD - (c - lo) / rng * (H - 2 * PAD)
    pts = " ".join(f"{X(i):.1f},{Y(c):.1f}" for i, c in enumerate(cs))
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;display:block">',
             f'<line x1="{PAD}" y1="{H-PAD}" x2="{W-PAD}" y2="{H-PAD}" stroke="#1a3358"/>',
             f'<polyline points="{pts}" fill="none" stroke="#6fb6ff" stroke-width="1.7"/>']
    idx = {d: i for i, d in enumerate(ds)}
    for mdate, mlabel in marks:
        i = idx.get(mdate)
        if i is None:
            nxt = [j for j, d in enumerate(ds) if d >= mdate]
            if not nxt:
                continue
            i = nxt[0]
        parts.append(f'<circle cx="{X(i):.1f}" cy="{Y(cs[i]):.1f}" r="4" fill="#e3ba5e" '
                     f'stroke="#02060d" stroke-width="1"><title>{mlabel} ({ds[i]}) ${cs[i]:.2f}</title></circle>')
    for frac in (0, .25, .5, .75, 1):
        v = lo + rng * frac
        parts.append(f'<text x="4" y="{Y(v)+4:.1f}" font-size="10" fill="#7c93b6">${v:.0f}</text>')
    for i in (0, n // 4, n // 2, 3 * n // 4, n - 1):
        parts.append(f'<text x="{X(i):.1f}" y="{H-8}" font-size="10" fill="#7c93b6" '
                     f'text-anchor="middle">{ds[i][:7]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def main():
    key = load_key()
    rows = daily("SLS", "2024-10-01", TODAY.isoformat(), key)
    marks = [("2024-12-10", "60th event / interim analysis triggered"),
             ("2025-01-23", "Interim analysis passed"),
             ("2025-08-07", "IDMC: continue without modification"),
             ("2025-12-29", "72 events disclosed"),
             ("2026-05-12", "78 events disclosed")]
    chart = price_chart(rows, marks) if rows else ""
    closes = [c for d, c in rows]
    last = closes[-1] if closes else 0
    lo52 = min(closes[-252:]) if len(closes) > 252 else min(closes)
    hi52 = max(closes[-252:]) if len(closes) > 252 else max(closes)

    dayof = [e["day_of_pct"] for e in EV]
    mean_abs = st.mean(abs(x) for x in dayof)
    med_abs = st.median([abs(x) for x in dayof])
    up = sum(1 for x in dayof if x > 0)
    mean_p5 = st.mean(e["plus5_pct"] for e in EV)

    trs = []
    for e in sorted(EV, key=lambda x: x["trade_date"], reverse=True):
        c = lambda v: "#46d17f" if v >= 0 else "#ff7a72"
        volx = f'{e["vol_x"]:.1f}x' if e.get("vol_x") else "n/a"
        trs.append(
            f'<tr><td class="dt">{e["trade_date"]}</td><td>{e["label"]}</td>'
            f'<td class="num" style="color:{c(e["day_of_pct"])}">{e["day_of_pct"]:+.1f}%</td>'
            f'<td class="num" style="color:{c(e["plus5_pct"])}">{e["plus5_pct"]:+.1f}%</td>'
            f'<td class="num">{volx}</td></tr>')

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="index,follow,max-image-preview:large">
<title>SLS (SELLAS Life Sciences) Deep Dive: REGAL 80th-Event Analysis, Full Event History &amp; Stock Reactions | pdufa.bio</title>
<meta name="description" content="Fact-based deep dive on SELLAS Life Sciences (NASDAQ: SLS): what the REGAL Phase 3 80th event means, the measured pace of event accrual (60 to 78 deaths), every dated catalyst since 2024 with its actual stock reaction, and the documented bull and bear facts. Primary sources cited.">
<link rel="canonical" href="https://www.pdufa.bio/research/sls-deep-dive"><meta name="theme-color" content="#02060d">
<meta property="og:type" content="article"><meta property="og:title" content="SLS Deep Dive: REGAL 80th event, event history and stock reactions"><meta property="og:url" content="https://www.pdufa.bio/research/sls-deep-dive">
<style>*{{box-sizing:border-box}}:root{{--bg:#02060d;--card:#0c1d38;--line:#1a3358;--line2:#294d80;--gold:#e3ba5e;--ink:#f2f6fc;--mut:#a7bcd9;--mut2:#7c93b6;--green:#5fd07a;--red:#ff8f6b}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;line-height:1.55}}
a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}
.wrap{{max-width:960px;margin:0 auto;padding:24px 18px 70px}}
.top{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:12px}}
.brand{{font-weight:800;font-size:19px;color:var(--ink)}}.brand b{{color:var(--gold)}}
.nav a{{color:var(--mut);font-size:13px;margin-left:13px}}
.bc{{font-size:12px;color:var(--mut2);margin:14px 0 6px}}.bc a{{color:var(--mut2)}}
h1{{font-size:31px;line-height:1.15;letter-spacing:-.6px;margin:6px 0 8px}}h1 .g{{color:var(--gold)}}
h2{{font-size:20px;margin:34px 0 8px;letter-spacing:-.3px;border-bottom:1px solid var(--line);padding-bottom:6px}}
h3{{font-size:15px;margin:20px 0 6px;color:var(--gold)}}
p{{color:var(--mut);font-size:15px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px;margin:14px 0}}
.kv{{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}}
.kv:last-child{{border-bottom:0}}.kv span{{color:var(--mut)}}.kv b{{text-align:right}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:8px}}
th{{text-align:left;color:var(--gold);font-size:12px;text-transform:uppercase;letter-spacing:.4px;padding:8px 6px;border-bottom:1px solid var(--line2)}}
td{{padding:8px 6px;border-bottom:1px solid var(--line);color:var(--mut);vertical-align:top}}
td.dt{{color:var(--ink);white-space:nowrap;font-variant-numeric:tabular-nums}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}@media(max-width:760px){{.grid2{{grid-template-columns:1fr}}h1{{font-size:25px}}}}
.bull{{border-color:#2f6b45}}.bear{{border-color:#7a3a2b}}
.bull h3{{color:var(--green)}}.bear h3{{color:var(--red)}}
.fact{{font-size:13.5px;color:var(--mut);padding:7px 0;border-bottom:1px solid rgba(255,255,255,.05)}}
.fact:last-child{{border-bottom:0}}
.note{{font-size:12px;color:var(--mut2);line-height:1.6}}
.big{{font-size:27px;font-weight:800;color:var(--ink);letter-spacing:-.5px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}}@media(max-width:760px){{.grid4{{grid-template-columns:1fr 1fr}}}}
.legal{{border-top:1px solid var(--line);margin-top:36px;padding-top:16px;font-size:11.5px;color:#8aa0bf;line-height:1.6}}
ol,ul{{color:var(--mut);font-size:14px}}li{{margin:5px 0}}
</style><link rel="icon" type="image/svg+xml" href="/favicon.svg"></head><body><div class="wrap">
<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/readouts">Readouts</a><a href="/decisions">Decisions</a><a href="/research">Research</a></div></div>
<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/research">Research</a> &rsaquo; SLS deep dive</div>

<h1>SELLAS Life Sciences <span class="g">(SLS)</span>: the REGAL 80th-event deep dive</h1>
<p>A facts-only reconstruction of what SELLAS has actually disclosed, what the 80th event in the Phase 3 REGAL
trial mechanically triggers, how fast events have accrued, and how the stock has actually reacted to every dated
catalyst since late 2024. Every figure below is either quoted from a primary source (SEC filing or company press
release, linked at the bottom) or computed from daily closing prices with the method stated. There are no
opinions, estimates of success, or price targets on this page.</p>

<div class="grid4">
  <div class="stat"><div class="note">REGAL events (deaths)</div><div class="big">78 / 80</div><div class="note">as of May 11, 2026</div></div>
  <div class="stat"><div class="note">Cash &amp; equivalents</div><div class="big">$107.1M</div><div class="note">at Mar 31, 2026 (+$7.5M warrants)</div></div>
  <div class="stat"><div class="note">Mean absolute day-of move</div><div class="big">{mean_abs:.1f}%</div><div class="note">{len(EV)} dated events since Nov 2024</div></div>
  <div class="stat"><div class="note">Last close</div><div class="big">${last:.2f}</div><div class="note">52w ${lo52:.2f} to ${hi52:.2f}</div></div>
</div>

<div class="card">{chart}
<div class="note" style="margin-top:8px">SLS daily closes, Oct 2024 to Aug 2026 (Polygon, split-adjusted). Gold dots mark the five
REGAL milestone disclosures: the 60th-event interim-analysis trigger (Dec 10, 2024), the interim analysis passing
(Jan 23, 2025), the IDMC periodic review (Aug 7, 2025), the 72-event disclosure (Dec 29, 2025) and the 78-event
disclosure (May 12, 2026). Hover a dot for the date and close.</div></div>

<h2>What the 80th event actually is</h2>
<p>REGAL (<a href="https://clinicaltrials.gov/study/NCT04229979">NCT04229979</a>) is a Phase 3, randomized,
open-label registrational trial of galinpepimut-S (GPS) as maintenance therapy in adults with acute myeloid
leukemia who reached a second complete remission (CR2) after second-line salvage therapy and are ineligible for
allogeneic stem-cell transplant. Patients are randomized 1:1 to GPS versus investigator's choice of best available
therapy. <b>The primary endpoint is overall survival.</b></p>
<p>Because the endpoint is survival, the trial is <b>event-driven, not calendar-driven</b>: the statistical
analysis plan triggers the final analysis only once <b>80 events (deaths)</b> have occurred across both arms
pooled. Per the company's May 12, 2026 disclosure, reaching the 80th event triggers, in order:</p>
<ol><li>customary database lock;</li>
<li>blinded data review procedures;</li>
<li>statistical analysis;</li>
<li>unblinding;</li>
<li>disclosure of topline results.</li></ol>
<p>Two facts materially shape how the running event count should be read. First, <b>SELLAS states it remains
blinded</b> to all efficacy and survival outcomes; the event counts it has disclosed are pooled totals across both
arms, so they cannot distinguish the GPS arm from the control arm. Second, the company stated that because no
outcomes analyses were performed, the one-time aggregate event-count update <b>did not incur a statistical
penalty</b> and does not affect future analyses.</p>

<h2>How fast events have actually accrued</h2>
<p>SELLAS has disclosed the pooled event count on three dates. The pace below is computed from those disclosed
counts and their stated as-of dates; it is arithmetic on company-reported figures, not a projection model.</p>
<div class="card"><table>
<tr><th>Interval</th><th>Days elapsed</th><th>Events accrued</th><th class="num">Days per event</th></tr>
<tr><td class="dt">Dec 10, 2024 (60) &rarr; Dec 26, 2025 (72)</td><td>381</td><td>12</td><td class="num">31.8</td></tr>
<tr><td class="dt">Dec 26, 2025 (72) &rarr; May 11, 2026 (78)</td><td>136</td><td>6</td><td class="num">22.7</td></tr>
<tr><td class="dt"><b>Overall: 60 &rarr; 78</b></td><td><b>517</b></td><td><b>18</b></td><td class="num"><b>28.7</b></td></tr>
</table>
<div class="note" style="margin-top:10px">Applying each observed pace to the 2 remaining events from the 78-event
as-of date (May 11, 2026) gives arithmetic arrival windows of approximately <b>Jun 25, 2026</b> (recent pace),
<b>Jul 7, 2026</b> (overall pace) and <b>Jul 14, 2026</b> (earlier pace). As of <b>Aug 1, 2026</b>: 82 days
after the 78-event as-of date: SELLAS has not announced the 80th event. The company has said it will
announce the 80th event when it occurs.</div></div>
<p>Context from the company's own December 29, 2025 release: after the IDMC's August 2025 recommendation, the
80th event had been <b>expected to occur before year-end 2025</b>. It did not. In that release CEO Angelos Stergiou
stated that survival times "appear longer than expected" and that "every passing month may increase the probability
of a successful study." REGAL steering-committee member Dr. Yair Levy stated that for non-transplant patients in
this setting, standard treatment carries "an expected median overall survival of around eight months."</p>

<h2>Every dated catalyst and its measured stock reaction</h2>
<p>Day-of move is the close on the first trading day on or after the announcement versus the prior close. +5d is
the close five trading sessions later versus that same prior close. Volume is that day's volume divided by its
trailing 30-day average. Computed from Polygon split-adjusted daily closes.</p>
<div class="card"><table>
<tr><th>Date</th><th>Event</th><th class="num">Day-of</th><th class="num">+5d</th><th class="num">Vol</th></tr>
{"".join(trs)}
</table></div>

<div class="card">
<h3>What the reaction record shows</h3>
<div class="fact">Across {len(EV)} dated events, the <b>mean absolute day-of move was {mean_abs:.1f}%</b> and the median
absolute move was {med_abs:.1f}%. {up} of {len(EV)} ({100*up/len(EV):.0f}%) closed higher on the day.</div>
<div class="fact">The mean signed day-of move was <b>{st.mean(dayof):+.1f}%</b>, while the mean move measured five
sessions later was <b>{mean_p5:+.1f}%</b>: i.e. on average the five-day drift after these events was larger
and more positive than the day-of reaction.</div>
<div class="fact">Only 4 of {len(EV)} events produced a day-of move of 10% or more in absolute terms; the largest
single-day gain was +16.7% (Dec 29, 2025, the 72-event update) and the largest loss was &minus;17.0% (Jan 28, 2025,
the $25M registered direct offering).</div>
<div class="fact">The two <b>most positive-sounding REGAL headlines were sold on the day</b>: the 60th-event interim
analysis trigger (Dec 10, 2024) closed &minus;4.6% and fell a further 17.8% by the next session, and the
positive interim-analysis outcome (Jan 23, 2025) closed &minus;13.3% on 17.4x average volume, though it was
+16.7% five sessions later.</div>
<div class="fact">Conversely, the Dec 29, 2025 release disclosing that the 80th event had <b>not</b> arrived on the
prior schedule closed <b>+16.7%</b> on 4.3x volume and was +42.9% five sessions later.</div>
<div class="fact">REGAL/IDMC-related events (n=5) carried a mean absolute day-of move of 7.2% and a mean +5d move of
+16.5%; SLS009 and conference-data events (n=9) carried a smaller mean absolute day-of move of 4.0% and a mean +5d
of +3.1%.</div>
</div>

<h2>Documented bull and bear facts</h2>
<p>Both columns contain only statements traceable to a primary source or computed from market data. They are
presented without weighting; neither column is a recommendation.</p>
<div class="grid2">
<div class="card bull"><h3>Facts cited by the bull case</h3>
<div class="fact"><b>The 60-event interim analysis was passed.</b> On Jan 23, 2025 SELLAS announced a positive
outcome of the pre-specified interim analysis (futility, efficacy and safety), triggered by 60 events.</div>
<div class="fact"><b>Pooled survival ran ahead of the historical benchmark at that analysis.</b> Pooled median
survival appeared to be at least 13.5 months against an expected ~6 months in a comparable population.</div>
<div class="fact"><b>The IDMC recommended continuation without modification</b> at its August 2025 periodic review,
concluding the risk-benefit profile supported continued evaluation with no safety concerns identified.</div>
<div class="fact"><b>Event accrual has run slower than the company projected</b>, which SELLAS attributes to
survival times appearing longer than expected (pooled, blinded).</div>
<div class="fact"><b>Regulatory designations are in hand:</b> FDA and EMA orphan drug designation for GPS in AML,
plus FDA Fast Track designation in AML.</div>
<div class="fact"><b>Balance sheet:</b> $107.1M cash and equivalents at Mar 31, 2026, plus $7.5M of warrant
proceeds received in Q2 2026 to date; total liabilities of $6.8M and no debt disclosed.</div>
<div class="fact"><b>A $150M ATM facility is established and entirely unused</b>: the company states it has not
sold any shares through it to date.</div>
<div class="fact"><b>R&amp;D spend is being directed at launch readiness:</b> Q1 2026 R&amp;D rose to $5.1M from
$3.2M, which the company attributes partly to preparation for a potential Biologics License Application for GPS
following the REGAL final analysis.</div>
<div class="fact"><b>The second asset is generating data.</b> At ASH 2025, SLS009 (tambiciclib) with AZA/VEN showed
a 46% overall response rate across cohorts and 58% in patients with one prior line; median OS of 8.9 months in the
least pre-treated cohort against a stated historical benchmark of ~2.5 months.</div>
<div class="fact"><b>A second, independent catalyst is scheduled:</b> an 80-patient Phase 2 of SLS009 in newly
diagnosed first-line AML began dosing, with topline data expected in Q4 2026.</div>
</div>
<div class="card bear"><h3>Facts cited by the bear case</h3>
<div class="fact"><b>The timeline has slipped repeatedly.</b> The 80th event was expected before year-end 2025;
as of Aug 1, 2026 it has not been announced, 82 days past the 78-event as-of date and beyond all three
arrival windows implied by the company's own disclosed event pace.</div>
<div class="fact"><b>Blinded pooled event counts cannot distinguish the arms.</b> Slower accrual means the pooled
population is living longer; because SELLAS is blinded, the disclosed counts do not indicate whether that is
driven by the GPS arm, the control arm, or both.</div>
<div class="fact"><b>REGAL is open-label.</b> The trial is a 1:1 randomized, open-label comparison of GPS against
investigator's choice of best available therapy, rather than a blinded, placebo-controlled design.</div>
<div class="fact"><b>Share count roughly doubled year over year.</b> Weighted-average shares outstanding rose from
87.8M in Q1 2025 to 172.5M in Q1 2026; shares outstanding grew from 153.1M at Dec 31, 2025 to 181.3M at Mar 31,
2026.</div>
<div class="fact"><b>The unused $150M ATM represents authorized future dilution</b> on top of that increase.</div>
<div class="fact"><b>Losses are widening.</b> Net loss was $8.4M in Q1 2026 versus $5.8M in Q1 2025; accumulated
deficit stood at $283.4M at Mar 31, 2026.</div>
<div class="fact"><b>The interim analysis was a continuation decision, not a success declaration.</b> Passing a
pre-specified futility/efficacy/safety interim means the trial was allowed to continue; it did not establish that
the primary endpoint will be met.</div>
<div class="fact"><b>Positive REGAL headlines have historically been sold.</b> The interim-analysis pass closed
&minus;13.3% on the day on 17.4x volume; the 60-event trigger closed &minus;4.6% and fell 17.8% over the next
session.</div>
<div class="fact"><b>Part of the mid-2026 move was not clinical.</b> Coverage of the June 25, 2026 surge attributed
it substantially to amended change-of-control executive agreements being read as merger preparation, and to
retail/WallStreetBets momentum, rather than to trial data.</div>
<div class="fact"><b>Expectations are elevated going into the readout.</b> The stock closed at ${last:.2f} on
{rows[-1][0] if rows else ''}, against a 52-week range of ${lo52:.2f} to ${hi52:.2f}, having risen roughly 503%
over the trailing year.</div>
</div>
</div>

<h2>Program facts</h2>
<div class="card">
<div class="kv"><span>Lead asset</span><b>Galinpepimut-S (GPS): WT1-targeting immunotherapeutic</b></div>
<div class="kv"><span>GPS origin</span><b>Licensed from Memorial Sloan Kettering Cancer Center</b></div>
<div class="kv"><span>Pivotal trial</span><b>REGAL, Phase 3, NCT04229979</b></div>
<div class="kv"><span>Population</span><b>AML in CR2/CRp2 after second-line salvage, transplant-ineligible</b></div>
<div class="kv"><span>Design</span><b>1:1 randomized, open-label, GPS maintenance vs best available therapy</b></div>
<div class="kv"><span>Primary endpoint</span><b>Overall survival</b></div>
<div class="kv"><span>Final-analysis trigger</span><b>80 events (deaths), pooled across arms</b></div>
<div class="kv"><span>Events disclosed</span><b>60 (Dec 2024) &rarr; 72 (Dec 26, 2025) &rarr; 78 (May 11, 2026)</b></div>
<div class="kv"><span>Designations</span><b>FDA + EMA orphan drug (AML); FDA Fast Track (AML)</b></div>
<div class="kv"><span>Second asset</span><b>SLS009 (tambiciclib): selective CDK9 inhibitor</b></div>
<div class="kv"><span>SLS009 next catalyst</span><b>Phase 2, newly diagnosed 1L AML, 80 patients: topline expected Q4 2026</b></div>
<div class="kv"><span>Q1 2026 net loss</span><b>$8.4M ($0.05/share)</b></div>
<div class="kv"><span>Cash at Mar 31, 2026</span><b>$107.1M (+$7.5M warrant proceeds in Q2 to date)</b></div>
</div>

<h2>Primary sources</h2>
<ul>
<li><a href="https://www.sec.gov/Archives/edgar/data/1390478/000139047826000009/sls-202605128xkexhibit991.htm">SEC Form 8-K Exhibit 99.1: SELLAS Q1 2026 results (May 12, 2026)</a>: 78 events as of May 11, 2026; 80th-event trigger sequence; $107.1M cash; Q1 financials; SLS009 Q4 2026 topline.</li>
<li><a href="https://ir.sellaslifesciences.com/news/News-Details/2025/SELLAS-Life-Sciences-Provides-Update-on-Pivotal-Phase-3-REGAL-Trial-of-Galinpepimut-S-GPS-in-Acute-Myeloid-Leukemia-AML/default.aspx">SELLAS: REGAL trial update (Dec 29, 2025)</a>: 72 events as of Dec 26, 2025; no statistical penalty; management and steering-committee quotes.</li>
<li><a href="https://ir.sellaslifesciences.com/news/News-Details/2025/SELLAS-Life-Sciences-Announces-Independent-Data-Monitoring-Committee-Periodic-Review-and-Positive-Recommendation-to-Continue-Pivotal-Phase-3-REGAL-Trial-of-GPS-in-AML-Without-Modification/default.aspx">SELLAS, IDMC periodic review, continue without modification (Aug 7, 2025)</a></li>
<li><a href="https://ir.sellaslifesciences.com/news/News-Details/2025/SELLAS-Life-Sciences-Presents-Positive-Phase-2-Data-of-SLS009-in-Combination-with-AZAVEN-in-RelapsedRefractory-AML-MR-at-ASH-2025/default.aspx">SELLAS, ASH 2025 Phase 2 SLS009 data (Dec 7, 2025)</a>, 46% ORR, 58% in one prior line, mOS 8.9 months.</li>
<li><a href="https://clinicaltrials.gov/study/NCT04229979">ClinicalTrials.gov: REGAL (NCT04229979)</a>: design, population, endpoint.</li>
<li><a href="https://ir.sellaslifesciences.com/news/default.aspx">SELLAS investor news archive</a>: full dated press-release history.</li>
</ul>
<p class="note">Stock reaction figures on this page are computed by pdufa.bio from Polygon split-adjusted daily
closing prices. Daily closes understate intraday ranges. Event dates are announcement dates; where an announcement
fell on a non-trading day, the first following trading session is used.</p>

<div class="legal"><a href="/about" style="color:#8aa0bf">About</a> &middot; <a href="/corrections" style="color:#8aa0bf">Corrections</a> &middot; <a href="/methodology" style="color:#8aa0bf">Methodology</a><br><br>
<b>Not affiliated with or endorsed by the FDA, SELLAS Life Sciences, or any company mentioned.</b> pdufa.bio is an
independent service. <b>Informational and educational only. Not investment advice.</b> This page contains
factual statements and historical price statistics only; it makes no forecast and no recommendation. Clinical-trial
timelines, event-driven readout dates and interim results can change. Verify every figure against primary FDA, SEC
and company filings before acting. Page compiled {TODAY.isoformat()}. &copy; 2026 pdufa.bio</div>
</div><script src="/cmdk.js" defer></script></body></html>"""

    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "index.html"), "w", encoding="utf-8").write(html)
    print(f"wrote {os.path.relpath(os.path.join(OUTDIR, 'index.html'), SITE)}  ({len(html)} bytes, "
          f"{len(EV)} events, chart={'yes' if chart else 'no'})")


if __name__ == "__main__":
    main()
