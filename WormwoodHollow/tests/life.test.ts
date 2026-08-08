import { describe, it, expect } from 'vitest';
import { stageForAge, updateStage } from '../src/systems/life';
import { newLife } from '../src/state';

describe('LifeSystem — stage thresholds', () => {
  it('maps age to the correct life-stage at each boundary', () => {
    expect(stageForAge(0)).toBe('child');
    expect(stageForAge(19)).toBe('child');
    expect(stageForAge(20)).toBe('youth');
    expect(stageForAge(49)).toBe('youth');
    expect(stageForAge(50)).toBe('grown');
    expect(stageForAge(99)).toBe('grown');
    expect(stageForAge(100)).toBe('keeper');
    expect(stageForAge(999)).toBe('keeper');
  });

  it('updateStage returns the new stage on transition, null otherwise', () => {
    const s = newLife({ now: 0, seed: 1 });
    expect(updateStage(s)).toBeNull(); // still child at age 0
    s.ageDays = 25;
    expect(updateStage(s)).toBe('youth');
    expect(s.stage).toBe('youth');
    expect(updateStage(s)).toBeNull(); // no re-fire
  });
});
