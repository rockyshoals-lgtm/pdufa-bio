"""Add PRIMARY-SOURCED 2026 conference dates to conf_registry.json.

WHY THIS MATTERS: the conference leg resolves a date ONLY from an observed registry entry.
With no 2026 date it falls back to month precision ("2026-07"), and a month is not tradeable.
AAIC 2026 is a live example: Biogen and ProMIS both announced Alzheimer's data for it, and we
blurred a real July catalyst into "sometime in July" purely because the lookup table was stale.

EVERY date below was read off the organiser's own site or an equivalent primary source and is
cited. Nothing here is projected, inferred, or carried forward from last year's day-of-year.
A conference date we cannot source is LEFT MISSING -- the extractor already degrades to month
precision on its own, and an honest blank beats a confident guess.
"""
import json, sys, datetime as dt
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# conf -> (start_date, source)   -- start day of the main scientific meeting
VERIFIED_2026 = {
    'AAIC':   ('2026-07-12', 'aaic.alz.org — July 12-15 2026, London'),
    'AHA':    ('2026-11-06', 'professional.heart.org — Nov 6-9 2026, Chicago'),
    'SNO':    ('2026-11-12', 'soc-neuro-onc.org — Nov 12-15 2026, Philadelphia'),
    'ASTRO':  ('2026-09-26', 'astro.org — Sept 26-30 2026, Boston'),
}
# already present and INDEPENDENTLY RE-VERIFIED this session:
#   ESMO 2026-10-23  (esmo.org: Oct 23-27, Madrid)          -> registry agrees
#   ASH  2026-12-12  (hematology.org: Dec 12-15, N.Orleans) -> registry agrees

reg = json.load(open('conf_registry.json'))
before = sum(1 for v in reg.values() if '2026' in (v.get('dates') or {}))

added, conflict = [], []
for c, (d, src) in VERIFIED_2026.items():
    if c not in reg:
        reg[c] = {'dates': {}, 'doy': dt.date.fromisoformat(d).timetuple().tm_yday}
    reg[c].setdefault('dates', {})
    cur = reg[c]['dates'].get('2026')
    if cur and cur != d:
        # NEVER silently overwrite. If the registry disagrees with a primary source, that is a
        # finding, not a merge conflict to paper over.
        conflict.append((c, cur, d, src))
        continue
    if cur == d:
        continue
    reg[c]['dates']['2026'] = d
    added.append((c, d, src))

json.dump(reg, open('conf_registry.json', 'w'), indent=1, sort_keys=True)
after = sum(1 for v in reg.values() if '2026' in (v.get('dates') or {}))

print('2026 dates: %d -> %d' % (before, after))
print()
for c, d, s in added:
    print('  + %-8s %s   %s' % (c, d, s))
if conflict:
    print()
    print('  *** REGISTRY DISAGREES WITH A PRIMARY SOURCE — resolve by hand, do not guess ***')
    for c, cur, d, s in conflict:
        print('  ! %-8s registry=%s  source=%s   (%s)' % (c, cur, d, s))

print()
missing = sorted(c for c, v in reg.items() if '2026' not in (v.get('dates') or {}))
print('still WITHOUT a 2026 date (%d) — these degrade to MONTH precision, by design:' % len(missing))
print('   ' + ', '.join(missing))
