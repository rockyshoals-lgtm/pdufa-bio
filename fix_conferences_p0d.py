# -*- coding: utf-8 -*-
"""P0-D: publish the conference presenter data we actually have, and stop overstating it.

WHAT THE AUDIT SAID
  * /conferences cites "256 presentations"; the study says 1,425.
  * Only 2 of 14 conferences show any presenter ("1 presenters" -- also a pluralisation bug).
  * "The restored 715-row / 39-conference crawler output has not been published."

WHAT THE DATA ACTUALLY SUPPORTS -- the third point needs correcting
The restored dataset is overwhelmingly HISTORICAL. Of 715 rows across 39 conferences, only
**4** are dated on or after today, one each for ASH, CTAD, SABCS and SITC. ESMO has 68 rows --
every one of them from the 2023, 2024 and 2025 meetings, none for the upcoming Oct-2026 meeting.

So publishing it does NOT fill the upcoming calendar; it adds four presenters. The presenter
mapping for upcoming conferences does not exist yet because abstract lists are released close to
the event -- which is exactly what the conference detail pages already say, honestly:
"Presenter list populates as abstracts are released."

The unpublished value is the HISTORY: "68 biotech presenters tracked across the last three ESMO
meetings" is true, substantive, backed by the 715 rows, and is the thing no competitor has. That
is what this script publishes.

WHAT IT DOES
  1. /conferences: "256 presentations" -> the real study n (1,425).
  2. /conferences: fixes "1 presenters" -> "1 presenter"; sets each card's count from the ACTUAL
     number of presenters announced for the UPCOMING meeting (so an unsupported count cannot sit
     on the page).
  3. /conference/{CODE}: publishes the announced upcoming presenters, and adds a historical
     coverage line ("N biotech presenters tracked across M past meetings, 2021-2026") sourced
     from the restored dataset.

Nothing is invented: every number is counted from catalysts_out/conference_presentations_history.csv.

Usage:  python fix_conferences_p0d.py [--dry-run]
"""
import argparse, json, os, re, shutil, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'pdufa_site_src')
HIST = os.path.join(HERE, 'catalysts_out', 'conference_presentations_history.csv')
STUDY = os.path.join(HERE, 'conf_study', 'conference_runup_PUBLISHED.csv')
TODAY = pd.Timestamp(dt.date.today())


def load():
    d = pd.read_csv(HIST, low_memory=False)
    d['cd'] = pd.to_datetime(d['catalyst_date'], errors='coerce')
    d = d[d['ticker'].notna()]
    return d


