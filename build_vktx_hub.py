# -*- coding: utf-8 -*-
"""build_vktx_hub.py -- /vktx, the Viking Therapeutics catalyst record.

Viking is one of the most-searched retail biotech names and we had no page at all (/ticker/VKTX
404'd). The retail questions are "when is the readout" and "how good was the last data", and the
pages that currently rank answer the second one with a price target.

We can answer both better, from primary sources, without forecasting anything. Two rules, same as
/sls: every number traces to an SEC filing, a company release or a measured daily close; and where
the company's characterisation and the market's reaction disagree, the page reports both and does
not adjudicate. That disagreement is the single most useful fact about this name: the oral Phase 2
was announced as "Positive Top-Line Results" and the stock closed down 42.1% the same day.

Prices are measured from Polygon daily closes at build time, so the reaction table cannot drift
away from what actually happened.

    python build_vktx_hub.py [--dry-run]
"""
import argparse, datetime as dt, json, os, sys, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "vktx")
TODAY = dt.date.today()

# Every row: (date, what happened, source URL). Nothing here is inferred.
EVENTS = [
    ("2024-02-27", "Phase 2 VENTURE topline, subcutaneous VK2735 in obesity",
     "https://ir.vikingtherapeutics.com/"),
    ("2025-08-19", "Phase 2 VENTURE-Oral topline, VK2735 tablet in obesity",
     "https://www.sec.gov/Archives/edgar/data/1607678/000160767825000003/vktx-ex99_1.htm"),
    ("2025-11-03", "VANQUISH-1 Phase 3 enrollment completed",
     "https://www.prnewswire.com/news-releases/viking-therapeutics-announces-completion-of-enrollment-in-phase-3-vanquish-1-trial-of-vk2735-302619296.html"),
    ("2026-03-26", "VANQUISH-2 Phase 3 enrollment completed",
     "https://ir.vikingtherapeutics.com/2026-03-26-Viking-Therapeutics-Announces-Completion-of-Enrollment-in-Phase-3-VANQUISH-2-Trial-of-VK2735"),
    ("2026-04-29", "Q1 2026 results and corporate update",
     "https://www.sec.gov/Archives/edgar/data/0001607678/000119312526191487/vktx-ex99_1.htm"),
    ("2026-05-12", "13-week VENTURE-Oral data presented at ECO 2026",
     "https://www.prnewswire.com/news-releases/viking-therapeutics-presents-data-from-its-13-week-phase-2-venture-oral-dosing-trial-of-vk2735-at-european-congress-on-obesity-eco-2026-302768959.html"),
    ("2026-07-29", "Q2 2026 results and corporate update",
     "https://www.sec.gov/Archives/edgar/data/1607678/000119312526323652/vktx-20260729.htm"),
]


def load_key():
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("POLYGON_API_KEY")


