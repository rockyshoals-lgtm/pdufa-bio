/**
 * LineageSystem — generational prestige. On death/age-out (or a forced fall) the
 * keeper passes the salt to the next child; the bloodline inherits a fraction of
 * lore plus recovered runes, and keeps part of the cleared depth. The new keeper
 * starts permanently stronger via loreMult.
 */
import { CONFIG } from '../config';
import { logLine, newLife, type Carryover, type GameState } from '../state';

export interface PassSaltOptions {
  forced: boolean; // true when the hollow fell (rot maxed) rather than a chosen pass
  now: number;
  seed: number;
}

export interface PassSaltResult {
  state: GameState;
  carried: number;
}

/** Compute lore carried forward to the bloodline (never negative). */
export function carryoverLore(s: GameState, forced: boolean): number {
  const gain =
    Math.floor(s.resources.lore * CONFIG.INHERIT_RATE) +
    s.runesRecovered -
    (forced ? 1 : 0);
  return Math.max(0, gain);
}

/** End the current keeper's life and begin the next generation. Pure. */
export function passSalt(s: GameState, opts: PassSaltOptions): PassSaltResult {
  const carried = carryoverLore(s, opts.forced);
  const prev: Carryover = {
    inheritedLore: s.inheritedLore + carried,
    bloodlineName: s.bloodlineName,
    generation: s.generation + 1,
    depthCleared: s.depthCleared,
    createdAt: s.createdAt,
    rot: s.rot,
  };
  const child = newLife({ now: opts.now, seed: opts.seed, prev });
  logLine(
    child,
    `The salt passes to ${child.keeperName} ${child.bloodlineName}, Gen ${child.generation}. ` +
      `Your line carries ${carried} lore forward, and a little more of the true name.`,
    opts.forced ? 'bad' : 'good',
  );
  return { state: child, carried };
}
