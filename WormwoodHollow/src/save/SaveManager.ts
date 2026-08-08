/**
 * SaveManager — persistence + save-schema handling.
 *
 * Serializes the whole GameState blob to a storage adapter (localStorage in the
 * browser; an in-memory map in tests / non-DOM environments). Save-versioning is
 * stubbed for M1 (returns as-is); M2 adds real migrations keyed on state.version.
 */
import { CONFIG } from '../config';
import type { GameState } from '../state';

export interface StorageAdapter {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** In-memory adapter for tests / SSR / when Web Storage is unavailable. */
export function memoryStorage(): StorageAdapter {
  const map = new Map<string, string>();
  return {
    getItem: (k) => (map.has(k) ? (map.get(k) as string) : null),
    setItem: (k, v) => void map.set(k, v),
    removeItem: (k) => void map.delete(k),
  };
}

/** localStorage if present and usable, else a memory fallback. */
export function defaultStorage(): StorageAdapter {
  try {
    if (typeof localStorage !== 'undefined') {
      const probe = '__ww_probe__';
      localStorage.setItem(probe, '1');
      localStorage.removeItem(probe);
      return localStorage;
    }
  } catch {
    /* fall through to memory */
  }
  return memoryStorage();
}

/**
 * Migrate a loaded save forward to the current schema. Each version bump backfills
 * the fields it introduced so old saves keep working.
 *
 *  v1 -> v2 : added bossesFelled, ending (M2 content).
 */
export function migrate(state: GameState): GameState {
  const from = state.version ?? 1;

  if (from < 2) {
    if (!state.bossesFelled) state.bossesFelled = {};
    if (state.ending === undefined) state.ending = null;
  }

  state.version = CONFIG.SAVE_VERSION;
  return state;
}

export class SaveManager {
  constructor(
    private storage: StorageAdapter = defaultStorage(),
    private key: string = CONFIG.SAVE_KEY,
  ) {}

  load(): GameState | null {
    try {
      const raw = this.storage.getItem(this.key);
      if (!raw) return null;
      return migrate(JSON.parse(raw) as GameState);
    } catch {
      return null;
    }
  }

  save(state: GameState): void {
    try {
      this.storage.setItem(this.key, JSON.stringify(state));
    } catch {
      /* quota / private mode — non-fatal for an idle game */
    }
  }

  clear(): void {
    try {
      this.storage.removeItem(this.key);
    } catch {
      /* non-fatal */
    }
  }
}
