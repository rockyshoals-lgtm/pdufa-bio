"""Guard (2026-11-27): a passed registry-window readout row resolved by a sponsor release names the release day on
its ticker hub. KPTI's XPORT-EC-042 row read "2026-05 Results released" (the registry month), as if results came out
in May; Karyopharm released them on Jul 30, 2026."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'pdufa_site_src')
sys.path.insert(0, ROOT)


def main():
    from build_ticker_hubs import pretty
    s = open(os.path.join(SITE, 'api', 'v1', 'dataset.mjs'), encoding='utf-8').read()
    rows = json.loads(s[s.index('['):s.rindex(']') + 1])
    bad, n = [], 0
    for r in rows:
        res = (r.get('_d') or {}).get('resolution') or {}
        if r.get('type') != 'Readout' or r.get('st') == 'Reported' or res.get('state') != 'sponsor_release':
            continue
        if len(str(res.get('date') or '')) != 10 or r.get('oc'):
            continue
        p = os.path.join(SITE, 'ticker', str(r.get('t') or '').upper(), 'index.html')
        if not os.path.exists(p):
            continue
        n += 1
        if 'Results released ' + pretty(res['date']) not in open(p, encoding='utf-8').read():
            bad.append(r['id'])
    if bad:
        print('FAIL -- hub shows the registry month, not the release day, for:', ', '.join(bad)); sys.exit(1)
    print(f'OK -- {n} sponsor-release readout row(s) name the release day on their hub.')


if __name__ == '__main__':
    main()
