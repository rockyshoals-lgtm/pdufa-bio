# -*- coding: utf-8 -*-
"""Patch the STATIC calendar page for the four resolved PDUFAs (BIIB / MRK / PFE / IONS).

WHY A SEPARATE SCRIPT (unchanged since yesterday): /calendar/index.html is pre-rendered HTML
with the slate baked in. It does NOT read api/data.js at runtime and has no generator. Fixing
api/data.js does not fix the rendered page.

WHAT YESTERDAY'S VERSION GOT WRONG, AND WHY THIS ONE COUNTS INSTEAD OF ASSUMING
fix_calendar_page.py ended with:

    h = ... ('%d scheduled FDA decisions' % (old_n - 2))

It assumed the delta. The page now says "59 scheduled FDA decisions" while carrying 57
scheduled rows. That two-row drift IS the "IONS still counted scheduled" symptom in the
handoff. Its own docstring had already learned this lesson for numberOfItems ("Deriving
numberOfItems from an ACTUAL count of remaining items is the safe move") -- the counter just
never got the same treatment. So: every count here is recomputed from the DOM after editing.

THE HEATMAP IS A STACKED BAR, NOT A BLOCK
Each week is one <g> with one <rect> per market-cap tier stacked bottom-up, plus a total label:
    Small #46d17f, Mid #5b8fd0, Large #33547e, Unlisted #28405f
    y = 189 - (pos + k) * 15      height = k * 15 - 1.2      label y = 189 - n*15 - 3
Verified against every existing block (n=1 -> y174/h13.8; n=2 -> y159/h28.8; Aug 17's
1/1/4/3 stack -> y174/h13.8, y159/h13.8, y99/h58.8, y54/h43.8).

Yesterday's script could only DELETE single-decision weeks (CORT, CELC). Aug 17 has 9 and
Aug 24 has 6, so they must be rebuilt at the new counts -- leaving a 9-tall bar to represent
6 decisions would be a chart that lies.

Removed from the pending board (all primary-source verified -- see fix_phantoms_2026_07_15.py):
    Aug 17 week: ALPMY, MRK, PFE  (approved 2026-07-10)   9 -> 6
    Aug 24 week: BIIB             (approved 2026-07-13)   6 -> 5

Idempotent. Run with --dry-run first.
"""
import os, re, shutil, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'pdufa_site_src', 'calendar', 'index.html')
TODAY = '2026-07-15'

TIER_FILL = [('Small', '#46d17f'), ('Mid', '#5b8fd0'), ('Large', '#33547e'), ('Unlisted', '#28405f')]


def week_block(wk, x, tiers, tickers):
    """Rebuild one week's stacked bar. tiers = {'Small':1,'Mid':1,'Large':2,'Unlisted':2}"""
    n = sum(tiers.values())
    lab = ', '.join(f'{tiers[t]} {t}' for t, _ in TIER_FILL if tiers.get(t))
    o = [f'<g><title>Week of {wk} · {n} decision{"s" if n != 1 else ""} · {lab}\n{" ".join(tickers)}</title>']
    pos = 0
    for t, fill in TIER_FILL:
        k = tiers.get(t, 0)
        if not k:
            continue
        y = 189 - (pos + k) * 15
        hgt = k * 15 - 1.2
        o.append(f'<rect x="{x}" y="{y:.1f}" width="37.9" height="{hgt:.1f}" rx="1.5" fill="{fill}"/>')
        pos += k
    ty = 189 - n * 15 - 3
    o.append(f'<text x="{float(x)+18.9:.1f}" y="{ty:.1f}" fill="#eef4fc" font-size="10" '
             f'font-weight="700" text-anchor="middle">{n}</text></g>')
    return ''.join(o)


def replace_week(h, wk, x, tiers, tickers, ch):
    i = h.find(f'Week of {wk} ·')
    if i < 0:
        ch.append(f'  = week {wk}: not found (already patched?)'); return h
    j = h.rfind('<g>', 0, i)
    k = h.find('</g>', i) + 4
    new = week_block(wk, x, tiers, tickers)
    if h[j:k] == new:
        ch.append(f'  = week {wk}: already correct'); return h
    ch.append(f'  ~ week {wk}: rebuilt -> {sum(tiers.values())} decisions ({" ".join(tickers)})')
    return h[:j] + new + h[k:]


