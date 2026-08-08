# -*- coding: utf-8 -*-
"""Rebuild the homepage's live blocks from the slate + decisions archive.

THE BUG THIS FIXES IS BIGGER THAN ONE STALE ROW.

The homepage bakes its countdowns into the HTML:

    <a class="row" href="/pdufa/CELC"><span class="cd"><b>7</b><i>days</i></span> ... PDUFA 2026-07-17

That "7" was true on the build date (as_of 2026-07-10). It is a literal. It does not tick.
So EVERY countdown on the homepage drifts one day per day until someone rebuilds. On 2026-07-15
the page claimed CELC was 7 days out (it was approved the day before), MNKD 16 days (really 11),
CAPR/OTLK 19 (really 14). The page was wrong about every single row, not just the phantom.

There is no generator for index.html in the repo, so this is it. It does three things:

  1. DROP rows that are no longer pending. Source of truth = the SLATE in api/data.js, which
     build_slate_from_crawl.py now sweeps against the decisions archive. If a (ticker, date) is
     gone from the slate, the FDA has ruled and the row must leave the homepage.
  2. RECOMPUTE every countdown from TODAY, off the row's own printed PDUFA date.
  3. PROMOTE the newly-decided into "Recently decided", newest first, capped at 10.

Rows are PATCHED, never regenerated: each carries a sparkline SVG built from price history we
cannot reconstruct here. When a row is promoted from pending to decided, its sparkline is
transplanted, so the decided card keeps its real price path.

Idempotent. Backs up first. Safe to run daily.
"""
import os, re, sys, json, shutil
import datetime as dt

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
HOME = os.path.join(SITE, 'index.html')
API = os.path.join(SITE, 'api', 'data.js')
DEC = os.path.join(SITE, 'decisions', 'index.html')
TODAY = dt.date.today()
MAX_DECS = 10


def load_slate():
    s = open(API, encoding='utf-8').read()
    i = s.find('const SLATE=')
    obj, _ = json.JSONDecoder().raw_decode(s[i + len('const SLATE='):])
    return {(c.get('ticker'), str(c.get('date'))[:10]) for c in obj['catalysts']}, obj.get('as_of')


def load_archive():
    """(ticker, date) -> (outcome, drug_label) from the decisions archive."""
    import html as _h
    h = open(DEC, encoding='utf-8').read()
    out = {}
    for tk, d, body in re.findall(
            r'<a class="row" href="/fda-decision/([A-Z]+)-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>', h, re.S):
        txt = _h.unescape(re.sub('<[^>]+>', ' ', body))
        outc = 'Approved' if 'Approved' in txt else ('CRL' if 'CRL' in txt else '?')
        label = txt.split('—', 1)[1].strip() if '—' in txt else ''
        out[(tk, d)] = (outc, re.sub(r'\s+', ' ', label))
    return out


