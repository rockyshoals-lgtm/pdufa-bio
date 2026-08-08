/**
 * ResourceSystem — salt, iron, herbs, lore accrue from queued work over in-game days.
 *
 * Production is per-day and scaled by the bloodline lore multiplier. This is the
 * "harvest" half of Come Morning — the same math runs live and offline.
 */
import { loreMult, RESOURCES, type GameState, type Resource } from '../state';

export type Harvest = Record<Resource, number>;

export function emptyHarvest(): Harvest {
  return { salt: 0, iron: 0, herbs: 0, lore: 0 };
}

/**
 * Accrue production over `days` into the (mutable working-copy) state.
 * Returns the amount gained per resource for reporting.
 */
export function accrueForDays(s: GameState, days: number): Harvest {
  const m = loreMult(s);
  const harvest = emptyHarvest();
  for (const k of RESOURCES) {
    const add = s.production[k] * days * m;
    s.resources[k] += add;
    harvest[k] = add;
  }
  return harvest;
}
