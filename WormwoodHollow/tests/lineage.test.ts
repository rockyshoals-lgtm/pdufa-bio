import { describe, it, expect } from 'vitest';
import { newLife, loreMult } from '../src/state';
import { carryoverLore, passSalt } from '../src/systems/lineage';

function keeper() {
  const s = newLife({ now: 500, seed: 7 });
  s.resources.lore = 40;
  s.runesRecovered = 2;
  s.inheritedLore = 5;
  s.depthCleared = 4;
  s.generation = 1;
  s.rot = 60;
  return s;
}

describe('LineageSystem — generational prestige', () => {
  it('carries floor(lore*rate)+runes forward on a chosen pass', () => {
    const s = keeper();
    // floor(40*0.25) + 2 = 12
    expect(carryoverLore(s, false)).toBe(12);
  });

  it('penalizes a forced fall by one and never goes negative', () => {
    const s = keeper();
    expect(carryoverLore(s, true)).toBe(11);
    const broke = newLife({ now: 0, seed: 1 }); // 0 lore, 0 runes
    expect(carryoverLore(broke, true)).toBe(0);
  });

  it('produces a stronger next generation with inherited lore + kept depth', () => {
    const s = keeper();
    const { state: child, carried } = passSalt(s, { forced: false, now: 900, seed: 99 });

    expect(carried).toBe(12);
    expect(child.generation).toBe(2);
    expect(child.inheritedLore).toBe(5 + 12); // 17
    expect(child.depthCleared).toBe(2); // floor(4 * 0.5)
    expect(child.bloodlineName).toBe(s.bloodlineName); // same line
    expect(child.stage).toBe('child');
    expect(child.ageDays).toBe(0);
    expect(loreMult(child)).toBeCloseTo(1 + 17 * 0.02, 6); // 1.34
    expect(child.log[0].t).toContain('The salt passes to');
  });
});
