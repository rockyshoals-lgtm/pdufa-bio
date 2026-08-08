# WORMWOOD HOLLOW — Build Brief for Fable

**Audience:** Fable (coding model) picking this up to build the game.
**Status:** Design locked, prototype started. This document is self-contained — you can build from it alone. Deeper lore in `docs/Story_Bible.md`; business/plan context in `docs/Product_Plan.md`; a runnable core-loop demo is in `prototype/index.html`.

---

## 0. How to use this doc

Read §1–§8 to understand *what* we're building and *how the loop works*, then §10–§12 for *file structure, conventions, and the ordered backlog*. Start at Milestone **M1** (§12); **M0 is already done** (the prototype). Keep the game feel: **Ozark folk-gothic dread**, quiet and patient, never splatter.

---

## 1. Vision & locked decisions

**Elevator:** An **idle-horror hybrid 2D RPG**. You play a child raised in a hollow of the Arkansas Ozarks, taught to salt the doorways against a thing no one will name. Over a lifetime (and across generations of your bloodline) you fight a slow blight — **the Rot** — seeping from a Norse-bound worm-god chained under the mountain. The idle layer *is* the horror: while you're away, the wards decay and the Rot creeps up the hollow.

**Locked:**
- **Genre/loop:** idle-horror hybrid (expeditions + real-time/offline Rot creep). NOT a twitch action game.
- **Protagonist:** a Hollow-born child who **grows up** (child → youth → grown → keeper). Life-stage = progression tier.
- **Prestige = generations:** one run = one keeper's life; on death/age-out you pass the salt to the next child and the *bloodline* inherits a fraction of lore/progress.
- **Tone:** folk-gothic, dread over gore. Mythos = Ozark folklore (surface) + Norse binding-legend (deep).
- **Title (working):** *Wormwood Hollow*.

---

## 2. Tech stack (and why)

| Layer | Choice | Why |
|---|---|---|
| Language | **TypeScript** | Type-safe game state; best AI-troubleshooting surface |
| Idle/meta UI | **HTML/CSS DOM** (framework-light; plain TS or lightweight Preact) | Idle games are number/UI-heavy; DOM is simplest to build, patch, and reason about |
| Expedition/cave scenes | **Phaser 3** (canvas) | 2D tile scenes for the descents; LLM-friendly, huge training coverage |
| Build | **Vite** | Fast dev server, trivial config |
| Mobile wrap | **Capacitor** | One codebase → iOS/Android; plugins for AdMob + IAP |
| Persistence | **localStorage** (prototype) → Capacitor Preferences / file (mobile) | Idle games need offline persistence + timestamped catch-up |

**Rule:** the meta/idle layer (wards, resources, Rot clock, generations) is DOM+TS and must be fully playable without Phaser. Phaser is layered in only for the cave-expedition scenes. The prototype already proves the meta layer.

---

## 3. Architecture

```
Game (singleton controller)
├── GameState              // all persisted data (see §5)
├── Clock                  // real-time tick + offline elapsed calc
├── systems/
│   ├── WardSystem         // salt/iron wards; decay; holds back Rot
│   ├── RotSystem          // corruption meter; advance rate = f(wardStrength, depthCleared)
│   ├── ResourceSystem     // salt, iron, herbs, lore; production over time
│   ├── ActionSystem       // player actions (lay salt, forage, smelt, study, expedition)
│   ├── LifeSystem         // aging, life-stage gating of actions
│   ├── LineageSystem      // generation prestige; inherited carryover
│   └── ExpeditionSystem   // descent runs into the 9 Depths (Phaser scene later)
├── save/ SaveManager      // serialize GameState + lastSeenTimestamp; offline catch-up
└── ui/                    // DOM views: HollowView, ActionBar, Log, ComeMorningReport
```

**Golden pattern (idle correctness):** never simulate every offline tick. On load, read `elapsedMs = now - state.lastSeen`, then **closed-form** advance Rot, decay wards, accrue resources, and age the keeper. Show the player a **"Come Morning"** report summarizing what changed (half harvest, half bad news). This is both the offline-earnings mechanic and a core horror beat.

---

## 4. The core loop

**Active session (seconds-to-minutes):**
1. Player returns → **Come Morning** report (offline catch-up).
2. Player spends resources to **re-lay wards** (push Rot back), and queues **production** (forage/smelt/study).
3. Player optionally **runs an expedition** into the next Depth (risk/reward; yields lore, runes, cleared ground).
4. Time passes (real-time tick); Rot creeps, wards decay. Player logs off.

