import { describe, it, expect } from 'vitest';
import { newLife, cloneState } from '../src/state';
import { expeditionOdds, runExpedition } from '../src/systems/expedition';
import { rngFromState } from '../src/rng';

function grownExplorer(seed: number) {
  const s = newLife({ now: 0, seed });
  s.stage = 'grown';
  s.flags.treeline = true;
  s.resources.herbs = 20;
  s.rngState = seed; // fix rng for determinism
  return s;
}

describe('ExpeditionSystem — deterministic resolution', () => {
  it('same seed + same state yields identical outcomes', () => {
    const a = grownExplorer(12345);
    const b = cloneState(a);

    runExpedition(a, rngFromState(a.rngState));
    runExpedition(b, rngFromState(b.rngState));

    expect(b.depthCleared).toBe(a.depthCleared);
    expect(b.rot).toBeCloseTo(a.rot, 9);
    expect(b.resources.lore).toBeCloseTo(a.resources.lore, 9);
    expect(b.runesRecovered).toBe(a.runesRecovered);
    expect(b.log[0].t).toBe(a.log[0].t);
  });

  it('always spends the herb cost', () => {
    const s = grownExplorer(1);
    const before = s.resources.herbs;
    runExpedition(s, rngFromState(s.rngState));
    expect(s.resources.herbs).toBeLessThanOrEqual(before - 4);
  });

  it('odds stay within the configured [0.2, 0.85] band', () => {
    const s = grownExplorer(1);
    s.wardStrength = 0;
    s.depthCleared = 0;
    expect(expeditionOdds(s)).toBeGreaterThanOrEqual(0.2);
    s.wardStrength = 100;
    s.depthCleared = 9;
    expect(expeditionOdds(s)).toBeLessThanOrEqual(0.85);
  });

  it('a successful descent clears depth, cuts Rot, and yields lore', () => {
    // find a seed that succeeds (odds ~0.63 here), then assert effects
    let seed = 0;
    let s = grownExplorer(seed);
    while (true) {
      s = grownExplorer(seed);
      const test = cloneState(s);
      runExpedition(test, rngFromState(test.rngState));
      if (test.depthCleared > s.depthCleared) {
        expect(test.rot).toBeLessThan(s.rot);
        expect(test.resources.lore).toBeGreaterThan(s.resources.lore);
        break;
      }
      seed++;
      if (seed > 50) throw new Error('no success seed found');
    }
  });
});
