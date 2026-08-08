import { describe, it, expect } from 'vitest';
import { newLife } from '../src/state';
import { SaveManager, memoryStorage } from '../src/save/SaveManager';
import { CONFIG } from '../src/config';

describe('SaveManager — persistence round-trip', () => {
  it('returns null when nothing is stored', () => {
    const mgr = new SaveManager(memoryStorage());
    expect(mgr.load()).toBeNull();
  });

  it('saves and reloads an equivalent state', () => {
    const store = memoryStorage();
    const mgr = new SaveManager(store);
    const s = newLife({ now: 12345, seed: 9 });
    s.resources.lore = 33;
    s.log.unshift({ t: 'a line', c: 'good' });

    mgr.save(s);
    const loaded = mgr.load();
    expect(loaded).not.toBeNull();
    expect(loaded!.resources.lore).toBe(33);
    expect(loaded!.keeperName).toBe(s.keeperName);
    expect(loaded!.log[0].t).toBe('a line');
    expect(loaded!.version).toBe(CONFIG.SAVE_VERSION);
  });

  it('clear removes the save', () => {
    const mgr = new SaveManager(memoryStorage());
    mgr.save(newLife({ now: 0, seed: 1 }));
    mgr.clear();
    expect(mgr.load()).toBeNull();
  });

  it('tolerates corrupt data (returns null, no throw)', () => {
    const store = memoryStorage();
    store.setItem(CONFIG.SAVE_KEY, '{not valid json');
    const mgr = new SaveManager(store);
    expect(mgr.load()).toBeNull();
  });
});
