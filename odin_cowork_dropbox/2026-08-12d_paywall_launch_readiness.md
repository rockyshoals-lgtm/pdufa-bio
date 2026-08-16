# Paywall launch readiness — pdufa.bio Pro
**2026-08-12 · every claim probed against the live site and the repo today**
*Facts and historical statistics only — not investment advice.*

---

# THE SHORT ANSWER

**The billing engine is done and it's good. You are ~1 week from being able to charge — but the gating item is alerts, not payments.**

Two honest numbers:

| | |
|---|---|
| **Engineering readiness** | **~85%** — the hard part is finished |
| **Legally able to accept a card** | **No.** No terms, no privacy policy, no refund policy, no contact method |

And a third thing worth saying plainly: **readiness isn't your constraint. Audience is.** At current traffic a paywall converts nearly nobody. More on that in §5.

---

# 1. WHAT'S BUILT — more than I expected

## 1.1 Billing contract: 21/21 passing

`node tests/billing_contract.mjs` → **21 passed, 0 failed**, covering the cases that actually bite:

```
PASS  API key issued + bound to session      PASS  key record stored hashed
PASS  replayed event does NOT reissue key    (Stripe delivers at-least-once)
PASS  same payment_intent cannot double-credit
PASS  payment_failed -> past_due (NOT revoked)
PASS  invoice.paid -> reactivated (renewal works)
PASS  subscription.deleted -> tier=free
PASS  cancelled key still gets PUBLIC fields (by design)
PASS  cancelled key -> RUN-UP SERIES re-locks
PASS  first reveal returns key · second reveal -> 404 (burned)
```

Webhook idempotency, double-credit protection, and dunning that doesn't nuke a paying customer on one failed card are the three things shipped products most often get wrong. All three are tested here.

## 1.2 The gates are live right now

Probed anonymously today:

```
/api/v1/runup    → 403 tier_forbidden  "The per-event run-up series…"
/api/v1/export   → 403 tier_forbidden  "Bulk export is a Pro feature"
/api/v1/usage    → 200  tier=anonymous, quota 1000, used 19, remaining 981
/api/account/me  → 401  not_signed_in
POST /api/stripe/checkout → 503 not_launched  ← deliberate kill switch
```

**Important distinction:** `health` reports `enforcing: false`, but that flag governs **quota blocking**, not feature gating. Feature gates are *already enforcing*. Metering counts correctly; it just doesn't cut anyone off yet.

## 1.3 Everything else that exists
- Stripe checkout, webhook, billing portal, API-key issue/rotate
- Magic-link auth (request / verify / logout), signed session cookie
- `/account` fully built: signed-out state, key reveal + regenerate, plan, "Manage billing & cancel — all handled by Stripe. We never see your payment details"
- API self-documents the upsell: `pro_features: [runup_series, export, calendar.ics, webhooks]`, per-row `_pro` string, `upgrade` URL with `?ref=api_meta` attribution
- Price points set: **$10/mo · $100/yr · credit top-ups from $5**
- A free/Pro boundary that is genuinely defensible: calendar, full decision archive, run-up study and API **free forever, no login**

That last point is the commercial asset. "The calendar is free. Pro is for the edge" is a real position, not a teaser wall.

---

# 2. 🔴 HARD BLOCKERS — cannot take money without these

## 2.1 No legal surface at all

```
/terms  404   /privacy 404   /refund-policy 404   /contact 404
/legal  404   /disclaimer 404   /terms-of-service 404
```
`/about` mentions **none** of: privacy, terms, refund, contact, email, cancel, cookie, GDPR.
*(`/policy.html` is a password-locked private feature preview — unrelated, and linked from nowhere.)*

Stripe's terms and the card-network rules both require a merchant to publish terms of service, a privacy policy, a refund/cancellation policy, and a working contact method. This isn't best practice, it's a condition of holding the account. **Not optional, and it's the single thing standing between you and a live checkout.**

