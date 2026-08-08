/**
 * ExpeditionSystem — a descent into the next Depth.
 *
 * M2: resolved encounters with content. Success chance scales with ward strength
 * and cleared depth. A descent onto a Lord's depth is a boss encounter (harder,
 * unique flavor, a guaranteed rune-shard on victory). Once the bottom is reached,
 * further descents become "deep patrols" that hold the line and pry loose the last
 * shards. M3 replaces the resolution with a Phaser tile scene that returns this
 * same outcome shape.
 */
import { CONFIG } from '../config';
import { clamp, logLine, type GameState } from '../state';
import { flavor } from '../content/flavor';
import { depthAt } from '../content/depths';
import { bossAtDepth } from '../content/bosses';
import type { Rng } from '../rng';

export interface ExpeditionOutcome {
  success: boolean;
  targetDepth: number;
  bossId: string | null;
  gotRune: boolean;
  deepPatrol: boolean;
}

/** Base success probability for a descent from the current state. */
export function expeditionOdds(s: GameState): number {
  return clamp(0.35 + s.wardStrength / 250 + s.depthCleared * 0.01, 0.2, 0.85);
}

/** Resolve one descent. Mutates the (working-copy) state; uses the provided RNG. */
export function runExpedition(s: GameState, rng: Rng): ExpeditionOutcome {
  s.resources.herbs -= CONFIG.EXPEDITION_HERB_COST;
  const targetDepth = s.depthCleared + 1;

  // --- Deep patrol: the bottom is reached; hold the line, farm remaining shards. ---
  if (targetDepth > CONFIG.DEPTHS) {
    const win = rng.next() < expeditionOdds(s);
    if (win) {
      s.rot = clamp(s.rot - CONFIG.DEEP_PATROL_ROT_CLEAR, 0, 100);
      s.resources.lore += 4;
      let gotRune = false;
      if (rng.next() < CONFIG.DEEP_PATROL_RUNE_CHANCE && s.runesRecovered < CONFIG.DEPTHS) {
        s.runesRecovered++;
        gotRune = true;
      }
      logLine(s, flavor(rng, 'deepPatrol'), 'good');
      if (gotRune) logLine(s, flavor(rng, 'expeditionRune'), 'good');
      return { success: true, targetDepth, bossId: null, gotRune, deepPatrol: true };
    }
    s.rot = clamp(s.rot + CONFIG.EXPEDITION_ROT_PENALTY, 0, 100);
    s.resources.herbs = Math.max(0, s.resources.herbs - 3);
    logLine(s, flavor(rng, 'expeditionLoss'), 'bad');
    return { success: false, targetDepth, bossId: null, gotRune: false, deepPatrol: true };
  }

  const boss = bossAtDepth(targetDepth);
  const depth = depthAt(targetDepth);

  // Encounter framing.
  if (boss) {
    logLine(s, boss.taunt, 'whisper');
  } else if (depth) {
    logLine(s, `${depth.name} — ${depth.hazard}`);
  }

  const odds = boss
    ? Math.max(0.1, expeditionOdds(s) - CONFIG.BOSS_ODDS_PENALTY)
    : expeditionOdds(s);

  if (rng.next() < odds) {
    s.depthCleared = clamp(targetDepth, 0, CONFIG.DEPTHS);
    s.rot = clamp(s.rot - CONFIG.EXPEDITION_ROT_CLEAR, 0, 100);
    s.resources.lore += 6 + s.depthCleared * 2;

    let gotRune = false;
    if (boss) {
      s.bossesFelled[boss.id] = true;
      if (s.runesRecovered < CONFIG.DEPTHS) {
        s.runesRecovered++;
        gotRune = true;
      }
      logLine(s, boss.defeat, 'good');
    } else {
      logLine(s, flavor(rng, 'expeditionWin'), 'good');
      if (rng.next() < CONFIG.EXPEDITION_RUNE_CHANCE && s.runesRecovered < CONFIG.DEPTHS) {
        s.runesRecovered++;
        gotRune = true;
        logLine(s, flavor(rng, 'expeditionRune'), 'good');
      }
    }
    return { success: true, targetDepth, bossId: boss?.id ?? null, gotRune, deepPatrol: false };
  }

  // Failure.
  s.rot = clamp(s.rot + CONFIG.EXPEDITION_ROT_PENALTY + (boss ? CONFIG.BOSS_ROT_PENALTY : 0), 0, 100);
  s.resources.herbs = Math.max(0, s.resources.herbs - 3);
  logLine(s, boss ? boss.repel : flavor(rng, 'expeditionLoss'), 'bad');
  return { success: false, targetDepth, bossId: boss?.id ?? null, gotRune: false, deepPatrol: false };
}
