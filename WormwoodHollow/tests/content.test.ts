import { describe, it, expect } from 'vitest';
import { CONFIG } from '../src/config';
import { DEPTHS, depthAt, bossForDepth } from '../src/content/depths';
import { BOSSES, bossAtDepth } from '../src/content/bosses';
import { WHISPERS, whisperByRot } from '../src/content/flavor';
import { makeRng } from '../src/rng';
import { PROLOGUE } from '../src/content/prologue';

describe('Depths data integrity', () => {
  it('has exactly CONFIG.DEPTHS depths, levels 1..N, unique', () => {
    expect(DEPTHS.length).toBe(CONFIG.DEPTHS);
    const levels = DEPTHS.map((d) => d.level);
    expect(levels).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
    expect(new Set(DEPTHS.map((d) => d.name)).size).toBe(DEPTHS.length);
    for (const d of DEPTHS) expect(d.hazard.length).toBeGreaterThan(10);
  });

  it('depthAt resolves by level', () => {
    expect(depthAt(9)?.name).toBe('The Bottom of the World');
    expect(depthAt(99)).toBeUndefined();
  });
});

describe('Boss data integrity', () => {
  it('has 4 Lords, each at a distinct real depth, none at the ritual floor (9)', () => {
    expect(BOSSES.length).toBe(4);
    const depths = BOSSES.map((b) => b.depth);
    expect(new Set(depths).size).toBe(4);
    for (const d of depths) {
      expect(d).toBeGreaterThanOrEqual(1);
      expect(d).toBeLessThan(CONFIG.DEPTHS); // bottom is the rite, not a boss
      expect(depthAt(d)).toBeDefined();
    }
  });

  it('bossAtDepth / bossForDepth agree and map known Lords', () => {
    expect(bossAtDepth(3)?.id).toBe('ezekiel');
    expect(bossForDepth(5)?.id).toBe('bledsoe');
    expect(bossAtDepth(1)).toBeUndefined();
  });

  it('every boss has taunt/defeat/repel flavor', () => {
    for (const b of BOSSES) {
      expect(b.taunt.length).toBeGreaterThan(10);
      expect(b.defeat.length).toBeGreaterThan(10);
      expect(b.repel.length).toBeGreaterThan(10);
    }
  });
});

describe('Old Gnaw whisper tiers scale with Rot', () => {
  it('picks from the tier matching the Rot level', () => {
    const rng = makeRng(1);
    expect(WHISPERS.low).toContain(whisperByRot(makeRng(1), 50));
    expect(WHISPERS.mid).toContain(whisperByRot(makeRng(2), 75));
    expect(WHISPERS.high).toContain(whisperByRot(makeRng(3), 90));
    void rng;
  });
});

describe('Prologue', () => {
  it('ends on the premise line', () => {
    expect(PROLOGUE.length).toBeGreaterThan(3);
    expect(PROLOGUE[PROLOGUE.length - 1].text).toBe('The salt is not for luck.');
  });
});
