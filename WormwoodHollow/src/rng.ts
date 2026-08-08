/**
 * Deterministic seeded RNG (mulberry32) so expeditions and any random beats are
 * reproducible — a bug that depends on RNG can be replayed from its seed.
 *
 * The generator is a small object carrying its own state; call next() for a float
 * in [0, 1). Persist `state` alongside GameState to keep a run reproducible across
 * save/load, or fork a child RNG for isolated subsystems.
 */
export interface Rng {
  /** current internal state (persist this) */
  state: number;
  /** returns a float in [0, 1) and advances the generator */
  next(): number;
}

/** Create a seeded RNG. Any 32-bit-ish integer seed works. */
export function makeRng(seed: number): Rng {
  const rng: Rng = {
    state: seed >>> 0,
    next() {
      this.state = (this.state + 0x6d2b79f5) >>> 0;
      let t = this.state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    },
  };
  return rng;
}

/** Restore an RNG from a persisted state value. */
export function rngFromState(state: number): Rng {
  const rng = makeRng(0);
  rng.state = state >>> 0;
  return rng;
}

/** Pick a random element using the provided RNG. */
export function pick<T>(rng: Rng, arr: readonly T[]): T {
  return arr[Math.floor(rng.next() * arr.length)];
}
