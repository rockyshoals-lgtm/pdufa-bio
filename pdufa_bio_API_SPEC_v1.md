# pdufa.bio API — Tiering, Credits & Resilience Spec (v1)
**Owner:** builder · **Date:** 2026-07-10 · **Status:** ready to implement
**Principle:** *The dates are free (SEO/backlink flywheel). The run-up & cohort intelligence is paid. Never hard-slam a user — degrade, then offer credits or Pro.*

---

## 1. Tiers

| Tier | Auth | Price | Monthly quota | Burst | Fields | Extras |
|---|---|---|---|---|---|---|
| **Anonymous** | none (keyless) | $0 | **1,000 req/day** | 10 req/min | Core (skeleton) | Attribution + link-back **required**. Keeps the free/embeddable flywheel alive. |
| **Free** | `x-api-key` | $0 | **10,000 req/mo** | 30 req/min | Core | Usage dashboard, email on 80% quota |
| **Pro** | `x-api-key` | **$10/mo · $100/yr** | **100,000 req/mo** | 120 req/min | Core + **Depth** | Webhooks, bulk CSV/JSONL export, `.ics` feeds, no attribution requirement |
| **Quant / Commercial** | `x-api-key` | **$149/mo** | **2,000,000 req/mo** | 600 req/min | Core + Depth + **History** | Full T-120→T+5 historical dataset, 99.9% SLO, priority support, commercial redistribution licence |
| **Credits (top-up)** | `x-api-key` | **$5 = 25k · $15 = 100k · $40 = 300k** | additive, **never expire** | tier burst | tier fields | Consumed only *after* monthly quota is exhausted |

**Why anonymous stays free:** every record already returns a `url` back to the detail page. Free keyless access = distributed backlinks from bots, Sheets, dashboards, newsletters — the exact off-page authority needed to win the head-term SEO race. Do **not** paywall the skeleton.

---

## 2. Field gating (the actual moat)

Gate by **field**, not by endpoint. Same URLs for everyone; the payload deepens with the tier.

### Core (Free / Anonymous)
```
id, ticker, company, date, date_precision, name, type,
therapeutic_area, market_cap_tier, status, url, updated_at
```

### Depth (Pro+) — *this is what people pay for*
```
nct_id, sponsor, indication, drug_class, market_cap_usd,
cohort_move_median_pct, cohort_move_p25_pct, cohort_move_p75_pct, cohort_n,
runup: { t_minus_120..t_plus_5 daily series }, runup_summary: { t30_pct, t7_pct, t1_pct },
resubmission_class, review_type, adcomm_linked_id, source_refs[]
```

### History (Quant only)
```
Full historical event archive + complete run-up series for all 1,683 study events;
bulk export endpoints; point-in-time snapshots (as_of=YYYY-MM-DD).
```

**Locked-field behaviour (important):** never silently omit. Return the key with an explicit lock marker so the upgrade path is discoverable in-payload:

```json
{
  "ticker": "CELC",
  "date": "2026-07-17",
  "status": "Upcoming",
  "url": "https://www.pdufa.bio/pdufa/CELC",
  "cohort_move_median_pct": null,
  "runup": null,
  "_locked": ["cohort_move_median_pct", "runup", "nct_id"],
  "_upgrade": "https://www.pdufa.bio/pricing?ref=api_locked_field"
}
```

---

## 3. Soft limit → credits or Pro (the core UX ask)

**Never hard-block at the boundary.** Three-stage ladder:

**Stage 1 — Warn (80% of quota).** Every response carries headers; send one email at 80% and 100%.
```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 2000
X-RateLimit-Reset: 1785542400
X-Credits-Remaining: 0
X-Quota-State: warning
```

**Stage 2 — Grace overage (100%–110%).** Serve the request, flag it. Buys goodwill; nothing breaks mid-job.
```
X-Quota-State: grace
X-Quota-Grace-Remaining: 640
Warning: 199 - "Quota exceeded; serving grace overage. Add credits or upgrade."
```

**Stage 3 — Soft stop (>110%, and no credits).** Return **`402 Payment Required`** (not a bare 429 — this is a commercial limit, not abuse) with an actionable body **and still include cached Core data if available** so the client degrades rather than dies.

```json
{
  "error": {
    "code": "quota_exhausted",
    "message": "Monthly quota used. Add credits or upgrade to Pro to continue.",
    "quota": { "limit": 10000, "used": 11000, "resets_at": "2026-08-01T00:00:00Z" },
    "options": [
      { "type": "credits", "label": "Add 25,000 requests — $5",
        "url": "https://www.pdufa.bio/pricing/credits?pack=25k&ref=api_402" },
      { "type": "upgrade", "label": "Go Pro — $10/mo, 100k req + run-up data + webhooks",
        "url": "https://www.pdufa.bio/pricing?ref=api_402" }
    ],
    "retry_after": 1800
  },
  "meta": { "served_from": "stale_cache", "as_of": "2026-07-10" },
  "data": [ /* last-known Core payload, if cached — else [] */ ]
}
```
Headers: `Retry-After: 1800`, `X-Quota-State: exhausted`, `Link: <…/pricing>; rel="payment"`.

