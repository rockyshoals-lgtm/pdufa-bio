# Idle/Incremental RPG — Shippable Product Plan

*Prepared for David · July 2026 · A realistic scope, tech, monetization, and milestone plan for a solo dev building with Claude + Fable.*

---

## 0. The bet, in one paragraph

Idle/incremental RPGs are the single best genre fit for a solo developer working with AI. They are **math-heavy and animation-light** (your code strength, minimal art burden), they **retain absurdly well** (a benchmarked idle RPG hit **D1 76.8% / D29 46.1%** vs. an industry D30 under 4%), and they **monetize through a hybrid model** (IAP + rewarded ads) that runs passively once tuned. The realistic catch is not the build — it's **user acquisition** and **live-ops**. This plan is designed to minimize both: ship a tight premium-flavored hybrid, lean on organic/ASO and one recurring content system instead of a daily live-ops treadmill.

---

## 1. Core loop

The genre's whole job is a satisfying **number-go-up** loop with meaningful decisions layered on top:

1. **Auto-battle** — your hero/party fights waves automatically, earning gold + XP.
2. **Spend** — upgrade heroes, gear, and skills; each upgrade makes the next wave faster.
3. **Wall** — progress slows at a boss/tier gate, forcing a choice.
4. **Prestige / Ascend** — reset progress for a permanent multiplier (meta-currency). This is the retention engine — the "just one more run" hook.
5. **Offline earnings** — the game keeps earning while closed (capped), so opening the app is always rewarding. *Cap the offline window deliberately (e.g., 8–12h) to drive daily returns.*

**Decision layers that make it an *RPG*, not just a clicker:** hero collection, party composition/synergy, gear with affixes, a skill tree, and elemental/class counters. The depth lives in *choices*, not reflexes.

---

## 2. Game systems (the design)

| System | v1 design | Why |
|---|---|---|
| **Progression** | Infinite stage ladder with boss gates every 10 stages | Classic idle spine, endless content from formulas |
| **Meta-currency (prestige)** | "Ascend" for souls → permanent % multipliers | The core retention loop |
| **Heroes** | 8–12 collectible heroes, 3 classes, gacha-lite pull with soft pity | Collection = spend motivation + variety |
| **Gear** | Slots with rarity + 1–2 affixes, auto-equip-best button | Depth without micromanagement fatigue |
| **Skill tree** | Small (~30 nodes) per hero | Meaningful build choices |
| **Currencies** | Gold (soft), Gems (premium), Souls (prestige) | Standard, legible 3-currency economy |
| **Offline** | Earns at ~50% of active rate, capped at 8h (raise cap via ad/IAP) | Drives returns + a clean monetization lever |
| **Live content** | Weekly rotating "event dungeon" generated procedurally | ONE recurring system = low babysitting |

**Economy math is the real product.** Idle games live or die on their growth-rate tuning (cost curves, multiplier stacking, prestige pacing). This is exactly the kind of spreadsheet-driven balancing I can build and simulate for you — we model the curves in Python, then port the tuned constants into the game.

**Theme hook (open):** your whole stack is Norse-named (ODIN, GUNGNIR, BIFROST) — a **Norse-mythology idle RPG** (climb Yggdrasil, ascend realms, "9 Realms" is *right there*) would be on-brand and thematically rich. Alternatives: dungeon/fantasy, sci-fi lab tycoon, or roguelite dungeon idler. Theme is your creative call; it barely changes the code.

---

## 3. Monetization design (grounded in 2026 data)

Idle RPGs win with an **IAP-dominant hybrid** — roughly **80/20 IAP-to-ads**. Benchmarks:

- **Blended ARPDAU** for tuned idle/RPG hybrids: **$0.15–$0.50**. Non-payers throw off $0.08–$0.15 via rewarded ads; payers add $0.30+ on top.
- **Rewarded video eCPM: ~$16–20.** Offerwall eCPM is far higher (**$400–530**) — worth adding once you have scale.
- **Rewarded ads are a spend accelerant, not just ad revenue:** players who engage rewarded ads are **~4x more likely to make an IAP**, with observed spend lifts of **+326%**.
- **60%+ of top-grossing games run hybrid** — single-model is leaving money on the table.

**What to actually build for v1:**

- **Rewarded ads (player-initiated only, never forced):** "2x offline earnings," "instant chest," "skip to next boss," "double this reward." These feel generous, not intrusive.
- **IAP:** remove-ads ($3–5 one-time), gem packs, a **$1–5 starter pack** (best-converting SKU in the genre), and a **season pass / battle pass** (~$5–10) once you have a content cadence.
- **No forced subscriptions.** They hurt trial-start in games; a battle pass is the "recurring" equivalent that fits the genre.