Note the tension you already created deliberately: commit `3e24c2d` — *"remove every contact invitation until one actually works."* Honest call. But you cannot sell to consumers with no support channel.

## 2.2 The pricing page promises a free trial that doesn't exist

Same page, two claims:

> *"Pro isn't taking payments or sign-ups. … We're not collecting emails in the meantime."*

> **FAQ:** *"What do I get with the free trial? **Full Pro access for 7 days.** Cancel any time before it ends and you won't be charged."*

A 7-day free trial is described in detail and does not exist. Good news: `FAQPage` count on `/pricing` is **0**, so this is *not* being fed to AI engines. Bad news: it's a consumer-facing misstatement about payment terms, which is the exact category that draws regulatory attention. **Delete it or build it — today. Minutes of work.**

## 2.3 Alerts are advertised and not built

Pricing promises four Pro features. Three exist. This one doesn't:

> *"Date-slip & decision alerts — email when a PDUFA moves, drops, or enters its run-up window."*

No alerting code anywhere in `api/`. The only outbound-email path is the magic link (`api/auth/request.mjs`). Nothing schedules, diffs dates, or sends.

**This is the true critical path.** Everything else on this page is hours or a day. Alerts are days-to-a-week, because they need date-diffing against yesterday's slate, a subscription model, a scheduler, delivery, and unsubscribe handling.

---

# 3. 🟠 MUST FIX BEFORE FLIPPING THE SWITCH

