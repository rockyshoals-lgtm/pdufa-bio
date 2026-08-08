// Dawn Dust — the single soft currency. Earned ONLY by waking up. Spent on cosmetics + streak freezes.
// Rule: money can never buy wake success. Cosmetics only.

export const DUST_ON_TIME = 10; // + streak bonus below
export const DUST_LATE = 4;
export const STREAK_FREEZE_COST = 60;
export const MAX_STREAK_FREEZES = 2;

export function dustForWake(streak: number, onTime: boolean): number {
  if (!onTime) return DUST_LATE;
  return DUST_ON_TIME + Math.min(streak, 30);
}

export type CosmeticSlot = 'hat' | 'aura';

export interface Cosmetic {
  id: string;
  slot: CosmeticSlot;
  name: string;
  emoji: string; // hats render this above the monster; auras use color
  color?: string; // aura glow color
  cost: number;
}

export const COSMETICS: Cosmetic[] = [
  // Hats
  { id: 'hat_cap', slot: 'hat', name: 'Morning Cap', emoji: '🧢', cost: 80 },
  { id: 'hat_bow', slot: 'hat', name: 'Dawn Bow', emoji: '🎀', cost: 80 },
  { id: 'hat_top', slot: 'hat', name: 'Fancy Top Hat', emoji: '🎩', cost: 150 },
  { id: 'hat_party', slot: 'hat', name: 'Party Cone', emoji: '🎉', cost: 120 },
  { id: 'hat_crown', slot: 'hat', name: 'Crown of Dawn', emoji: '👑', cost: 300 },
  { id: 'hat_wizard', slot: 'hat', name: 'Wizard Hat', emoji: '🪄', cost: 200 },
  // Auras (override glow color)
  { id: 'aura_gold', slot: 'aura', name: 'Golden Hour', emoji: '🌟', color: '#FBBF24', cost: 150 },
  { id: 'aura_ember', slot: 'aura', name: 'Ember Aura', emoji: '🔥', color: '#F87171', cost: 150 },
  { id: 'aura_frost', slot: 'aura', name: 'Frost Aura', emoji: '❄️', color: '#22D3EE', cost: 150 },
  { id: 'aura_void', slot: 'aura', name: 'Void Aura', emoji: '🌌', color: '#8B5CF6', cost: 220 },
  { id: 'aura_rose', slot: 'aura', name: 'Rose Dawn', emoji: '🌸', color: '#F472B6', cost: 220 },
];

export function getCosmetic(id: string | null): Cosmetic | undefined {
  return COSMETICS.find((c) => c.id === id);
}