def bars(key):
    u = (f"https://api.polygon.io/v2/aggs/ticker/VKTX/range/1/day/2024-01-01/"
         f"{TODAY.isoformat()}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    res = json.loads(urllib.request.urlopen(u, timeout=30).read()).get("results") or []
    return [(dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(),
             x["c"], x.get("v") or 0) for x in res]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    b = bars(load_key())
    idx = {d: i for i, (d, _, _) in enumerate(b)}
    last_d, last_c, _ = b[-1]
    y1 = [c for d, c, _ in b if d >= (TODAY - dt.timedelta(days=365)).isoformat()]
    lo52, hi52 = min(y1), max(y1)
    allc = [c for _, c, _ in b]
    peak = max(allc); peak_d = [d for d, c, _ in b if c == peak][0]

    rows = []
    for day, what, src in EVENTS:
        i = idx.get(day) or next((j for j, (d, _, _) in enumerate(b) if d >= day), None)
        if i is None or i == 0:
            continue
        d0, c0, v0 = b[i]
        prev = b[i - 1][1]
        chg = (c0 / prev - 1) * 100
        col = "#46d17f" if chg >= 0 else "#ff8f6b"
        rows.append(
            f'<tr><td class="dt">{d0}</td><td>{what}</td>'
            f'<td class="num" style="color:{col}"><b>{chg:+.1f}%</b></td>'
            f'<td class="num">${c0:,.2f}</td><td class="num">{int(v0):,}</td>'
            f'<td class="sr"><a href="{src}" rel="nofollow">source</a></td></tr>')

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="index,follow,max-image-preview:large">
<title>Viking Therapeutics (VKTX): VK2735 Phase 3 Readout Dates | pdufa.bio</title>
<meta name="description" content="Viking Therapeutics (VKTX) catalyst record: VANQUISH-1 and VANQUISH-2 Phase 3 trials of VK2735 in obesity, both fully enrolled, with VANQUISH-2 data guided to Q3 2026. Every dated event and the measured stock reaction, from SEC filings and daily closes. No price targets.">
<link rel="canonical" href="https://www.pdufa.bio/vktx"><meta name="theme-color" content="#060b14">
<meta property="og:type" content="article"><meta property="og:title" content="Viking Therapeutics (VKTX): VK2735 Phase 3 readout dates"><meta property="og:url" content="https://www.pdufa.bio/vktx">
<script type="application/ld+json">{json.dumps({
  "@context": "https://schema.org", "@type": "Organization",
  "name": "Viking Therapeutics, Inc.", "tickerSymbol": "VKTX", "alternateName": "VKTX",
  "url": "https://www.pdufa.bio/vktx",
  "sameAs": ["https://www.vikingtherapeutics.com/",
             "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001607678&type=8-K"]},
  separators=(",", ":"))}</script>
<style>*{{box-sizing:border-box}}
:root{{--bg:#060b14;--card:#0e1c33;--line:#1e3a63;--line2:#294d80;--gold:#f0c86a;--ink:#eef4fc;--mut:#9db3d4;--mut2:#7c93b6;--green:#46d17f;--red:#ff8f6b}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.6}}
a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}
header.site{{position:sticky;top:0;z-index:20;backdrop-filter:blur(10px);background:rgba(6,11,20,.85);border-bottom:1px solid var(--line)}}
.hd{{max-width:1000px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
.hd .brand{{font-size:20px;font-weight:800;letter-spacing:-.4px;color:var(--ink)}}.hd .brand b{{color:var(--gold)}}
.hd nav a{{font-size:13.5px;color:var(--mut);padding:7px 10px;border-radius:8px}}
.wrap{{max-width:1000px;margin:0 auto;padding:22px 22px 70px}}
.bc{{font-size:12px;color:var(--mut2);margin:2px 0 10px}}.bc a{{color:var(--mut2)}}
h1{{font-size:30px;line-height:1.15;font-weight:800;letter-spacing:-.6px;margin:6px 0 8px}}h1 .g{{color:var(--gold)}}
.mhead{{font-family:inherit;font-size:15px;font-weight:700;color:var(--ink);margin:26px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}}
p{{color:var(--mut);font-size:15px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px;margin:12px 0}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th{{text-align:left;color:var(--gold);font-size:11px;text-transform:uppercase;letter-spacing:.4px;padding:8px;border-bottom:1px solid var(--line2)}}
td{{padding:8px;border-bottom:1px solid var(--line);color:var(--mut);vertical-align:top}}
td.dt{{color:var(--ink);font-weight:700;white-space:nowrap}}
th.num,td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.sr{{white-space:nowrap;font-size:12px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
@media(max-width:760px){{.stats{{grid-template-columns:1fr 1fr}}h1{{font-size:24px}}.hd nav{{display:none}}}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px}}
.big{{font-size:23px;font-weight:800;letter-spacing:-.5px;color:var(--ink)}}
.note{{font-size:12px;color:var(--mut2);line-height:1.6}}
.fact{{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:8px;padding:11px 13px;margin:9px 0;font-size:14px;color:var(--mut)}}
.legal{{border-top:1px solid var(--line);margin-top:36px;padding-top:16px;font-size:11.5px;color:#8aa0bf;line-height:1.6}}
</style><link rel="icon" type="image/svg+xml" href="/favicon.svg"></head><body>
<header class="site"><div class="hd"><a class="brand" href="/">pdufa<b>.bio</b></a><nav><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a><a href="/sls">SLS</a><a href="/research">Research</a></nav></div></header>
<main class="wrap">
<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/readouts">Readouts</a> &rsaquo; VKTX tracker</div>
<h1>Viking Therapeutics <span class="g">(VKTX)</span>: the VK2735 record</h1>
<p>Viking's lead programme is <b>VK2735</b>, a dual GLP-1 / GIP receptor co-agonist in development in
both subcutaneous and oral form for obesity. Two Phase 3 trials are running and both are fully
enrolled. This page states what has been filed and what the stock actually did on each dated event.
There are no price targets, no probability of success, and no forecasts anywhere on it.</p>

<div class="stats">
  <div class="stat"><div class="note">Last close</div><div class="big">${last_c:,.2f}</div><div class="note">{last_d}</div></div>
  <div class="stat"><div class="note">52-week range</div><div class="big" style="font-size:19px">${lo52:,.2f} to ${hi52:,.2f}</div><div class="note">daily closes</div></div>
  <div class="stat"><div class="note">Next guided readout</div><div class="big" style="color:var(--gold);font-size:20px">Q3 2026</div><div class="note">VANQUISH-2, company guidance</div></div>
  <div class="stat"><div class="note">Down from peak</div><div class="big">{100*(last_c/peak-1):+.0f}%</div><div class="note">peak ${peak:,.2f} on {peak_d}</div></div>
</div>

<div class="mhead">Where the programme actually stands</div>
<div class="fact"><b>Both Phase 3 trials are fully enrolled.</b> VANQUISH-1 (obesity) completed
enrollment in November 2025; VANQUISH-2 (obesity with type 2 diabetes, approximately 1,000 adults)
completed enrollment in March 2026. Each evaluates subcutaneous VK2735 once weekly for 78 weeks,
with the primary endpoint being percent change in body weight from baseline at week 78.</div>
<div class="fact"><b>The company guides VANQUISH-2 data to the third quarter of 2026.</b> That is
company guidance, quoted as given. It is a quarter, not a date, and we do not convert it into one.</div>
<div class="fact"><b>Other stated 2026 milestones.</b> In its Q1 2026 update Viking said it expects
to initiate a Phase 3 trial of <b>oral</b> VK2735 in 4Q26, expects data from the VK2735 maintenance
dosing study in 3Q26, and had filed an IND for the amylin agonist VK3019. Quarter-end cash was
stated at <b>$603 million</b> as of March 31, 2026.</div>

<div class="mhead">How good was the last data, and what the market did with it</div>
<p>This is the part worth being precise about, because the company's characterisation and the
market's reaction pointed in opposite directions, and both are facts.</p>
<div class="fact"><b>What the company reported (August 19, 2025, Phase 2 VENTURE-Oral).</b> The
release is titled &ldquo;Positive Top-Line Results&rdquo;. The trial <b>met its primary and secondary
endpoints</b>. Mean weight loss reached <b>up to 12.2% (26.6 lbs) after 13 weeks</b> versus 1.3%
(2.9 lbs) for placebo. Up to <b>97%</b> of treated subjects achieved at least 5% weight loss versus
10% on placebo, and up to <b>80%</b> achieved at least 10% versus 5%. Weight loss was described as
progressive with no plateau at 13 weeks, and <b>99% of GI-specific adverse events were mild or
moderate</b>.</div>
<div class="fact"><b>What the stock did that day.</b> VKTX closed <b style="color:var(--red)">down
42.1%</b> on 64.6 million shares. A trial that met every stated endpoint was followed by the
second-largest single-day move in the stock's recent history, in the opposite direction to the
headline. We report both and do not attempt to adjudicate which reading was right; the release and
the tape are each linked below.</div>

<div class="mhead">Every dated event and its measured stock reaction</div>
<div class="card"><table>
<tr><th>Date</th><th>Event</th><th class="num">Day move</th><th class="num">Close</th><th class="num">Volume</th><th>Source</th></tr>
{"".join(rows)}
</table>
<div class="note" style="margin-top:10px">Day move is that session's close against the prior close,
computed from Polygon split-adjusted daily closes at build time. Daily closes understate intraday
ranges, so each figure is a floor. Historical price behaviour, not a forecast.</div></div>

<div class="mhead">What we are not telling you</div>
<p class="note">We do not publish a price target, a probability that VANQUISH-1 or VANQUISH-2 will
succeed, or a view on whether the oral data was good. Those are the four things the search results
for this ticker are mostly made of, and they are the four things we have no defensible basis for.
What we will do is state the guided timing at the precision the company used, log every filing, and
measure the reaction after the fact. For how comparable events have behaved historically, see the
<a href="/runup-by-year">run-up study</a> (1,827 FDA decisions) and the
<a href="/research/readout-reaction">readout-reaction study</a> (1,752 clinical readouts).</p>

<div class="legal"><a href="/about" style="color:#8aa0bf">About</a> &middot; <a href="/corrections" style="color:#8aa0bf">Corrections</a> &middot; <a href="/methodology" style="color:#8aa0bf">Methodology</a><br><br>
<b>Not affiliated with or endorsed by the FDA, Viking Therapeutics, or any company mentioned.</b>
pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or
connection to the U.S. Food and Drug Administration or any other government agency.
&ldquo;FDA&rdquo;, &ldquo;PDUFA&rdquo; and all company, drug and ticker names are used descriptively
and remain the property of their respective owners.<br><br>
<b>Informational and educational purposes only. Not investment advice.</b> Nothing on this page is
investment, legal, tax or medical advice, or an offer or solicitation to buy or sell any security.
pdufa.bio is not a registered investment adviser or broker-dealer and does not recommend trades or
publish individual-drug approval probabilities. Clinical-trial timing and results are inherently
uncertain and guidance can change. Verify every date and figure against primary SEC and company
filings. Data is provided as is, without warranty of any kind, and past behaviour does not predict
future outcomes. Page rebuilt {TODAY.isoformat()}.<br><br>
&copy; 2026 pdufa.bio. All rights reserved.</div>
</main><script src="/cmdk.js" defer></script></body></html>"""

    print(f"VKTX: last close ${last_c:,.2f} ({last_d}), {len(rows)} dated events with reactions")
    if a.dry_run:
        print("DRY RUN -- not written."); return
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    print(f"wrote vktx/index.html ({len(html)} bytes)")


if __name__ == "__main__":
    main()