**Residual-income read:** the retention is the good news (idle players stick for months, so revenue compounds). The honest part: **games need scale** to matter, and scale = user acquisition. Plan to earn via ASO/organic + a small ad-spend test, not a viral miracle.

---

## 4. Tech stack (chosen for "you + Fable can troubleshoot")

Your top requirement — that you and a coding model can fix bugs fast — points to one answer:

### ✅ Primary recommendation: **Phaser 3 + TypeScript → Capacitor** (web-first, wrapped to mobile)

- **Why it wins for AI dev:** Phaser is the framework LLMs know best — its repo literally states "every major frontier LLM was trained on Phaser," and it ships agent skills for Claude/Cursor. Plain TypeScript/web code is the *easiest thing for me and Fable to read, run, and patch*. I can build and test the game logic directly in my sandbox and hand you a playable web build.
- **One codebase → iOS + Android** via **Capacitor** (wraps the web app; plugins exist for AdMob and in-app purchases).
- **Distribution flexibility:** also runs as a web/PWA build for free, so you can soft-launch on the open web before the stores.

### ⚖️ Strong alternative: **Godot 4.6** (native engine)

- **Godot 4.6** (Jan 2026) added **Google Play Billing, Play Games Services, Apple StoreKit 2, and AdMob** integration; MIT-licensed, **zero royalties**, best-in-class 2D pipeline, lightweight — ideal for idle games.
- **Trade-off vs. Phaser:** GDScript is less deeply "known" by LLMs than web/TS, and **I can't operate the Godot editor GUI** — you'd drive the editor while Fable and I write scripts. Better native performance and the cleanest monetization SDKs, at the cost of AI-troubleshooting smoothness.

**My call:** start in **Phaser/TS** for the prototype and MVP (fastest AI loop, web playtesting), and only consider Godot if you hit a performance/monetization-SDK wall — which an idle game almost never does.

**Backend:** none needed for v1 (all state local + cloud save via platform APIs). Add a tiny serverless layer only if/when you want leaderboards or server-validated purchases.

---

## 5. Art & audio strategy (the real bottleneck)

Code is the easy part; **visual coherence is what sinks solo games.** Idle games are forgiving here because they're icon-and-UI heavy, not animation-heavy.

- **Style:** pick a constraint-friendly aesthetic — flat/vector, pixel art, or a single AI-art style locked to one model + one prompt template for consistency.
- **Assets needed for v1:** ~12 hero portraits, ~30 gear/skill icons, a few backgrounds, UI kit, ~40 SFX, 2–3 music loops.
- **Sourcing:** AI-generated art (with a strict style guide), asset packs (itch.io, Kenney, Synty-style 2D), or a small paid commission for hero portraits (the one place hand-made pays off). SFX/music from royalty-free libraries or generators.
- **I can help** generate icon sets, write the style guide, and organize assets — but **you own the art-direction decisions** (the taste call).

---

## 6. MVP scope (v1.0) — ship small, then grow

**In:** core auto-battle loop · stage ladder + bosses · 8 heroes · gear + auto-equip · one prestige layer · offline earnings · rewarded ads + remove-ads IAP + starter pack + gem packs · cloud save · one procedural event dungeon.

**Cut from v1 (add post-launch):** battle pass, guilds/social, PvP, second prestige layer, live events calendar, offerwall, additional hero classes.

**Definition of "shippable":** the core loop is fun for ~2 hours, prestige feels rewarding, monetization SKUs work end-to-end, and it passes store review. That's it — idle games grow *after* launch through content updates, not a giant v1.

---

## 7. Milestone roadmap

Rough calendar for a part-time solo dev + AI. Compress if full-time.

