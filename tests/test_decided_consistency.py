"""CI guard #12: a Decided record must state its outcome and never claim a future countdown.

WHY THIS EXISTS (audit 2026-07-25)
The rendered site correctly showed "MNKD 2026-07-24 - Approved", but /api/v1/events served the SAME
decision as a self-contradicting record: status "Decided", date 2026-07-26 (the goal date),
days_to_decision +1 (a future countdown), and NO outcome field at all. /llms.txt points AI crawlers
straight at that API, so the machine-readable truth has to match the page.

Invariants enforced on the published dataset (both what's stored and what the serializer must expose):
  * every st=="Decided" record carries an outcome (oc) in {Approved, CRL, Withdrawn};
  * a Decided record never carries a positive days_to_decision (the serializer nulls it);
  * the serializer (_lib.mjs) exposes `outcome`/`decision_date` and derives `Awaiting` for a
    past-dated Upcoming PDUFA -- checked structurally so the behaviour can't silently regress.

    python tests/test_decided_consistency.py
"""
import json, os, re, sys

SITE = 'pdufa_site_src'
DATASET = os.path.join(SITE, 'api', 'v1', 'dataset.mjs')
LIB = os.path.join(SITE, 'api', 'v1', '_lib.mjs')
OK_OUTCOMES = {'Approved', 'CRL', 'Withdrawn'}


def main():
    if not os.path.exists(DATASET):
        print(f'  SKIP {DATASET} not found'); return 0
    txt = open(DATASET, encoding='utf-8').read()
    arr = json.loads(txt[txt.index('['):txt.rindex(']') + 1])

    fail = []
    decided = [r for r in arr if r.get('st') == 'Decided']
    for r in decided:
        oc = r.get('oc')
        if oc not in OK_OUTCOMES:
            fail.append(f'{r.get("t")} {r.get("d")}: Decided but outcome (oc) is {oc!r} '
                        f'(must be one of {sorted(OK_OUTCOMES)})')

    # the serializer must (a) expose outcome, (b) null days_to_decision on Decided, (c) derive Awaiting
    lib = open(LIB, encoding='utf-8').read() if os.path.exists(LIB) else ''
    for needle, why in (
        ('base.outcome', 'shape() must expose `outcome`'),
        ('base.decision_date', 'shape() must expose `decision_date`'),
        ("base.status === 'Decided'", 'shape() must special-case Decided to null days_to_decision'),
        ("'Awaiting'", 'shape() must derive Awaiting for a past-dated Upcoming PDUFA'),
    ):
        if needle not in lib:
            fail.append(f'_lib.mjs serializer regressed: {why} (missing {needle!r})')

    print(f'decided records: {len(decided)}  (all must carry an outcome)')
    if fail:
        for f in fail:
            print(f'  FAIL {f}')
        print(f'\n{len(fail)} Decided-consistency violation(s). The API would contradict the page. '
              f'DO NOT PUBLISH.')
        return 1
    print(f'OK -- every Decided record has an outcome; serializer exposes outcome/decision_date, '
          f'nulls days_to_decision on Decided, and derives Awaiting.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
