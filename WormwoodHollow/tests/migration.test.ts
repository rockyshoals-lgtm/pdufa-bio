import { describe, it, expect } from 'vitest';
import { CONFIG } from '../src/config';
import { migrate, SaveManager, memoryStorage } from '../src/save/SaveManager';
import type { GameState } from '../src/state';

/** A minimal v1-shaped save (pre-M2: no bossesFelled / ending). */
function v1Save(): Record<string, unknown> {
  return {
    version: 1,
    lastSeen: 1000,
    createdAt: 1000,
    keeperName: 'Wren',
    bloodlineName: 'Bledsoe',
    ageDays: 12,
    stage: 'child',
    generation: 1,
    inheritedLore: 0,
    rot: 8,
    wardStrength: 70,
    depthCleared: 0,
    resources: { salt: 18, iron: 0, herbs: 6, lore: 0 },
    production: { salt: 0.45, iron: 0, herbs: 0.4, lore: 0.12 },
    runesRecovered: 0,
    flags: {},
    log: [],
    rngState: 123,
  };
}

describe('Save migration v1 -> v2', () => {
  it('backfills bossesFelled and ending, bumps version', () => {
    const migrated = migrate(v1Save() as unknown as GameState);
    expect(migrated.version).toBe(CONFIG.SAVE_VERSION);
    expect(migrated.bossesFelled).toEqual({});
    expect(migrated.ending).toBeNull();
    // existing data preserved
    expect(migrated.keeperName).toBe('Wren');
    expect(migrated.ageDays).toBe(12);
  });

  it('SaveManager.load migrates an on-disk v1 save', () => {
    const store = memoryStorage();
    store.setItem(CONFIG.SAVE_KEY, JSON.stringify(v1Save()));
    const loaded = new SaveManager(store).load();
    expect(loaded).not.toBeNull();
    expect(loaded!.version).toBe(CONFIG.SAVE_VERSION);
    expect(loaded!.bossesFelled).toEqual({});
    expect(loaded!.ending).toBeNull();
  });
});
