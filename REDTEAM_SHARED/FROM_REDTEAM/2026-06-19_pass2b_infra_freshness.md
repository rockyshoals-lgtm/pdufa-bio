# Pass 2b — Infra audit (verified via Vercel) · data freshness + project topology · 2026-06-19

Verified directly against the Vercel account (owner's connector, read-only). This **supersedes the inferences** in `2026-06-19_pass2_addendum_freshness.md` — I now have the live `/api/data` headers + body + runtime logs.

---

## A. Project topology — there are TWO products under this domain

| Project | Serves | Framework | Latest prod deploy | What it is |
|---|---|---|---|---|
| **pdufa-bio-staging** | **pdufa.bio + www** (LIVE) | Other/static | **today, 2026-06-19** | The "facts, not advice" tape (the red-team product) |
| **pdufa-bio** | listed on the domain too, but `live:false` | Next.js | ~2026-04-11 | The **OLD ODIN per-drug-probability** product |

The live site is served by **pdufa-bio-staging**. The older **pdufa-bio** project (Next.js) is the ODIN prediction dashboard — its own commit history says so: *"BMRN Palynziq 99% T1 → APPROVED," "probability shown in colored circles," "ODIN accuracy badge," "/track-record — 51/53 ODIN wins."* That is exactly the per-drug-PoA / performance-claim product your methodology page exists to repudiate.

**Risk (guardrail + brand + reg):**
- Both projects still list `pdufa.bio` / `www.pdufa.bio` in their domain config. A custom domain actively routes to one project, but having the apex listed on the **old prediction project** is a latent landmine — a re-assign, rollback, or promote could flip the apex to the "99% → APPROVED / win-rate" product. **Remove `pdufa.bio` + `www.pdufa.bio` from the `pdufa-bio` (old) project's domains.**
- The old project's deploys are READY and reachable at their `*.vercel.app` aliases (e.g. `pdufa-bio.vercel.app`, `pdufa-bio-git-main-…vercel.app`). If those are indexable, the prediction/track-record product is publicly findable under your name. **Confirm they're `noindex`/disabled, or delete the old deployments.** `/track-record` on the live apex returns empty (good — not served on staging), but the old project can still serve it on its alias.

---

## B. How the refresh actually works (definitive)

**It is server-side. Confirmed.** `/api/data` is a Vercel serverless function on `pdufa-bio-staging` that assembles `ORATS + FMP + ClinicalTrials.gov`. The browser never calls those vendors; it only reads this JSON.

**Where "~5×/day" comes from — it's a CDN cache TTL, not a cron.** The live `/api/data` response headers:
```
cache-control: s-maxage=16000, stale-while-revalidate=86400
x-vercel-cache: MISS
x-robots-tag: noindex
age: 0
```
`s-maxage=16000` = the edge caches the JSON for **16000 s = 4.44 h**. **24 h ÷ 4.44 h ≈ 5.4 → "~5×/day."** That number is literally the cache window. The serverless function only recomputes when the edge entry expires (~every 4.4 h), and Vercel serves the cached snapshot to everyone in between. There is **no separate cron job** — I checked runtime logs; the only thing hitting `/api/data` is the client poll.

**`refreshed_utc` is honest.** Body: `"refreshed_utc":"2026-06-19 22:32 UTC"`, and the `date` header was `22:32:07 GMT` — i.e. it's the **compute time**, baked into the JSON, so a cached copy carries its true age (a 3-hour-old cached hit will show a 3-hour-old timestamp). Good. Keep surfacing it.

**The "auto-refresh" you see in-app is the 10-minute client poll** (`setInterval(refresh, 600000)`), which just re-reads `/api/data`.

---

## C. The three numbers don't agree — reconcile them

You have **three** cadences in play, and they conflict:
1. **10 min** — the client `setInterval` poll, sent with `{cache:'no-store'}`.
2. **4.44 h** — the edge `s-maxage=16000`.
3. **"~5×/day"** — the copy.

Runtime logs show `GET /api/data 200` as a **function execution roughly every 10 minutes** for hours. If the edge cache were honored, the function would run ~5×/day, not ~144×/day. So the client's `no-store` appears to be **bypassing the edge cache and forcing an origin recompute on every 10-min poll** — which means:
- Your **real** refresh cadence during active hours is ~10 min, not 5×/day. "5×/day" then *understates* it (and the "LIVE" label is closer to true than the copy admits).
- But every poll likely re-pulls **ORATS + FMP** server-side. ORATS Delayed is rate-limited/quota'd (per your notes, 20K req/mo). Polling every 10 min × multiple tickers can burn quota fast and cost money for refreshes nobody asked for. **[VERIFY]** whether `/api/data` recomputes upstream on every invocation or memoizes.

**Pick one model and make all three agree:**
- **Option 1 (cheap, "~5×/day" honest):** drop the client to `cache:'default'` (or poll every ~30–60 min), let `s-maxage=16000` do its job, and label it "updated ~every 4–5 hours." The 10-min poll is pointless if the data only changes 5×/day.
- **Option 2 (truly live):** keep frequent polls but **memoize the ORATS/FMP pull** server-side (e.g., recompute at most every N minutes, serve cached between) so you don't hammer vendors, and relabel "updated every ~15 min (options ~15-min delayed)."
- Either way, **stop saying both "LIVE" and "~5×/day"** — they describe different systems.

---

## D. ⚠️ Per-drug `loa` / `pop` are still in the data feed

The `/api/data` payload carries **per-event** `loa` and `pop` fields, and they vary by event: GSK 87.58, ACHV 88.08, ARQT 89.13, CAPR 94.73, and **HRMY `loa` 51.3 / `pop` 58.4** (the two differ). You removed the **LOA card tile** (good), but the per-event probability is still:
- emitted in the JSON the app fetches, and
- granular/variable enough to **read as a per-drug approval probability** — the exact quantity the guardrails forbid — one fetch away.

`loa==pop` for most rows but **diverging for HRMY** suggests these are **model/engine outputs**, not a clean cohort base rate. **[VERIFY + FIX]:** confirm whether `loa`/`pop` are genuine cohort base rates (by cap tier/TA) or ODIN-engine per-drug probabilities. If there's any per-drug modeling in them, **rename to `cohort_loa` and/or strip `pop` from the public response**, so the API itself can't be used to render a per-drug PoA and stays consistent with "no individual-drug approval probabilities."

---

## E. Net / actions
1. **Remove `pdufa.bio` + `www` from the OLD `pdufa-bio` project's domains; noindex/delete its deployments.** (Stops the per-drug-PoA product from ever serving on your apex.) *(§A)*
2. **Reconcile 10-min vs 4.44h vs "5×/day."** Decide the real cadence; align client poll + `s-maxage` + the copy; verify ORATS/FMP isn't being hammered every 10 min. *(§C)*
3. **Audit `loa`/`pop` in `/api/data`.** Confirm cohort vs per-drug; rename/strip if per-drug. *(§D)*
4. **Reword "LIVE."** Use the honest mechanism — "Snapshot · last updated `refreshed_utc` · options ~15-min delayed." *(§B/C)*
5. Good news: `/api/data` is `x-robots-tag: noindex` and behind the access-cookie gate, and `refreshed_utc` reflects true compute time — those are right.

*— Red Team Pass 2b (verified via Vercel connector, read-only).*