def main(dry):
    h = open(P, encoding='utf-8').read()
    ch = []

    # 1) BIIB Aug 24 pending row -> resolved (approved 2026-07-13)
    m = re.search(r'<a class="row" href="/pdufa/BIIB">.*?</a>', h, re.S)
    if m:
        h = h[:m.start()] + (
            '<a class="row" href="/fda-decision/BIIB-2026-07-13"><div class="t">BIIB · 2026-07-13 · '
            '<span class="ok">✓ Approved</span></div><div class="d">LEQEMBI IQLIK (lecanemab-irmb) '
            ': Early Alzheimer&#x27;s disease (at-home initiation dose)</div></a>') + h[m.end():]
        ch.append('  ~ row: BIIB pending -> Approved 2026-07-13')
    else:
        ch.append('  = row: BIIB already resolved')

    # 2) KEYTRUDA+Padcev Aug 17 pending row -> resolved (approved 2026-07-10). One row, three
    #    sponsors (Astellas partners PADCEV with Pfizer); link the Merck decision page.
    m = re.search(r'<a class="row" href="/pdufa/PFE-keytruda">.*?</a>', h, re.S)
    if m:
        h = h[:m.start()] + (
            '<a class="row" href="/fda-decision/MRK-2026-07-10"><div class="t">ALPMY / MRK / PFE · '
            '2026-07-10 · <span class="ok">✓ Approved</span></div><div class="d">KEYTRUDA '
            '(pembrolizumab) plus Padcev (enfortumab vedotin-ejfv) — Muscle-invasive bladder cancer '
            '(MIBC)</div></a>') + h[m.end():]
        ch.append('  ~ row: KEYTRUDA+Padcev pending -> Approved 2026-07-10')
    else:
        ch.append('  = row: KEYTRUDA+Padcev already resolved')

    # 3) IONS row already said "Approved" but under the GOAL date and pointing at the page we
    #    retired. The decision was 2026-06-24 (Ionis 8-K Ex-99.1).
    m = re.search(r'<a class="row" href="/fda-decision/IONS-2026-06-30">.*?</a>', h, re.S)
    if m:
        h = h[:m.start()] + (
            '<a class="row" href="/fda-decision/IONS-2026-06-24"><div class="t">IONS · 2026-06-24 · '
            '<span class="ok">✓ Approved</span></div><div class="d">TRYNGOLZA (olezarsen): Severe '
            'hypertriglyceridemia</div></a>') + h[m.end():]
        ch.append('  ~ row: IONS 2026-06-30 -> 2026-06-24 (real decision date)')
    else:
        ch.append('  = row: IONS already on the real decision date')

    # 4) JSON-LD — drop the two resolved Events
    for name in ('PFE-keytruda', 'BIIB'):
        m = re.search(r'\{"@type":"ListItem","position":\d+,"item":\{"@type":"Event"[^}]*"url":'
                      r'"https://www\.pdufa\.bio/pdufa/' + re.escape(name) + r'"[^}]*\}\},?', h)
        if m:
            h = h[:m.start()] + h[m.end():]
            ch.append(f'  - JSON-LD: removed Event /pdufa/{name}')

    # 5) heatmap — rebuild the two affected weeks at their true counts
    h = replace_week(h, 'Aug 17', '253.3', {'Small': 1, 'Mid': 1, 'Large': 2, 'Unlisted': 2},
                     ['BMY', 'BNTX', 'CAPR', 'CTMX', 'EVAX', 'RARE'], ch)
    h = replace_week(h, 'Aug 24', '294.2', {'Small': 1, 'Large': 4},
                     ['GILD', 'JAZZ', 'ONC', 'RPRX', 'ZYME'], ch)

    # 6) counts — RECOMPUTED from the DOM, never decremented
    n_items = len(re.findall(r'\{"@type":"ListItem"', h))
    h = re.sub(r'"numberOfItems":\d+', f'"numberOfItems":{n_items}', h, count=1)
    n_sched = len(re.findall(r'<a class="row" href="/pdufa/', h))
    old = re.search(r'(\d+) scheduled FDA decisions', h)
    if old:
        h = h[:old.start()] + f'{n_sched} scheduled FDA decisions' + h[old.end():]
        ch.append(f'  = counter: {old.group(1)} -> {n_sched} scheduled (counted from rows)')
    ch.append(f'  = numberOfItems -> {n_items} (counted); ListItems={n_items}, /pdufa/ rows={n_sched}')

    for c in ch:
        print(c)
    if not dry:
        shutil.copy2(P, P + '.bak_' + TODAY)
        open(P, 'w', encoding='utf-8').write(h)
        print('\nwrote calendar/index.html')
    else:
        print('\n--dry-run: nothing written')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    main(ap.parse_args().dry_run)