| # | Item | Evidence | Effort |
|---|---|---|---|
| 3.1 | **Stripe only half-configured** | `prices_configured: 2`, but code references **6** price IDs (PRO_MONTHLY, PRO_ANNUAL, QUANT_MONTHLY, CREDITS_25K/100K/300K). **Annual and credit packs are advertised on the page but not wired.** | hours |
| 3.2 | **`billing_live: false`** | Still test mode. Needs live keys + a real end-to-end purchase. | hours |
| 3.3 | **Quota enforcement off** | `enforcing: false`. Free tier is effectively unlimited (1000/mo counted, never blocked). Must flip at launch or free undercuts Pro. | minutes |
| 3.4 | **Email delivery unverified** | `api/auth/request.mjs` falls back to `console.error` when `RESEND_API_KEY` is unset. Magic link is the **only** login path — if mail doesn't send, nobody can ever sign in. Verify end-to-end. | hours |
| 3.5 | **Two generations of billing code coexist** | Legacy CommonJS `api/create-checkout-session.js` + `api/stripe-webhook.js` alongside ESM `api/stripe/checkout.mjs` + `api/stripe/webhook.mjs`. **If both webhooks are registered in Stripe you risk double-processing.** Confirm one endpoint registered; delete the legacy pair. | hours |
| 3.6 | **`api/verify-access.js` beta backdoor** | `PRO_BETA_UNLOCK` shared secret; the file's own comment flags email-alone as a weak credential. Remove before launch. | minutes |
| 3.7 | **`/account` breadcrumb reads "Home › Pricing"** | cosmetic, but it's the billing page | minutes |
| 3.8 | `/api/v1/runup_series.mjs` + `/api/v1/dataset.mjs` return **500** | Vercel tries to invoke 966KB data modules as functions. Not exposed (good — the data isn't leaking), but a 500 in a crawlable path is a poor signal. Route away or 404. | minutes |

---

# 4. TIME TO LAUNCH

**Two scenarios, and the difference is entirely alerts.**

### Scenario A — launch without alerts (~3–4 days)
Drop the alerts bullet from Pro, ship the other three (live tracker, full dataset export, screener).

| Day | Work |
|---|---|
| 1 | Terms, privacy, refund/cancellation policy, contact method |
| 1 | Remove the free-trial FAQ; remove the alerts bullet; delete legacy handlers + beta backdoor |
| 2 | Wire remaining 4 Stripe prices; live keys; verify magic-link delivery end-to-end |
| 3 | Real card purchase → key issued → gate opens → cancel → gate re-locks. Then `enforcing=1`, `billing_live=1` |

### Scenario B — launch with alerts as promised (~1.5–2 weeks)
Everything above, plus building the alerting engine: daily slate diff, subscription prefs, scheduler, delivery, unsubscribe, and a guard so a data-refresh bug can't email everyone a false date change.

**Recommendation: Scenario A.** Alerts are the strongest Pro feature *and* the one most likely to embarrass you if it misfires — an email saying "LNTH's PDUFA moved" when it didn't is a trust event, and trust is the whole brand. Ship the three that are ready, build alerts properly, add them at no extra cost. That's also a good reason for existing subscribers to stay.

---

# 5. THE HARDER QUESTION: *should* you launch now?

Readiness isn't the binding constraint. **Traffic is.**

| Channel | Current |
|---|---|
| Bing | 18 clicks / 776 impressions over 3 days ≈ **6 clicks/day** |
| Google | 38 clicks / 1,610 impressions over **90 days** ≈ 0.4/day |
| Combined | **~200 visits/month** |

At 200 visits/month, even a strong 2% conversion is **~4 subscribers ≈ $40/month**. That doesn't fund anything — but it does buy something more useful: **proof that someone will pay, and the first cohort of people telling you what Pro is missing.**

Meanwhile the trajectory is genuinely good: **Bing #1** on the head term, AI citations **8 → 35 → 72 → 115**, and Google's 418 "discovered, not indexed" pages still to unlock. All of that compounds on the **free** surface. The free calendar is the growth engine; the paywall doesn't accelerate it.

**So:** get to launch-*capable* in the next week — the legal gap should be closed regardless, and the free-trial misstatement should come down today. Then decide the launch date on traffic, not on code.

There's also real value in the position you've already published:

> *"Pro isn't taking payments or sign-ups. It opens when we're 100% satisfied with the product, not before."*

That is on-brand, and it's the same instinct that made you refuse to publish an approval rate over unverified data. **Keep it — but make it true.** Right now that paragraph sits directly above a description of a 7-day free trial.

---

# 6. ORDER OF WORK

| # | Item | Blocker? | Effort |
|---|---|---|---|
| 1 | **Delete the free-trial FAQ** | consumer misstatement | minutes |
| ~~2~~ | ~~Bing API migration~~ — **withdrawn 2026-08-12, my error; `api.svc/json` is the surviving protocol** | none | — |
| 3 | Terms · privacy · refund/cancellation · contact | **hard blocker** | 1 day |
| 4 | Delete legacy checkout/webhook pair + `PRO_BETA_UNLOCK` | double-charge risk | hours |
| 5 | Wire remaining 4 Stripe prices | annual is advertised | hours |
| 6 | Verify magic-link email end to end | only login path | hours |
| 7 | Decide: cut alerts from Pro, or build them | scope call | — |
| 8 | Live-mode test purchase → cancel → verify re-lock | — | half day |
| 9 | Flip `enforcing=1`, `billing_live=1` | — | minutes |

---

# 7. BOTTOM LINE

You built the hard part properly. A billing stack with passing idempotency, dunning and revocation tests is further than most products are on launch day, and the free/Pro boundary is a real position rather than a hostage-taking.

Three things stand between you and a live checkout:

1. **No terms, privacy, refund policy or contact method.** Non-negotiable, ~1 day.
2. **A 7-day free trial advertised on a page that says you're not taking payments.** Take it down today.
3. **Alerts are sold and unbuilt.** Cut them from the launch promise or spend the week.

Do those and you can charge in about four days. But at ~200 visits/month, I'd close the legal gap now, take the false claim down now, and let Bing and the AI citations keep compounding before you actually open the door.

---
*Not investment advice. Not legal advice — have a lawyer review the terms, privacy and refund policies before you accept a payment.*
