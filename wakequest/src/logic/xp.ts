// XP & leveling curve. Level N requires cumulative xpForLevel(N).
export const BASE_WAKE_XP = 50;
export const PERFECT_CHALLENGE_BONUS = 25;
export const SNOOZE_PENALTY = 15; // per snooze, subtracted from wake XP (floor 10)

export function xpForLevel(level: number): number {
  // cumulative XP needed to REACH this level
  if (level <= 1) return 0;
  return Math.round(100 * Math.pow(level - 1, 1.5));
}

export function levelFromXp(xp: number): number {
  let lvl = 1;
  while (xpForLevel(lvl + 1) <= xp) lvl++;
  return lvl;
}

export function levelProgress(xp: number): { level: number; pct: number; into: number; needed: number } {
  const level = levelFromXp(xp);
  const cur = xpForLevel(level);
  const next = xpForLevel(level + 1);
  const into = xp - cur;
  const needed = next - cur;
  return { level, pct: Math.min(1, into / needed), into, needed };
}

export function streakMultiplier(streak: number): number {
  if (streak >= 30) return 2.0;
  if (streak >= 14) return 1.75;
  if (streak >= 7) return 1.5;
  if (streak >= 3) return 1.25;
  return 1.0;
}

export function wakeXp(streak: number, snoozes: number, perfectChallenge: boolean): number {
  const base = Math.max(10, BASE_WAKE_XP - snoozes * SNOOZE_PENALTY);
  const bonus = perfectChallenge ? PERFECT_CHALLENGE_BONUS : 0;
  return Math.round((base + bonus) * streakMultiplier(streak));
}

export const LEVEL_TITLES = [
  'Snooze Victim',
  'Drowsy Recruit',
  'Blanket Escapist',
  'Dawn Apprentice',
  'Sunrise Scout',
  'Morning Machine',
  'Circadian Knight',
  'Dawn Commander',
  'Solar Champion',
  'Wake Lord',
] as const;

export function titleForLevel(level: number): string {
  return LEVEL_TITLES[Math.min(LEVEL_TITLES.length - 1, Math.floor((level - 1) / 3))];
}
