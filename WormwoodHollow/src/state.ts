/**
 * Game state model + pure factory helpers.
 *
 * GameState is the single serialized blob (see save/SaveManager). Everything the
 * game persists lives here. State transitions are pure functions in systems/ and
 * core/ — views never mutate this directly.
 */
import { CONFIG } from './config';
import { makeRng, pick } from './rng';
import { NAMES, KIN } from './content/names';

export type Resource = 'salt' | 'iron' | 'herbs' | 'lore';
export type LifeStage = 'child' | 'youth' | 'grown' | 'keeper';

export const RESOURCES: readonly Resource[] = ['salt', 'iron', 'herbs', 'lore'];

export interface LogEntry {
  t: string;
  c: string; // css class: '', 'good', 'bad', 'whisper'
}

export interface GameState {
  version: number;
  lastSeen: number; // epoch ms, for offline catch-up
  createdAt: number;

  // Keeper (current life)
  keeperName: string;
  ageDays: number;
  stage: LifeStage;

  // Bloodline (persists across generations)
  generation: number;
  inheritedLore: number;
  bloodlineName: string;

  // The Hollow
  rot: number; // 0..100
  wardStrength: number; // 0..100
  depthCleared: number; // 0..9

  // Resources
  resources: Record<Resource, number>;
  production: Record<Resource, number>; // per in-game day

  // Progress
  runesRecovered: number; // 0..9
  bossesFelled: Record<string, boolean>; // boss id -> defeated this life
  ending: string | null; // chosen ending id once the master-rune is reached
  flags: Record<string, boolean>;
  log: LogEntry[];

  // Determinism
  rngState: number;
}

/** Carryover passed from a dying keeper to the next child. */
export interface Carryover {
  inheritedLore: number;
  bloodlineName: string;
  generation: number;
  depthCleared: number;
  createdAt: number;
  rot: number;
}

export interface NewLifeOptions {
  now: number;
  seed: number;
  prev?: Carryover;
}

export const clamp = (x: number, a: number, b: number): number =>
  Math.max(a, Math.min(b, x));

/** Round to one decimal place (display helper). */
export const round1 = (x: number): number => Math.round(x * 10) / 10;

/** Permanent production multiplier from accumulated bloodline lore. */
export function loreMult(s: GameState): number {
  return 1 + s.inheritedLore * CONFIG.LORE_MULT;
}

/** Create a fresh keeper life. If `prev` is given, inherit bloodline carryover. */
export function newLife(opts: NewLifeOptions): GameState {
  const { now, seed, prev } = opts;
  const rng = makeRng(seed);
  return {
    version: CONFIG.SAVE_VERSION,
    lastSeen: now,
    createdAt: prev ? prev.createdAt : now,
    keeperName: pick(rng, NAMES),
    bloodlineName: prev ? prev.bloodlineName : pick(rng, KIN),
    ageDays: 0,
    stage: 'child',
    generation: prev ? prev.generation : 1,
    inheritedLore: prev ? prev.inheritedLore : 0,
    rot: prev ? clamp(prev.rot * 0.5 + 8, 6, 40) : 8,
    wardStrength: 70,
    depthCleared: prev ? Math.floor(prev.depthCleared * CONFIG.DEPTH_KEEP) : 0,
    resources: { salt: 18, iron: prev ? 2 : 0, herbs: 6, lore: 0 },
    production: { salt: 0.45, iron: 0, herbs: 0.4, lore: 0.12 },
    runesRecovered: 0,
    bossesFelled: {},
    ending: null,
    flags: {},
    log: [],
    rngState: rng.state,
  };
}

/** Deep clone for pure transitions (idle cadence makes this cheap). */
export function cloneState(s: GameState): GameState {
  return {
    ...s,
    resources: { ...s.resources },
    production: { ...s.production },
    bossesFelled: { ...s.bossesFelled },
    flags: { ...s.flags },
    log: s.log.map((e) => ({ ...e })),
  };
}

/** Prepend a log line (newest first), capped at 40 entries. Mutates the passed state. */
export function logLine(s: GameState, text: string, cls = ''): void {
  s.log.unshift({ t: text, c: cls });
  if (s.log.length > 40) s.log.length = 40;
}
