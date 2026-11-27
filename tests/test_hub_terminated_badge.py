"""Guard (2026-11-27): a passed readout row whose trial ClinicalTrials.gov lists as terminated, withdrawn or
suspended, with no sponsor finding on the row, says so on its ticker hub. GOSS, JSPR and IMMP hubs read
"Date passed, no result yet" while the API and /readouts said "Terminated per registry"."""
import datetime, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'pdufa_site_src')
WORD = {'TERMINATED': 'Trial terminated per ClinicalTrials.gov', 'WITHDRAWN': 'Trial withdrawn per ClinicalTrials.gov',
        'SUSPENDED': 'Trial suspended per ClinicalTrials.gov'}

def main():
    s = open(os.path.join(SITE, 'api', 'v1', 'dataset.mjs'), encoding='utf-8').read()
    rows = json.loads(s[s.index('['):].rstrip().rstrip(';'))
    bad, n = [], 0
    for r in rows:
        if r.get('type') != 'Readout' or r.get('st') == 'Reported':
            continue
        dd = r.get('_d') or {}
        os_ = str((dd.get('registry') or {}).get('overall_status') or '')
        if os_ not in WORD or dd.get('resolution') or str(r.get('d') or '9999')[:7] >= datetime.date.today().isoformat()[:7]:
            continue
        p = os.path.join(SITE, 'ticker', str(r.get('t') or '').upper(), 'index.html')
        if not os.path.exists(p):
            continue
        n += 1
        if WORD[os_] not in open(p, encoding='utf-8').read():
            bad.append(r['id'])
    if bad:
        print('FAIL -- hub omits the registry status for:', ', '.join(bad)); sys.exit(1)
    print(f'OK -- {n} passed registry-stopped readout row(s) state the registry status on their hub.')

if __name__ == '__main__':
    main()