def main(dry):
    d = load()
    study_n = len(pd.read_csv(STUDY, low_memory=False))
    upcoming = d[d.cd >= TODAY]
    past = d[d.cd < TODAY]

    # per-conference facts, all counted from the dataset
    facts = {}
    for conf in sorted(set(d.conference.dropna())):
        up = upcoming[upcoming.conference == conf]
        pa = past[past.conference == conf]
        facts[conf] = {
            'upcoming_tickers': sorted(set(up.ticker.astype(str))),
            'past_presenters': int(len(pa)),
            'past_meetings': int(pa.cd.dt.date.nunique()),
            'past_tickers': int(pa.ticker.nunique()),
            'first_year': int(pa.cd.dt.year.min()) if len(pa) else None,
            'last_year': int(pa.cd.dt.year.max()) if len(pa) else None,
        }
    up_summary = {c: len(f['upcoming_tickers']) for c, f in facts.items() if f['upcoming_tickers']}
    print(f'study n = {study_n:,} | conferences in dataset = {len(facts)} | '
          f'upcoming presenters = {len(upcoming)} {up_summary}')

    # ---------------- 1 + 2) the /conferences index ----------------
    P = os.path.join(SITE, 'conferences', 'index.html')
    s = open(P, encoding='utf-8').read()
    orig = s
    changes = []

    if 'across 256 presentations' in s:
        s = s.replace('across 256 presentations', f'across {study_n:,} presentations')
        changes.append(f'promo card: 256 -> {study_n:,} presentations')

    # Drive this off the codes ON THE PAGE, not just those present in the dataset. A conference
    # with NO rows at all (e.g. ESC) still shipped "1 presenters" -- an unsupported count. Any
    # code the page renders must show a number the dataset can back, which for those is 0.
    page_codes = sorted(set(re.findall(r'href="/conference/([A-Za-z0-9]+)"', s)))
    for code in page_codes:
        facts.setdefault(code, {'upcoming_tickers': [], 'past_presenters': 0, 'past_meetings': 0,
                                'past_tickers': 0, 'first_year': None, 'last_year': None})
    for code in page_codes:
        n = len(facts[code]['upcoming_tickers'])
        word = 'presenter' if n == 1 else 'presenters'
        pat = re.compile(r'(href="/conference/' + re.escape(code) + r'"[^>]*>.{0,400}?\u00b7\s*)(\d+)\s*presenters?', re.S)
        m = pat.search(s)
        if m and (m.group(2) != str(n) or f'{n} {word}' not in m.group(0)):
            changes.append(f'{code}: "{m.group(2)} presenters" -> "{n} {word}"')
            s = pat.sub(lambda mm: mm.group(1) + f'{n} {word}', s, count=1)

    if s != orig and not dry:
        shutil.copy2(P, P + '.bak_p0d')
        open(P, 'w', encoding='utf-8').write(s)
    print('\n/conferences index:')
    for c in changes:
        print('   ', c)
    if not changes:
        print('    (no changes)')

    # ---------------- 3) conference detail pages ----------------
    print('\n/conference/{CODE} detail pages:')
    for code, f in sorted(facts.items()):
        dp = os.path.join(SITE, 'conference', code, 'index.html')
        if not os.path.exists(dp):
            continue
        h = open(dp, encoding='utf-8').read()
        h0 = h
        n_up = len(f['upcoming_tickers'])

        # the "Biotech presenters tracked" KV -> the real upcoming count
        h = re.sub(r'(<span>Biotech presenters tracked</span><b>)\d+(</b>)',
                   lambda m: m.group(1) + str(n_up) + m.group(2), h, count=1)

        # publish the announced upcoming presenters, else keep the honest placeholder
        if n_up:
            cards = ''.join(
                f'<a class="card" href="/ticker/{t}" style="display:block;text-decoration:none">'
                f'<b style="color:#e3ba5e">{t}</b><div style="font-size:12.5px;color:#a7bcd9">'
                f'Presenting at {code} 2026: announced</div></a>' for t in f['upcoming_tickers'])
            h = re.sub(r'<h2>Biotech presenters</h2><div class="grid">.*?</div></div>',
                       f'<h2>Biotech presenters</h2><div class="grid">{cards}</div>', h, count=1, flags=re.S)

        # historical coverage — this is the restored dataset's real, publishable value
        if f['past_presenters'] and 'presenter-history-v1' not in h:
            note = (f'<div class="card" id="presenter-history-v1" style="margin-top:12px">'
                    f'<b>Presenter history</b><div class="sub" style="margin-top:6px">'
                    f'We have tracked <b>{f["past_presenters"]}</b> biotech presentations by '
                    f'<b>{f["past_tickers"]}</b> companies across <b>{f["past_meetings"]}</b> past '
                    f'{code} meeting{"s" if f["past_meetings"] != 1 else ""} '
                    f'({f["first_year"]}–{f["last_year"]}). Upcoming presenters populate as '
                    f'abstracts are released. See the '
                    f'<a href="/research/conference-runup" style="color:#6fb6ff">conference run-up '
                    f'study</a> for how these names behaved into the meeting.</div></div>')
            h = h.replace('<div class="legal">', note + '\n<div class="legal">', 1)

        if h != h0:
            if not dry:
                shutil.copy2(dp, dp + '.bak_p0d')
                open(dp, 'w', encoding='utf-8').write(h)
            print(f'    {code:9s} upcoming={n_up}  history={f["past_presenters"]} presentations / '
                  f'{f["past_tickers"]} companies / {f["past_meetings"]} meetings')

    print('\n--dry-run: nothing written' if dry else '\ndone')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    main(ap.parse_args().dry_run)
