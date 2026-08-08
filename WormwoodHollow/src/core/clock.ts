/**
 * Clock — all wall-clock math lives here (with SaveManager). Never trust the system
 * clock without clamping: offline elapsed is capped at OFFLINE_CAP_DAYS and guarded
 * against clock rollback (negative elapsed) so a user can't cheat by changing time.
 */
import { CONFIG } from '../config';

export interface Elapsed {
  elapsedSec: number; // real seconds since lastSeen (clamped ≥ 0)
  rawDays: number; // uncapped in-game days
  days: number; // capped in-game days actually applied
  capped: boolean; // true if rawDays exceeded the offline cap
}

/** Convert a lastSeen/now pair into capped in-game days elapsed. */
export function computeElapsed(lastSeen: number, now: number): Elapsed {
  const elapsedSec = Math.max(0, (now - lastSeen) / 1000);
  const rawDays = elapsedSec * CONFIG.DAY_PER_REAL_SEC;
  const days = Math.min(rawDays, CONFIG.OFFLINE_CAP_DAYS);
  return { elapsedSec, rawDays, days, capped: rawDays > CONFIG.OFFLINE_CAP_DAYS };
}

/** In-game days for a live tick delta (uncapped; short intervals). */
export function tickDays(lastTick: number, now: number): number {
  return Math.max(0, (now - lastTick) / 1000) * CONFIG.DAY_PER_REAL_SEC;
}
