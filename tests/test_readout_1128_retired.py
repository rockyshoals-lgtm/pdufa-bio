"""Guard (2026-11-27): three registry-estimate readouts the sponsor's own words contradict stay off the site, and
the Syndax axatilimab Phase 3 row names the trial it replaces (apply_1128_omw_readouts.py has the sources)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    from apply_1128_omw_readouts import RETIRE, SNDX_ROW
    s = open(os.path.join(ROOT, 'pdufa_site_src', 'api', 'v1', 'dataset.mjs'), encoding='utf-8').read()
    rows = json.loads(s[s.index('['):s.rindex(']') + 1])
    bad = []
    ncts = {f['nct'] for f in RETIRE.values()}
    for r in rows:
        blk = (r.get('_d') or {}).get('nct_id') or {}
        if r['id'] in RETIRE or (r.get('st') == 'Estimated' and isinstance(blk, dict)
                                 and str(blk.get('nct') or '').upper() in ncts):
            bad.append(f"{r['id']} is back")
    sndx = [r for r in rows if r['id'] == SNDX_ROW]
    if not sndx or (sndx[0].get('_d') or {}).get('nct_stated') != 'NCT06585774':
        bad.append(f'{SNDX_ROW} lost its NCT06585774')
    if bad:
        print('FAIL --', '; '.join(bad)); sys.exit(1)
    print('OK -- VERITAC-3, Descartes-08 SLE and the duplicate axatilimab estimate stay off; Syndax row names its NCT.')


if __name__ == '__main__':
    main()
