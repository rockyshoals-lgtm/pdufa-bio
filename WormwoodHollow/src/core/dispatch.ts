/**
 * Action dispatcher — the one place player actions are applied.
 *
 * Pure: clones the state, restores the seeded RNG, runs the action, persists the
 * advanced RNG state (unless the action began a new keeper, which carries its own
 * fresh RNG). Post-processing (stage transitions, hollow-fall) is handled by the
 * Game controller so the dispatcher stays a clean (state, id) => state transition.
 */
import { cloneState, type GameState } from '../state';
import { rngFromState } from '../rng';
import { actionById } from '../content/actions';
import { endingById } from '../content/endings';

export interface ActionEnv {
  now: number;
  seed: number; // used if the action starts a new life (Pass the salt)
}

/** Apply an action by id. Returns the new state (unchanged if the action can't run). */
export function applyAction(state: GameState, id: string, env: ActionEnv): GameState {
  const action = actionById(id);
  if (!action) return state;
  if (!action.stages.includes(state.stage)) return state; // stage gate
  if (!action.can(state)) return state; // resource / flag gate

  const working = cloneState(state);
  const rng = rngFromState(working.rngState);
  const next = action.run(working, { rng, now: env.now, seed: env.seed });

  // If the action mutated the working copy in place, persist the advanced RNG.
  // If it returned a brand new state (Pass the salt), leave its fresh RNG intact.
  if (next === working) next.rngState = rng.state;

  return next;
}

/** Choose one of the three endings at the master-rune. Pure. No-op if unavailable. */
export function applyEnding(state: GameState, endingId: string): GameState {
  const ending = endingById(endingId);
  if (!ending || !ending.available(state) || state.ending) return state;
  const working = cloneState(state);
  ending.apply(working);
  return working;
}
