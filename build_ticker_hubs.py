# -*- coding: utf-8 -*-
"""Generate /ticker/{TICKER}/ hub pages — the missing spine of the internal-link graph (P1-3).

WHY THIS EXISTS
The audit calls this "the biggest SEO item left." pdufa.bio will not out-authority
BiopharmaWatch/BPIQ/MarketBeat on the head term ("PDUFA calendar 2026") this year; the winnable
path is the tail. Every event page already links to /calendar, /conferences, /condition/* — the
one link they CANNOT make is to a company hub, because it didn't exist. ~210 pages from data we
already own (every forward PDUFA + every past FDA decision per company), near-zero competition
("MNKD catalysts", "SRPT FDA history").

WHAT A HUB IS
One page per ticker aggregating that company's FDA catalysts:
  * Upcoming — links to the existing /pdufa/{slug} detail pages (which carry the run-up chart etc.)
  * Decision history — links to the existing /fda-decision/{TICKER}-{date} pages, with outcome.
It INVENTS no data and RE-STATES no numbers: it is a link hub over pages that already exist, so
it cannot drift from them. Every outbound link is verified to resolve to a real file at build.

THE RULES (from the backlog — non-negotiable)
  * No scores, probabilities, win rates, sizing, entry/exit. Facts only.
  * Self-canonical, index,follow. Same chrome/footer/disclaimer as the rest of the site.
  * Verify every internal link resolves to an existing page. A hub that links to a 404 is worse
    than no hub — it manufactures exactly the "Not found" errors we just cleaned out of GSC.

Usage:  python build_ticker_hubs.py            # build all, update sitemap
        python build_ticker_hubs.py --dry-run  # report coverage, write nothing
"""
import os, re, json, html, argparse, datetime as dt, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
TODAY = dt.date.today().isoformat()

# ---- site chrome, lifted verbatim from an existing /pdufa page so hubs are visually identical --
HEAD_CSS = ("""<style>*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;line-height:1.5}a{color:#6fb6ff;text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:820px;margin:0 auto;padding:22px 18px 60px}.top{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px;flex-wrap:wrap;row-gap:6px}.brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}.nav{display:flex;flex-wrap:wrap;gap:4px 12px;justify-content:flex-end}.nav a{color:#a7bcd9;font-size:13px;margin-left:14px}.nav a:first-child{margin-left:0}.bc{font-size:12px;color:#94a9c9;margin:16px 0 4px}.bc a{color:#94a9c9}h1{font-size:27px;line-height:1.18;letter-spacing:-.4px;margin:6px 0 4px}h1 .g{color:#e3ba5e}h2{font-size:18px;margin:26px 0 8px;color:#e3ba5e}.sub{color:#a7bcd9;font-size:15px;margin:6px 0 16px}.card{background:#0c1d38;border:1px solid #1a3358;border-radius:12px;padding:14px 16px;margin:14px 0}.kv{display:flex;justify-content:space-between;gap:12px;font-size:14px;padding:7px 0;border-bottom:1px solid #112b48}.kv:last-child{border:0}.kv span{color:#a7bcd9}.kv b{color:#f2f6fc;text-align:right}.badge{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;margin-left:8px;vertical-align:middle}.app{background:#0e3320;color:#7ee2a0;border:1px solid #1f6e42}.crl{background:#3a1010;color:#ff8a8a;border:1px solid #6e2020}.chip{display:inline-block;font-size:12px;color:#a7bcd9;border:1px solid #2a496f;border-radius:20px;padding:4px 11px;margin:3px 6px 3px 0}.cta{display:block;background:linear-gradient(135deg,#13315c,#0c1d38);border:1px solid #e3ba5e;border-radius:12px;padding:15px 16px;margin:20px 0;color:#f2f6fc}.cta b{color:#e3ba5e}.note{font-size:12px;color:#94a9c9}.row{display:block;background:#0c1d38;border:1px solid #1a3358;border-radius:10px;padding:11px 13px;color:#f2f6fc;margin:8px 0}.row:hover{border-color:#2a496f;text-decoration:none}.row .t{font-weight:800}.row .d{font-size:12.5px;color:#a7bcd9}footer{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}footer b{color:#a7bcd9}</style>"""
    """<link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/fonts/IBMPlexMono-600.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/fonts/fonts.css"><style id="typesys">h1,h2,h3,.brand{font-family:'Space Grotesk',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important;letter-spacing:-.5px}body{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}.tk,.dt,.dd,.row .t,.count{font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums;letter-spacing:-.2px}</style><link rel="icon" type="image/svg+xml" href="/favicon.svg">""")

NAV = ('<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>'
       '<div class="nav"><a href="/calendar">Calendar</a><a href="/conferences">Conferences</a>'
       '<a href="/adcomm">AdComm</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a>'
       '<a href="/research">Research</a><a href="/account">Account</a></div></div>')

