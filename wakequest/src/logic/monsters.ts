import { PetMood } from '../types';

/**
 * Monster evolution system.
 * Wake power: on-time wake = +2, snoozed wake = +1.
 * 11 forms per species = base form + 10 evolutions.
 */
export const EVOLUTION_THRESHOLDS = [0, 4, 10, 18, 28, 42, 60, 84, 114, 152, 200];
export const MAX_STAGE = EVOLUTION_THRESHOLDS.length - 1; // 10

export interface MonsterForm {
  name: string;
  emoji: string;
}

export interface MonsterSpecies {
  id: string;
  name: string;
  vibe: string; // one-line personality pitch shown at starter selection
  bio: string;
  colors: readonly [string, string];
  forms: MonsterForm[]; // length 11
  dialogue: {
    greeting: string[]; // home screen
    ring: string[]; // alarm ringing
    praise: string[]; // wake completed
    snooze: string[]; // user snoozed
    moods: Record<PetMood, string>;
  };
}

export const SPECIES: MonsterSpecies[] = [
  {
    id: 'embyr',
    name: 'Embyr',
    vibe: 'Chaotic fire gremlin. Your personal hype beast.',
    bio: 'Embyr runs on pure adrenaline and considers the snooze button a mortal enemy. Loud, loyal, slightly unhinged.',
    colors: ['#FBBF24', '#F87171'],
    forms: [
      { name: 'Spark', emoji: '✨' },
      { name: 'Cinder', emoji: '🔸' },
      { name: 'Embyr', emoji: '🔥' },
      { name: 'Flareling', emoji: '🦎' },
      { name: 'Scorch', emoji: '🌋' },
      { name: 'Pyroclaw', emoji: '🐾' },
      { name: 'Blazerunner', emoji: '💨' },
      { name: 'Infernyx', emoji: '🐉' },
      { name: 'Solaris', emoji: '☀️' },
      { name: 'Nova Tyrant', emoji: '💥' },
      { name: 'SUNBORN ETERNAL', emoji: '🌞' },
    ],
    dialogue: {
      greeting: [
        "LET'S GOOO. What are we conquering today?",
        'I stayed lit all night waiting for this.',
        'You + me + sunrise = undefeated.',
      ],
      ring: [
        "UP. NOW. The snooze button fears us — let's keep it that way.",
        'I will scream. Lovingly. GET UP.',
        'Every second in bed my flame gets smaller. DO YOU WANT THAT?',
      ],
      praise: [
        "THAT'S MY HUMAN! Absolute legend!",
        "You woke up like a champion. I'm literally glowing.",
        "The sun called. It's jealous of you.",
      ],
      snooze: [
        'Snooze?! We had a DEAL.',
        "My flame just flickered. I hope you're happy.",
        "Fine. FIVE minutes. I'm counting every one.",
      ],
      moods: {
        radiant: 'I AM BECOME SUNRISE. Nothing can stop us.',
        happy: 'Feeling toasty. Keep feeding the fire.',
        sleepy: 'My flame is low… wake up on time and stoke it.',
        sad: "A damp little ember. That's what I am now.",
        sick: 'You snoozed me into a pile of cold ash.',
      },
    },
  },
  {
    id: 'nimbus',
    name: 'Nimbus',
    vibe: 'Dramatic storm cloud. Moody poet with thunder.',
    bio: 'Nimbus feels everything deeply and narrates your mornings like an epic saga. Rewards consistency with rainbows, punishes snoozing with drizzle.',
    colors: ['#22D3EE', '#8B5CF6'],
    forms: [
      { name: 'Wisp', emoji: '🌫️' },
      { name: 'Puff', emoji: '☁️' },
      { name: 'Nimbus', emoji: '🌥️' },
      { name: 'Drizzle', emoji: '🌦️' },
      { name: 'Squall', emoji: '🌧️' },
      { name: 'Thunderpup', emoji: '⛈️' },
      { name: 'Stormcaller', emoji: '🌩️' },
      { name: 'Tempest', emoji: '🌪️' },
      { name: 'Cyclonius', emoji: '🌀' },
      { name: 'Skybreaker', emoji: '⚡' },
      { name: 'EYE OF THE DAWN', emoji: '🌈' },
    ],
    dialogue: {
      greeting: [
        'Another dawn, another chapter of our legend.',
        'The sky told me today matters. It usually lies. Not today.',
        'I gathered three clouds and a sunbeam for you.',
      ],
      ring: [
        'Rise. The storm waits for no sleeper.',
        'Hear that thunder? That was me. Politely.',
        'The horizon is doing something beautiful and you are MISSING it.',
      ],
      praise: [
        'And so the hero rose, and the sky wept with joy.',
        'Magnificent. I shall rain on someone else today.',
        'You have earned one (1) rainbow. Redeemable immediately.',
      ],
      snooze: [
        'A snooze? In THIS economy of dreams?',
        'I am not mad. I am drizzling. There is a difference.',
        'Five more minutes of grey sky, then. As you wish.',
      ],
      moods: {
        radiant: 'I am a sunrise with legs. Metaphorically.',
        happy: 'Partly cloudy with a 100% chance of pride.',
        sleepy: 'Fog is rolling in… wake on time to clear it.',
        sad: 'Light showers. Emotionally.',
        sick: 'Full storm warning. This is your doing.',
      },
    },
  },
  {
    id: 'moss',
    name: 'Moss',
    vibe: 'Zen forest spirit. Gentle, patient, ancient.',
    bio: 'Moss has watched a thousand sunrises and wants to watch a thousand more — with you. No judgment, just quiet strength and very good posture.',
    colors: ['#34D399', '#22D3EE'],
    forms: [
      { name: 'Seedling', emoji: '🌱' },
      { name: 'Sprout', emoji: '🌿' },
      { name: 'Moss', emoji: '🍀' },
      { name: 'Fernkin', emoji: '🌾' },
      { name: 'Thicket', emoji: '🌳' },
      { name: 'Grovekeeper', emoji: '🌲' },
      { name: 'Oakenheart', emoji: '🪵' },
      { name: 'Wildwarden', emoji: '🦌' },
      { name: 'Elderbloom', emoji: '🌸' },
      { name: 'Forest Colossus', emoji: '⛰️' },
      { name: 'THE EVERGREEN', emoji: '🌍' },
    ],
    dialogue: {
      greeting: [
        'Good morning. The light is soft today.',
        'I grew a new leaf while you slept. Look.',
        'Breathe in. We have everything we need.',
      ],
      ring: [
        'The forest wakes. So should you.',
        'Rise gently, but rise.',
        'Even the oldest trees reach for morning light.',
      ],
      praise: [
        'Well done. Growth is quiet like this.',
        'The sunrise noticed you today. So did I.',
        'One good morning. Then another. That is how forests happen.',
      ],
      snooze: [
        'Rest is sacred. But this is not rest — this is hiding.',
        'I will wait. Trees are patient. Streaks are not.',
        'Hmm. The leaf I grew for you wilted a little.',
      ],
      moods: {
        radiant: 'I am in full bloom because of you.',
        happy: 'Roots deep, branches high. All is well.',
        sleepy: 'A little wilted… morning light would help.',
        sad: 'The canopy feels thin lately.',
        sick: 'Blight. From snooze. It is always snooze.',
      },
    },
  },
  {
    id: 'byte',
    name: 'Byte',
    vibe: 'Sarcastic digital ghost. Deadpan, judgmental, secretly devoted.',
    bio: 'Byte lives in your phone, has read your screen time report, and is unimpressed. Wake up on time and it might admit it likes you.',
    colors: ['#F472B6', '#8B5CF6'],
    forms: [
      { name: 'Bit', emoji: '▫️' },
      { name: 'Byte', emoji: '👾' },
      { name: 'Pixel', emoji: '🟪' },
      { name: 'Glitchling', emoji: '📟' },
      { name: 'Datafang', emoji: '💾' },
      { name: 'Cyberwisp', emoji: '🛸' },
      { name: 'Voltframe', emoji: '🔋' },
      { name: 'Neonshade', emoji: '🕶️' },
      { name: 'Quantum Husk', emoji: '⚛️' },
      { name: 'Singularity', emoji: '🌌' },
      { name: 'THE MAINFRAME', emoji: '🖥️' },
    ],
    dialogue: {
      greeting: [
        'Oh good, you booted up. Statistically improbable.',
        'I ran the numbers. Today has a 73% chance of being decent.',
        "Welcome back. I deleted nothing while you slept. You're welcome.",
      ],
      ring: [
        'Alarm event detected. Executing wake_up.exe. Do not resist.',
        'Your bed is a trap with pillows. I have charts.',
        'Beep. Beep. I can do this in 4K all morning.',
      ],
      praise: [
        "Wake latency: acceptable. I'm… mildly impressed.",
        'Achievement logged. Backing up this rare event twice.',
        'Statistically, you are becoming a morning person. Weird flex. Noted.',
      ],
      snooze: [
        'Snooze registered. Adding it to the permanent record.',
        'ERROR 404: discipline not found.',
        'Recalculating your potential… downward.',
      ],
      moods: {
        radiant: "System status: TRANSCENDENT. Whatever you're doing, keep doing it.",
        happy: 'All processes nominal. Vibes: cautiously good.',
        sleepy: 'Running on low power mode. Like someone else I know.',
        sad: 'Fragmented. Defrag me with an on-time wake.',
        sick: 'Corrupted by snooze events. Send help. Or coffee.',
      },
    },
  },
];

export function getSpecies(id: string | null): MonsterSpecies {
  return SPECIES.find((s) => s.id === id) ?? SPECIES[0];
}

export function stageForPower(power: number): number {
  let stage = 0;
  for (let i = 0; i < EVOLUTION_THRESHOLDS.length; i++) {
    if (power >= EVOLUTION_THRESHOLDS[i]) stage = i;
  }
  return stage;
}

export function evolutionProgress(power: number): { stage: number; pct: number; into: number; needed: number; maxed: boolean } {
  const stage = stageForPower(power);
  if (stage >= MAX_STAGE) return { stage, pct: 1, into: 0, needed: 0, maxed: true };
  const cur = EVOLUTION_THRESHOLDS[stage];
  const next = EVOLUTION_THRESHOLDS[stage + 1];
  return { stage, pct: (power - cur) / (next - cur), into: power - cur, needed: next - cur, maxed: false };
}

export function pickLine(lines: string[]): string {
  return lines[Math.floor(Math.random() * lines.length)];
}

/** Deterministic-per-day line so the greeting doesn't change on every re-render. */
export function dailyLine(lines: string[]): string {
  const day = Math.floor(Date.now() / 86_400_000);
  return lines[day % lines.length];
}
