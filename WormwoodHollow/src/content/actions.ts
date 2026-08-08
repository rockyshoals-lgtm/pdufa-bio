/**
 * ActionSystem content — the "Ways & Works" the keeper can perform, gated by
 * life-stage. Each action is a pure transition over a working-copy state; the
 * dispatcher (core/actions.applyAction) handles cloning, RNG, and post-processing.
 *
 * Convention: an action mutates the passed state and returns it, OR returns a brand
 * new state (only "Pass the salt", which begins a new keeper).
 */
import { CONFIG } from '../config';
import { clamp, logLine, type GameState, type LifeStage } from '../state';
import type { Rng } from '../rng';
import { runExpedition } from '../systems/expedition';
import { passSalt } from '../systems/lineage';

export interface ActionContext {
  rng: Rng;
  now: number;
  seed: number;
}

export interface Action {
  id: string;
  label: string;
  cost: string;
  stages: readonly LifeStage[];
  danger?: boolean;
  rite?: boolean;
  can(s: GameState): boolean;
  run(s: GameState, ctx: ActionContext): GameState;
}

const ALL: readonly LifeStage[] = ['child', 'youth', 'grown', 'keeper'];
const FROM_YOUTH: readonly LifeStage[] = ['youth', 'grown', 'keeper'];
const FROM_GROWN: readonly LifeStage[] = ['grown', 'keeper'];

export const ACTIONS: readonly Action[] = [
  {
    id: 'salt',
    label: 'Lay the salt line',
    cost: `${CONFIG.SALT_PER_LAY} salt`,
    stages: ALL,
    can: (s) => s.resources.salt >= CONFIG.SALT_PER_LAY,
    run: (s) => {
      s.resources.salt -= CONFIG.SALT_PER_LAY;
      s.wardStrength = clamp(s.wardStrength + CONFIG.WARD_PER_LAY, 0, 100);
      logLine(s, "A finger's width, all the way 'round. The white line holds the dark at the sill.", 'good');
      return s;
    },
  },
  {
    id: 'draw',
    label: 'Draw salt from the lick',
    cost: '+salt',
    stages: ALL,
    can: () => true,
    run: (s) => {
      s.resources.salt += CONFIG.DRAW_SALT_GAIN;
      s.production.salt += CONFIG.DRAW_SALT_PROD;
      logLine(s, 'You haul brine up from the salt-lick and set it to boil.');
      return s;
    },
  },
  {
    id: 'forage',
    label: 'Forage the near woods',
    cost: '+herbs',
    stages: ALL,
    can: () => true,
    run: (s) => {
      s.resources.herbs += CONFIG.FORAGE_HERB_GAIN;
      s.production.herbs += CONFIG.FORAGE_HERB_PROD;
      logLine(s, 'Mullein, bloodroot, wormwood. The yarb-basket fills.');
      return s;
    },
  },
  {
    id: 'smelt',
    label: 'Smelt iron at the forge',
    cost: '+iron',
    stages: FROM_YOUTH,
    can: () => true,
    run: (s) => {
      s.resources.iron += CONFIG.SMELT_IRON_GAIN;
      s.production.iron += CONFIG.SMELT_IRON_PROD;
      logLine(s, 'Iron over the door, points-up. The old cold metal hates what comes.');
      return s;
    },
  },
  {
    id: 'iron',
    label: 'Hang iron & silver',
    cost: `${CONFIG.IRON_PER_HANG} iron`,
    stages: FROM_YOUTH,
    can: (s) => s.resources.iron >= CONFIG.IRON_PER_HANG,
    run: (s) => {
      s.resources.iron -= CONFIG.IRON_PER_HANG;
      s.wardStrength = clamp(s.wardStrength + CONFIG.WARD_PER_HANG, 0, 100);
      logLine(s, 'Iron and silver at every threshold. The ward stands stronger than salt alone.', 'good');
      return s;
    },
  },
  {
    id: 'study',
    label: 'Study the remedy-book',
    cost: '+lore',
    stages: ALL,
    can: () => true,
    run: (s) => {
      const g = s.stage === 'child' ? 1 : 2;
      s.resources.lore += g;
      s.production.lore += CONFIG.STUDY_LORE_PROD;
      logLine(s, 'Charms and cures, and stranger letters in the margins no preacher can read.');
      return s;
    },
  },
  {
    id: 'treeline',
    label: 'Cross the treeline',
    cost: 'one-time',
    stages: FROM_YOUTH,
    can: (s) => !s.flags.treeline,
    run: (s) => {
      s.flags.treeline = true;
      s.rot = clamp(s.rot + CONFIG.TREELINE_ROT, 0, 100);
      logLine(s, "You went past where you're allowed. Something out there knew your name — and now the line is thinner for it.", 'bad');
      return s;
    },
  },
  {
    id: 'expedition',
    label: 'Descend into the caves',
    cost: `${CONFIG.EXPEDITION_HERB_COST} herbs`,
    stages: FROM_GROWN,
    can: (s) => !!s.flags.treeline && s.resources.herbs >= CONFIG.EXPEDITION_HERB_COST,
    run: (s, ctx) => {
      runExpedition(s, ctx.rng);
      return s;
    },
  },
  {
    id: 'pass',
    label: 'Pass the salt to the next child',
    cost: 'prestige',
    stages: ['keeper'],
    danger: true,
    can: () => true,
    run: (s, ctx) => passSalt(s, { forced: false, now: ctx.now, seed: ctx.seed }).state,
  },
];

export function actionById(id: string): Action | undefined {
  return ACTIONS.find((a) => a.id === id);
}

/** Actions available to the keeper right now (stage-gated + treeline once). */
export function availableActions(s: GameState): Action[] {
  return ACTIONS.filter((a) => {
    if (!a.stages.includes(s.stage)) return false;
    if (a.id === 'treeline' && s.flags.treeline) return false;
    return true;
  });
}
