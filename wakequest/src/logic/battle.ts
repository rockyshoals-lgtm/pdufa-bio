// Deterministic monster battle engine.
// Fighters are built from REAL wake data — waking up on time literally trains your monster.

export interface Fighter {
  name: string;
  speciesId: string;
  stage: number;
  streak: number;
  onTimeRate: number; // 0..1
  energy: number; // 0..100
  seed: number;
}

export interface BattlePayload extends Fighter {
  v: 1;
}

export interface TurnLog {
  attacker: 0 | 1;
  miss: boolean;
  crit: boolean;
  damage: number;
  hp: [number, number]; // after this turn
  line: string;
}

export interface BattleResult {
  winner: 0 | 1 | -1; // -1 = draw
  turns: TurnLog[];
  maxHp: [number, number];
}

export function encodeBattlePayload(f: Fighter): string {
  const p: BattlePayload = { v: 1, ...f };
  return JSON.stringify(p);
}

export function decodeBattlePayload(data: string): Fighter | null {
  try {
    const p = JSON.parse(data);
    if (p?.v !== 1 || typeof p.speciesId !== 'string' || typeof p.stage !== 'number') return null;
    return {
      name: String(p.name || 'Wild Monster').slice(0, 20),
      speciesId: p.speciesId,
      stage: Math.max(0, Math.min(10, Math.round(p.stage))),
      streak: Math.max(0, Math.min(999, Math.round(p.streak ?? 0))),
      onTimeRate: Math.max(0, Math.min(1, Number(p.onTimeRate ?? 0.5))),
      energy: Math.max(0, Math.min(100, Math.round(p.energy ?? 50))),
      seed: Math.abs(Math.round(p.seed ?? 1)) || 1,
    };
  } catch {
    return null;
  }
}

// mulberry32 — deterministic PRNG so both phones can replay the exact same fight
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function stats(f: Fighter) {
  return {
    maxHp: Math.round(80 + f.energy * 0.6 + f.stage * 9),
    atk: 9 + f.stage * 2.5 + Math.min(f.streak, 30) * 0.4,
    accuracy: 0.72 + f.onTimeRate * 0.23,
    crit: 0.08 + f.stage * 0.012,
  };
}

const HIT_LINES = ['lands a solid hit', 'strikes true', 'attacks with morning fury', 'unleashes wake power'];
const CRIT_LINES = ['CRITICAL — powered by a flawless streak', 'DEVASTATING blow', 'CRITICAL sunrise strike'];
const MISS_LINES = ['whiffs — too many snoozes', 'attacks the air', 'misses badly'];

export function simulateBattle(a: Fighter, b: Fighter): BattleResult {
  const rng = mulberry32((a.seed ^ (b.seed << 1)) >>> 0 || 42);
  const sa = stats(a);
  const sb = stats(b);
  const hp: [number, number] = [sa.maxHp, sb.maxHp];
  const fighters = [
    { f: a, s: sa },
    { f: b, s: sb },
  ];
  const turns: TurnLog[] = [];
  // Higher on-time rate strikes first — punctuality wins initiative
  let attacker: 0 | 1 = a.onTimeRate >= b.onTimeRate ? 0 : 1;

  for (let round = 0; round < 24 && hp[0] > 0 && hp[1] > 0; round++) {
    const atk = fighters[attacker];
    const defIdx = (1 - attacker) as 0 | 1;
    const miss = rng() > atk.s.accuracy;
    const crit = !miss && rng() < atk.s.crit;
    let damage = 0;
    let line: string;
    if (miss) {
      line = `${atk.f.name} ${MISS_LINES[Math.floor(rng() * MISS_LINES.length)]}!`;
    } else {
      const variance = 0.85 + rng() * 0.3;
      damage = Math.max(3, Math.round(atk.s.atk * variance * (crit ? 1.8 : 1)));
      hp[defIdx] = Math.max(0, hp[defIdx] - damage);
      line = crit
        ? `${atk.f.name}: ${CRIT_LINES[Math.floor(rng() * CRIT_LINES.length)]}! −${damage}`
        : `${atk.f.name} ${HIT_LINES[Math.floor(rng() * HIT_LINES.length)]}. −${damage}`;
    }
    turns.push({ attacker, miss, crit, damage, hp: [hp[0], hp[1]], line });
    attacker = defIdx;
  }

  const winner: 0 | 1 | -1 = hp[0] <= 0 && hp[1] <= 0 ? -1 : hp[1] <= 0 ? 0 : hp[0] <= 0 ? 1 : hp[0] >= hp[1] ? 0 : 1;
  return { winner, turns, maxHp: [sa.maxHp, sb.maxHp] };
}
