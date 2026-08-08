import { describe, it, expect } from 'vitest';
import { newLife } from '../src/state';
import { applyAction } from '../src/core/dispatch';

const env = { now: 1000, seed: 5 };

describe('dispatch.applyAction — gated, pure transitions', () => {
  it('lay salt spends salt and raises the ward', () => {
    const s = newLife({ now: 0, seed: 1 }); // salt 18, ward 70
    const next = applyAction(s, 'salt', env);
    expect(next).not.toBe(s); // new object (pure)
    expect(s.resources.salt).toBe(18); // input untouched
    expect(next.resources.salt).toBe(13);
    expect(next.wardStrength).toBe(84);
  });

  it('refuses when resources are insufficient (can gate)', () => {
    const s = newLife({ now: 0, seed: 1 });
    s.resources.salt = 2;
    const next = applyAction(s, 'salt', env);
    expect(next).toBe(s); // unchanged
  });

  it('refuses actions above the current life-stage (stage gate)', () => {
    const s = newLife({ now: 0, seed: 1 }); // child
    s.resources.iron = 10;
    const next = applyAction(s, 'iron', env); // iron is youth+
    expect(next).toBe(s);
  });

  it('advances the persisted RNG state for random actions', () => {
    const s = newLife({ now: 0, seed: 1 });
    s.stage = 'grown';
    s.flags.treeline = true;
    s.resources.herbs = 20;
    const before = s.rngState;
    const next = applyAction(s, 'expedition', env);
    expect(next.rngState).not.toBe(before);
  });

  it('unknown action id is a no-op', () => {
    const s = newLife({ now: 0, seed: 1 });
    expect(applyAction(s, 'nope', env)).toBe(s);
  });
});