FOOTER = ('<footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent '
          'service; "FDA", "PDUFA", and all company, drug, and ticker names are used descriptively '
          'and remain the property of their owners. <b>Informational and educational only, not '
          'investment advice.</b> Data and historical statistics only; no trade recommendations and '
          'no individual-drug approval probabilities. Verify every date and outcome against primary '
          'FDA / SEC / company filings. &copy; 2026 pdufa.bio</footer>')

MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return html.escape(str(s or ''), quote=True)


def pretty(iso):
    try:
        d = dt.date.fromisoformat(iso[:10]); return f'{MON[d.month]} {d.day}, {d.year}'
    except Exception:
        return iso or ''


def load_data():
    src = open(os.path.join(SITE, 'api', 'data.js'), encoding='utf-8').read()
    i = src.find('const SLATE=')
    slate, _ = json.JSONDecoder().raw_decode(src[i + len('const SLATE='):])
    fwd = collections.defaultdict(list)
    name = {}
    for c in slate['catalysts']:
        tk = c.get('ticker')
        if not tk:
            continue
        fwd[tk].append(dict(date=c.get('date'), drug=c.get('drug'), indication=c.get('indication')))
        nm = c.get('name')
        if nm and nm not in ('', tk) and len(nm) > len(name.get(tk, '')):
            name[tk] = nm

    arch = open(os.path.join(SITE, 'decisions', 'index.html'), encoding='utf-8').read()
    past = collections.defaultdict(list)
    for tk, d, body in re.findall(
            r'<a class="row" href="/fda-decision/([A-Z]+)-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>', arch, re.S):
        txt = re.sub('<[^>]+>', ' ', body)
        outc = 'Approved' if 'Approved' in txt else ('CRL' if 'CRL' in txt else '?')
        lab = txt.split('—', 1)[1].strip() if '—' in txt else ''
        lab = re.sub(r'\s+', ' ', lab)[:70]
        if lab.lower() in ('price-only', 'price only', ''):
            lab = ''   # placeholder archive row -> no fake drug label; the page says 'FDA decision'
        past[tk].append(dict(date=d, outcome=outc, label=lab))

    # company name also from decision pages (covers past-only tickers with no slate row)
    for d in os.listdir(os.path.join(SITE, 'fda-decision')):
        m = re.match(r'([A-Z]{2,6})-\d{4}-\d{2}-\d{2}$', d)
        if not m or m.group(1) in name:
            continue
        p = os.path.join(SITE, 'fda-decision', d, 'index.html')
        if not os.path.exists(p):
            continue
        cm = re.search(r'<span>Company</span><b>([^<]+)</b>', open(p, encoding='utf-8', errors='replace').read())
        if cm:
            name[m.group(1)] = html.unescape(cm.group(1)).strip()

    # Clinical readouts from the dataset (the slate is PDUFA-only).
    readouts = collections.defaultdict(list)
    dsp = os.path.join(SITE, 'api', 'v1', 'dataset.mjs')
    if os.path.exists(dsp):
        dsrc = open(dsp, encoding='utf-8', errors='replace').read().replace('\x00', '')
        drows, _ = json.JSONDecoder().raw_decode(dsrc[dsrc.find('['):])
        for r in drows:
            if r.get('type') != 'Readout':
                continue
            tkr = str(r.get('t') or '').upper()
            if not tkr:
                continue
            readouts[tkr].append(dict(date=str(r.get('d') or ''), drug=r.get('name'),
                                      outcome=(r.get('_d') or {}).get('readout_outcome') or r.get('oc'), url=r.get('url'),
                                      precision=r.get('dp') or 'day',
                                      status=r.get('st')))
            nm = r.get('company')
            if nm and len(str(nm)) > len(name.get(tkr, '')):
                name[tkr] = str(nm)

    # /pdufa/{slug} detail pages that exist, grouped by ticker
    slugs = collections.defaultdict(list)
    for d in sorted(os.listdir(os.path.join(SITE, 'pdufa'))):
        if os.path.isdir(os.path.join(SITE, 'pdufa', d)):
            mm = re.match(r'([A-Z]{2,6})(?:-.*)?$', d)
            if mm:
                slugs[mm.group(1)].append(d)
    return fwd, past, name, slugs, readouts


