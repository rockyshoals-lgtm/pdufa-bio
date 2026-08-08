#!/usr/bin/env python3
"""What appeared TODAY that wasn't there yesterday?

A daily scan that just rewrites a 600-row CSV is a daily scan nobody reads. The only reason to
run this every day is that a scheduling PR gives a MEASURED MEDIAN OF 3 DAYS of warning -- so
the question is never "what is the calendar" but "what showed up in the last 24 hours".

Writes daily/NEW_<date>.csv and prints the new exact-day rows, loudest first.
"""
import sys, os, glob, datetime as dt
import pandas as pd

KEY = ['ticker', 'catalyst_date', 'date_basis', 'trial', 'conference']

def load(p):
    d = pd.read_csv(p)
    for k in KEY:
        if k not in d.columns:
            d[k] = ''
    d[KEY] = d[KEY].fillna('')
    return d

def keyset(d):
    return set(map(tuple, d[KEY].astype(str).values))

def main():
    today_file = sys.argv[1] if len(sys.argv) > 1 else None
    if not today_file or not os.path.exists(today_file):
        print('daily_diff: no input file'); return 0

    prior = sorted(p for p in glob.glob(os.path.join('daily', 'readouts_*.csv'))
                   if os.path.abspath(p) != os.path.abspath(today_file))
    cur = load(today_file)
    if not prior:
        print(f'daily_diff: first run — {len(cur)} rows form the baseline. No diff to show.')
        return 0

    prev = load(prior[-1])
    old = keyset(prev)
    cur['_k'] = list(map(tuple, cur[KEY].astype(str).values))
    new = cur[~cur['_k'].isin(old)].drop(columns=['_k'])

    print()
    print('=' * 84)
    print(f'DAILY DIFF   {os.path.basename(prior[-1])}  ->  {os.path.basename(today_file)}')
    print('=' * 84)
    print(f'   yesterday {len(prev)} rows   today {len(cur)} rows   NEW {len(new)}')
    if not len(new):
        print('   nothing new.')
        return 0

    outp = os.path.join('daily', f'NEW_{dt.date.today().isoformat()}.csv')
    new.to_csv(outp, index=False)

    # An exact day with real lead time is the only thing worth waking up for.
    hard = new[(new.date_precision == 'day') &
               (new.date_basis.isin(['company_pr', 'conference_schedule', 'company_guidance']))]
    if len(hard):
        print()
        print(f'   *** {len(hard)} NEW EXACT-DAY READOUTS ***')
        today = dt.date.today()
        rows = []
        for _, r in hard.iterrows():
            try:
                lead = (dt.date.fromisoformat(str(r.catalyst_date)) - today).days
            except Exception:
                continue
            rows.append((lead, r))
        for lead, r in sorted(rows):
            tag = str(r.get('conference') or r.get('trial') or '?')
            urg = '  <<< IMMINENT' if lead <= 7 else ''
            print(f'   T-{lead:<4} {r.catalyst_date}  {str(r.ticker):6s} '
                  f'{str(r.date_basis):19s} [{tag:9s}]{urg}')
    print()
    print(f'   -> {outp}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