**Lifetime (the meta arc):** total elapsed time ages the keeper through life-stages, unlocking actions and raising stakes, until death/age-out → **Lineage** prestige → next child begins, stronger.

**Win condition:** across generations, descend far enough and gather enough true-name lore to **re-cut the master-rune** at Depth 9 in a single keeper's life.

---

## 5. Game state (data model — starting TypeScript)

```ts
type Resource = 'salt' | 'iron' | 'herbs' | 'lore';
type LifeStage = 'child' | 'youth' | 'grown' | 'keeper';

interface GameState {
  version: number;
  lastSeen: number;              // epoch ms, for offline catch-up
  createdAt: number;

  // Keeper (current life)
  keeperName: string;
  ageDays: number;               // in-game days lived this life
  stage: LifeStage;

  // Bloodline (persists across generations)
  generation: number;            // 1, 2, 3...
  inheritedLore: number;         // carryover currency (permanent multiplier source)
  bloodlineName: string;

  // The Hollow
  rot: number;                   // 0..100 corruption of the hollow
  wardStrength: number;          // 0..100 how well the salt/iron line holds
  depthCleared: number;          // 0..9 how deep the caves are pushed back

  // Resources
  resources: Record<Resource, number>;
  production: Record<Resource, number>; // per in-game day, from queued work

  // Progress
  runesRecovered: number;        // 0..9 binding fragments (the win track)
  flags: Record<string, boolean>;// story beats, boss states
  log: string[];
}
```

---

## 6. Systems spec

**Wards (salt/iron):** `wardStrength` decays at `WARD_DECAY_PER_DAY`. Laying salt spends `salt` to add ward. Ward is the dam that slows the Rot.

**Rot:** advances per in-game day by `ROT_BASE_RATE * max(0, 1 - wardStrength/100) * depthPressure`, where `depthPressure = 1 + depthCleared*0.15` (deeper you dig, more it seeps). Rot at 100 = a **losing spiral** event (the hollow falls → forced early lineage pass). Rot is pushed *down* by clearing ground on expeditions and by strong wards.

**Resources & production:** `forage → herbs`, `smelt → iron`, `harvest/trade → salt`, `study → lore`. Production accrues per in-game day (works offline — the "harvest" half of Come Morning).

**Actions (gated by life-stage):**
| Action | Child | Youth | Grown | Keeper | Effect |
|---|:-:|:-:|:-:|:-:|---|
| Lay Salt | ✅ | ✅ | ✅ | ✅ | −salt, +wardStrength |
| Forage / Chores | ✅ | ✅ | ✅ | ✅ | +herbs/+salt production |
| Smelt Iron | | ✅ | ✅ | ✅ | +iron, stronger wards |
| Study remedy-book | ✅(slow) | ✅ | ✅ | ✅ | +lore |
| Cross the Treeline (transgression beat) | | ✅ | ✅ | ✅ | unlocks expeditions; first Rot breach |
| Run Expedition | | | ✅ | ✅ | descend a Depth; risk; +lore/+rune, −rot |
| Re-cut Rune (endgame) | | | | ✅ | consume lore+rune at Depth 9 → ending |
| Pass the Salt (prestige) | | | | ✅ | end life → next generation |

**Life-stages (LifeSystem):** age thresholds in in-game days (see §7). Each transition fires a flavor beat and unlocks the row above.

**Lineage (prestige):** on Pass the Salt / death, compute `inheritedLore += floor(lore * INHERIT_RATE) + runesRecovered`; reset keeper life fields; keep `depthCleared` partially (`floor(depthCleared * DEPTH_KEEP)`), bump `generation`. New keeper starts with a permanent multiplier `1 + inheritedLore * LORE_MULT`.

**Expeditions (ExpeditionSystem):** a run into `depthCleared+1`. Prototype = a resolved risk event (chance of injury vs. reward scaled by wardStrength/resources). Later = a Phaser tile scene with resource drain, enemies (the blighted), and a boss at each Depth (§9).

---

## 7. Starting tuning constants (put in `src/config.ts` — tune later)