def render(tk, fwd, past, name, slugs, readouts):
    company = name.get(tk, '')
    disp = f'{tk} — {esc(company)}' if company else tk
    n_up, n_past = len(fwd.get(tk, [])), len(past.get(tk, []))
    title = f'{tk} FDA Calendar: PDUFA Dates & Decision History | pdufa.bio'
    desc = (f'{tk}{" (" + esc(company) + ")" if company else ""} FDA catalyst hub: '
            f'{n_up} upcoming PDUFA/decision page(s) and {n_past} past FDA decision(s) with dates '
            f'and outcomes. Facts only — verify against primary filings.')
    if len(desc) > 158:      # long company names blow the 160 cap (the /ticker/IRD CI red)
        desc = desc[:158].rsplit(' ', 1)[0].rstrip(',;:') + '.'
    url = f'https://www.pdufa.bio/ticker/{tk}'

    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
           f'<title>{esc(title)}</title><meta name="description" content="{desc}">'
           f'<link rel="canonical" href="{url}"><meta name="robots" content="index,follow,max-image-preview:large">'
           f'<meta name="theme-color" content="#02060d">'
           f'<meta property="og:type" content="website"><meta property="og:site_name" content="pdufa.bio">'
           f'<meta property="og:url" content="{url}"><meta property="og:title" content="{esc(title)}">'
           f'<meta property="og:description" content="{desc}">{HEAD_CSS}']

    # JSON-LD: breadcrumb + an ItemList of this company's decision pages (no scores)
    items = []
    for j, p in enumerate(sorted(past.get(tk, []), key=lambda x: x['date'], reverse=True), 1):
        if os.path.exists(os.path.join(SITE, 'fda-decision', f"{tk}-{p['date']}", 'index.html')):
            items.append({"@type": "ListItem", "position": len(items) + 1,
                          "url": f"https://www.pdufa.bio/fda-decision/{tk}-{p['date']}"})
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.pdufa.bio/"},
            {"@type": "ListItem", "position": 2, "name": "Tickers", "item": "https://www.pdufa.bio/calendar"},
            {"@type": "ListItem", "position": 3, "name": tk, "item": url}]},
        {"@type": "ItemList", "name": f"{tk} FDA catalysts and decisions",
         "numberOfItems": len(items), "itemListElement": items}]}
    out.append(f'<script type="application/ld+json">{json.dumps(ld)}</script></head><body><div class="wrap">')
    out.append(NAV)
    out.append(f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/calendar">PDUFA Calendar</a> &rsaquo; {tk}</div>')
    out.append(f'<h1>{tk} <span class="g">FDA calendar</span> &amp; decision history</h1>')
    sub = []
    if company:
        sub.append(esc(company))
    sub.append(f'{n_up} upcoming' if n_up else 'no upcoming catalyst on file')
    sub.append(f'{n_past} past FDA decision{"s" if n_past != 1 else ""}')
    out.append(f'<div class="sub">{" · ".join(sub)}</div>')

    # Upcoming — driven by the CURRENT SLATE, not the /pdufa slug directories.
    # The slug dirs are stale static pages: a swept/decided catalyst (e.g. MRK-keytruda, approved
    # 2026-07-10) still has its /pdufa page saying "target 2026-08-17". Listing slug dirs would
    # resurrect exactly the decided-as-pending phantoms we spent sessions removing. The slate is
    # the authoritative forward calendar; link each slate row to a matching detail page by drug
    # token when one exists, else to the month calendar. Never link a swept page back onto a hub.
    up = sorted(fwd.get(tk, []), key=lambda x: x.get('date') or '9999')
    if up:
        out.append('<h2>Upcoming FDA catalysts</h2>')
        for c in up:
            drug, ind, date = c.get('drug') or '', c.get('indication') or '', c.get('date') or ''
            href = '/calendar'
            dtoks = {w.lower() for w in re.findall(r'[A-Za-z]{4,}', drug)}
            for s in slugs.get(tk, []):
                stoks = set(s.lower().replace('-', ' ').split())
                if dtoks & stoks:
                    href = f'/pdufa/{s}'; break
            label = f'{tk} · {pretty(date)}' if date else tk
            d2 = ' — '.join(x for x in (esc(drug) or 'FDA decision', esc(ind)) if x)
            out.append(f'<a class="row" href="{href}"><span class="t">{label}</span>'
                       f'<span class="d">{d2}</span></a>')

    # Decision history — link to the existing /fda-decision pages, newest first, verified to exist
    ph = sorted(past.get(tk, []), key=lambda x: x['date'], reverse=True)
    ph = [p for p in ph if os.path.exists(os.path.join(SITE, 'fda-decision', f"{tk}-{p['date']}", 'index.html'))]
    if ph:
        out.append(f'<h2>FDA decision history ({len(ph)})</h2>')
        for p in ph:
            badge = '<span class="badge app">✓ Approved</span>' if p['outcome'] == 'Approved' else \
                    ('<span class="badge crl">✕ CRL</span>' if p['outcome'] == 'CRL' else '')
            lab = esc(p['label']) or 'FDA decision'
            out.append(f'<a class="row" href="/fda-decision/{tk}-{p["date"]}">'
                       f'<span class="t">{pretty(p["date"])}{badge}</span>'
                       f'<span class="d">{lab}</span></a>')

    # Clinical readouts. The hub has always SAID it covers "PDUFA dates, advisory committee
    # meetings and clinical readouts", but it was built only from the PDUFA slate and the
    # decisions archive, so a company whose catalyst is a readout had no hub at all: AMLX posted
    # a positive Phase 3 on 2026-08-18 (published to /readouts at +63.8%) and /ticker/AMLX was a
    # 404 for six days. Readouts come from the dataset, and a reported one carries its outcome.
    rh = sorted(readouts.get(tk, []), key=lambda x: x['date'], reverse=True)
    if rh:
        out.append(f'<h2>Clinical readouts ({len(rh)})</h2>')
        for r in rh:
            oc = str(r.get('outcome') or '')
            badge = (f'<span class="badge app">✓ {esc(oc)}</span>' if oc.lower().startswith('pos')
                     else (f'<span class="badge crl">✕ {esc(oc)}</span>'
                           if oc.lower().startswith('neg') else ''))
            when = pretty(r['date']) if r.get('precision') == 'day' else r['date'][:7]
            href = r.get('url') or '/readouts'
            ext = ' rel="nofollow"' if str(href).startswith('http') else ''
            out.append(f'<a class="row" href="{esc(href)}"{ext}>'
                       f'<span class="t">{when}{badge}</span>'
                       f'<span class="d">{esc(r.get("drug") or "Clinical readout")}</span></a>')

    out.append('<div style="margin:16px 0">'
               '<a class="chip" href="/calendar">Full PDUFA calendar →</a>'
               '<a class="chip" href="/decisions">All FDA decisions →</a>'
               '<a class="chip" href="/readouts">Phase readouts →</a></div>')
    out.append('<a class="cta" href="/calendar"><b>See the full 2026 PDUFA calendar &rarr;</b></a>')
    out.append('<p class="note">This page aggregates ' + tk + "'s FDA catalysts from pdufa.bio's own "
               'calendar and decision archive. Each item links to its source page. Facts and dates '
               'only; verify against primary FDA / SEC / company filings.</p>')
    out.append(FOOTER)
    out.append('</div><script src="/cmdk.js" defer></script></body></html>')
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    fwd, past, name, slugs, readouts = load_data()
    tickers = sorted(set(fwd) | set(past) | set(readouts))
    print(f'{len(tickers)} ticker hubs to build '
          f'({sum(1 for t in tickers if slugs.get(t) and past.get(t))} with both, '
          f'{sum(1 for t in tickers if slugs.get(t) and not past.get(t))} upcoming-only, '
          f'{sum(1 for t in tickers if past.get(t) and not slugs.get(t))} history-only)')

    built, links, deadlinks = 0, 0, 0
    for tk in tickers:
        h = render(tk, fwd, past, name, slugs, readouts)
        links += len(re.findall(r'href="/(?:pdufa|fda-decision)/', h))
        if a.dry_run:
            continue
        d = os.path.join(SITE, 'ticker', tk)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(h)
        built += 1

    # verify every outbound event link resolves to a real file (no manufactured 404s)
    for tk in tickers:
        for s in slugs.get(tk, []):
            if not os.path.exists(os.path.join(SITE, 'pdufa', s, 'index.html')):
                deadlinks += 1; print(f'  DEAD /pdufa/{s}')
    print(f'built {built} hubs, {links} internal links, {deadlinks} dead links (must be 0)')

    if a.dry_run:
        print('--dry-run: nothing written'); return

    # sitemap: add every hub
    P = os.path.join(SITE, 'sitemap.xml'); s = open(P, encoding='utf-8').read()
    import shutil; shutil.copy2(P, P + '.bak_' + TODAY + '_hubs')
    added = 0
    anchor = re.search(r'<url><loc>https://www\.pdufa\.bio/[^<]*</loc>.*?</url>\n?', s, re.S)
    if anchor is None:
        # build_sitemap.py owns the sitemap now and reformats it; this legacy insert step just
        # crashed on the new format (2026-08-20). The hubs are already written; build_sitemap
        # picks them up on its own pass.
        print('sitemap: anchor not found (build_sitemap.py owns the file now); skipped')
        return
    ins = anchor.end()
    block = ''
    for tk in tickers:
        loc = f'https://www.pdufa.bio/ticker/{tk}'
        if loc + '</loc>' in s:
            continue
        block += f'<url><loc>{loc}</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq></url>\n'
        added += 1
    s = s[:ins] + block + s[ins:]
    open(P, 'w', encoding='utf-8').write(s)
    import xml.dom.minidom as X; X.parseString(s)
    print(f'sitemap: +{added} hub URLs, now {s.count("<loc>")} total, well-formed')


if __name__ == '__main__':
    main()
