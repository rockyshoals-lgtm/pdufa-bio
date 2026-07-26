"""CI guard (P0-C): every figure on /research/conference-runup must come from ONE dataframe.

WHAT HAPPENED
The page's headline table reproduced the dataset to the decimal. The PROSE and the JSON-LD FAQ
did not — they came from earlier cuts:

  figure            page prose   source truth
  event day         -0.63%       -0.56%
  D-1 -> D+5        -1.74%       -1.59%
  D-1 -> D+10       -2.00%       -1.93%
  mean D-30         +5.89%       +5.53%
  ran up 50%+        6.5%          6.2%
  ran up 25%+       15.8%         15.7%
  fell 25%+          8.4%          8.6%
  std dev           33.6%         33.5%

Worse, the JSON-LD FAQ mixed THREE cuts in one answer: nano -7.11% (n=121) came from
conference_runup_FULL_v3, while small +3.28% / micro +2.14% came from `cap_tier_final` — the
HINDSIGHT-biased column /corrections had already publicly disowned. On the correct point-in-time
tiers micro-caps are NEGATIVE (-1.95%), so the page was telling Google and every LLM that
micro-caps "fare best" using a methodology it had itself retracted.

JSON-LD is the surface Google and AI crawlers read. A stale number there outlives the page.

CANONICAL SOURCE: conf_study/conference_runup_PUBLISHED.csv
  * headline moves  -> event_day / post_5d / post_10d / runup_30d (all 1,425 rows)
  * cap tiers       -> cap_tier_pit (point-in-time; 1,105 known, 320 null and disclosed)
`cap_tier_final` is the superseded hindsight column — never publish from it.

    python tests/test_research_figures_match_source.py
"""
import os, re, sys

PAGE = os.path.join('pdufa_site_src', 'research', 'conference-runup', 'index.html')
DATA = os.path.join('conf_study', 'conference_runup_PUBLISHED.csv')


def main():
    if not (os.path.exists(PAGE) and os.path.exists(DATA)):
        print('  SKIP page or dataset not present'); return 0
    try:
        import pandas as pd
    except ImportError:
        print('  SKIP pandas unavailable'); return 0

    d = pd.read_csv(DATA, low_memory=False)
    html = open(PAGE, encoding='utf-8').read()
    fail = 0

    def present(val, label):
        """The value must appear on the page in some numeric form (entity-minus tolerated)."""
        nonlocal fail
        s = f'{val:.2f}'
        variants = [s, s.replace('-', '&minus;'), s.lstrip('-'), f'{val:+.2f}']
        if not any(v in html for v in variants):
            print(f'  FAIL {label}: source says {s}% — not found on the page')
            fail += 1

    r = d.runup_30d
    present(d.event_day.median(), 'event-day median')
    present(d.post_5d.median(),   'D-1->D+5 median')
    present(d.post_10d.median(),  'D-1->D+10 median')
    present(r.mean(),             'mean D-30 run-up')

    for val, label in ((round((r >= 50).mean() * 100, 1), 'ran up 50%+'),
                       (round((r >= 25).mean() * 100, 1), 'ran up 25%+'),
                       (round((r <= -25).mean() * 100, 1), 'fell 25%+'),
                       (round(r.std(), 1), 'std dev')):
        if f'{val}%' not in html:
            print(f'  FAIL {label}: source says {val}% — not found on the page')
            fail += 1

    # cap tiers must come from the point-in-time column, with counts on the page
    g = d[d.cap_tier_pit.notna()].groupby('cap_tier_pit')['runup_30d'].agg(['count', 'median'])
    for tier in ('nano', 'micro', 'small', 'mid', 'large'):
        if tier not in g.index:
            continue
        n = int(g.loc[tier, 'count'])
        med = g.loc[tier, 'median']
        if f'>{n}<' not in html:
            print(f'  FAIL {tier}: source n={n} not on the page')
            fail += 1
        s = f'{med:.2f}'
        if not any(v in html for v in (s, s.replace('-', '&minus;'), f'{med:+.2f}')):
            print(f'  FAIL {tier}: source median {s}% not on the page')
            fail += 1

    # The superseded hindsight figures must never be presented as CURRENT findings.
    # Citing one as the "before" value inside a correction narrative is legitimate and is how the
    # methodology note explains what changed ("micro-caps went from +2.14% on the hindsight tiers
    # to -1.95% on point-in-time tiers"). So this only fails when the number appears WITHOUT
    # correction-narrative language nearby — same context-awareness as the SEO-invariant guard.
    NARRATIVE = re.compile(r'hindsight|moved from|went from|changed sign|superseded|previously|'
                           r'was\s|before|correction', re.I)
    for bad, why in (('-7.11%', 'nano from FULL_v3'),
                     ('+2.14%', 'micro from hindsight cap_tier_final'),
                     ('+3.28%', 'small from hindsight cap_tier_final')):
        for variant in (bad, bad.replace('-', '&minus;')):
            for m in re.finditer(re.escape(variant), html):
                window = html[max(0, m.start() - 260): m.start()]
                if NARRATIVE.search(window):
                    continue          # explicitly framed as the superseded value
                print(f'  FAIL superseded figure {bad} presented as current ({why})')
                fail += 1

    # the 320 uncovered presentations must be disclosed
    n_null = int(d.cap_tier_pit.isna().sum())
    if str(n_null) not in html or '1,105' not in html:
        print(f'  FAIL cap-tier coverage not disclosed ({n_null} presentations have no tier)')
        fail += 1

    if fail:
        print(f'\n{fail} figure(s) on /research/conference-runup do not match '
              f'{DATA}. Regenerate every number from one dataframe. DO NOT PUBLISH.')
        return 1
    print(f'OK -- every published figure matches {DATA} (n={len(d)}, '
          f'cap tier known for {len(d)-n_null}, {n_null} disclosed as excluded).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