```ts
export const CONFIG = {
  TICK_MS: 1000,                 // real-time tick
  DAY_PER_REAL_MIN: 1,           // 1 in-game day per real minute (idle pacing knob)
  WARD_DECAY_PER_DAY: 4,         // wardStrength lost/day
  ROT_BASE_RATE: 2.0,            // rot points/day at zero ward
  SALT_PER_LAY: 5, WARD_PER_LAY: 12,
  OFFLINE_CAP_HOURS: 12,         // Come Morning caps accrual + Rot (drives daily return)
  STAGE_DAYS: { child: 0, youth: 30, grown: 90, keeper: 240 },
  INHERIT_RATE: 0.25, DEPTH_KEEP: 0.5, LORE_MULT: 0.02,
  ROT_FALL_THRESHOLD: 100,       // hollow falls -> forced lineage pass
  DEPTHS: 9,
};
```

---

## 8. Content hooks

- **9 Depths** under Bald Knob = the difficulty ladder (Story Bible §11/§7). Each has a name, a hazard, and a boss.
- **4 named bosses** (Story Bible §9): Granny-Witch Bledsoe, the Blighted Preacher Ezekiel, the Miller, the Gowrow. Each guards a **rune fragment**.
- **Flavor system:** a `FlavorBank` keyed by event (`onReturn`, `onRotRise`, `onStageUp`, `onWardBreak`, `onExpeditionWin/Loss`, `onGenerationPass`). Pull Ozark-gothic one-liners; Old Gnaw whispers at high Rot. Seed lines from Story Bible §3 & §14.
- **Endings (3):** Re-bind / Unmake / Inherit (Story Bible §11).

---

## 9. Project structure (target)

```
WormwoodHollow/
├── Fable_Build_Brief.md      ← you are here
├── README.md
├── docs/  Story_Bible.md  Product_Plan.md
├── prototype/ index.html    ← runnable M0 demo (no build)
├── src/                     ← Vite + TS app (build here from M1)
│   ├── main.ts
│   ├── config.ts
│   ├── state.ts
│   ├── systems/ …
│   ├── ui/ …
│   ├── content/ flavor.ts  depths.ts  bosses.ts
│   └── scenes/  (Phaser, from M3)
├── index.html
├── package.json  vite.config.ts  tsconfig.json  capacitor.config.ts
└── assets/  (art/audio, later)
```

---

## 10. Conventions

- TypeScript strict mode. Pure functions for all state transitions (`(state, input) => state`) so systems are unit-testable and offline catch-up reuses the same math.
- **All time math in one place** (`Clock` + `SaveManager`). Never trust wall-clock without clamping (`OFFLINE_CAP_HOURS`, guard against clock-rollback/cheating).
- Keep meta layer Phaser-free. UI reads state, dispatches actions; never mutate state in views.
- Deterministic seeded RNG for expeditions (reproducible bugs).
- No secrets/keys in client. Ads/IAP via Capacitor plugins behind an interface so they're stubbable in web builds.

---

## 11. Definition of done — vertical slice

A player can: get a **Come Morning** report → lay wards → queue production → age from child to youth to grown → run an expedition that clears a Depth and drops a rune → have the Rot visibly threaten if neglected → **Pass the Salt** and start Gen 2 measurably stronger. Runs in-browser and as a Capacitor Android build. Ad/IAP stubs wired (not live).

---

## 12. Backlog (ordered)

- **M0 — Core-loop prototype** ✅ *(done: `prototype/index.html` — DOM idle loop, Rot/ward, actions, expeditions, aging, generations, offline catch-up, localStorage.)*
- **M1 — Port to Vite+TS project.** Recreate the prototype loop as typed systems (§3/§5/§6) with unit tests on the offline-catch-up + Rot/ward math. *Start here.*
- **M2 — Content & feel.** FlavorBank (Ozark-gothic lines), the 4 bosses as resolved encounters, 9 Depths data, the 3 endings, save-versioning/migration, tutorial (the §14 "Salt Line" opening).
- **M3 — Phaser expedition scenes.** Tile-based descents: movement, resource drain, the blighted enemies, per-Depth boss fight; hand results back to the meta layer.
- **M4 — Monetization + mobile.** Capacitor build; AdMob rewarded ("2x the harvest," "re-lay the wards"), IAP (remove-ads, salt/iron packs, a season "Turning"); soft-launch instrumentation.

---

*Design owner: David. This brief + the two docs in `docs/` + the prototype are the complete handoff. Build folk-gothic, build patient, build the dread into the idle.*
