/**
 * LifeSystem — the keeper ages through life-stages, which gate available actions.
 *
 * Total in-game days lived determines the stage. A transition is a flavor beat and
 * unlocks new work (see content/actions stage gating).
 */
import { CONFIG } from '../config';
import type { GameState, LifeStage } from '../state';

/** The life-stage a keeper of the given age belongs to. */
export function stageForAge(ageDays: number): LifeStage {
  const t = CONFIG.STAGE_DAYS;
  if (ageDays >= t.keeper) return 'keeper';
  if (ageDays >= t.grown) return 'grown';
  if (ageDays >= t.youth) return 'youth';
  return 'child';
}

/**
 * Recompute the keeper's stage from their age. Mutates the working copy and returns
 * the new stage if it changed (so the caller can fire flavor), else null.
 */
export function updateStage(s: GameState): LifeStage | null {
  const ns = stageForAge(s.ageDays);
  if (ns !== s.stage) {
    s.stage = ns;
    return ns;
  }
  return null;
}
