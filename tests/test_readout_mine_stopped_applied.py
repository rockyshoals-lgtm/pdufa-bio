"""Guard (2026-11-27): a readout the company STOPPED must not be served as "no topline announced".

The 2026-11-26 readout mine found, and its red team confirmed, that Aardvark terminated the Phase 3 HERO trial of
ARD-101 early (the company's Oct 23, 2026 release). apply_1126_readout_mine.py mapped "stopped" to
"guidance_dropped", and for a passed window that wrote resolution no_topline, so /ticker/AARD and /readouts said
"Window passed, no topline announced" for a trial the company had ended. The apply now writes company_stopped.

Check: every record in odin_cowork_dropbox/*readout_mine*.json with status "stopped", a red-team verdict of
CONFIRMED or FIX and an existing_row_id, whose row is still in the dataset with a passed date and not Reported,
must carry resolution state company_stopped (or sponsor_release, a results release found later). A row can be kept
on purpose by listing its id in _readout_ta_manual.json "stopped_kept" with a reason."""
import datetime as dt, glob, io, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    s = io.open(os.path.join(ROOT, 'pdufa_site_src', 'api', 'v1', 'dataset.mjs'), encoding='utf-8').read()
    rows = {r.get('id'): r for r in json.loads(s[s.index('['):s.rindex(']') + 1])}
    try:
        man = json.load(io.open(os.path.join(ROOT, '_readout_ta_manual.json'), encoding='utf-8'))
        kept = {k.get('id') for k in man.get('stopped_kept', [])}
    except Exception:  # noqa: BLE001
        kept = set()
    today = dt.date.today().isoformat()
    bad, n = [], 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'odin_cowork_dropbox', '*readout_mine*.json'))):
        try:
            d = json.load(io.open(f, encoding='utf-8'))
        except Exception:  # noqa: BLE001
            continue
        recs = d.get('rows', []) if isinstance(d, dict) else d
        for rec in recs if isinstance(recs, list) else []:
            if not isinstance(rec, dict) or rec.get('status') != 'stopped':
                continue
            if rec.get('rt_verdict') not in ('CONFIRMED', 'FIX'):
                continue
            rid = rec.get('existing_row_id')
            r = rows.get(rid)
            if not r or rid in kept or r.get('type') != 'Readout' or r.get('st') == 'Reported':
                continue
            if str(r.get('d') or '') >= today:
                continue
            n += 1
            state = ((r.get('_d') or {}).get('resolution') or {}).get('state')
            if state not in ('company_stopped', 'sponsor_release'):
                bad.append(f'{rid} ({os.path.basename(f)}): resolution {state!r}')
    if bad:
        print('FAIL -- the readout mine found these trials stopped by the company (red-team confirmed), but the '
              'site serves them as something else. Set _d.resolution to company_stopped with the company\'s date, '
              'link and words, or list the id in _readout_ta_manual.json "stopped_kept" with a reason:')
        for b in bad:
            print('  ' + b)
        sys.exit(1)
    print(f'OK -- {n} passed readout row(s) the mine found stopped; each is served as stopped by the company.')


if __name__ == '__main__':
    main()
