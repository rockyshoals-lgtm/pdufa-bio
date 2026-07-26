"""CI guard #9: a page that bakes a countdown must also ship the hydrator that corrects it.

WHY THIS EXISTS
The board renders "days to PDUFA" as literal HTML: <span class="cd"><b>5</b><i>days</i></span>.
That number is frozen at BUILD time. On 2026-07-22 every countdown on the live homepage read
exactly one day high, because the HTML had been generated on 07-21 and the clock moved. It would
have read two days high the next morning, and so on -- silently, forever, with no test failing.
Meanwhile /api/v1/events computed t_minus live and was correct. Page wrong, API right: the same
"the page and the data disagree" class as the ticker fan-out.

THE FIX IS STRUCTURAL, NOT A REBUILD
Regenerating pages hourly would paper over it -- and still be wrong between runs, or whenever a
run is missed or a CDN serves a cached copy. Instead index.html ships a hydrator that recomputes
each countdown from the PDUFA date already present in the DOM, at VIEW time. A stale baked number
is then harmless because the browser overwrites it.

SO THE INVARIANT IS: baked countdown  =>  hydrator present.
Drift in the baked value is reported but does NOT fail, precisely because the hydrator fixes it.
What must never happen is a page shipping baked countdowns with no hydrator.

    python tests/test_countdown_integrity.py
"""
import os, re, sys, datetime as dt

SITE = 'pdufa_site_src'
# a baked countdown inside a catalyst row, with its own PDUFA date
ROW = re.compile(r'<span class="cd"><b>(-?\d+)</b><i>days?</i></span>.*?PDUFA (\d{4}-\d{2}-\d{2})', re.S)
# the hydrator's load-bearing parts -- deleting any of these silently breaks the correction
HYDRATOR_MARKS = ('data-cd-hydrated', "querySelectorAll('a.row')", 'PDUFA')


def is_live(rel):
    """Backups, .bak snapshots and unpromoted drafts are not served; don't gate CI on them."""
    low = rel.lower()
    return not (os.path.basename(low).startswith('_') or 'backup' in low
                or '.bak' in low or 'redesign' in low)


def main():
    if not os.path.isdir(SITE):
        print(f'  SKIP {SITE} not found'); return 0

    today = dt.date.today()
    fail, drift, checked = [], [], 0

    for root, _, files in os.walk(SITE):
        for f in files:
            if not f.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(root, f), SITE)
            if not is_live(rel):
                continue
            html = open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
            baked = ROW.findall(html)
            if not baked:
                continue
            checked += 1
            missing = [m for m in HYDRATOR_MARKS if m not in html]
            if missing:
                fail.append((rel, len(baked), missing))
            for shown, date in baked:
                actual = (dt.date.fromisoformat(date) - today).days
                if int(shown) != actual:
                    drift.append((rel, date, int(shown), actual))

    if drift:
        print(f'  note: {len(drift)} baked countdown(s) are stale vs today ({today}) -- '
              f'expected, and corrected in-browser by the hydrator. Sample:')
        for rel, date, shown, actual in drift[:3]:
            print(f'      {rel}  PDUFA {date}  baked {shown}  actual {actual}')

    # --- API half: dataset.mjs bakes days_to_decision, so the handler MUST recompute it ---
    ds = os.path.join(SITE, 'api', 'v1', 'dataset.mjs')
    lib = os.path.join(SITE, 'api', 'v1', '_lib.mjs')
    if os.path.exists(ds) and os.path.exists(lib):
        baked_api = '"days_to_decision"' in open(ds, encoding='utf-8', errors='ignore').read()
        recomputed = 'base.days_to_decision =' in open(lib, encoding='utf-8', errors='ignore').read()
        if baked_api and not recomputed:
            fail.append(('api/v1/_lib.mjs', 0,
                         ['shape() must recompute base.days_to_decision — dataset.mjs bakes it '
                          'at generation time and it freezes there']))

    if fail:
        for rel, n, missing in fail:
            print(f'  FAIL {rel}: ships {n} baked countdown(s) but the hydrator is absent or '
                  f'gutted (missing: {missing}).')
        print(f'\n{len(fail)} page(s) bake a countdown with nothing to correct it. Those numbers '
              f'freeze on the build date and silently drift one day per day. DO NOT PUBLISH.')
        return 1

    print(f'OK -- {checked} live page(s) with baked countdowns, all ship an intact hydrator '
          f'({len(drift)} stale baked value(s), all self-correcting at view time).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
