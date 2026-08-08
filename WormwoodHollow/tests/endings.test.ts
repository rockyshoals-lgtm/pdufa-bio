import { describe, it, expect } from 'vitest';
import { newLife } from '../src/state';
import { CONFIG } from '../src/config';
import { ENDINGS } from '../src/content/endings';
import { applyEnding } from '../src/core/dispatch';

function atRune(lore = 0) {
  const s = newLife({ now: 0, seed: 3 });
  s.runesRecovered = CONFIG.DEPTHS;
  s.depthCleared = CONFIG.DEPTHS;
  s.resources.lore = lore;
  return s;
}

describe('Endings availability + effects', () => {
  it('re-bind and inherit unlock at the master-rune; unmake needs the full name', () => {
    const s = atRune(0);
    const avail = (id: string) => ENDINGS.find((e) => e.id === id)!.available(s);
    expect(avail('rebind')).toBe(true);
    expect(avail('inherit')).toBe(true);
    expect(avail('unmake')).toBe(false);

    const deep = atRune(CONFIG.ENDING_UNMAKE_LORE);
    expect(ENDINGS.find((e) => e.id === 'unmake')!.available(deep)).toBe(true);
  });

  it('is not available before reaching the bottom with nine shards', () => {
    const s = newLife({ now: 0, seed: 1 });
    for (const e of ENDINGS) expect(e.available(s)).toBe(false);
  });

  it('applyEnding(re-bind) wins the run and floods the bloodline with lore', () => {
    const s = atRune(40);
    s.inheritedLore = 5;
    const next = applyEnding(s, 'rebind');
    expect(next).not.toBe(s); // pure
    expect(next.ending).toBe('rebind');
    expect(next.flags.won).toBe(true);
    // 5 + floor(40*0.5) + 9*5 = 5 + 20 + 45 = 70
    expect(next.inheritedLore).toBe(70);
  });

  it('applyEnding(unmake) purges the Rot entirely', () => {
    const s = atRune(CONFIG.ENDING_UNMAKE_LORE);
    s.rot = 80;
    const next = applyEnding(s, 'unmake');
    expect(next.ending).toBe('unmake');
    expect(next.rot).toBe(0);
  });

  it('refuses a locked or unknown ending (no-op)', () => {
    const locked = atRune(0);
    expect(applyEnding(locked, 'unmake')).toBe(locked); // lore gate
    expect(applyEnding(locked, 'nope')).toBe(locked);
    const already = atRune(0);
    const won = applyEnding(already, 'rebind');
    expect(applyEnding(won, 'inherit')).toBe(won); // already ended
  });
});
