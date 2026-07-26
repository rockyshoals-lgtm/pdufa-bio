"""CI guard (P0-A): a PDUFA date must never fan out onto companies that aren't parties to it.

WHAT HAPPENED
The 2026-08-17 Keytruda + Padcev perioperative-MIBC decision shipped live under SIX tickers.
Three were real (MRK sponsor, PFE + ALPMY own Padcev). Three — BNTX (BioNTech), CTMX (CytomX),
EVAX (Evaxion) — have no connection to the application at all. Evaxion is a Danish AI-vaccine
microcap with no bladder-cancer BLA. Same pattern put MIRM on Incyte's zilurgisertib.

Cause: rows were joined on drug/indication TEXT with no sponsor key — a many-to-many join.

THE FINGERPRINT THIS TEST KEYS ON
The bogus rows are diagnosable from the payload alone. On the same (date, drug) they carried:
  * market_cap = null / market_cap_tier = null, while their real siblings resolved a market cap
  * a DIFFERENT indication string ("Perioperative muscle-invasive bladder cancer " — note the
    trailing space) vs the real rows' "Muscle-invasive bladder cancer (MIBC)"
A ticker that resolves no market cap sitting beside one that does, on the same drug and date, is
a join artifact until proven otherwise. That asymmetry is the signal.

WHY IT ALSO CHECKS PARTNERS
A real co-party can still be wrong: ALPMY (Astellas, genuine Padcev co-owner) sat on that same
Aug-17 row AFTER the FDA approved the drug on 2026-07-10. already_decided() missed it because it
only sweeps a ticker holding its own archive row — a partner ticker on a decided event survives.
So this also flags any multi-ticker group whose date has already passed.

    python tests/test_no_ticker_fanout.py
"""
import json, os, re, sys, collections, datetime as dt

API = os.path.join('pdufa_site_src', 'api', 'data.js')
DATASET = os.path.join('pdufa_site_src', 'api', 'v1', 'dataset.mjs')


def load_slate():
    src = open(API, encoding='utf-8').read()
    i = src.find('const SLATE=')
    slate, _ = json.JSONDecoder().raw_decode(src[i + len('const SLATE='):])
    return slate['catalysts']


def load_dataset():
    """The v1 API (/api/v1/events) is served by dataset.mjs — a SEPARATE file from the SLATE.
    P0-A looked closed because api/data.js was cleaned while dataset.mjs still returned the fan-out:
    the page was clean, the API was not. Both surfaces must satisfy this guard. Normalised to the
    slate's field names so one checker covers both."""
    if not os.path.exists(DATASET):
        return []
    src = open(DATASET, encoding='utf-8').read()
    arr = json.loads(src[src.index('['):src.rindex(']') + 1])
    out = []
    for e in arr:
        if e.get('type') != 'PDUFA':
            continue
        out.append({'ticker': e.get('t'), 'date': e.get('d'), 'name': e.get('company'),
                    'drug': e.get('name'), 'status': e.get('st'),
                    'indication': (e.get('_d') or {}).get('indication'),
                    'mcap': (e.get('_d') or {}).get('market_cap_usd')})
    return out



