/**
 * Wormwood Hollow — tuning constants.
 *
 * These values reproduce the M0 prototype's demo-tuned feel (per-second pacing so
 * the loop is legible in a short sitting). The Fable Build Brief §7 lists a slower
 * "production" tuning (per-minute days, hour-based offline cap); switch DAY_PER_REAL_SEC
 * and OFFLINE_CAP_DAYS when moving off demo pace. All game math reads from here so
 * balancing never requires touching systems code.
 */
export interface Config {
  TICK_MS: number;
  /** in-game days elapsed per real second (idle pacing knob) */
  DAY_PER_REAL_SEC: number;
  /** wardStrength lost per in-game day */
  WARD_DECAY_PER_DAY: number;
  /** rot points per in-game day at zero ward */
  ROT_BASE_RATE: number;
  /** offline accrual + rot are capped at this many in-game days ("salt only holds so long") */
  OFFLINE_CAP_DAYS: number;
  /** minimum real seconds away before a Come Morning report is shown */
  OFFLINE_MIN_SEC: number;
  /** age thresholds (in-game days) for each life-stage */
  STAGE_DAYS: { child: number; youth: number; grown: number; keeper: number };
  /** fraction of a keeper's lore carried to the bloodline on prestige */
  INHERIT_RATE: number;
  /** fraction of depthCleared kept across generations */
  DEPTH_KEEP: number;
  /** permanent production multiplier contributed per point of inherited lore */
  LORE_MULT: number;
  /** rot value at which the hollow falls (forced lineage pass) */
  ROT_FALL: number;
  /** number of Depths / binding runes */
  DEPTHS: number;
  /** localStorage save key */
  SAVE_KEY: string;
  /** save schema version */
  SAVE_VERSION: number;

  // --- action tuning (see content/actions.ts) ---
  SALT_PER_LAY: number;
  WARD_PER_LAY: number;
  DRAW_SALT_GAIN: number;
  DRAW_SALT_PROD: number;
  FORAGE_HERB_GAIN: number;
  FORAGE_HERB_PROD: number;
  SMELT_IRON_GAIN: number;
  SMELT_IRON_PROD: number;
  IRON_PER_HANG: number;
  WARD_PER_HANG: number;
  STUDY_LORE_PROD: number;
  TREELINE_ROT: number;
  EXPEDITION_HERB_COST: number;
  EXPEDITION_ROT_CLEAR: number;
  EXPEDITION_ROT_PENALTY: number;
  EXPEDITION_RUNE_CHANCE: number;
  /** odds subtracted when the descent is a boss encounter */
  BOSS_ODDS_PENALTY: number;
  /** extra rot on a failed boss encounter */
  BOSS_ROT_PENALTY: number;
  /** rot cleared / rune chance when patrolling the already-cleared deep (depth maxed) */
  DEEP_PATROL_ROT_CLEAR: number;
  DEEP_PATROL_RUNE_CHANCE: number;
  /** lore required (true-name knowledge) for the Unmake ending */
  ENDING_UNMAKE_LORE: number;
}

export const CONFIG: Config = {
  TICK_MS: 1000,
  DAY_PER_REAL_SEC: 0.4,
  WARD_DECAY_PER_DAY: 3.0,
  ROT_BASE_RATE: 2.4,
  OFFLINE_CAP_DAYS: 12,
  OFFLINE_MIN_SEC: 45,
  STAGE_DAYS: { child: 0, youth: 20, grown: 50, keeper: 100 },
  INHERIT_RATE: 0.25,
  DEPTH_KEEP: 0.5,
  LORE_MULT: 0.02,
  ROT_FALL: 100,
  DEPTHS: 9,
  SAVE_KEY: 'wormwood_v1',
  SAVE_VERSION: 2,

  SALT_PER_LAY: 5,
  WARD_PER_LAY: 14,
  DRAW_SALT_GAIN: 6,
  DRAW_SALT_PROD: 0.04,
  FORAGE_HERB_GAIN: 4,
  FORAGE_HERB_PROD: 0.05,
  SMELT_IRON_GAIN: 2,
  SMELT_IRON_PROD: 0.03,
  IRON_PER_HANG: 3,
  WARD_PER_HANG: 24,
  STUDY_LORE_PROD: 0.05,
  TREELINE_ROT: 8,
  EXPEDITION_HERB_COST: 4,
  EXPEDITION_ROT_CLEAR: 15,
  EXPEDITION_ROT_PENALTY: 10,
  EXPEDITION_RUNE_CHANCE: 0.4,
  BOSS_ODDS_PENALTY: 0.15,
  BOSS_ROT_PENALTY: 8,
  DEEP_PATROL_ROT_CLEAR: 8,
  DEEP_PATROL_RUNE_CHANCE: 0.4,
  ENDING_UNMAKE_LORE: 200,
};

export const STAGE_ORDER = ['child', 'youth', 'grown', 'keeper'] as const;
