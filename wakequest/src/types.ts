export type ChallengeType = 'math' | 'memory' | 'shake' | 'typing' | 'random';

export interface Alarm {
  id: string;
  hour: number;
  minute: number;
  label: string;
  /** 0=Sun … 6=Sat. Empty = one-shot alarm. */
  days: number[];
  enabled: boolean;
  challenge: ChallengeType;
  notificationIds: string[];
}

export interface WakeRecord {
  date: string; // YYYY-MM-DD
  onTime: boolean;
  snoozes: number;
  xpEarned: number;
}

export type PetMood = 'radiant' | 'happy' | 'sleepy' | 'sad' | 'sick';

export interface RootStackParamList {
  Tabs: undefined;
  AddAlarm: { alarmId?: string } | undefined;
  Ring: { alarmId: string };
  Challenge: { alarmId: string; snoozes: number };
  Reward: { xp: number; streak: number; leveledUp: boolean; evolvedTo?: string; dust: number; freezeUsed: boolean };
  BattleSetup: undefined;
  Battle: { me: string; opponent: string };
  Shop: undefined;
  [key: string]: object | undefined;
}
