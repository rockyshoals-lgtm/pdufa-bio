# Audit + strategy: comparative drug context
**2026-08-08 · Cowork session · Amendment 033 filing**
*Live origin checks, Bing SERP probes, GSC + Bing Webmaster Tools. Not investment advice.*

---

# PART 1 — AUDIT: WHAT SHIPPED

## ✅ `dateModified` is live
The missing machine-readable freshness signal is now emitted:

| Page | `dateModified` | Visible line | Matches? |
|---|---|---|---|
| `/` | `2026-08-08T12:49:14+00:00` | Updated August 8, 2026 | ✅ |
| `/sls` | `2026-08-08T12:49:14+00:00` | Updated August 8, 2026 | ✅ |
| `/calendar` | `2026-08-07` | Updated August 7, 2026 | ✅ |
| `/decisions` | `2026-08-07` | Updated August 7, 2026 | ✅ |
| `/vktx` | `2026-08-07` (+ `datePublished` 2026-08-03) | Updated August 7, 2026 | ✅ |

**Structured date and visible date agree on every page** — that was the critical requirement, and it's met.

Also worth crediting: `dateModified` is **not** blindly following `Last-Modified`. `/calendar` reports `Last-Modified: Aug 8 17:37 GMT` but `dateModified: 2026-08-07`, because the *content* last changed on the 7th even though the file was rewritten on the 8th. That's the correct discipline — stamping a fresh date on unchanged content is a spam signal, and the builder avoided it.

`/sls` also now emits `FAQPage` (it had zero JSON-LD two days ago), which was the top schema recommendation.

## 🟡 Three small gaps remain
1. **Format is mixed.** `/` and `/sls` use full ISO-8601 with timezone; `/calendar`, `/decisions`, `/vktx` use date-only (`2026-08-07`). Date-only is valid but coarser — it can't express "3 hours ago," which is precisely the display we're chasing. Standardise on full ISO-8601 + offset everywhere.
2. **`datePublished` only on `/vktx`.** Engines use the published/modified *pair* to judge whether a page is new or maintained. Cheap to add.
3. **`/sls` still lacks `Organization` + `BreadcrumbList`.** It has FAQPage now, but our best page still isn't entity-bound or in a breadcrumb trail. `/vktx` has `Organization` — just mirror it.

## 🔵 Indexing status — submitted, not yet indexed
- **Bing:** `/sls` still returns *"no results"* on a `url:` probe ~24h after IndexNow submission. `/` and `/calendar` remain indexed. Normal latency; not a fault. Worth one more check at 72h.
- **Bing Webmaster Tools is now signed in** ✅ — but reports *"data being processed, may take up to 48 hours."* Real numbers Sunday.
- **Google unchanged:** 51 indexed / 456 not / **421 "Discovered – currently not indexed."** Identical to the 7th; GSC's report lags several days, so the sitemap-ping effect isn't visible yet.

## 💡 Found in BWT — worth acting on
Bing has shipped **AI Performance** reporting (public preview) plus **Intents, Topics, Citation Share and Compare**. It shows *when your site is cited in AI-generated answers* across Copilot and Bing AI summaries, which URLs get referenced, and your citation share versus other sources.

In the 08-07 strategy I listed "AI citations — **untracked, instrument this now**" as a metric with no instrument. **This is the instrument, it's free, and we're already in the tool.** Turn it on. Given we're cited by Copilot on long-tail ticker queries but *not* on head terms, this measures the exact gap we're trying to close.

---

# PART 2 — SHOULD WE PUBLISH HOW GOOD THE DRUG IS VS INCUMBENTS?

**Short answer: yes — this is the strongest expansion available. But not as a verdict. Publish the comparative *context*, never a comparative *score*.**

## Why it's valuable
1. **It's the question retail actually has and nobody answers.** "Will it be approved?" is a date question — that's the current product. "Is it any good, and will it sell?" is what determines whether a stock *holds* its gains after approval. Every competitor stops at the date.
2. **It's the natural extension of assets already held.** Drug, indication, NCT, trial design, decision archive, label. The comparative layer sits directly on top.
3. **Enormous long-tail surface.** `{drug} vs {incumbent}` is a high-volume, high-intent query family that pairs perfectly with the §2 long-tail thesis — and it's evergreen, unlike a PDUFA date that expires.
4. **It's the most AI-citable content type there is.** Comparison tables with sourced values are exactly what answer engines lift. Directly feeds the AEO play we can now measure in BWT.
5. **It's the first thing genuinely worth charging for.** Dates are commodity. Comparative analysis is work.

## Why the naive version would be a serious mistake
1. **Cross-trial comparison is scientifically invalid.** You cannot line up ORR, PFS or OS from two separate trials with different populations, endpoints, eras and statistical plans and declare a winner. It is the single most common error in retail biotech analysis. If we publish naive cross-trial tables, we *become* the problem we currently stand against.
2. **It breaks the brand promise.** The entire differentiator is *"facts and historical statistics only… no approval probabilities… we publish our own corrections."* "Drug A is better than Drug B" is interpretation. The moment we score drugs, we're an analyst shop, and the trust posture — which is the actual moat — is gone.
3. **YMYL exposure.** Comparative efficacy claims are medical information a patient might act on and financial information an investor might trade on. A wrong or unsourced comparison is a materially worse liability than a wrong date.

