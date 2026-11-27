"""Guard (2026-11-27): an Estimated readout row must name a drug that is in the trial its date comes from.

An Estimated row's date is the registry's primary-completion window for one ClinicalTrials.gov record. When the
row's drug is not that record's drug, the site dates the wrong drug: /ticker/OGN listed "Elonva" with the
completion date of PHERFLOT, an academic gastric-cancer trial of pembrolizumab; /ticker/AXSM listed AXS-14 with an
AXS-05 neuroimaging study; Werewolf, Lantern, Cellectar, Aclaris, Cullinan, Legend, Iovance and Wave rows named one
drug and carried another drug's trial. After the window passed, each was served "no topline found" for a drug that
was never in the trial. _readout_ta_manual.json "nct_mismatch" had listed several of these since 2026-10 without
taking them off the site.

Check: for every Estimated readout row with registry titles (_d.nct_id.title / brief_title), some code or name
token of the row's name (4+ characters, punctuation and spaces ignored) must appear in a title. Synonyms the titles
don't spell (a code name for a brand, e.g. CM4620 = Auxora) are listed in _readout_ta_manual.json
"trial_name_ok" with the name the registry uses ("title_name", which must appear in a title) or, where the titles
name no drug at all, a "basis" saying where the drug was read."""
import io, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP = set('with plus combination monotherapy phase study trial dose high cell cells therapy oral tablet tablets '
           'injection topical pediatric adult adults patients treatment versus alfa alpha beta human recombinant '
           'subcutaneous intravenous'.split())


def compact(s):
    return re.sub(r'[^a-z0-9]', '', str(s or '').lower())


def name_tokens(name):
    out = set()
    for w in re.findall(r'[A-Za-z0-9]+(?:[- ][0-9]+)?', str(name or '').replace('®', '').replace('™', '')):
        c = compact(w)
        if len(c) >= 4 and c not in STOP:
            out.add(c)
    return out


def main():
    s = io.open(os.path.join(ROOT, 'pdufa_site_src', 'api', 'v1', 'dataset.mjs'), encoding='utf-8').read()
    rows = json.loads(s[s.index('['):s.rindex(']') + 1])
    man = json.load(io.open(os.path.join(ROOT, '_readout_ta_manual.json'), encoding='utf-8'))
    ok = {e['id']: e for e in man.get('trial_name_ok', [])}
    bad, n = [], 0
    for r in rows:
        if r.get('type') != 'Readout' or r.get('st') != 'Estimated':
            continue
        raw = (r.get('_d') or {}).get('nct_id')
        blk = raw if isinstance(raw, dict) else {'nct': raw}
        titles = ' '.join(t for t in (blk.get('title'), blk.get('brief_title')) if t)
        if not titles:
            continue
        n += 1
        ct = compact(titles)
        if any(t in ct for t in name_tokens(r.get('name'))):
            continue
        e = ok.get(r['id'])
        if e and str(e.get('basis') or '').strip() and (not e.get('title_name') or compact(e['title_name']) in ct):
            continue
        why = 'listed in trial_name_ok, but its title_name is not in the registry title' if e else \
              'no name token of the row is in the registry title'
        bad.append(f"{r['id']} ({blk.get('nct')}): row \"{str(r.get('name'))[:50]}\" vs trial \"{titles[:90]}\": {why}")
    for e in ok.values():
        if not str(e.get('basis') or '').strip():
            bad.append(f"trial_name_ok {e.get('id')}: no basis")
    if bad:
        print('FAIL -- Estimated readout rows dated by a trial of a different drug. Retire the row, rename it to the '
              'trial\'s drug, or list a true synonym in _readout_ta_manual.json "trial_name_ok":')
        for b in bad:
            print('  ' + b)
        sys.exit(1)
    print(f'OK -- {n} Estimated readout row(s); each names a drug that is in the trial it is dated by.')


if __name__ == '__main__':
    main()
