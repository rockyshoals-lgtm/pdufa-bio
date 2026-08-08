# pdufa.bio API v1 — Implementation Report vs SPEC
**Date:** 2026-07-11 · **Against:** `pdufa_bio_API_SPEC_v1.md` · **Status:** Phase 1 shipped & live

Phase 1 ("meter, don't charge") is **live in production** with the full response contract, field gating, and resilience posture. **42/42 contract tests pass**, including the CI-critical one: *no Depth field ever reaches a Free or Anonymous key.*

Base URL: `https://www.pdufa.bio/api/v1`

---

## What shipped ✅

| Spec § | Item | Status | Live evidence |
|---|---|---|---|
| §1 | 4 tiers (Anonymous / Free / Pro / Quant) | ✅ | `X-Api-Tier` header; quotas 1k/day · 10k · 100k · 2M wired |
| §1 | Anonymous keyless stays free (SEO flywheel) | ✅ | `curl /api/v1/pdufa` → 200, no key. Every record returns a `url` link-back to pdufa.bio |
| §2 | **Field gating (the moat)** — Core vs Depth | ✅ | Anonymous/Free: all 10 Depth fields `null` + `_locked[]` + `_upgrade` URL. Pro: real values |
| §2 | Never silently omit locked fields | ✅ | `_locked` lists all 10; `_upgrade` → `/pricing?ref=api_locked_field` |
| §5 | Stable `id`, `updated_at`, `date_precision` | ✅ | `pdufa_gsk_2026-06-18`; `date_precision` ∈ day/month/quarter |
| §5 | Typed aliases | ✅ | `/events` 398 · `/pdufa` 83 · `/readouts` 299 · `/conferences` 14 · `/adcomm` 2 |
| §5 | `/usage`, `/health` | ✅ | Both 200; `/health` reports `metered` + `enforcing` state |
| §5 | `/export` (CSV/JSONL), `/calendar.ics` | ✅ | Pro-gated → 403 `tier_forbidden` + `_upgrade` for anonymous |
| §3 | Quota ladder headers | ✅ | `X-RateLimit-Limit/Remaining/Reset`, `X-Credits-Remaining`, `X-Quota-State` (ok/warning/grace/exhausted/unmetered) |
| §3 | 402 ≠ 429 (commercial vs abuse) | ✅ | `quota402()` returns 402 + credit/upgrade options + cached Core data + `Link: rel="payment"` |
| §4 | Cost weighting | ✅ | `X-Credits-Cost`: core=1, `include=runup`=5, `/export`=50 |
| §4 | **Fail-open limiter** | ✅ | No KV configured → `X-Quota-State: unmetered`, request served. Limiter can never take the API down |
| §4 | Identity = key, else `hash(ip+ua)` | ✅ | SHA-256, never IP alone |
| §7 | Uniform error model + `X-Request-Id` | ✅ | 400 `invalid_param` (lists valid params), 401 `invalid_key`, 403 `tier_forbidden`, 402 `quota_exhausted` |
| §8.1 | Cache-first, stale-tolerant | ✅ | `CDN-Cache-Control: s-maxage=1800, stale-while-revalidate=86400, stale-if-error=604800` — verified live; edge MISS→HIT confirmed |
| §7 | `ETag` / `If-None-Match` → 304 | ✅ | Verified live |
| §12 | Contract tests (tier × field matrix) | ✅ | `tests/api_contract.mjs` — **42/42 pass** |
| §9 | Docs: tier table, field matrix, recipes, headers, errors | ✅ | `/developers` rewritten (Sheets `IMPORTDATA`, pandas, JS, `.ics`) |

### The Depth data is real (this is what makes Pro worth paying for)
Cohort decision-day move distributions, computed from **1,704 historical PDUFA events**:

| Cap tier | n | median | p25 | p75 |
|---|---|---|---|---|
| Nano | 116 | −0.11% | **−7.98%** | **+8.11%** |
| Micro | 302 | −0.90% | −5.30% | +3.63% |
| Small | 274 | 0.00% | −3.99% | +2.75% |
| Mid | 222 | −0.01% | −2.05% | +2.51% |
| Large | 790 | 0.00% | −0.93% | +1.03% |

That spread — nano ±8% vs large ±1% — is the product. Free gets the dates; Pro gets the dispersion.

---

## Deliberately deferred (needs infra/decisions, not code)

| Item | Why | Unblock |
|---|---|---|
| **Live quota enforcement** | Needs Redis/KV. Code is written and pluggable — reads `UPSTASH_REDIS_REST_URL` + `_TOKEN`; absent → fail-open `unmetered` (exactly the spec's §4 requirement). | Add the 2 env vars, then set `API_ENFORCE=1` to move from Phase 1 (observe) → Phase 2 (enforce). No code change. |
| **Credits / Stripe** | Needs Stripe account + LemonSqueezy decision (already pending). Idempotent `payment_intent_id` keying specified. | Blocked on the same LemonSqueezy reply. |
| **Webhooks (§6)** | Needs a queue + DLQ + durable store; biggest single build. HMAC signing scheme and retry ladder are specified and ready. | Schedule as its own phase — it's the feature that justifies $10/mo. |
| **Quant History tier** | Full T-120→T+5 series for 1,683 events would bloat the bundle. | Serve from object storage / separate route rather than the function bundle. |

---

## Notes for the audit team
- **Keys:** tiers read from env `API_KEYS_FREE` / `API_KEYS_PRO` / `API_KEYS_QUANT` (comma-separated). Currently unset → everyone is `anonymous`, which is the correct fail-safe (free tier works, Depth stays locked). Nothing is exposed.
- **Vercel rewrites the client-facing `Cache-Control`** to `max-age=0, must-revalidate` regardless of what the function sets — so we set `CDN-Cache-Control` / `Vercel-CDN-Cache-Control` too. Edge caching verified (MISS → HIT, `age` incrementing); `stale-if-error` now explicit at the CDN layer.
- **Anonymous is not paywalled and should not be.** Every payload carries the `url` back to the detail page — that's the backlink flywheel the spec calls for.

*Facts and historical statistics only — no per-drug approval probabilities. Not investment advice.*
