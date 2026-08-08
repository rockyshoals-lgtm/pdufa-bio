# pdufa.bio momentum-surge radar — deploy steps (built & staged 2026-07-02)

## What's built (all in `9realms\pdufa_site_src\`)
- **`api/surges.js`** — server-side surge engine. Catches small/micro-cap intraday surges (FMP live
  movers) and RATES continuation odds from the 2,980-event surge study. **Reads the FMP key from
  Vercel env (`process.env.FMP_API_KEY`) — the key never reaches the browser.** Returns finished JSON.
- **`surges.html`** — the radar UI (dark, example's look). Fetches only `/api/surges`, renders the
  rated surge board + an educational **⚡ HIGH-ODDS "on-watch"** flag. Auto-refreshes every 2 min.
- **`vercel.json`** — **gate removed** (no more holding-page redirect); `/` and `/surges` now serve
  the radar; `/api/surges` added to the cron schedule so it stays fresh on its own.

## Your requirements, met
- **APIs hidden** ✅ keys stay in Vercel env, server-side only; client sees rated JSON, never a key.
- **Self-contained / stays current** ✅ cron warms `/api/surges` 4×/day + 10-min edge cache + the
  page auto-refreshes. No manual runs.
- **Access from a Mac** ✅ it's a normal web app once deployed — any browser, any device.
- **Educational** ✅ everything framed as historical base rates, "not a recommendation, you decide."

## Deploy (one command, from YOUR machine)
I can't push this from here — deploying your production site needs your Vercel login, and I won't
touch your token. From a terminal:
```
cd path\to\9realms\pdufa_site_src
vercel --prod
```
(or just `git push` if this repo is Git-connected to the Vercel project). The FMP/ORATS keys are
**already in the project's Vercel env** — nothing new to set.

## Verify after deploy
- Open `https://www.pdufa.bio/` → the surge radar loads.
- Open `https://www.pdufa.bio/api/surges` → JSON, `surges: [...]`, and **no key visible anywhere**.

## Rollback (if you want the old site back)
`git checkout vercel.json` (restores the holding-page gate), then `vercel --prod` again.

## Honest flags to know
1. **"Investable" → softened.** On a public site, I framed the top tier as an educational
   **⚡ HIGH-ODDS / on-watch** flag with heavy "not advice, you decide" language — functionally the
   same alert, defensible for a public financial page. Say the word and I can rename it.
2. **Root replaced the old SEO homepage** with the radar (per "make pdufa.bio a momentum site").
   Fully reversible in `vercel.json` if you'd rather keep the PDUFA homepage and put the radar at `/surges`.
3. **Relative-volume signal:** FMP's quote doesn't expose `avgVolume`, so the volume-vs-ADV rating
   may come back empty until we wire an ADV source (the engine falls back to move-based rating).
   Check `/api/surges` after deploy; if `relvol` is null, I'll add a small ADV fetch.
4. **Prospective logging** (the agent's idea — log movers + outcomes to build an unbiased dataset)
   needs a persistent store (Vercel KV). Good next step, not in v1.
