# Full Audit — Pro "Coming Soon" State
**Date:** 2026-07-11 · Live, hard-cache-bypassed (`cache:'reload'` + bust param)
*Not investment advice. Checkout inspected only; no purchase attempted.*

---

## 0. 🙋 First: I was wrong four times, and I know why now

Four items I reported as "still broken" were **stale-cache artifacts on my end**:

| I claimed | Actual (hard reload) |
|---|---|
| Sitemap = 170 URLs, 100% non-www | ✅ **334 URLs, 100% www** |
| `/research/conference-runup` has zero schema | ✅ **Full Dataset + Article + FAQPage + BreadcrumbList** |
| Meta description 231 chars | ✅ **149 chars** |
| API still locks depth fields (P1-3 not done) | ✅ **`_locked: none`** — `indication` returns fine |

**Root cause:** `fetch(..., {cache:'no-store'})` was **not** bypassing an edge/service-worker cache on this site. Only `cache:'reload'` **plus** a cache-busting query param returns truth. **The builder was right on every count.** I've switched methods permanently.

---

## ✅ THE PRO "COMING SOON" IMPLEMENTATION IS CORRECT

| Check | Result |
|---|---|
| `/api/stripe/checkout?plan=pro_monthly` | ✅ Redirects to **`/pricing?soon=1`** — **not Stripe.** No payment possible. |
| `pro_annual`, `credits_25k` | ✅ Same. All payment paths safely closed. |
| Pricing page | ✅ **"COMING SOON"** badge · *"not on sale yet — we're finishing it properly first"* |
| Email capture | ✅ **"Notify me"** — *"Pro isn't taking payments yet… no spam, no card."* |
| `/account` · `/login` · `/pricing/credits` | ✅ All **200** (built) |

**This was the right call**, and it's better than just disabling the button: it converts a broken funnel into the **email list you never had** — the exact retention gap I flagged in the Kaizen. Free calendar stays open; nothing that ranks is gated.

---

## 🔴 THE ONE CRITICAL RISK: is the waitlist actually saving emails?

`/api/notify` exists (**405 on GET** = POST-only endpoint, live). **But your own backlog says `RESEND_API_KEY` is unset.**

**If `/api/notify` tries to send via Resend and the key is missing, every signup could be silently dropped.**

The entire value of the "coming soon" window **is** capturing those emails. If it's failing, you're burning the launch runway and collecting nothing.

### Verify this immediately — it's a 5-minute check
1. Does `/api/notify` **persist to a database/KV first**, and only *then* attempt to send?
2. Or does it **only** call Resend (and fail closed)?
3. Submit a test address and confirm the row lands in storage.
4. **Never let email capture depend on an email-sending key.** Persist first, send second, and if the send fails, the address must still be stored.

> **This is now the highest-risk item on the board — higher than the crawler.** A silently-failing waitlist during a "coming soon" window is a pure, unrecoverable loss.

---

## ✅ ACCURACY: the published research is verified — 10/10 exact

I recomputed every figure on `/research/readout-reaction` from the raw data independently:

| Published | My computation | |
|---|---|---|
| Median move **3.8%** | 3.80% | ✅ |
| Within ±2% = **35.1%** | 35.1% | ✅ |
| Within ±5% = **56.5%** | 56.5% | ✅ |
| Within ±10% = **70.8%** | 70.8% | ✅ |
| Crashed 30%+ = **7.6%** | 7.6% | ✅ |
| Ran 50%+ = **3.1%** | 3.1% | ✅ |
| Micro n=350, |move| 8.71%, dud 32%, crash 11.7% | identical | ✅ |
| Small n=424, 6.16%, 45%, 10.8% | identical | ✅ |
| Mid n=543, 2.99%, 63%, 5.3% | identical | ✅ |
| Large n=435, 1.67%, 79%, 3.9% | identical | ✅ |

