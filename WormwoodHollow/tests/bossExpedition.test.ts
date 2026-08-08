import { describe, it, expect } from 'vitest';
import { newLife, cloneState } from '../src/state';
import { runExpedition } from '../src/systems/expedition';
import { rngFromState } from '../src/rng';
import { CONFIG } from '../src/config';

function explorer(seed: number, depthCleared: number) {
  const s = newLife({ now: 0, seed });
  s.stage = 'grown';
  s.flags.treeline = true;
  s.resources.herbs = 40;
  s.wardStrength = 100; // best odds
  s.depthCleared = depthCleared;
  s.rngState = seed;
  return s;
}

describe('Boss encounters', () => {
  it('a won boss descent fells the Lord and guarantees a rune', () => {
    // target depth 3 = Brother Ezekiel
    for (let seed = 0; seed < 100; seed++) {
      const s = explorer(seed, 2);
      const test = cloneState(s);
      const out = runExpedition(test, rngFromState(test.rngState));
      if (out.success) {
        expect(out.bossId).toBe('ezekiel');
        expect(test.bossesFelled.ezekiel).toBe(true);
        expect(test.runesRecovered).toBe(1);
        expect(test.depthCleared).toBe(3);
        return;
      }
    }
    throw new Error('no winning seed vs boss found');
  });

  it('a failed boss descent costs extra Rot and no depth', () => {
    for (let seed = 0; seed < 100; seed++) {
      const s = explorer(seed, 2);
      const test = cloneState(s);
      const out = runExpedition(test, rngFromState(test.rngState));
      if (!out.success) {
        expect(out.bossId).toBe('ezekiel');
        expect(test.depthCleared).toBe(2);
        expect(test.rot).toBeGreaterThan(s.rot);
        return;
      }
    }
    throw new Error('no losing seed vs boss found');
  });
});

describe('Deep patrol at the bottom', () => {
  it('does not increase depth past the maximum and can still find shards', () => {
    let sawRune = false;
    for (let seed = 0; seed < 60; seed++) {
      const s = explorer(seed, CONFIG.DEPTHS); // already at bottom
      s.runesRecovered = 0;
      const out = runExpedition(s, rngFromState(s.rngState));
      expect(out.deepPatrol).toBe(true);
      expect(s.depthCleared).toBe(CONFIG.DEPTHS); // never exceeds
      if (out.gotRune) sawRune = true;
    }
    expect(sawRune).toBe(true);
  });
});
