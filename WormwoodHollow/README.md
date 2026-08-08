# Wormwood Hollow

An **idle-horror hybrid 2D RPG** — Ozark folk-gothic dread with a Norse binding-legend underneath. You play a child raised in a hollow of the Arkansas Ozarks, taught to salt the doorways against a thing no one will name, and you fight a slow blight (**the Rot**) across a lifetime and down a bloodline.

## What's in this folder

```
WormwoodHollow/
├── Fable_Build_Brief.md     ← START HERE (handoff for the coding model): stack, architecture,
│                               data model, core-loop spec, conventions, ordered backlog M0–M4
├── prototype/index.html     ← PLAYABLE core-loop demo (no install — just open it)
├── docs/
│   ├── Story_Bible.md        ← world, villain (Níðgrímr / Old Gnaw), 9 depths, bosses, endings, prologue
│   └── Product_Plan.md       ← genre/monetization/tech rationale
└── src/                      ← Vite+TS build (Milestone M1 — DONE). See "Run the M1 build" below.
```

## Run the M1 build

The meta/idle layer is now a typed Vite + TypeScript project (framework-free DOM UI).

```bash
npm install
npm run dev        # local dev server (hot reload)
npm run build      # typecheck + production build to dist/
npm run test       # 44 unit tests (Vitest): offline/Rot/ward/lineage math + M2 content
npm run typecheck  # tsc --noEmit
```

### M1 source map

```
src/
├── config.ts              tuning constants (all game math reads from here)
├── state.ts               GameState types + newLife factory + helpers
├── rng.ts                 deterministic seeded RNG (mulberry32)
├── core/
│   ├── advance.ts         advanceDays — the one closed-form time transition (live + offline)
│   ├── clock.ts           elapsed math, offline cap, clock-rollback guard
│   ├── dispatch.ts        applyAction — the one place actions are applied (pure)
│   └── game.ts            Game controller: tick loop, offline catch-up, prestige, hooks
├── systems/               pure transitions: rot, ward, resource, life, lineage, expedition
├── content/               actions, flavor (FlavorBank + whisper tiers), names,
│                          depths (9), bosses (4 Lords), endings (3), prologue
├── save/SaveManager.ts    localStorage (browser) / in-memory (tests) + v1→v2 migration
└── ui/                    styles.css, dom.ts, view.ts (reads state, dispatches actions)
tests/                     advance, clock, life, lineage, expedition, dispatch, save,
                           content, bossExpedition, endings, migration
```

## M2 — content & feel (DONE)

Layered onto the M1 loop:

- **9 Depths** (`content/depths.ts`) under Bald Knob, each with a name + hazard line, from the Root Cellar down to the Bottom of the World.
- **4 Lords** (`content/bosses.ts`) — Brother Ezekiel (drowned church, D3), the Miller (D4), Granny-Witch Bledsoe (D5), and the Gowrow (D7). Descending onto a Lord's depth is a resolved boss encounter: harder odds, unique taunt/defeat/repel flavor, and a guaranteed rune-shard on victory. At the bottom, descents become "deep patrols" that hold the line and farm the last shards.
- **3 endings** (`content/endings.ts`) at the master-rune — **Re-bind** (continue the cycle, flood the bloodline with lore), **Unmake** (true ending; needs the full true name — a lore gate), **Inherit** (become the warden). Chosen via an in-game modal.
- **Expanded FlavorBank** (`content/flavor.ts`) — event-keyed Ozark-gothic lines, plus **Old Gnaw whispers that escalate with the Rot** (low → mid → high tiers), a ward-break beat, and generational-pass lines.
- **The Salt Line prologue** (`content/prologue.ts`) — the §14 opening, shown once per fresh bloodline as a paged card that lands the premise.
- **Save-versioning** — schema bumped to v2 with a real `migrate()` that backfills old (v1) saves.

All state transitions are pure `(state, input) => state` functions, so the offline
catch-up reuses the exact same math as the live tick and every branch is unit-tested.
Time math is centralized in `clock.ts` + `SaveManager`; the meta layer is Phaser-free
(Phaser enters at M3). **Next: M3 — Phaser expedition scenes.**

## Play the prototype

Double-click **`prototype/index.html`** (any modern browser — no build step, no internet). It saves to `localStorage`, so it persists and does real offline catch-up.

**Try this:**
1. As a **child**, tap *Lay the salt line* and *Draw salt* / *Forage* — watch the Ward hold the Rot back.
2. Do nothing for a bit and watch the **Rot creep** and the Ward decay. Let it run and the hollow can fall.
3. At **youth** (age 20) you can *Cross the treeline* — the transgression that unlocks the caves and breaches the ward.
4. At **grown** (age 50) *Descend into the caves* — push back a Depth, recover binding **runes**.
5. At **keeper** (age 100) *Pass the salt* — start the next generation; the bloodline keeps a slice of your lore (a permanent multiplier).
6. Hit **"Simulate: away a while"** to see the **Come Morning** report — the offline catch-up that makes idle time into dread (half harvest, half bad news).

> Time is **demo-accelerated** (~0.4 in-game days per real second) so a full life is minutes, not months. Real pacing is a one-line tune in `CONFIG` (`prototype/index.html`) and `src/config.ts` in the real build.

## For the build (Fable)

Read `Fable_Build_Brief.md`. **M0 (this prototype) is done.** Start at **M1** — port the loop to a typed Vite+TypeScript project with unit tests on the offline-catch-up and Rot/ward math, then M2 content, M3 Phaser expedition scenes, M4 Capacitor + monetization.

*Informational/educational project. Folklore grounding fictionalized from Vance Randolph's* Ozark Magic and Folklore *and regional legend.*
