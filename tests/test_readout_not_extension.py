"""Guard (2026-11-27): an Estimated readout row (a ClinicalTrials.gov primary-completion window, not a company
statement) must not point at a standalone extension study: an open-label extension, roll-over or long-term safety study.
phase_readout_miner.is_catalyst() has refused extension studies since 2026-10-11, but rows added before then
stayed: /readouts listed "Seralutinib, Dec 2026" for Gossamer's
PROSERA-EXT extension, whose treatment period runs "until the market approval of seralutinib", and 12 more
safety extensions or long-term safety studies (Corcept, Insmed, BeOne, Ionis x2, MBX, Supernus, Madrigal, Sanofi,
PTC, plus Gossamer's and Jasper's terminated ones) were dated as readouts. An extension PERIOD inside a
randomized trial is not flagged (phase_readout_miner.is_extension_study cuts it out first).

Titles come from the row itself (_d.nct_id.title / brief_title, written by refresh_readout_registry.py from the
registry on every rebuild), falling back to readout_audit/readout_ncts.json. Company-guided rows are not checked:
their date is the company's statement, not the registry's. A row can be kept on purpose by listing its id in
_readout_ta_manual.json "extension_kept" with a reason."""
import importlib.util, io, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rule():
    spec = importlib.util.spec_from_file_location('phase_readout_miner', os.path.join(ROOT, 'phase_readout_miner.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    rule = _rule()
    s = io.open(os.path.join(ROOT, 'pdufa_site_src', 'api', 'v1', 'dataset.mjs'), encoding='utf-8').read()
    rows = json.loads(s[s.index('['):s.rindex(']') + 1])
    try:
        snips = json.load(io.open(os.path.join(ROOT, 'readout_audit', 'readout_ncts.json'), encoding='utf-8'))
    except Exception:  # noqa: BLE001
        snips = {}
    try:
        man = json.load(io.open(os.path.join(ROOT, '_readout_ta_manual.json'), encoding='utf-8'))
        kept = {k.get('id') for k in man.get('extension_kept', [])}
    except Exception:  # noqa: BLE001
        kept = set()
    bad, n = [], 0
    for r in rows:
        if r.get('type') != 'Readout' or r.get('st') != 'Estimated' or r.get('id') in kept:
            continue
        raw = (r.get('_d') or {}).get('nct_id')
        blk = raw if isinstance(raw, dict) else {'nct': raw}
        nct = str(blk.get('nct') or '')
        titles = [blk.get('title'), blk.get('brief_title')]
        if not any(titles):
            titles = [str((snips.get(nct) or {}).get('snip') or '').split('|', 1)[-1]]
        titles = [t for t in titles if t]
        if not titles:
            continue
        n += 1
        hit = next((t for t in titles if rule.is_extension_study(t)), None)
        if hit:
            bad.append(f"{r['id']} ({nct}): \"{hit[:120]}\"")
    if bad:
        print('FAIL -- Estimated readout rows point at extension / long-term safety studies, which are not topline '
              'readouts. Retire the row, or list it in _readout_ta_manual.json "extension_kept" with a reason:')
        for b in bad:
            print('  ' + b)
        sys.exit(1)
    print(f'OK -- {n} Estimated readout row(s) with a registry title; none is an extension or long-term safety study.')


if __name__ == '__main__':
    main()
