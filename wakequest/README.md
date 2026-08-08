# WakeQuest ⏰👾

A gamified alarm clock for Android + iOS, built with Expo / React Native (one codebase, both platforms). Dark neon glassmorphic UI. You pick a starter monster; it evolves up to 10 times — powered entirely by you waking up.

## The monsters

On first launch you choose one of four starters, each with its own personality that greets you daily, taunts you when the alarm rings, praises you when you win, and guilt-trips you when you snooze:

| Monster | Personality | Evolution line (stage 0 → 10) |
|---|---|---|
| **Embyr** 🔥 | Chaotic fire gremlin, your hype beast | Spark → Cinder → … → Nova Tyrant → SUNBORN ETERNAL |
| **Nimbus** ⛈️ | Dramatic storm-cloud poet | Wisp → Puff → … → Skybreaker → EYE OF THE DAWN |
| **Moss** 🌱 | Zen forest spirit, gentle and ancient | Seedling → Sprout → … → Forest Colossus → THE EVERGREEN |
| **Byte** 👾 | Sarcastic digital ghost, secretly devoted | Bit → Byte → … → Singularity → THE MAINFRAME |

**Evolution**: on-time wake = +2 wake power, snoozed wake = +1. Thresholds run 4 → 200 wake power across 10 evolutions (~3–4 months of consistent mornings to max out). Evolution is permanent; energy/mood is the day-to-day layer (on-time +18, snooze −12).

## ⚔️ Monster Battles (face-to-face, no server)

On the Monster tab, tap **Battle**. One player shows their QR Battle Code, the other scans it with their camera — both monsters fight in an animated turn-based battle resolved deterministically from **real wake data**: stage = power, streak = attack, on-time rate = accuracy + initiative, energy = HP. Waking up on time literally trains your fighter. Works fully offline, no accounts.

## ✨ Dawn Dust economy

One soft currency, earned **only by waking up** (on-time: 10 + streak bonus; late: 4). Spend it in the Dust Shop on hats (🧢🎩👑), auras (colored glow effects on your monster), and **Streak Freezes** (60 dust, max 2 banked — auto-consumed to save your streak if you miss a day). Hard rule baked into the design: money can never buy wake success. No ads, anywhere, ever — that's the differentiator vs Alarmy.

## The game loop

1. **Alarm fires** → tap the notification → full-screen Ring screen (vibration + your monster taunting you).
2. **Dismiss = complete a challenge**: Math Gauntlet, Memory Match, Shake It Off, or Wake Typing (or "Surprise me" random).
3. **Rewards**: base 50 XP, −15 per snooze, +25 perfect-challenge bonus, all multiplied by your streak (×1.25 at 3 days → ×2.0 at 30 days). Level titles go from *Snooze Victim* to *Wake Lord*. Evolution moments get a full celebration screen.
4. **Monster tab**: mood dialogue, evolution progress bar, full evolution line with locked forms shown as ???, rename your monster.
5. **Stats tab**: streak, best streak, on-time rate, 14-day dot calendar.

Long-press any alarm card on the home screen to preview the full ring → challenge → reward flow without waiting for morning.

## Run it

```bash
cd wakequest
npm install
npx expo start        # scan QR with Expo Go (Android/iOS)
```

For store-ready builds:

```bash
npx eas build --platform android
npx eas build --platform ios
```

## Project structure

```
App.tsx                     navigation + notification tap → Ring screen
src/theme/theme.ts          design tokens (neon palette, glass, glow)
src/state/store.ts          zustand + AsyncStorage persisted game state
src/logic/xp.ts             XP curve, streak multipliers, level titles
src/logic/pet.ts            energy/mood engine
src/logic/monsters.ts       4 species × 11 forms, personalities, evolution thresholds
src/logic/alarms.ts         expo-notifications scheduling (weekly/one-shot/snooze/bedtime)
src/logic/battle.ts         deterministic battle engine + QR payload encode/decode
src/logic/economy.ts        Dawn Dust rewards, cosmetics catalog, streak freeze rules
src/components/             GlassCard, NeonButton, XPBar, MonsterAvatar
src/screens/                Starter, Home, AddAlarm, Ring, Challenge, Reward, Monster,
                            Stats, BattleSetup, Battle, Shop
src/challenges/             the four minigames
```

## 🛡️ Native Android alarm module (the reliability layer)

`modules/wakequest-alarm/` is a local Expo module (Kotlin) that makes Android alarms **actually reliable**:

- `AlarmManager.setAlarmClock()` — the same API as the stock clock app: exempt from Doze and battery optimization, shows the system alarm indicator, survives the app being killed.
- **Full-screen ring activity** over the lock screen (turns the screen on, loops the system alarm sound on the ALARM audio stream, vibrates, back button disabled). "START CHALLENGE" hands off to the React Native Ring screen with the alarm id.
- **Boot receiver** re-registers all alarms after a reboot; weekly repeats self-reschedule natively after each fire.
- expo-notifications still schedules in parallel everywhere as the cross-platform safety net; the JS wrapper (`src/logic/nativeAlarm.ts`) no-ops gracefully on iOS and in Expo Go.

**Building it** (native code ⇒ Expo Go won't include it):

```bash
npx expo prebuild --platform android   # or: npx expo run:android
npx eas build --platform android       # production
```

## Honest platform caveats

- **Android is now solved** via the native module (dev client / production builds only — in Expo Go you still get the notification fallback).
- **iOS remains notification-based by OS policy** — Apple does not allow third-party full-screen alarms. Sound stops after ~30s unless the app is foregrounded (the Ring screen vibrates continuously). This limitation applies to every alarm app on iOS, including Alarmy.
- Test on a physical device — simulators don't do notifications/accelerometer well.

## Built-in growth features

- **Share button** on every reward screen ("Day 14 🔥 — beat my streak. #WakeQuest")
- **QR battles** — the face-to-face moment that markets itself
- **Bedtime reminders** — nightly streak-protection nudge (toggle on Stats tab)
- **Streak freezes** — Duolingo-style loss-aversion, earnable not paid-only

## Roadmap (not yet built)

- **Home/lock-screen widget** — monster mood + streak (Finch's #1 retention driver; needs native module)
- **Eggs + collection book** — hatch new species at streak milestones, rarity tiers
- **Room-code online battles** via Supabase realtime → guilds, leaderboards, streak duels
- **Share cards as images** (react-native-view-shot) for IG/TikTok, creator templates
- **Remote config + seasonal event monsters** for live-ops
- "Shame mode": auto-post to a group chat if you snooze 3×

---
*Built July 2026. Not medical advice; consult your pillow.*