def check_ticker_name_crossassignment(cats):
    """A ticker must not carry another company's name.

    The fan-out guard groups by (date, drug-text). A row whose drug string is TRUNCATED evades it:
    RPRX shipped as date 2026-08-25, name "Nuvalent", drug "Ziihera" — Royalty Pharma's ticker,
    Nuvalent's name, Jazz's drug. Three companies fused into one row, and it grouped separately
    from the real JAZZ/ZYME rows because "Ziihera" != "Ziihera (zanidatamab-hrii) - (HERIZON-GEA-01)".
    Text grouping cannot catch that; a ticker/name cross-check can.

    Benign formatting variants ("Gilead Sciences" vs "Gilead Sciences Inc.") are ignored: we only
    fail when a ticker's name matches the canonical name of a DIFFERENT ticker.
    """
    import re as _re
    def norm(n):
        n = _re.sub(r'[^a-z0-9 ]', ' ', (n or '').lower())
        n = _re.sub(r'\b(inc|corp|corporation|plc|ltd|limited|company|co|holdings|therapeutics|'
                    r'pharmaceuticals|pharma|sciences|group|sa|nv|ag)\b', ' ', n)
        return ' '.join(n.split())
    canon = {}
    for c in cats:
        t, n = c.get('ticker'), norm(c.get('name'))
        if t and n:
            canon.setdefault(t, set()).add(n)
    fail = 0
    for c in cats:
        t, n = c.get('ticker'), norm(c.get('name'))
        if not t or not n:
            continue
        for other, names in canon.items():
            if other != t and n in names and n not in canon.get(t, set()) - {n}:
                if len(canon.get(t, set())) == 1 and n in names and other != t:
                    print(f'  FAIL ticker/name cross-assignment: {t} ({c.get("date")}) carries '
                          f'"{c.get("name")}" — that is {other}\'s name')
                    fail += 1
                    break
    return fail


def check_surface(cats, today, label):
    fail = 0
    groups = collections.defaultdict(list)
    for c in cats:
        drug = (c.get('drug') or '').strip().lower()
        if not drug:
            continue                      # null-drug rows are a separate defect
        groups[(c.get('date'), drug[:40])].append(c)

    for (date, drug), g in sorted(groups.items()):
        if len(g) < 2:
            continue
        resolved = [x for x in g if x.get('mcap') is not None]
        unresolved = [x for x in g if x.get('mcap') is None]

        # 1) the join-artifact signature: some siblings resolve a market cap, others don't
        if resolved and unresolved:
            print(f'  FAIL join artifact {date} "{drug[:44]}": no-mcap tickers '
                  f'{sorted(x["ticker"] for x in unresolved)} alongside resolved '
                  f'{sorted(x["ticker"] for x in resolved)}')
            fail += 1

        # 2) inconsistent indication text across a shared (date, drug) — the other tell
        inds = {(x.get('indication') or '').strip().lower() for x in g}
        if len(inds) > 1:
            print(f'  FAIL indication mismatch {date} "{drug[:44]}": {sorted(inds)[:3]}')
            fail += 1

        # 3) a multi-ticker event whose date has passed and is STILL marked upcoming — partner
        #    rows survive the decided-sweep (the ALPMY class). A group correctly flipped to
        #    Decided is fine: the date is history, not a phantom-pending row. Only rows still
        #    claiming to be upcoming past their date are the defect.
        still_up = [x for x in g if str(x.get('status', '')).lower() in ('', 'upcoming')]
        if date and date < today and still_up:
            print(f'  FAIL past-dated multi-ticker event {date} "{drug[:44]}": '
                  f'{sorted(x["ticker"] for x in still_up)} still Upcoming — '
                  f'decided events must be swept for EVERY party')
            fail += 1

    fail += check_ticker_name_crossassignment(cats)

    multi = sum(1 for g in groups.values() if len(g) > 1)
    if fail:
        print(f'  [{label}] {fail} failure(s)')
    else:
        print(f'  [{label}] OK — {len(cats)} PDUFA rows, {multi} multi-ticker events, no artifacts')
    return fail


def main():
    if not os.path.exists(API):
        print(f'  SKIP {API} not found'); return 0
    today = dt.date.today().isoformat()
    # BOTH surfaces must pass: the page (api/data.js SLATE) AND the v1 API (dataset.mjs).
    fail = check_surface(load_slate(), today, 'api/data.js')
    fail += check_surface(load_dataset(), today, 'api/v1/dataset.mjs')
    if fail:
        print(f'\n{fail} ticker fan-out failure(s) across surfaces. Join on sponsor/applicant, '
              f'never on drug text. Fix BOTH the page and the API. DO NOT PUBLISH.')
        return 1
    print('OK -- no join artifacts on either the page slate or the v1 API dataset.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