**Every number matches exactly.** The run-up windows (−0.07% / +0.00% / +0.23%) also match my panel.

### The page itself is the best thing on the site
- **The "note on honesty" section** — publicly explaining *why you refused to publish the punchy 68% stat* because the bucket spans −14.9% to +5.0% — is the single strongest trust signal in this category. Nobody else would ever write it.
- Cites **PLOS One** as corroboration rather than claiming discovery.
- Cites **Wong/Siah/Lo (2019)** for phase success rates and explains why it won't publish its own (65% unlabelled).
- States the pre-announcement-drift gap as *"a gap we could not fill by searching, not a claim to be first."*
- **CC BY 4.0 + `data@pdufa.bio`** — that's the backlink engine, correctly built.

**Independent corroboration found this pass:** the event-study literature reports that *"classification as early-biotech vs big-pharma had the most impact on abnormal returns"* — which independently validates the **market-cap-dominance** finding from my enrichment work.

---

## 🟠 One precision nit (because precision *is* the brand)
The trilogy table publishes **PDUFA run-up as "≈0%"**. From the unified panel the actual figure is **+0.57% (n=1,792)**. That's still "no meaningful run-up," but you have the exact number — **publish it.** A site that prints `n` next to everything shouldn't hedge one cell with a tilde.

---

## ⬜ REMAINING OPEN — in priority order

| # | Item | Status |
|---|---|---|
| **🔴 NEW** | **Verify `/api/notify` persists emails without `RESEND_API_KEY`** | **Highest risk — the coming-soon window is worthless if this fails** |
| **P2-1** | `ConferencePresentation` type in `catalyst_crawler.py` | 🔴 **The moat is still leaking.** ASCO26 = 6 events; **EHA26 / ADA26 = zero.** No conference type exists in the live pipeline. |
| **P2-2** | Backfill ASCO26 / EHA26 / ADA26 / ASCO-GU26 | Blocked on P2-1 |
| — | `RESEND_API_KEY` · Stripe credit price IDs | **Owner action** (Stripe is moot until Pro launches) |
| **P0-4** | Cap `prior_crl_count` at 4 | 28 events show counts to 26 (company-level counting) |
| **P4-4** | CRL tracker → *"What happens after a CRL"* | Lead with 73.5% → 42.9% → 26.9% |
| **P6-1** | Rebuild BIFROST SI from `si_panel_2017_2026.csv.gz` | Current SI features are lookahead-biased |
| **P8-1** | **`/ticker/{TICKER}` hubs** | ⭐ Biggest SEO left — ~400 pages, near-zero competition |
| **P8-3/4** | Watchlist/.ics · `/about` + corrections log | The corrections log now writes itself — you have a *great* one |
| — | Real-device mobile QA | Still unverified (tool can't force a mobile viewport) |

### New data ready to publish (from enrichment round 2)
- **`conf_study/UNIFIED_catalyst_panel.csv`** — 5,487 events, 3 catalyst classes, 2015–2026
- **`conf_study/readout_MASTER_enriched.csv`** — 1,752 readouts × 88 cols (CT.gov trial design + FINRA SI + reaction)
- **The market-cap-artifact finding** — trial design, enrollment and short interest **all dissolve** under a cap-tier control. Same shape as the SI debunk you already shipped. *Publish the null.*

---

## Verdict

**The site is in genuinely good shape and the accuracy is now verifiable — I checked ten published figures against raw data and all ten matched exactly.** The research pages are better than anything a competitor has, the "coming soon" call was correct, and the CI guards mean my false regression reports can't become real ones.

**Two things stand between this and flawless:**
1. **Confirm the waitlist is actually storing emails.** If it depends on the missing Resend key, the entire coming-soon window is producing nothing.
2. **Fix the crawler.** Every enrichment round makes the dataset more valuable and the leak more expensive.

Everything else is polish.

---
*Facts and historical statistics only. Not investment advice.*
