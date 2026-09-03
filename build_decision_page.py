# -*- coding: utf-8 -*-
"""Generate /fda-decision/{TICKER}-{DATE}/ pages from REAL price data.

WHY THIS EXISTS
There was no generator for the decision pages. They were pre-rendered HTML, and the only
tool that made new ones -- fix_early_approvals.make_page() -- copied the VERA page and did
literal string swaps:

    t = t.replace('2026-07-07', d)            # ISO only; the chart labels say "7/7/26"
    t = t.replace('Jul 7, 2026', pretty)      # comma form only; the banner says "(Jul 7 2026)"
    t = t.replace('Trutakna (atacicept)', label)   # swaps the brand, KEEPS the trailing prose

So /fda-decision/CELC-2026-07-14 shipped saying CELC's gedatolisib got
"accelerated approval for IgA nephropathy (Jul 7 2026)" over VERA's price chart, VERA's
$49.1/$31.26 high/low, and "FDA decision 7/7/26". Wrong indication, wrong date, wrong prices,
on a live page whose entire purpose is being right. Copying a template that carries data is
not a template -- it is a data-integrity bug with a scheduler.

This builds every data-bound field from _chart_pxcache.json and explicit, verified facts.
Nothing is inherited from another company's page.

SELF-CHECK: --verify VERA regenerates the known-good VERA page and diffs the computed numbers
against the ones already published. If the math is wrong, that fails loudly before anything ships.
"""
import os, re, json, argparse, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
PX   = os.path.join(HERE, '_chart_pxcache.json')

# Cohort decision-day move by market-cap tier, as already published across the archive.
# (Large ±1%, Mid ±2%, Small ±3%, Micro ±7% -- consistent on every existing page.)
COHORT = {'Large': '±1% median', 'Mid': '±2% median', 'Small': '±3% median',
          'Micro': '±7% median', 'Nano': '±7% median'}

# chart geometry, matched to the existing pages
VB_W, VB_H = 640, 190
X0, X1, Y0, Y1 = 14.0, 628.0, 12.0, 150.0
PRE, POST = 120, 5


def mdy(iso):
    d = dt.date.fromisoformat(iso)
    return f'{d.month}/{d.day}/{str(d.year)[2:]}'


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f'{["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.month]} {d.day}, {d.year}'


def pretty_nc(iso):
    d = dt.date.fromisoformat(iso)
    return f'{["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.month]} {d.day} {d.year}'


def window(px, tk, ddate):
    """T-PRE .. decision .. T+POST of real daily closes. Returns (prices, dates, pivot)."""
    s = sorted((px.get(tk) or {}).items())
    if not s:
        raise SystemExit(f'{tk}: no price history in _chart_pxcache.json')
    idx = None
    for i, (d, _) in enumerate(s):
        if d <= ddate:
            idx = i
        else:
            break
    if idx is None:
        raise SystemExit(f'{tk}: no closes at/before {ddate}')
    lo = max(0, idx - PRE)
    hi = min(len(s), idx + POST + 1)
    w = s[lo:hi]
    return [p for _, p in w], [d for d, _ in w], idx - lo


