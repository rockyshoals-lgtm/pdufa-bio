# BUILD_SPEC — pdufa.bio Live Radar Rebuild

_Informational and educational only — not investment advice. Odin Catalyst LLC._

## 1. Goal

Turn pdufa.bio into a **live, always-on, cross-platform dashboard** that a user can open from a Mac
(or phone, or any browser) via a URL — no dependency on a specific PC being awake, and **no way for a
viewer to corrupt the data**. Two engines, presented as two tabs/sections:

- **Momentum / Meme / UOA Radar** — whole-market micro/nano-cap movers + unusual options activity, updated as often as the UW/FMP plans allow.
- **Biotech Catalyst Analyzer** — upcoming PDUFA catalysts scored by ODIN.

## 2. Current state (what already exists)

| Thing | Where | Notes |
|---|---|---|
| pdufa.bio site source | `9realms\pdufa_site_src\` | **Static HTML + Vercel serverless (`api/`) + Stripe (`stripe@^16`) + PWA (`manifest.webmanifest`).** No React/Next framework. Pages: `index.html`, `app.html`, `calendar.html`, `pricing.html`, `product.html`, `readouts/`, `research/`, `pdufa/`, `historic.json`, etc. Deployed on Vercel (`.vercel/`). |
| Momentum scanner | `9realms\Momentum Scanner\` | Working Python reference impl (copied to `/assets`). File-based output + local dashboard. |
| Biotech analyzer UI | `/assets/biotech_catalyst_analyzer.html` | Uploaded prototype. WebSocket client only — no backend. |
| Supabase project | `pdufa-bio` (ref `dgygdomjzxizwmbokvfn`, org `jklfactpnsvfeyqmlnjg`, us-east-2, PG17) | **Currently PAUSED** — must be restored before use. |
| Vercel team | "David Moore's projects" (`team_HLoQLqGljk4BGwM2Recpsid5`) | Hosts pdufa.bio. |
| API keys | On the build machine as env vars | `FMP_API_KEY`, `UW_API_KEY`, `LUNARCRUSH_API_KEY` are set. `REDDIT_*` not set. |

## 3. Target architecture — single writer, many readers

```
          ┌────────────────────────── Vercel (pdufa.bio) ──────────────────────────┐
          │                                                                          │
  Vercel Cron ──► /api/scan-fast   (every ~60s, market hours)  ─┐                    │
  Vercel Cron ──► /api/scan-full   (every ~3m,  market hours)  ─┤ write (service key)│
          │                                                     ▼                    │
          │                                            ┌──────────────────┐          │
          │                                            │  Supabase (PG17) │  ◄─ single source of truth
          │                                            │  radar_snapshots │          │
          │                                            └──────────────────┘          │
          │                                                     ▲                    │
          │   /radar (momentum tab)  ─┐                         │ read-only (anon)   │
          │   /radar (biotech tab)   ─┴── static pages ── poll ─┘                    │
          └──────────────────────────────────────────────────────────────────────────┘
                         every browser (Mac / phone / PC) only READS
```

**Why this shape:** the site is already on Vercel with an `api/` serverless dir and a Supabase project
exists, so this reuses both. The Supabase table is the **only** thing that ever gets written, and only by
the cron jobs (using the service role key). Browsers read through the anon key with row-level security that
permits **SELECT only**. That structurally removes the "screw over the data integrity" risk: a viewer
*cannot* write, and there is never more than one writer.

### Recommended build path
**Vercel Cron + Vercel serverless functions (Node/TypeScript) + Supabase store.** Reimplement the momentum
algorithm (see `MOMENTUM_ENGINE.md`) in the serverless function. The full scan is ~500–700 sequential HTTP
calls / ~150s in the current Python; **parallelize** it (bounded concurrency, e.g. 8–10 in flight via
`Promise.all` batches) so a full enrichment finishes in ~15–30s, inside Vercel's function limit.

Alternatives (document, don't assume): **Supabase Edge Functions + `pg_cron`** (keeps compute next to the
data; Deno/TS) or a **small always-on container** running the existing Python (lowest port risk, ~$5/mo,
but needs a host the user provisions). See Open Decisions.

## 4. Update cadence + rate-limit reality

"As often as we can" is bounded by API quotas, not ambition. Design around it:

- **Fast lane (`/api/scan-fast`, ~60s):** UW flow-alerts firehose (**1 call**) + FMP `biggest-gainers` + `most-actives` (**2 calls**) = ~3 calls/run. Trivial load. Updates the movers list, UOA firehose, and 🚀 ROCKET flags quickly.
- **Full enrichment (`/api/scan-full`, ~3 min):** per-candidate quote/options/short/news/social. This is the heavy one.
- **Run market-hours only** (Mon–Fri 9:30–16:00 ET). Off-hours the tape is stale anyway. This alone cuts daily call volume ~4×.
- **Cache slow-moving data** to keep the 3-min cycle cheap:
  - Short interest → changes ~daily. Fetch **once/day**, cache.
  - Social (LunarCrush/StockTwits/ApeWisdom) → refresh every ~15 min, cache.
  - Company profile/sector/`averageVolume` → near-static. Cache per session/day.
  - So the 3-min cycle mostly refreshes **quote + per-name options volume + the firehose** — the fast-moving signals.
- **UW limit:** ~120 requests/minute plus daily caps that vary by plan (user is on Retail Pro + API Basic). **Verify the actual daily cap before locking cadence** and throttle to stay under it. FMP limits depend on the FMP plan tier — verify too.

## 5. Data model (Supabase)

Append-only snapshots + a "latest" view. Keeping history enables the backlog item "do ROCKET flags precede
outsized next-day moves?" without look-ahead.

```sql
create table if not exists radar_snapshots (
  id           bigint generated always as identity primary key,
  engine       text not null check (engine in ('momentum','biotech')),
  generated_at timestamptz not null,
  payload      jsonb not null,
  created_at   timestamptz not null default now()
);
create index on radar_snapshots (engine, generated_at desc);

