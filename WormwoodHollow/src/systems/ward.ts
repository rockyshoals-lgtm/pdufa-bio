/**
 * WardSystem — the salt/iron line that dams back the Rot.
 *
 * Ward decays a fixed amount per in-game day. Laying salt or hanging iron/silver
 * spends resources to push it back up (iron is stronger than salt alone). Mutating
 * helpers operate on a working copy owned by the caller (see core/advance & actions).
 */
import { CONFIG } from '../config';

/** Ward strength lost over `days` (closed-form, clamped at caller). */
export function wardDecayForDays(days: number): number {
  return CONFIG.WARD_DECAY_PER_DAY * days;
}