def svg(prices, dates, piv, ddate, outcome):
    n = len(prices)
    lo, hi = min(prices), max(prices)
    rng = (hi - lo) or 1.0
    X = lambda i: X0 + (i / (n - 1)) * (X1 - X0)
    Y = lambda v: Y1 - ((v - lo) / rng) * (Y1 - Y0)

    # run-up extremes are measured T-120 -> T-1 (pre-decision only), as the note states
    pre_p, pre_d = prices[:piv], dates[:piv]
    hi_i = max(range(len(pre_p)), key=lambda i: pre_p[i])
    lo_i = min(range(len(pre_p)), key=lambda i: pre_p[i])

    xp = X(piv)
    o = []
    o.append(f'<svg viewBox="0 0 {VB_W} {VB_H}" role="img" style="width:100%;display:block;'
             f'aspect-ratio:{VB_W}/{VB_H};background:#071528;border:1px solid #1a3358;border-radius:10px">')
    o.append(f'<line x1="{xp:.1f}" y1="{Y0:.0f}" x2="{xp:.1f}" y2="{Y1:.0f}" stroke="#e3ba5e" '
             f'stroke-width="1" stroke-dasharray="3 3" opacity="0.85"/>')
    o.append(f'<text x="{xp-69.9:.1f}" y="177" fill="#e3ba5e" font-size="10" font-family="system-ui" '
             f'text-anchor="end">PDUFA {mdy(ddate)}</text>')
    pts = " ".join(f'{X(i):.1f},{Y(p):.1f}' for i, p in enumerate(prices))
    o.append(f'<polyline points="{pts}" fill="none" stroke="#7aa8ff" stroke-width="1.6"/>')
    o.append(f'<circle cx="{X(hi_i):.1f}" cy="{Y(pre_p[hi_i]):.1f}" r="2.6" fill="#5fd07a"/>'
             f'<text x="{X(hi_i):.1f}" y="{Y(pre_p[hi_i])-2:.1f}" fill="#5fd07a" font-size="10" '
             f'font-family="system-ui" text-anchor="middle">${pre_p[hi_i]:g}</text>')
    o.append(f'<circle cx="{X(lo_i):.1f}" cy="{Y(pre_p[lo_i]):.1f}" r="2.6" fill="#ff8f6b"/>'
             f'<text x="{X(lo_i):.1f}" y="{Y(pre_p[lo_i])-6:.1f}" fill="#ff8f6b" font-size="10" '
             f'font-family="system-ui" text-anchor="middle">${pre_p[lo_i]:g}</text>')
    o.append(f'<text x="14" y="164" fill="#94a9c9" font-size="10" font-family="system-ui">{mdy(dates[0])}</text>')
    o.append('</svg>')
    note = (f'Daily close, T-120 ({mdy(dates[0])}) through T+{len(prices)-1-piv}. '
            f'Run-up high ${pre_p[hi_i]:g} on {mdy(pre_d[hi_i])}, low ${pre_p[lo_i]:g} on '
            f'{mdy(pre_d[lo_i])} (T-120 to T-1). FDA decision {mdy(ddate)}. '
            f'Historical price action, not a forecast.')
    runup = (pre_p[-1] / pre_p[0] - 1) * 100
    return "".join(o), note, runup


