import { PetMood } from '../types';

export const ENERGY_ON_TIME = 18;
export const ENERGY_SNOOZE = -12;
export const ENERGY_MISS = -30;

export function clampEnergy(e: number): number {
  return Math.max(0, Math.min(100, Math.round(e)));
}

export function moodFromEnergy(energy: number): PetMood {
  if (energy >= 80) return 'radiant';
  if (energy >= 55) return 'happy';
  if (energy >= 30) return 'sleepy';
  if (energy >= 10) return 'sad';
  return 'sick';
}

export const MOOD_META: Record<PetMood, { emoji: string; line: string; color: string }> = {
  radiant: { emoji: '🌟', line: 'Your monster is GLOWING. You are unstoppable.', color: '#FBBF24' },
  happy: { emoji: '😊', line: 'Your monster is happy! Keep the streak alive.', color: '#34D399' },
  sleepy: { emoji: '😴', line: 'Your monster is drowsy… wake up on time tomorrow.', color: '#22D3EE' },
  sad: { emoji: '🥺', line: 'Your monster misses your morning energy.', color: '#8B5CF6' },
  sick: { emoji: '🤒', line: 'Your monster is sick from all the snoozing!', color: '#F87171' },
};
