# Pro-data gating — ACTIVE on production (beta-bridge), Stripe slots in later

**STATUS: LIVE as of 2026-06-26.** `PRO_GATING_ENABLED=1` is set on Production. Closes Security-Audit (Pass 11) finding #1: `/api/data` no longer serves the paid dataset (options/IV/implied-move + Silent-Shift) to anonymous callers.

**Verified live on the apex:**
- Anonymous `GET /api/data` (no cookie) → `pro_gating:true, pro:false`, 37 events with calendar facts, **0 with `opt`, 0 with `reg.slip`** (Pro fields stripped).
- `GET /api/verify-access?key=<beta pass>` → `pro:true, via:beta, cookie_set:true`; subsequent `/api/data` → `pro:true`, **37/37 with `opt`, 12 with `reg.slip`**.
- `/app` unlock (`dec(pw)`) runs clean (no error), renders the full dashboard with implied-move/IV/call-wall. The gate now calls `/api/verify-access?key=<stored pass>` before its `/api/data` fetch (wired into the encrypted `/app` + `/today` sources, re-encrypted).

**Env (Production):** `PRO_SESSION_SECRET` (random), `PRO_BETA_UNLOCK` (= current gate pass, the beta bridge), `PRO_GATING_ENABLED=1`. Stripe path (`STRIPE_SECRET_KEY`) is still dormant — when added, paying subscribers authenticate via the same cookie with no further front-end change.

---

## Original design notes (mechanism)

## What ships now (no behavior change until you flip the flag)
- **`api/data.js`** — free/pro split behind `PRO_GATING_ENABLED`:
  - Flag **OFF** (default, today): returns the full payload + the same `s-maxage=16000` cache. **Nothing changes.**
  - Flag **ON**: a request with a valid `pb_pro` cookie gets the full payload (`Cache-Control: private, no-store`); everyone else gets the **free view** — calendar facts (ticker, company, drug, indication, date, cap, price, cohort base rates, decided/outcome) with the **Pro fields stripped**: `c.opt` (options / implied move / IV / OI) and `c.reg.slip` (Silent-Shift date-slip). Free view is `public, s-maxage=16000` (cacheable); `Vary: Cookie, Origin`.
  - Response now includes `pro: <bool>` and `pro_gating: <bool>` so the client knows its tier.
- **`api/verify-access.js`** — mints a signed, **HttpOnly** `pb_pro` cookie (HMAC-SHA256, 24 h, `Domain=.pdufa.bio`, `Secure`, `SameSite=Lax`) when the caller is a paying Pro subscriber (Stripe) **or** presents the temporary beta-unlock key. Tokens are timing-safe-verified and reject expired/tampered/wrong-secret (unit-tested).

Auth is **cookie + HMAC**, no DB needed. CORS already scoped to the origin; the uncached `/api/data.js` alias is already killed (Pass 11).

## Env vars (set in Vercel → Settings → Environment Variables, all **Sensitive**, server-only)
| var | purpose | when |
|---|---|---|
| `PRO_SESSION_SECRET` | random 32+ byte secret that signs/verifies the `pb_pro` cookie | **required** to mint/verify (set a long random string) |
| `PRO_GATING_ENABLED` | `1` turns the free/pro split ON | flip to `1` at Pro go-live |
| `PRO_BETA_UNLOCK` | shared secret for the pre-Stripe bridge (`/api/verify-access?key=…`) | optional, for testing/beta before Stripe |
| `STRIPE_SECRET_KEY` | the real subscriber check | at Stripe go-live |

## Go-live checklist (when Stripe is ready)
1. Set `PRO_SESSION_SECRET` (e.g. `openssl rand -base64 48`).
2. **Wire the front-end** (the last mile — needs a re-encrypt of `/app`): after the user authenticates Pro, call `GET /api/verify-access?email=<their email>` (Stripe path) — it Set-Cookies `pb_pro`; subsequent `/api/data` fetches then return the full payload automatically (cookie is sent same-origin). The page reads `pro` from the `/api/data` response to show/hide Pro UI. For a pre-Stripe beta, call `/api/verify-access?key=<PRO_BETA_UNLOCK>` from the gate-unlock handler instead.
3. Set `STRIPE_SECRET_KEY` (+ the Stripe product/price/webhook per `STRIPE_SETUP.md`).
4. **Flip `PRO_GATING_ENABLED=1`** and redeploy.
5. Verify: `curl https://pdufa.bio/api/data` (no cookie) → has `pro:false`, **no `opt` fields**. With a valid `pb_pro` cookie → `pro:true`, `opt` present.

## Still recommended (Pass 11, not in this change)
- **Rate-limit `/api/data`** (Vercel Firewall ~60/min/IP, or KV edge middleware) — protects the ORATS/FMP budget even for the free payload.
- **Rotate the shared access pass**; harden `verify-access` with an email magic-link before scaling (email alone is a weak credential).
- Promote CSP from Report-Only to enforcing after watching for violations.

**Status:** mechanism built + unit-tested + deployed dormant. Activation = set the env vars, wire the one front-end call (with the `/app` re-encrypt), and flip the flag — all doable in the Stripe go-live session.