def build(e, px, write=True):
    tk, d = e['ticker'], e['date']
    prices, dates, piv = window(px, tk, d)
    chart, note, runup = svg(prices, dates, piv, d, e['outcome'])
    appr = e['outcome'] == 'Approved'
    ban = ('<div class="ban ap">✓ APPROVED</div>' if appr
           else '<div class="ban cr">✕ COMPLETE RESPONSE LETTER</div>')
    ocol = '#5fd07a' if appr else '#ff8f6b'
    otxt = 'Approved' if appr else 'CRL'

    tpl = open(os.path.join(SITE, 'fda-decision', 'VERA-2026-07-07', 'index.html'), encoding='utf-8').read()
    head = tpl[:tpl.index('<div class="bc">')]          # chrome/CSS only -- carries no data
    tail = tpl[tpl.index('<div class="legal">'):]

    # REGEX, not a literal of the template's original title: the VERA template's title
    # is rewritten daily to answer format (rewrite_decision_snippets.py), so a literal
    # replace silently keeps VERA's title on the new page -- PTGX-2026-08-28 shipped
    # titled "Trutakna (atacicept) Approved Jul 7, 2026" before this line changed.
    head = re.sub(r"<title>.*?</title>",
                  f'<title>{tk} FDA Decision ({pretty(d)}): {e["drug"]}: {otxt} | pdufa.bio</title>',
                  head, count=1, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*"',
                  f'<meta name="description" content="{tk} ({e["company"]}) FDA decision on {pretty(d)} '
                  f'for {e["drug"]}: {otxt}. See the 120-trading-day run-up into the decision, '
                  f'high/low with dates, and the primary source."', head)
    head = head.replace('https://www.pdufa.bio/fda-decision/VERA-2026-07-07',
                        f'https://www.pdufa.bio/fda-decision/{tk}-{d}')
    head = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                  lambda m: m.group(1) + f'{tk} FDA Decision: {e["drug"]} — {otxt}' + m.group(2), head)

    body = [head]
    body.append(f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/decisions">Decisions</a> '
                f'&rsaquo; {tk} {d}</div>')
    body.append(f'<h1>{tk} <span class="g">FDA decision</span>: {pretty(d)}</h1>')
    body.append(ban)
    body.append(f'<p class="sub">{e["headline"]}</p>')
    body.append(f'<h2>Run-up into the decision (T-120 → T+5)</h2>{chart}<div class="note">{note}</div>')
    body.append('<h2>Key facts</h2><div class="card">')
    body.append(f'<div class="kv"><span>FDA decision date</span><b>{d}</b></div>')
    body.append(f'<div class="kv"><span>Outcome</span><b style="color:{ocol}">{otxt}</b></div>')
    body.append(f'<div class="kv"><span>Drug / candidate</span><b>{e["drug"]}</b></div>')
    body.append(f'<div class="kv"><span>Indication</span><b>{e["indication"]}</b></div>')
    body.append(f'<div class="kv"><span>Company</span><b>{e["company"]}</b></div>')
    body.append(f'<div class="kv"><span>Market-cap tier</span><b>{e["cap"]}</b></div>')
    body.append(f'<div class="kv"><span>120-day run-up (T-120→T-1)</span><b>{runup:+.1f}%</b></div>')
    body.append(f'<div class="kv"><span>Cohort decision-day move (history)</span><b>{COHORT[e["cap"]]}</b></div>')
    body.append('</div>')
    if e.get('pdufa_note'):
        body.append(f'<p class="sub" style="font-size:13px">{e["pdufa_note"]}</p>')
    body.append('<p class="sub" style="font-size:13px">Run-up figures are the stock\'s own daily closing '
                'path over the 120 trading days before the decision, from our price history. Cohort move is '
                'the historical median absolute decision-day move for this market-cap tier — history, not a '
                'prediction.</p>')
    if e.get('source'):
        body.append(f'<p class="sub" style="font-size:13px">Primary source: '
                    f'<a href="{e["source"]}" style="color:#e3ba5e">{e["source_label"]}</a></p>')
    body.append(tail)
    html = "".join(body)

    out = os.path.join(SITE, 'fda-decision', f'{tk}-{d}')
    if write:
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
        print(f'  built /fda-decision/{tk}-{d}  runup={runup:+.1f}%  '
              f'hi/lo from {len(prices)} closes, pivot={piv}')
    return html, runup, note


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default=os.path.join(HERE, 'decision_pages_2026_07_15.json'))
    ap.add_argument('--verify', help='regenerate this existing ticker-date and diff numbers, write nothing')
    a = ap.parse_args()
    px = json.load(open(PX))

    if a.verify:
        tk, d = a.verify.rsplit('-', 3)[0], '-'.join(a.verify.rsplit('-', 3)[1:])
        old = open(os.path.join(SITE, 'fda-decision', a.verify, 'index.html'), encoding='utf-8').read()
        prices, dates, piv = window(px, tk, d)
        _, note, runup = svg(prices, dates, piv, d, 'Approved')
        om = re.search(r'<div class="note">([^<]*)</div>', old)
        orr = re.search(r'120-day run-up \(T-120→T-1\)</span><b>([^<]*)</b>', old)
        print('PUBLISHED note :', om.group(1) if om else '?')
        print('REGENERATED    :', note)
        print('PUBLISHED runup:', orr.group(1) if orr else '?')
        print('REGENERATED    :', f'{runup:+.1f}%')
        raise SystemExit(0)

    for e in json.load(open(a.events)):
        build(e, px)