def main():
    h = open(HOME, encoding='utf-8').read()
    orig = len(h)
    shutil.copy(HOME, HOME + '.bak')
    slate, as_of = load_slate()
    arch = load_archive()
    print(f'slate as_of={as_of} · {len(slate)} pending · archive {len(arch)} decisions · today {TODAY}')

    # ---------- 1 + 2: the "Next FDA decisions" list ----------
    a = h.find('<div class="list">')
    b = h.find('</div>\n  </section>', a)
    if a < 0 or b < 0:
        print('!! could not locate the Next-FDA-decisions list — aborting'); return 1
    block = h[a:b]

    rows = re.findall(r'<a class="row" href="/pdufa/[^"]+">.*?</a>', block, re.S)
    kept, dropped, retimed, unparsed = [], [], 0, []
    for r in rows:
        # The ticker span comes in TWO shapes. Listed names carry a cap tag, so the ticker is
        # followed by a space:      <span class="tk">ALPMY <em class="cap">Large</em></span>
        # UNLISTED names have no cap tag, so the ticker butts straight onto the close tag:
        #                           <span class="tk">BNTX</span>
        # Requiring \s after the ticker silently skipped every unlisted row (BNTX, CTMX kept a
        # stale 38-day countdown while everything around them was corrected). Accept both.
        tk = re.search(r'<span class="tk">([A-Z]+)(?=[\s<])', r)
        pd_ = re.search(r'PDUFA (\d{4}-\d{2}-\d{2})', r)
        if not tk or not pd_:
            # e.g. "Q4 2026 (est.)" rows have no exact date and no countdown to fix.
            unparsed.append(re.search(r'href="([^"]+)"', r).group(1))
            kept.append(r); continue
        key = (tk.group(1), pd_.group(1))
        if key not in slate:
            dropped.append((key, r))          # FDA has ruled; off the homepage it goes
            continue
        # recompute the countdown from TODAY, not from whenever this page was last built
        n = (dt.date.fromisoformat(pd_.group(1)) - TODAY).days
        n = max(n, 0)
        lab = 'day' if n == 1 else 'days'
        r2 = re.sub(r'<span class="cd"><b>\d+</b><i>\w+</i></span>',
                    f'<span class="cd"><b>{n}</b><i>{lab}</i></span>', r, count=1)
        if r2 != r:
            retimed += 1
        kept.append(r2)

    new_block = '<div class="list">' + ''.join(kept)
    h = h[:a] + new_block + h[b:]
    print(f'  next-decisions: {len(rows)} rows -> kept {len(kept)}, dropped {len(dropped)}, '
          f'countdowns corrected {retimed}')
    for (tk, d), _ in dropped:
        print(f'    dropped {tk} {d} (decided — no longer in slate)')
    if unparsed:
        # Surface these. A row we could not parse is a row whose countdown we did NOT fix, and a
        # silent skip is how BNTX/CTMX kept a wrong number while everything around them updated.
        print(f'    NOT retimed (no exact date parsed): {", ".join(unparsed)}')

    # ---------- 3: promote the newly decided into "Recently decided" ----------
    c = h.find('<div class="decs">')
    if c < 0:
        print('!! no decs block'); return 1
    dend = h.find('</div>', c)
    decs_block = h[c:dend]
    existing = set(re.findall(r'/fda-decision/([A-Z]+-\d{4}-\d{2}-\d{2})', decs_block))

    add = []
    for (tk, d), row in dropped:
        # find this event in the archive; the decision date may differ from the listed PDUFA date
        # (approved early), so match on ticker and take the most recent decision on/before it.
        cands = sorted([(dd, v) for (t2, dd), v in arch.items() if t2 == tk and dd <= d],
                       reverse=True)
        if not cands:
            print(f'    !! {tk} dropped but NOT in the archive — cannot promote. Add it first.')
            continue
        ddate, (outc, label) = cands[0]
        slug = f'{tk}-{ddate}'
        if slug in existing:
            continue
        spk = re.search(r'<svg class="spk".*?</svg>', row, re.S)   # transplant the real price path
        spk = spk.group(0) if spk else ''
        cls = 'ap' if outc == 'Approved' else 'cr'
        icon = '✓' if outc == 'Approved' else '✕'
        add.append((ddate, f'<a class="dec {cls}" href="/fda-decision/{slug}">'
                           f'<span class="di">{icon}</span><span class="dt">{tk}</span>{spk}'
                           f'<span class="dd">{ddate} · {outc}</span></a>'))

    if add:
        old_rows = re.findall(r'<a class="dec \w+" href="/fda-decision/[^"]+">.*?</a>', decs_block, re.S)
        merged = [r for _, r in sorted(add, reverse=True)] + old_rows
        merged = merged[:MAX_DECS]
        h = h[:c] + '<div class="decs">' + ''.join(merged) + h[dend:]
        for ddate, _ in sorted(add, reverse=True):
            print(f'  recently-decided: promoted {ddate}')
        print(f'  recently-decided: now {len(merged)} rows (cap {MAX_DECS})')
    else:
        print('  recently-decided: nothing new to promote')

    open(HOME, 'w', encoding='utf-8').write(h)
    print(f'\nwrote {HOME}  ({orig} -> {len(h)} chars)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