**Credit consumption order:** monthly quota → grace → credits → 402. Credits **never expire** and roll across tiers.

**Abuse ≠ commercial limit.** Burst/DoS violations return **429** with `Retry-After` (short). Only *quota* exhaustion returns 402. Keep the two paths distinct so legitimate users are never shown a scary rate-limit error.

---

## 4. Rate limiting design

- **Algorithm:** token bucket for burst (per-minute) + sliding-window counter for quota (per-day/month).
- **Identity key:** `api_key` when present, else `hash(ip + user_agent)` for anonymous. Never key on IP alone (NATs/CGNAT punish shared users).
- **Storage:** Redis (Upstash/Vercel KV) with atomic `INCR`+`EXPIRE`. Counters must be **atomic** — use a Lua script for check-and-decrement so concurrent requests can't over-spend credits.
- **Fail-open on limiter outage.** If Redis is unreachable, **allow the request** and log — never take the API down because the meter is down. Emit `X-Quota-State: unmetered`.
- **Cost weighting:** not all calls are equal. Charge credits by cost, and expose it:
  - Core list request = **1 credit**
  - `include=runup` (per event, heavy series) = **5 credits**
  - Bulk export (`/export`) = **50 credits**
  - `X-Credits-Cost: 5` on every response.

---

## 5. Endpoints (v1)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/events` | All types. Params: `ticker,type,ta,status,from,to,limit,offset,include,format` |
| GET | `/api/v1/pdufa` · `/readouts` · `/conferences` · `/adcomm` | Typed convenience aliases of `/events` |
| GET | `/api/v1/events/{id}` | Single event; `?include=runup,cohort` (Pro) |
| GET | `/api/v1/runup/{id}` | **Pro** — T-120→T+5 series |
| GET | `/api/v1/export` | **Pro** — bulk CSV/JSONL, async job + signed URL |
| GET | `/api/v1/usage` | Key's quota, credits, cost-to-date |
| GET | `/api/v1/calendar.ics` | **Pro** — subscribable calendar feed (`?ticker=…`) |
| POST/GET/DELETE | `/api/v1/webhooks` | **Pro** — manage subscriptions |
| GET | `/api/v1/health` | Liveness/readiness |

**Add now:** stable `id` per event (immutable, e.g. `pdufa_celc_2026-07-17`), `updated_at`, and `date_precision` (`day` \| `month` \| `quarter` \| `half`) — the readouts feed is month-precision and consumers must know.

---

## 6. Webhooks (the feature worth $10/mo)

**Events:** `event.created`, `event.date_changed` (the date-slip alert), `event.status_changed` (Approved/CRL/Delayed), `event.removed`.

```json
{
  "id": "evt_01J9Z…",
  "type": "event.date_changed",
  "created_at": "2026-07-10T14:02:11Z",
  "data": {
    "event_id": "pdufa_celc_2026-07-17",
    "ticker": "CELC",
    "previous": { "date": "2026-07-17" },
    "current":  { "date": "2026-10-17" },
    "reason": "FDA extended review (major amendment)",
    "source_url": "https://…company-8k",
    "url": "https://www.pdufa.bio/pdufa/CELC"
  }
}
```

**Resilience requirements:**
- **Signing:** `X-Pdufa-Signature: t=<ts>,v1=<HMAC-SHA256(secret, t + "." + body)>`. Reject if `|now-t| > 5min` (replay defence). Publish the verification snippet in docs.
- **Delivery:** at-least-once. Consumers must treat `id` as an **idempotency key**.
- **Retries:** exponential backoff — 8 attempts over 24h (`1m, 5m, 15m, 1h, 3h, 6h, 12h, 24h`). Success = any 2xx within 5s.
- **Circuit breaker:** after 20 consecutive failures, auto-disable the endpoint, email the owner, expose `status: disabled` in `/webhooks`.
- **Dead-letter queue:** store failed deliveries 7 days; allow manual replay from the dashboard.
- **Ordering:** not guaranteed — always include `created_at` and let consumers reconcile by `event_id`.

---

## 7. Error model (uniform)

```json
{ "error": { "code": "invalid_param", "message": "…", "field": "ta",
             "docs": "https://www.pdufa.bio/developers#params",
             "request_id": "req_01J…" } }
```