## The version that captures the value without the risk

**Reframe from "how good is it" to "what is it up against, and what can honestly be compared."** Six modules, all factual, all sourced:

### 1. Head-to-head — only when it actually exists
If the pivotal trial had an **active comparator**, the comparison is a fact, not an inference. Report comparator, endpoint, result, p-value, and the trial. If it was **single-arm**, say so plainly — and say why that matters. The FDA twice refused Replimune's RP1 on exactly that basis before approving it on the third pass. That's reportable history, not opinion.

### 2. Trial design as the comparator
"Single-arm vs randomised, active-controlled" is objective, and it is *the* thing the FDA itself weighted for both REPL and CAPR. **No competitor surfaces this.** It's the highest-signal, lowest-risk comparative field available.

### 3. Label vs label, not trial vs trial
Once approved, the **label is a primary source**. Gwyn Lo's label restricts to BMI < 30 kg/m²; the incumbent patch's label doesn't. That's a factual, citable, commercially meaningful difference — and it requires zero interpretation.

### 4. "What it would displace"
Name the current standard of care with a citation. Don't rank it. *"Current first-line: X (approved 2019). This candidate is positioned for patients who have progressed on X."* Useful, factual, safe.

### 5. Structural differentiators — which actually drive uptake
Route, dosing frequency, cold chain, REMS, first-in-class vs me-too, orphan status, oral vs infused. These are objective label/filing facts, and they predict commercial adoption better than efficacy deltas do. *Gwyn Lo is a once-weekly patch* — a fact, and a real differentiator.

### 6. **The killer module: "why these numbers aren't comparable"**
A short standing explainer on every comparison page:

> *These trials enrolled different populations, used different endpoints, and ran in different eras. Cross-trial comparison is not valid and we don't publish one. Here is what **is** comparable: [design] [label] [route] [line of therapy].*

This is the differentiator. It is exactly the existing brand voice, it's genuinely educational, it will be **heavily cited by AI** because it's the clearest statement of a real methodological problem, and **no competitor will ever write it** — because it isn't promotional and it makes their own comparisons look sloppy.

## Suggested page shape — `/compare/{drug}-vs-{incumbent}`
```
Candidate: Gwyn Lo (norelgestromin/EE)   Incumbent: [patch], approved 2001
─────────────────────────────────────────────────────────────────
Trial design       Phase 3 Luminous, single-arm, n=…   │ RCT vs …
Primary endpoint   Pearl Index 4.14 (95% CI 2.77–5.95) │ PI …
Head-to-head?      NO — not studied against incumbent
Label limits       BMI < 30 kg/m²                      │ none
Route / dosing     Weekly transdermal patch            │ …
Approval basis     505(b)(2)                           │ NDA
─────────────────────────────────────────────────────────────────
⚠ These trials are not comparable head-to-head. [why →]
Sources: FDA label · sponsor PR · NCT05139121
```
Every cell sourced. **No score. No winner. No probability.**

## Rollout
1. **Start with the ~20 approved drugs in the archive that have a named incumbent.** Manual, verified, high quality. Prove the format.
2. Add the "not comparable" explainer as a reusable component + `/learn` article — instant AEO asset.
3. Extend to upcoming PDUFAs (comparative context *before* the decision is the highest-value moment).
4. Only then consider automation, and only for label/design fields — never for efficacy prose.
5. Gate the deepest version behind Pro; keep design + "what it displaces" free, because that's what earns the links.

---

# PART 3 — PRIORITY

| # | Action | Why |
|---|---|---|
| 1 | Turn on **BWT AI Performance / Citation Share** | Free instrument for the one metric we couldn't measure |
| 2 | Standardise `dateModified` to full ISO-8601 + offset; add `datePublished` | Enables "hours ago" display, not just "days ago" |
| 3 | `Organization` + `BreadcrumbList` on `/sls` | Best page still not entity-bound |
| 4 | Re-probe `/sls`,`/tickers`,`/vktx` on Bing at 72h | Confirms IndexNow → index conversion |
| 5 | **Pilot 5 `/compare/` pages** on decided drugs w/ named incumbents | Highest-value new surface; validate the format before scaling |
| 6 | Publish the **"why cross-trial comparison isn't valid"** explainer | Cheapest, most citable, most on-brand asset available |

---

# BOTTOM LINE

The freshness work landed properly — structured and visible dates agree, and `dateModified` correctly tracks *content* change rather than deploy time, which is the subtle part most sites get wrong. Remaining items are polish.

On comparative efficacy: **it's the right expansion and probably the largest untapped one, but only in the form of sourced context, never a verdict.** The instinct to answer "is this drug actually good?" is correct — retail genuinely needs it and no competitor provides it. The discipline that makes it safe is the same one that already differentiates the site: publish what the record says, name what can't be known, and refuse to score. A comparison page that ends with *"these trials are not comparable, and here's why"* is more trustworthy — and more quotable — than any competitor's confident ranking.

---
*Facts and historical statistics only. Not investment advice. Verify against primary FDA / SEC / company filings.*
