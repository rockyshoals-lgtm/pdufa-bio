# -*- coding: utf-8 -*-
"""/research/implied-vs-actual -- what the options market priced before FDA decisions.

Audit 2026-09-05c section 6: the most-asked pre-catalyst question no free source
answers. Rendered from implied_moves.json (build_implied_moves.py, the production
computation over the run-up study's own universe). The two mandatory caveats ship
in the page's second and third paragraphs, before any number a reader could act on.
No strategy verb appears anywhere on this page.
"""
import datetime as dt
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "research", "implied-vs-actual")
SRC = os.path.join(HERE, "implied_moves.json")


def esc(s):
    return html.escape(str(s), quote=False)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f'{["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.month]} {d.day}, {d.year}'


def main():
    data = json.load(io.open(SRC, encoding="utf-8"))
    agg, events = data["aggregate"], data["events"]
    n = agg["computed"]

    # the individually quotable rows: biggest realized moves vs what was priced
    big = sorted((e for e in events if e.get("actual_5d_pct") is not None),
                 key=lambda e: -abs(e["actual_5d_pct"]))[:10]
    def tklink(tk):
        # hub-gated, same rule as the conference builders: never link a 404 hub
        if os.path.isdir(os.path.join(SITE, "ticker", tk)):
            return f'<a class="lit" href="/ticker/{esc(tk)}">{esc(tk)}</a>'
        return esc(tk)

    rows = "".join(
        f'<tr><td>{tklink(e["t"])}</td>'
        f'<td>{esc(pretty(e["pdufa"]))}</td>'
        f'<td>&plusmn;{e["priced_pct"]:.1f}%</td>'
        f'<td>{e["actual_pct"]:+.1f}%</td>'
        f'<td>{e["actual_5d_pct"]:+.1f}%</td>'
        f'<td>{e["atm_iv_pct"]:.0f}%</td></tr>'
        for e in big if e.get("atm_iv_pct"))
    years = "".join(
        f'<tr><td>{y}</td><td>{b["n"]}</td><td>&plusmn;{b["median_priced_pct"]:.1f}%</td>'
        f'<td>{b["median_actual_abs_pct"]:.1f}%</td><td>{b["exceeded"]}</td></tr>'
        for y, b in agg["by_year"].items())

    title = ("What the Options Market Priced Before FDA Decisions, vs What Happened "
             "(2020-2026) | pdufa.bio")
    desc = (f"Across {n} FDA decisions, at-the-money options priced a median "
            f"±{agg['median_priced_pct']}% move about two weeks out. The median "
            f"next-close move was {agg['median_actual_abs_pct']}%. Measured, sourced, "
            f"with caveats.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."

    qa = [("What does the priced move measure?",
           "For each decision we take the options chain snapshot closest to 14 days "
           "before the decision, the nearest listed expiry after it, and the "
           "at-the-money straddle (call mid plus put mid) divided by the stock "
           "price. That is the move the options market priced from the snapshot "
           "date through that expiry. It prices roughly two weeks of ordinary "
           "movement PLUS the event, so it is not the event-implied move alone."),
          ("How often did the actual move exceed what was priced?",
           f"At the first close after the decision, {agg['n_exceeded']} of {n} "
           f"({agg['exceed_rate_pct']}%). Within five trading days, "
           f"{agg['n_exceeded_5d']} of {n} ({agg['exceed_5d_rate_pct']}%). The gap "
           f"between those two rates is itself a finding: a large share of the "
           f"realized move arrives after the first close. These are historical "
           f"measurements of this sample, not a property of future decisions."),
          ("Which events are covered?",
           f"{n} of the {agg['universe_events']} events in our run-up study "
           f"({agg['coverage_pct']}%) had a usable options chain snapshot in the 30 "
           f"days before the decision. Coverage requires listed options with real "
           f"quotes, so the computable set skews toward larger, optionable "
           f"companies; the smallest names are underrepresented.")]
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                         "mainEntity": [{"@type": "Question", "name": q,
                                         "acceptedAnswer": {"@type": "Answer", "text": a2}}
                                        for q, a2 in qa]}, ensure_ascii=False)
    faq = "".join(
        f'<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
        f'padding:14px 16px;margin:12px 0"><b>{esc(q)}</b>'
        f'<div style="color:#9db3d4;font-size:14px;margin-top:6px">{esc(a2)}</div></div>'
        for q, a2 in qa)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="https://www.pdufa.bio/research/implied-vs-actual"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="https://www.pdufa.bio/research/implied-vs-actual"><style>*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.6}}a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}.wrap{{max-width:860px;margin:0 auto;padding:22px 18px 60px}}.top{{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}}.brand{{font-size:19px;font-weight:800}}.brand b{{color:#e3ba5e}}.nav a{{color:#a7bcd9;font-size:13px;margin-left:14px}}h1{{font-size:26px;line-height:1.2;margin:10px 0 6px}}h2{{font-size:18px;color:#e3ba5e;margin:26px 0 8px}}.bc{{font-size:12px;color:#94a9c9;margin:16px 0 4px}}.bc a{{color:#94a9c9}}.sub{{color:#a7bcd9;font-size:15px}}p{{max-width:78ch}}table{{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px}}caption{{text-align:left;color:#a7bcd9;font-size:13px;padding:4px 0}}th,td{{border:1px solid #1e3a63;padding:7px 9px;text-align:left}}th{{background:#0c1d38;color:#a7bcd9}}.note{{font-size:12px;color:#94a9c9;line-height:1.6}}footer{{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}}footer b{{color:#a7bcd9}}</style><script type="application/ld+json">{jsonld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/research">Research</a><a href="/runup-by-year">Run-up</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; <a href="/research">Research</a> &rsaquo; Implied vs actual</div><h1>What the options market priced before FDA decisions, and what happened</h1><div class="sub">Across <b>{n}</b> FDA decisions from 2020 to 2026, at-the-money options roughly two weeks out priced a median move of <b>&plusmn;{agg['median_priced_pct']}%</b>. The median move at the first close after the decision was <b>{agg['median_actual_abs_pct']}%</b>, and within five trading days <b>{agg['median_actual_5d_abs_pct']}%</b>. The actual move exceeded what was priced in <b>{agg['exceed_rate_pct']}%</b> of cases at one day and <b>{agg['exceed_5d_rate_pct']}%</b> within five.</div>

<h2>Read these two caveats before any number below</h2>
<p><b>1. A straddle two weeks out prices two weeks of ordinary movement plus the event.</b> Every figure here is the move the options market priced from the snapshot date through the first expiry after the decision. It is not the event-implied move, and this page never calls it that.</p>
<p><b>2. These are measurements of history, published with their distribution.</b> They describe what happened across this sample of decisions. They are not a property of future decisions, not a strategy, and not investment advice; option prices reflect risks (including total loss) this page does not measure.</p>

<h2>By year</h2>
<table><caption>Median priced move (T-14 ATM straddle) vs median first-close move, FDA decisions with a computable chain, by year. Updated {esc(pretty(agg['as_of']))}.</caption><tr><th>Year</th><th>n</th><th>Median priced</th><th>Median actual (1st close)</th><th>Exceeded priced</th></tr>{years}</table>

<h2>The largest realized moves, against what was priced</h2>
<table><caption>Ten largest five-day moves in the sample. "Priced" is the ATM straddle at the snapshot; both actual horizons shown because reactions can build over days.</caption><tr><th>Ticker</th><th>Decision</th><th>Priced (T-14)</th><th>Next close</th><th>5 trading days</th><th>ATM IV</th></tr>{rows}</table>

<h2>Method and coverage</h2>
<p>Universe: the {agg['universe_events']} PDUFA events in <a class="lit" href="/runup-by-year">our run-up study</a>. For each event we take the options chain snapshot closest to 14 days before the decision (accepted anywhere in the prior 30 days; the snapshot date is recorded per event), the nearest listed expiry after the decision date, and the at-the-money straddle mid divided by the stock price. The actual move is the study's own close-to-close move across the decision (the eve close to the first close after, and to the fifth trading day after), so this page and the run-up study cannot disagree about what happened. {n} events ({agg['coverage_pct']}%) were computable; coverage requires listed options with real two-sided quotes, so small and nano-cap names are underrepresented, and the aggregate figures describe the computable set, not every FDA decision.</p>

<h2>Questions</h2>{faq}
<p class="note">Historical measurements of specific decisions from recorded options quotes. Nothing here predicts any pending application or recommends any position. Not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> Options involve substantial risk including total loss of premium. Verify every figure against primary sources.<br><br>&copy; 2026 pdufa.bio. All rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>"""

    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print(f"wrote /research/implied-vs-actual (n={n}, coverage {agg['coverage_pct']}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
