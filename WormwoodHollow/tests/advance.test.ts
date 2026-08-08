import { describe, it, expect } from 'vitest';
import { newLife } from '../src/state';
import { advanceDays } from '../src/core/advance';
import { computeElapsed } from '../src/core/clock';
import { CONFIG } from '../src/config';

const base = () => newLife({ now: 1_000_000, seed: 42 });

describe('advanceDays — closed-form time math', () => {
  it('is a no-op for zero or negative days', () => {
    const s = base();
    const { state, report } = advanceDays(s, 0);
    expect(state.wardStrength).toBe(s.wardStrength);
    expect(state.rot).toBe(s.rot);
    expect(report.rotGain).toBe(0);
    expect(report.wardLoss).toBe(0);
  });

  it('does not mutate the input state (pure)', () => {
    const s = base();
    const wardBefore = s.wardStrength;
    advanceDays(s, 10);
    expect(s.wardStrength).toBe(wardBefore);
  });

  it('decays ward, creeps Rot against the decayed ward, accrues harvest, ages', () => {
    const s = base(); // ward 70, rot 8, depth 0, prod salt .45/herbs .4/lore .12
    const { state, report } = advanceDays(s, 10);

    // ward: 70 - 3*10 = 40
    expect(state.wardStrength).toBeCloseTo(40, 6);
    expect(report.wardLoss).toBeCloseTo(30, 6);

    // rot: gap=0.6, pressure=1 -> 2.4*0.6*10 = 14.4 ; 8 + 14.4 = 22.4
    expect(report.rotGain).toBeCloseTo(14.4, 6);
    expect(state.rot).toBeCloseTo(22.4, 6);

    // harvest (loreMult = 1)
    expect(report.harvest.salt).toBeCloseTo(4.5, 6);
    expect(report.harvest.herbs).toBeCloseTo(4.0, 6);
    expect(report.harvest.lore).toBeCloseTo(1.2, 6);
    expect(report.harvest.iron).toBeCloseTo(0, 6);

    expect(state.ageDays).toBeCloseTo(10, 6);
  });

  it('applies the bloodline lore multiplier to harvest', () => {
    const s = base();
    s.inheritedLore = 50; // loreMult = 1 + 50*0.02 = 2.0
    const { report } = advanceDays(s, 10);
    expect(report.harvest.salt).toBeCloseTo(9.0, 6); // 0.45*10*2
  });

  it('clamps rot to 100 and ward to 0 over a long span', () => {
    const s = base();
    const { state } = advanceDays(s, 10_000);
    expect(state.wardStrength).toBe(0);
    expect(state.rot).toBe(100);
  });

  it('depth pressure accelerates Rot the deeper you have dug', () => {
    const shallow = base();
    const deep = base();
    deep.depthCleared = 9; // pressure 1 + 9*0.15 = 2.35
    const g0 = advanceDays(shallow, 5).report.rotGain;
    const g9 = advanceDays(deep, 5).report.rotGain;
    expect(g9).toBeCloseTo(g0 * 2.35, 6);
  });
});

describe('computeElapsed — offline catch-up cap + rollback guard', () => {
  it('converts real seconds to in-game days', () => {
    const now = 1_000_000;
    const el = computeElapsed(now - 10_000, now); // 10s
    expect(el.elapsedSec).toBeCloseTo(10, 6);
    expect(el.rawDays).toBeCloseTo(10 * CONFIG.DAY_PER_REAL_SEC, 6);
    expect(el.capped).toBe(false);
  });

  it('caps at OFFLINE_CAP_DAYS when away a long time', () => {
    const now = 5_000_000;
    const el = computeElapsed(0, now); // huge span
    expect(el.days).toBe(CONFIG.OFFLINE_CAP_DAYS);
    expect(el.capped).toBe(true);
  });

  it('guards against clock rollback (negative elapsed -> 0)', () => {
    const now = 1_000_000;
    const el = computeElapsed(now + 60_000, now); // lastSeen in the future
    expect(el.elapsedSec).toBe(0);
    expect(el.days).toBe(0);
    expect(el.capped).toBe(false);
  });
});