| Code | Meaning |
|---|---|
| 200 / 304 | OK / Not Modified (honour `If-None-Match`) |
| 400 `invalid_param` | Bad/unknown param — **list valid values in the message** |
| 401 `invalid_key` | Key missing/malformed |
| 403 `tier_forbidden` | Field/endpoint above tier → include `_upgrade` URL |
| 404 `not_found` | Unknown event id |
| 402 `quota_exhausted` | **Commercial limit → credits/upgrade options** |
| 429 `rate_limited` | Burst/abuse → `Retry-After` |
| 500 `internal` | Always with `request_id` |
| 503 `degraded` | Origin down → serving stale cache (see §8) |

**Always return `X-Request-Id`** and log it. Never leak stack traces.

---

## 8. Resilience — hard requirements

1. **Cache-first, stale-tolerant.** Edge cache 30 min (`s-maxage=1800`), plus **`stale-while-revalidate=86400`** and **`stale-if-error=604800`**. If the origin/DB fails, the edge serves last-good data with `meta.served_from: "stale_cache"` and `503`-free `200`. *The API should be nearly impossible to fully take down.*
2. **Read replicas + static fallback.** Pre-render a nightly static JSON snapshot to object storage/CDN. If DB is unreachable, serve the snapshot. Data slightly old > API down.
3. **Timeouts & budgets.** Origin timeout 3s; total request budget 5s. Never hang.
4. **Fail-open limiter** (§4) — the meter must never be a single point of failure.
5. **Atomic credit accounting.** Lua/transactional check-and-decrement; reconcile nightly against the billing ledger. Under-charge rather than double-charge on ambiguity.
6. **Idempotent billing.** Credit purchases keyed by Stripe `payment_intent_id`; replays must not double-credit.
7. **Backpressure.** Global concurrency cap; shed anonymous traffic *first* (paid users protected under load). Anonymous gets `503` + `Retry-After` before any paying key is throttled.
8. **Abuse controls.** Per-key + per-IP + per-ASN limits; block datacenter ASNs at the anonymous tier if scraping appears; WAF rules; anomaly alert on >10× baseline. Scraping the whole calendar should cost real money or a key.
9. **Key security.** Store **hashed** keys (never plaintext); support rotation with a 24h dual-valid overlap; scoped keys (read-only); one-click revoke.
10. **Versioning.** `/v1` frozen. Breaking changes → `/v2` + `Sunset` + `Deprecation` headers and 6 months' notice. **Additive changes only** in v1 — clients must tolerate new fields.
11. **Observability.** SLOs: **99.9% availability, p95 < 400ms, error rate < 0.5%.** Alert on 402/429 spikes (pricing friction), 5xx, cache-hit-rate drop, webhook DLQ growth.
12. **Contract tests.** Golden-file tests for every endpoint × tier (Anonymous/Free/Pro/Quant) asserting exactly which fields appear/lock. CI must fail if a Depth field ever leaks to Free.
13. **Load test before launch:** 10× expected peak; verify graceful degradation, not collapse.

---

## 9. Docs & DX (`/developers`)
- Tier table + field matrix + **live "try it" console**.
- **Copy-paste recipes** (the real conversion driver): Google Sheets `IMPORTDATA`, Python/pandas, Discord bot, `.ics` subscribe, webhook verification.
- Show `X-RateLimit-*` / `X-Credits-*` headers and the 402 body in the docs so limits feel fair and predictable.
- Publish the attribution requirement + a copy-paste badge.

---

## 10. Rollout

**Phase 1 (week 1) — Meter, don't charge.** Ship keys, quotas, headers, `/usage`, stable `id`, `date_precision`. All limits **observe-only** (log, never block). Learn real usage.
**Phase 2 (week 2–3) — Enforce softly.** Turn on warn → grace → 402 with credits/Pro options. Ship Stripe credit packs.
**Phase 3 (week 4+) — Monetise depth.** Gate Depth fields behind Pro, ship webhooks + `.ics` + bulk export. Launch Quant tier.

### Acceptance criteria
- [ ] Anonymous keyless access still works and still returns `url` link-backs.
- [ ] No Depth field is ever returned to a Free key (contract test enforced in CI).
- [ ] Hitting quota returns **402** with working credits **and** Pro links — and still serves cached Core data.
- [ ] Killing Redis → API stays up (fail-open, `unmetered`).
- [ ] Killing the DB → API still serves stale/snapshot data with `served_from` set.
- [ ] Webhook signature verifies; failed deliveries retry and land in the DLQ.
- [ ] Credits never double-charge on Stripe webhook replay.
- [ ] Load test at 10× peak degrades gracefully (anonymous shed first, paid unaffected).

---
*Facts and historical statistics only — no per-drug approval probabilities. Not investment advice.*