-- newest snapshot per engine (what the frontend reads)
create or replace view latest_snapshot as
  select distinct on (engine) engine, generated_at, payload
  from radar_snapshots order by engine, generated_at desc;

-- read-only for the public anon role; writes only via service role (cron)
alter table radar_snapshots enable row level security;
create policy "public read" on radar_snapshots for select using (true);
-- (no insert/update/delete policy => anon cannot write; service_role bypasses RLS)
```

`payload` for `engine='momentum'` = the scan JSON documented in `MOMENTUM_ENGINE.md` (see
`/assets/sample_momentum_scan.json` for a real example). `payload` for `engine='biotech'` = the array shape
documented in `BIOTECH_ENGINE.md`.

## 6. Frontend integration into pdufa.bio

- Add a **`/radar`** page (or two: `/radar` momentum, `/radar/biotech`) matching the existing site's plain-HTML +
  Tailwind-ish style. Reuse the nav/header/footer and PWA manifest so it feels native to pdufa.bio.
- Each page fetches `latest_snapshot` from Supabase (anon key, PostgREST or `@supabase/supabase-js`) on load
  and polls every ~30–60s. Show **"Last updated \<time\>"** and a connection state.
- Prefer **polling** over WebSockets. The uploaded biotech UI uses a `/ws` socket; replace that with a poll of
  the Supabase `latest_snapshot` — simpler, robust, no socket server to run.
- Keep the momentum dashboard's existing card/ROCKET visual language (`/assets/momentum_meme_dashboard.html`).
- **Disclaimer footer on every view.**

## 7. Secrets & config (non-negotiable)

- **Keys are environment variables / platform secrets only. Never hardcode, never commit, never expose to the client.**
  `FMP_API_KEY`, `UW_API_KEY`, `LUNARCRUSH_API_KEY` (+ optional `REDDIT_CLIENT_ID/SECRET`, `APEWISDOM` needs none).
- Set them as **Vercel Environment Variables** (for the serverless scan functions) and/or **Supabase Function Secrets**.
- The browser only ever gets the Supabase **anon** key + URL (safe, read-only via RLS). It must **never** receive FMP/UW/LC keys.
- Service role key stays server-side (cron functions only).

## 8. Compliance

- "Informational and educational only — not investment advice." on every page and in the API payload (`disclaimer` field already present in the momentum payload).
- Don't tell users to buy/sell/hold. Present data; they decide.
- Respect vendor ToS (UW, FMP, social) for redistribution/caching.

## 9. Acceptance criteria

1. A public URL loads the radar on a Mac and phone with no PC running.
2. **Momentum tab shows non-zero candidates during active market hours** (proves the `avgVolume` fix landed) and 🚀 ROCKETs can fire.
3. Biotech tab lists ODIN-scored upcoming PDUFAs with score + days-to-PDUFA.
4. Both tabs show a live "last updated" stamp and refresh on cadence.
5. RLS verified: the anon key **cannot** write; only cron (service role) writes. One writer, ever.
6. No FMP/UW/LC secret is present in any client bundle, page, or repo file.
7. Sources degrade gracefully — if UW or a social source is down, the scan skips it and still publishes.
8. Disclaimer visible on every view.

## 10. Open decisions (carried over — confirm before/at build)

1. **Build path** — Recommended: Vercel serverless + Supabase (matches existing stack). Alt: Supabase Edge Functions; or a Python container reusing `/assets/momentum_meme_scanner_v1.py` as-is.
2. **Biotech data source** — What feeds `hype_score` / `pdufa_date` / `breakdown`? Options: ODIN scores a PDUFA calendar (via the `9realms` ODIN engine / MCP `odin_rank`), or a specific calendar file/table in `Odin Perfection\` the builder should read. **Needs confirmation** — see `BIOTECH_ENGINE.md`.
3. **Social vendors to enable** — Recommended: add **ApeWisdom** (free Reddit mention velocity) and keep LunarCrush + StockTwits. Skip paid duplicates (Quiver/Finnhub) unless wanted. See `DATA_SOURCES.md`.
4. **Deploy + secrets** — Who restores the paused Supabase project and sets the Vercel/Supabase secrets. Keys must be moved into platform env, never into code.
