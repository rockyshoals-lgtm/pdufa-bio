# Paywall Audit — LIVE
**Date:** 2026-07-11 · Cache-busted, live inspection. *No purchase was completed — checkout was inspected only.*

---

## TL;DR
**The metering is excellent — genuinely to spec. But you can take a customer's $100 and they have no way to log in and get what they bought.** Two revenue/trust holes and one leak. Fix before you drive any traffic at this.

**The biggest risk you avoided:** none of your ranking content got gated. SEO surface is fully intact.

---

# ✅ What's working (and it's a lot)

### SEO surface — intact. This was the big one.
Every content page is still **200, publicly crawlable, no paywall, no login wall**: `/`, `/calendar`, `/pdufa/CELC`, `/readouts`, `/conferences`, `/adcomm`, `/decisions`, `/screener`, `/research`, `/runup-by-year`. Full HTML bodies. **Nothing that ranks got put behind the wall.** Exactly right.

### API metering — implemented to spec
- **Anonymous access still works, no key required** → the backlink/embed flywheel is preserved. ✅ *This was the whole point.*
- Headers all present: `x-ratelimit-limit: 1000` · `x-ratelimit-remaining` · `x-quota-state: ok` · `x-credits-remaining` · **`x-credits-cost: 1`** · `x-request-id` · CORS `*`
- **Field gating works:** Core fields returned free; Depth returned as `null` with a **`_locked` array** and an **`_upgrade` URL** in the payload. Exactly the design.
- **`/api/v1/usage`** returns tier, quota (limit/used/remaining/resets_at/window), `credits_remaining`, `burst_per_min: 10`, `depth_access: false`, `history_access: false`, upgrade link.
- **Error model is genuinely good:** `400 invalid_param` lists every valid parameter + docs link + request_id. `401 invalid_key` says *"…or omit it for anonymous access."* That's better than most commercial APIs.
- New Core fields shipped as specced: **`id`, `date_precision`, `updated_at`**.
- **Pro checkout works** — `/api/stripe/checkout?plan=pro_monthly` and `pro_annual` both redirect to Stripe.
- **Logomark shipped** (finally).

---

# 🔴 CRITICAL — fix before promoting

## 1. There is no login, signup, or account page. At all.
```
/login    → 404
/signup   → 404
/account  → 404
```
**A user pays $100/yr through Stripe… and then what?** There is no way to:
- log in,
- retrieve their API key,
- see usage,
- manage or cancel the subscription.

**You can currently take money and not deliver access.** That is a chargeback and refund generator, and it will torch trust in a product whose entire brand is credibility. **This is the single most urgent item.**

**Fix:** ship `/account` (API key display + regenerate, usage, plan, cancel link → Stripe customer portal) and an auth path (magic-link email is enough; no passwords to store).

## 2. The credits purchase path is dead — it 503s
```
/api/stripe/checkout?plan=credits_25k
→ 503 {"code":"unconfigured",
       "message":"No Stripe price ID configured for \"credits_25k\".
                  Set STRIPE_PRICE_CREDITS_25K in the environment."}
```
And the landing pages don't exist: `/pricing/credits` → **404**, `/credits` → **404**.

So the entire *"buy more credits"* half of the soft-limit ladder is broken. When a user exhausts quota and the 402 offers them credits, that path **503s**. The pricing page doesn't even mention credits.

**Fix:** create the Stripe price IDs (`STRIPE_PRICE_CREDITS_25K` / `_100K` / `_300K`), set the env vars, build `/pricing/credits`, and surface credits on `/pricing`.

## 3. The paywall is trivially bypassed — and it's charging for what you give away
The API locks these behind Pro:
`nct_id · indication · market_cap_usd · cash_runway_months · days_to_decision · cohort_move_median/p25/p75 · cohort_n · runup_summary`

But the **public page `/pdufa/CELC` displays all of them** — indication, cohort stats, NCT ID, and cash runway are all right there in free, crawlable HTML.

Anyone can scrape the free page to get exactly the fields you're charging for. The gate is **leaky and internally inconsistent** — and charging for data you publish for free is a bad look for an accuracy/honesty brand.

**Fix — pick one principle and hold it:**
> **If it's visible on a public page, it's free in the API.**

Concretely: **unlock `indication`, `nct_id`, `days_to_decision`, and `market_cap_usd` in the API** (they're public anyway, and `days_to_decision` is trivially derived from `date` — locking it is pointless friction). Keep genuinely proprietary depth (**`runup_summary`, the full T-120→T+5 series, `cohort_move_*`, `cash_runway_months`**) as Pro *and* consider showing only a teaser of those on the page. That keeps the moat where the moat actually is.

---

# 🟠 MEDIUM

4. **Locking `indication` cripples the free API's usefulness for embeds** — which is the exact mechanism that generates the backlinks you need for the head-term SEO fight. Don't undercut the flywheel to protect a field you publish for free.
5. **The docs never say how to get an API key.** `/developers` documents `x-api-key`, credits and the 402 — but there's no "get a key" flow (because there's no account page). Circular.
6. **Rate limits aren't documented** on `/developers` even though the headers are implemented. Publish the numbers (1,000/day anonymous, 10/min burst) — predictable limits feel fair; invisible ones feel arbitrary.

---

# Priority order
1. **`/account` + auth + API key delivery** — you are taking money without delivering access. *(blocker)*
2. **Configure Stripe credit price IDs + `/pricing/credits`** — the soft-limit's escape hatch 503s. *(blocker)*
3. **Reconcile page-vs-API gating** — unlock the fields you already publish; keep the run-up/cohort moat paid.
4. Document key issuance + rate limits on `/developers`.

---

# Verdict
The engineering is genuinely good — the metering, headers, field gating, error model and usage endpoint are better than most paid APIs I've seen. **The gap isn't the paywall; it's the plumbing around it.** You built a turnstile with no ticket booth behind it.

Nothing that ranks got gated, so there's no SEO damage — you have time to fix this properly before pushing traffic.

---
*Not investment advice. Checkout inspected only; no purchase completed.*
