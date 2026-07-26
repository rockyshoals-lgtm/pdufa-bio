"""CI guard (P0-B): the API must never claim more date precision than the page.

WHAT HAPPENED
All 299 readouts in /api/v1/events carried `"date":"2026-06-15","date_precision":"day"`. Every
single one fell on the 15th -- that is not 299 companies choosing the middle of the month, it is
the month MIDPOINT used as a sortable stand-in for a ClinicalTrials.gov primary-completion
ESTIMATE.

The rendered page got this right and said so plainly:
    "Dates are estimated primary-completion windows from ClinicalTrials.gov, not fixed
     announcements - they shift."
and rendered every row as "AGIO . Jun 2026 (est.)".

The API contradicted its own page. A consumer -- including an LLM, and /llms.txt is LIVE --
reads `2026-06-15` + `date_precision: day` and publishes "AGIO reports June 15." That date does
not exist. Same class of defect as a fabricated conference date: a month estimate stamped as a
hard day.

THE INVARIANTS
1. A day-precision date must not be suspiciously concentrated on one day-of-month. If >60% of a
   type's dates land on the same day, that day is a placeholder, not an announcement.
2. Every month-precision record must carry `dm` (date_month) so consumers have the real
   granularity and never need to parse `d`.
3. An "Estimated" record must never be day-precision -- if we're estimating, we don't have a day.

    python tests/test_api_precision_honesty.py
"""
import json, os, re, sys, collections

DATASET = os.path.join('pdufa_site_src', 'api', 'v1', 'dataset.mjs')
LIB = os.path.join('pdufa_site_src', 'api', 'v1', '_lib.mjs')


def load():
    s = open(DATASET, encoding='utf-8').read()
    return json.loads(s[s.index('['):s.rindex(']') + 1])


def main():
    if not os.path.exists(DATASET):
        print(f'  SKIP {DATASET} not found'); return 0
    arr = load()
    fail = 0

    by_type = collections.defaultdict(list)
    for e in arr:
        by_type[e.get('type')].append(e)

    for t, rows in sorted(by_type.items()):
        day_rows = [e for e in rows if e.get('dp') == 'day' and e.get('d')]
        if len(day_rows) >= 20:
            dom = collections.Counter((e['d'] or '')[8:10] for e in day_rows)
            top, n = dom.most_common(1)[0]
            if n / len(day_rows) > 0.60:
                print(f'  FAIL {t}: {n}/{len(day_rows)} day-precision dates land on the {top}th '
                      f'({n/len(day_rows):.0%}) — that is a placeholder, not an announced day')
                fail += 1

    # month precision must carry date_month
    missing_dm = [e for e in arr if e.get('dp') == 'month' and not e.get('dm')]
    if missing_dm:
        print(f'  FAIL {len(missing_dm)} month-precision records lack `dm` (date_month), '
              f'e.g. {missing_dm[0].get("id")}')
        fail += 1

    # an estimate is not a day
    est_day = [e for e in arr if e.get('st') == 'Estimated' and e.get('dp') == 'day']
    if est_day:
        print(f'  FAIL {len(est_day)} records are status="Estimated" but date_precision="day" '
              f'— e.g. {est_day[0].get("id")}. If we are estimating, we do not have a day.')
        fail += 1

    # the API must actually expose date_month
    if os.path.exists(LIB) and 'date_month' not in open(LIB, encoding='utf-8').read():
        print('  FAIL _lib.mjs CORE does not emit date_month — consumers cannot see real granularity')
        fail += 1

    if fail:
        print(f'\n{fail} precision-honesty failure(s). The API must not claim more precision '
              f'than the page. DO NOT PUBLISH.')
        return 1
    counts = collections.Counter(e.get('dp') for e in arr)
    print(f'OK -- {len(arr)} records, precision {dict(counts)}; no placeholder days claimed as '
          f'announcements, all month rows carry date_month.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
