import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { Alarm, WakeRecord } from '../types';
import { clampEnergy, ENERGY_ON_TIME, ENERGY_SNOOZE } from '../logic/pet';
import { dustForWake, getCosmetic, MAX_STREAK_FREEZES, STREAK_FREEZE_COST } from '../logic/economy';
import { getSpecies, stageForPower } from '../logic/monsters';
import { levelFromXp, wakeXp } from '../logic/xp';

function todayKey(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function yesterdayKey(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

interface WakeQuestState {
  alarms: Alarm[];
  xp: number;
  streak: number;
  bestStreak: number;
  lastWakeDate: string | null;
  totalWakes: number;
  totalSnoozes: number;
  history: WakeRecord[];
  petEnergy: number;
  petName: string;
  /** Chosen starter species id (null until onboarding). */
  speciesId: string | null;
  /** Evolution currency: on-time wake +2, snoozed wake +1. */
  wakePower: number;
  /** Dawn Dust — soft currency earned only by waking up. */
  dawnDust: number;
  /** Streak freezes auto-save a broken streak. Max 2 banked. */
  streakFreezes: number;
  ownedCosmetics: string[];
  equippedHat: string | null;
  equippedAura: string | null;
  bedtime: { enabled: boolean; hour: number; minute: number; notifId: string | null };

  upsertAlarm: (alarm: Alarm) => void;
  removeAlarm: (id: string) => void;
  setAlarmEnabled: (id: string, enabled: boolean, notificationIds: string[]) => void;
  recordSnooze: () => void;
  completeWake: (
    snoozes: number,
    perfectChallenge: boolean
  ) => {
    xpGained: number;
    streak: number;
    leveledUp: boolean;
    evolvedTo?: string;
    dustGained: number;
    freezeUsed: boolean;
  };
  renamePet: (name: string) => void;
  chooseStarter: (speciesId: string) => void;
  buyCosmetic: (id: string) => boolean;
  equipCosmetic: (id: string | null, slot: 'hat' | 'aura') => void;
  buyStreakFreeze: () => boolean;
  setBedtime: (b: { enabled: boolean; hour: number; minute: number; notifId: string | null }) => void;
}

export const useStore = create<WakeQuestState>()(
  persist(
    (set, get) => ({
      alarms: [],
      xp: 0,
      streak: 0,
      bestStreak: 0,
      lastWakeDate: null,
      totalWakes: 0,
      totalSnoozes: 0,
      history: [],
      petEnergy: 60,
      petName: '',
      speciesId: null,
      wakePower: 0,
      dawnDust: 0,
      streakFreezes: 0,
      ownedCosmetics: [],
      equippedHat: null,
      equippedAura: null,
      bedtime: { enabled: false, hour: 22, minute: 30, notifId: null },

      upsertAlarm: (alarm) =>
        set((s) => {
          const i = s.alarms.findIndex((a) => a.id === alarm.id);
          const alarms = [...s.alarms];
          if (i >= 0) alarms[i] = alarm;
          else alarms.push(alarm);
          return { alarms };
        }),

      removeAlarm: (id) => set((s) => ({ alarms: s.alarms.filter((a) => a.id !== id) })),

      setAlarmEnabled: (id, enabled, notificationIds) =>
        set((s) => ({
          alarms: s.alarms.map((a) => (a.id === id ? { ...a, enabled, notificationIds } : a)),
        })),

      recordSnooze: () =>
        set((s) => ({
          totalSnoozes: s.totalSnoozes + 1,
          petEnergy: clampEnergy(s.petEnergy + ENERGY_SNOOZE),
        })),

      completeWake: (snoozes, perfectChallenge) => {
        const s = get();
        const today = todayKey();
        if (s.lastWakeDate === today) {
          // already counted today — small consolation XP, no streak change
          const xpGained = 10;
          set({ xp: s.xp + xpGained });
          return { xpGained, streak: s.streak, leveledUp: false, dustGained: 0, freezeUsed: false };
        }
        const continues = s.lastWakeDate === yesterdayKey();
        // Streak freeze: if the streak would break, burn a banked freeze to save it
        const freezeUsed = !continues && s.lastWakeDate !== null && s.streak > 0 && s.streakFreezes > 0;
        const streak = continues || freezeUsed ? s.streak + 1 : 1;
        const xpGained = wakeXp(streak, snoozes, perfectChallenge);
        const prevLevel = levelFromXp(s.xp);
        const newXp = s.xp + xpGained;
        const leveledUp = levelFromXp(newXp) > prevLevel;

        // Evolution: on-time wakes feed your monster twice as much
        const powerGain = snoozes === 0 ? 2 : 1;
        const newPower = s.wakePower + powerGain;
        const prevStage = stageForPower(s.wakePower);
        const newStage = stageForPower(newPower);
        const evolvedTo = newStage > prevStage ? getSpecies(s.speciesId).forms[newStage].name : undefined;

        const dustGained = dustForWake(streak, snoozes === 0);
        const record: WakeRecord = { date: today, onTime: snoozes === 0, snoozes, xpEarned: xpGained };
        set({
          xp: newXp,
          streak,
          bestStreak: Math.max(s.bestStreak, streak),
          lastWakeDate: today,
          totalWakes: s.totalWakes + 1,
          wakePower: newPower,
          dawnDust: s.dawnDust + dustGained,
          streakFreezes: freezeUsed ? s.streakFreezes - 1 : s.streakFreezes,
          history: [...s.history.slice(-89), record],
          petEnergy: clampEnergy(s.petEnergy + (snoozes === 0 ? ENERGY_ON_TIME : Math.floor(ENERGY_ON_TIME / 3))),
        });
        return { xpGained, streak, leveledUp, evolvedTo, dustGained, freezeUsed };
      },

      renamePet: (name) => set({ petName: name.trim() }),

      chooseStarter: (speciesId) => set({ speciesId }),

      buyCosmetic: (id) => {
        const s = get();
        const item = getCosmetic(id);
        if (!item || s.ownedCosmetics.includes(id) || s.dawnDust < item.cost) return false;
        set({ dawnDust: s.dawnDust - item.cost, ownedCosmetics: [...s.ownedCosmetics, id] });
        return true;
      },

      equipCosmetic: (id, slot) => {
        const s = get();
        if (id !== null && !s.ownedCosmetics.includes(id)) return;
        if (slot === 'hat') set({ equippedHat: id });
        else set({ equippedAura: id });
      },

      buyStreakFreeze: () => {
        const s = get();
        if (s.streakFreezes >= MAX_STREAK_FREEZES || s.dawnDust < STREAK_FREEZE_COST) return false;
        set({ dawnDust: s.dawnDust - STREAK_FREEZE_COST, streakFreezes: s.streakFreezes + 1 });
        return true;
      },

      setBedtime: (bedtime) => set({ bedtime }),
    }),
    {
      name: 'wakequest-store',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);
