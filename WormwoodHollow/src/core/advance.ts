/**
 * advanceDays — the single source of truth for time passing.
 *
 * Both the live tick and the offline catch-up call this. It is a PURE transition:
 * it clones the state, applies ward decay, then Rot creep (against the decayed
 * ward), then resource accrual, then aging — and returns the new state plus a
 * report for the Come Morning summary. Never simulate tick-by-tick.
 */
import { clamp, cloneState, type GameState } from '../state';
import { wardDecayForDays } from '../systems/ward';
import { rotGainForDays } from '../systems/rot';
import { accrueForDays, emptyHarvest, type Harvest } from '../systems/resource';

export interface AdvanceReport {
  aged: number; // in-game days advanced
  rotGain: number; // rot points added (pre-clamp)
  wardLoss: number; // ward strength lost
  harvest: Harvest; // resources gained
}

export function advanceDays(state: GameState, days: number): {
  state: GameState;
  report: AdvanceReport;
} {
  const s = cloneState(state);
  const report: AdvanceReport = {
    aged: days,
    rotGain: 0,
    wardLoss: 0,
    harvest: emptyHarvest(),
  };
  if (days <= 0) return { state: s, report };

  // 1. Ward decays first.
  const wardBefore = s.wardStrength;
  s.wardStrength = clamp(s.wardStrength - wardDecayForDays(days), 0, 100);
  report.wardLoss = wardBefore - s.wardStrength;

  // 2. Rot creeps against the now-decayed ward.
  const gain = rotGainForDays(s, days);
  s.rot = clamp(s.rot + gain, 0, 100);
  report.rotGain = gain;

  // 3. Production accrues (the harvest half of Come Morning).
  report.harvest = accrueForDays(s, days);

  // 4. The keeper ages.
  s.ageDays += days;

  return { state: s, report };
}