| Phase | What | Output | ~Time |
|---|---|---|---|
| **0 · Prototype** | Core loop in Phaser: auto-battle, gold, upgrades, one prestige | Playable web build, "is it fun?" | 1–2 wks |
| **1 · Economy tuning** | Model cost/growth curves in Python, simulate 100 prestiges, port constants | Balanced, non-broken progression | 1 wk |
| **2 · Vertical slice** | Add heroes, gear, skill tree, offline, real UI/art pass | Feels like a real game | 3–5 wks |
| **3 · Monetization** | AdMob + IAP via Capacitor plugins, remove-ads/starter/gems, cloud save | Money plumbing works | 2–3 wks |
| **4 · Content + polish** | Event dungeon, tutorial/onboarding, juice (numbers popping, sfx), settings | Store-ready build | 2–4 wks |
| **5 · Soft launch** | Release in 1–2 small markets (or web/PWA), watch D1/D7 + ARPDAU, fix | Real retention/rev data | 2–4 wks |
| **6 · Global launch** | ASO, store listing, screenshots, small UA test | Live in stores | 1–2 wks |
| **7 · Live-ops (light)** | Weekly event refresh, monthly hero/content drop, tuning | Ongoing residual | recurring |

**Total to global launch: ~3–5 months part-time.** The honest 80/20: Phase 0 tells you fast whether to keep going.

---

## 8. Division of labor

| Task | Me (Claude/Cowork) | Fable | You |
|---|---|---|---|
| Game design / systems / economy math | ✅ lead | ✅ | ✅ decide |
| Code (game logic, save, combat, procedural) | ✅ build & test | ✅ heavy lifting | review/run |
| Economy simulation in Python | ✅ | ✅ | validate |
| Debugging / patches | ✅ | ✅ | reproduce |
| Art direction / taste calls | assist | — | ✅ own |
| Asset generation/organization | ✅ | — | curate |
| Capacitor build / device testing | guidance | code | ✅ run locally |
| App Store / Play accounts + submission | guidance | — | ✅ must do |
| AdMob / IAP account setup | guidance | — | ✅ must do |
| Marketing / ASO / community | ✅ copy & strategy | — | ✅ execute |

**The three things only you can do:** run the build tooling on your machine, hold the developer/ad/IAP accounts, and make the taste/art-direction calls. Everything code-shaped, Fable and I carry.

---

## 9. Costs & revenue reality

**Upfront (near-zero to start):**
- Apple Developer: **$99/yr** · Google Play: **$25 one-time**.
- Engine: **$0** (Phaser and Godot both free).
- Art/audio: **$0–500** depending on AI vs. commissioned.
- Optional UA test: a few hundred dollars to read early metrics.

**Revenue realism:** idle retention compounds, but income scales with installs. At a blended **$0.15–$0.50 ARPDAU**, 1,000 daily-active users ≈ **$150–500/day**; the whole game is a machine for turning installs into retained DAU. Don't quit on ad revenue alone — the IAP layer (esp. starter pack + battle pass) is where idle games actually earn.

---

## 10. Risks & the babysitting truth

- **Live-ops is the babysitting tax.** Even a "light" cadence means a weekly event refresh + monthly content or players churn. The single procedural event system in v1 is designed to make this a few hours, not a full-time job.
- **UA is the hard part, not the code.** Building it is very doable; *getting installs* is the real challenge for every indie game. Budget time for ASO and organic (TikTok/Reddit/short-form gameplay clips).
- **Store compliance & SDK breakage.** OS updates and ad-SDK changes occasionally break builds — the recurring maintenance that SaaS avoids. Web/Capacitor keeps most of this in patchable JS.
- **Balancing exploits.** Idle economies get broken by clever players; expect a few tuning patches post-launch.
- **Opportunity cost.** Reality check vs. your last question: this is **more hands-on than the pdufa.bio/API ideas.** Worth doing if you *want* to build a game — less optimal if pure passive income is the only goal.

---

## 11. Immediate next step

The fastest way to de-risk everything above is **Phase 0**: I build a **playable Phaser prototype of the core loop** — auto-battle, gold, upgrades, one prestige reset — that you can open in a browser and feel within one session. If the "one more prestige" hook grabs you, we commit; if not, we've spent an afternoon, not a quarter.

**Say the word and I'll start the prototype** (and, if you like, model the economy curves in parallel so the numbers feel right from day one).

---

*Sources: [Playio rewarded-ad benchmarks 2026](https://blog.playio.co/rewarded-ad-benchmarks-2026), [Game Growth Advisor F2P models 2026](https://gamegrowthadvisor.com/blog/2026-04-02-f2p-monetization-models-comparison-2026/), [Gamigion idle engagement](https://www.gamigion.com/idle/), [AppRadar mobile engines 2026](https://appradar.com/blog/mobile-game-engines-development-platforms), [Ziva solo game dev tools 2026](https://ziva.sh/blogs/solo-game-development), [ax0x — best engine for AI](https://blog.ax0x.ai/best-game-engine-for-ai). Informational planning document, not a guarantee of revenue.*
