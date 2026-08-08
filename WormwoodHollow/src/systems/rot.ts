/**
 * RotSystem — the corruption meter creeping up the hollow.
 *
 * Closed-form: Rot advances per in-game day proportional to how far the ward has
 * fallen below full, amplified by how deep you've dug (depthPressure). Strong wards
 * (=100) halt it entirely; a broken ward (=0) lets it run at ROT_BASE_RATE * pressure.
 * Never simulate tick-by-tick — this is the offline catch-up math too.
 */
import { CONFIG } from '../config';
import type { GameState } from '../state';

/** Pressure multiplier from cleared depth: deeper diggings seep faster. */
export function depthPressure(s: GameState): number {
  return 1 + s.depthCleared * 0.15;
}

/** Rot points gained over `days` given the CURRENT ward strength (closed-form). */
export function rotGainForDays(s: GameState, days: number): number {
  const wardGap = Math.max(0, 1 - s.wardStrength / 100);
  return CONFIG.ROT_BASE_RATE * wardGap * depthPressure(s) * days;
}
