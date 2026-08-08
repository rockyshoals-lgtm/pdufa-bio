/**
 * Game — the singleton controller. Owns the live GameState, wires the real-time
 * tick, applies actions, runs offline catch-up, and fires render / Come Morning
 * callbacks. All state math is delegated to the pure systems; Game only orchestrates
 * (and is the only holder of wall-clock + RNG-seed sources, injectable for tests).
 */
import { CONFIG } from '../config';
import {
  cloneState,
  logLine,
  newLife,
  type GameState,
} from '../state';
import { rngFromState } from '../rng';
import { advanceDays, type AdvanceReport } from './advance';
import { computeElapsed, tickDays } from './clock';
import { applyAction, applyEnding } from './dispatch';
import { updateStage } from '../systems/life';
import { passSalt } from '../systems/lineage';
import { STAGE_FLAVOR, FLAVOR, flavor, whisperByRot } from '../content/flavor';
import { SaveManager } from '../save/SaveManager';

export interface ComeMorningInfo {
  days: number;
  report: AdvanceReport;
  capped: boolean;
  fell: boolean;
}

export interface FinalizeResult {
  fell: boolean;
}

export interface GameHooks {
  onChange?: (s: GameState) => void;
  onComeMorning?: (info: ComeMorningInfo) => void;
}

export type NowFn = () => number;
export type SeedFn = () => number;

const randomSeed: SeedFn = () => Math.floor(Math.random() * 0xffffffff);

export class Game {
  state: GameState;
  private lastTick: number;

  constructor(
    private save: SaveManager = new SaveManager(),
    public hooks: GameHooks = {},
    private now: NowFn = Date.now,
    private seed: SeedFn = randomSeed,
  ) {
    this.state = this.save.load() ?? newLife({ now: this.now(), seed: this.seed() });
    this.lastTick = this.now();
  }

  /** Boot: seed the opening line if fresh, then run offline catch-up. */
  init(): void {
    if (this.state.log.length === 0) {
      logLine(this.state, FLAVOR.boot[0], 'whisper');
    }
    this.offlineCatchup();
  }

  /** Advance for time the player was away; returns the report (also fires the hook). */
  offlineCatchup(): ComeMorningInfo | null {
    const now = this.now();
    const el = computeElapsed(this.state.lastSeen, now);
    if (el.elapsedSec < CONFIG.OFFLINE_MIN_SEC) {
      this.state.lastSeen = now;
      this.lastTick = now;
      this.save.save(this.state);
      return null;
    }
    const { state, report } = advanceDays(this.state, el.days);
    this.state = state;
    const { fell } = this.finalize();
    this.state.lastSeen = now;
    this.lastTick = now;
    this.save.save(this.state);
    this.emitChange();

    const info: ComeMorningInfo = { days: el.days, report, capped: el.capped, fell };
    this.hooks.onComeMorning?.(info);
    return info;
  }

  /** Real-time tick: advance a small delta, whisper as the Rot rises. */
  tick(): void {
    const now = this.now();
    const d = tickDays(this.lastTick, now);
    this.lastTick = now;

    const { state } = advanceDays(this.state, d);
    this.state = state;
    if (!this.state.flags.won) this.finalize();
    this.maybeWhisper();

    this.state.lastSeen = now;
    this.save.save(this.state);
    this.emitChange();
  }

  /** Apply a player action by id, then finalize + persist + render. */
  doAction(id: string): void {
    const now = this.now();
    this.state = applyAction(this.state, id, { now, seed: this.seed() });
    this.finalize();
    this.state.lastSeen = now;
    this.save.save(this.state);
    this.emitChange();
  }

  /** Choose one of the three endings at the master-rune. */
  chooseEnding(endingId: string): void {
    this.state = applyEnding(this.state, endingId);
    this.state.lastSeen = this.now();
    this.save.save(this.state);
    this.emitChange();
  }

  /** True on a fresh Gen-1 life that hasn't seen the Salt Line prologue yet. */
  needsPrologue(): boolean {
    return (
      this.state.generation === 1 &&
      !this.state.flags.prologueSeen &&
      this.state.ending === null
    );
  }

  markPrologueSeen(): void {
    this.state.flags.prologueSeen = true;
    this.save.save(this.state);
  }

  /** Abandon the bloodline and start over. */
  reset(): void {
    this.state = newLife({ now: this.now(), seed: this.seed() });
    logLine(this.state, FLAVOR.newBloodline[0]);
    this.lastTick = this.now();
    this.state.lastSeen = this.lastTick;
    this.save.save(this.state);
    this.emitChange();
  }

  /** DEV: pretend the player was away `hours` real hours, then run catch-up. */
  simulateAway(hours: number): ComeMorningInfo | null {
    this.state.lastSeen = this.now() - hours * 3600 * 1000;
    this.save.save(this.state);
    return this.offlineCatchup();
  }

  /** Stage transitions, ward-break flavor, and hollow-fall check. Mutates this.state. */
  private finalize(): FinalizeResult {
    const newStage = updateStage(this.state);
    if (newStage && newStage !== 'child') {
      logLine(this.state, STAGE_FLAVOR[newStage]);
    }

    // Ward-break beat: fire once when the line goes fully down, re-arm when raised.
    if (this.state.wardStrength <= 0) {
      if (!this.state.flags._wardDown) {
        const rng = rngFromState(this.state.rngState);
        logLine(this.state, flavor(rng, 'wardBreak'), 'bad');
        this.state.rngState = rng.state;
        this.state.flags._wardDown = true;
      }
    } else {
      this.state.flags._wardDown = false;
    }

    let fell = false;
    if (!this.state.flags.won && this.state.rot >= CONFIG.ROT_FALL) {
      fell = true;
      const child = passSalt(this.state, {
        forced: true,
        now: this.now(),
        seed: this.seed(),
      }).state;
      logLine(child, FLAVOR.hollowFell[0], 'bad');
      this.state = child;
    }
    return { fell };
  }

  private maybeWhisper(): void {
    if (this.state.rot <= 60) return;
    const working = cloneState(this.state);
    const rng = rngFromState(working.rngState);
    if (rng.next() < 0.03) {
      logLine(working, whisperByRot(rng, working.rot), 'whisper');
    }
    working.rngState = rng.state;
    this.state = working;
  }

  private emitChange(): void {
    this.hooks.onChange?.(this.state);
  }
}
