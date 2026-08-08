# Handoff to the audit team — session of 2026-07-12

Read this before the next pass. It tells you **what changed**, **what to verify**, and — more usefully — **what is deliberately NOT done**, so you don't spend a pass re-finding it.

> **Verify with `cache:'reload'` + a bust param.** `cache:'no-store'` does not bypass the edge cache on this site. Four of your previous findings were stale-cache artifacts; that method is the reason.

---

## SHIPPED & LIVE (verify these)

### 1. Homepage responsive bug — FIXED
Your #1. Verified on the deployed page, not the build:

| | before | after |
|---|---|---|
| overflow @ 390px | **220px** | **0** |
| overflow @ 914px | **81px** | **0** |
| mobile nav | absent | burger + drawer + logomark |

**You were right about the symptom and wrong about the cause**, and it mattered. You named `aside.panel` — that selector matches nothing (`panel` is on a `div` *inside* an unclassed `<aside>`). The real bug: `.mn` is a 2-col grid that only collapsed below **820px**, but overflow began at **914px**, because **CSS grid children default to `min-width:auto`** so the sidebar refused to shrink. Fixing what you named would have left the overflow in place.

Fix: `min-width:0` on grid children · breakpoint 820→980 · `overflow-x:hidden` guard · ported the *exact* `navpolish` header component from `calendar/index.html` (the homepage was simply never migrated). 44px tap targets ride along in that block.

**New CI guard:** `tests/test_responsive.mjs` — fails the build if any page lacks the shared header, or has a multi-column grid without `min-width:0`.

### 2. `/about` — LIVE
E-E-A-T. `Organization` + `AboutPage` schema, `correctionsPolicy` and `publishingPrinciples` wired to `/corrections`. States plainly what we refuse to publish.
> **One thing needs your view, or David's:** it says "run by a single independent operator" rather than naming a person. Naming a human is stronger E-E-A-T. That's David's call, not mine, so I left it un-named rather than publish his identity unasked.

### 3. `/corrections` — LIVE
Ten real corrections, each with cause and consequence. Including the ones that make us look bad:
- market-cap tiers assigned **with hindsight** (nano −9.84% → −7.11%)
- **we deleted a real conference** (ANE→ENA) and put it back — a correction to a correction
- **our crawler was inventing conference presentations that never happened**
- the **68% stat we refused to publish**
- the **bug report we rejected** (your `ret_1d` −521% claim — the column is already in percent)
- `prior_crl_count` counting a *company's* CRLs against a *drug*

### 4. `/llms.txt` — LIVE
AEO. Carries the key citable facts with their `n`, the free API surface, and an explicit "do not present this as investment advice / do not quote a figure without its n".

### 5. `/research/readout-reaction` — trilogy table corrected
You said PDUFA run-up was hedged as "≈0%" when it is **+0.57% (n=1,792)**. I recomputed it independently from the panel — **exact match**, published. The table actually had *three* stale cells, not one.

### 6. Sitemap
**336 URLs, 100% www.** `/about` + `/corrections` added.

---

## NOT DONE — don't report these as new findings

- **`/ticker/{TICKER}` hubs** — agreed, biggest winnable SEO item. Not started. ~400 pages.
- **`/glossary`** — not started.
- **ODIN retrain** — `prior_crl_count` is capped in the dataset, but **the deployed model was fit on the uncapped feature**. The cap does nothing until a retrain. Do not report the model as fixed.
- **BIFROST short-interest features remain lookahead-biased** (one Apr-2026 snapshot smeared across 2020–2026). `explosion_score` is therefore **unusable** — its top features are SI/float.
- **Real-device mobile QA** — still unverified on actual hardware.

---

## IN FLIGHT — do not audit the conference dataset this pass

The conference crawler is mid-rebuild. The study numbers **will move**, and any figure you check today is provisional.

Context you should have: the crawler was **fabricating catalysts**. A filing saying *"Presented data at ESMO 2025"* became an **upcoming 2026 event**, because the year detector defaulted to the *filing* year when it couldn't read one, then projected forward. **74 of 121 projected rows were past-tense history sold as future**; one landed in 2027. None reached the study (it only prices exact dates) but **26 would have gone on the public calendar**. Fixed: it now refuses to emit a date after the filing date unless the filing says the company *will* present. An extractor-version stamp now makes it **impossible to append across a semantics change**.

Expect the final study count to come in **below** the 1,986 figure quoted mid-session — that number rested on the buggy layers. Smaller and honest is the intended outcome.

---

## What I'd most like you to attack

1. **The corrections page itself.** Is any entry spun, softened, or self-serving? It's worthless if it's marketing.
2. **`/about`'s claims.** We say we never publish approval probabilities. Find a page that does.
3. **The `min-width:0` fix** — check every *other* multi-column grid on the site, not just the homepage. The CI guard only covers 6 routes.
4. **`/llms.txt` accuracy.** Every number in it must match its source page. If one drifts, that's a citation we've poisoned at the source.

*Facts and historical statistics only. Not investment advice.*
