# Red team — Gemini's "Strategic Audit and Competitive Intelligence Report"
**2026-09-06 · every factual claim about pdufa.bio checked against the live site today · every competitor claim checked against the SERPs I ran on 2026-09-05**
*Facts and build mechanics only — not investment advice.*

---

# VERDICT

**The report is right about what our moat is and wrong about most of the numbers it uses to prove it.** Three of its six strategies violate the doctrine the report itself praises. It has no concept of *speed*, which is the lever that has produced every measurable gain this month. And its competitor set is the one competitors describe on their own pricing pages, not the one that actually outranks us on Google.

**Take from it:** the CRL taxonomy (reframed), the watchlist/date-slip idea (blocked until `/terms` exists), and the correct observation that our UI lags our data. **Reject:** the dilution "probability," the IRA countdown, and the anti-AI attack campaign.

---

# 1. THE NUMBERS ARE STALE OR WRONG — every one I could check

| Gemini says | Live site today | Verdict |
|---|---|---|
| "446 logged historical FDA decisions, 73% (327) approvals, 27% (119) CRLs" | **462 decisions · 347 approvals · 115 CRLs** | Stale — and the CRL count moved *down* (119→115), so quoting Gemini's figure would publish a number the archive has since corrected |
| "1,754 trackable U.S. PDUFA events" | **1,845** | Stale by 91 events |
| "**mean** price path indexed to 100 at T-120" | *"Medians throughout. A handful of 300% moves would make means meaningless here."* | **Wrong method.** The page says the opposite in its second sentence |
| "2022 dropped an average of 5.1%… 2023 3.8%" | 2022 **−0.7%** · 2023 **−5.2%** (medians) | **Wrong numbers.** Neither appears anywhere on the site |
| "2024–2026 … 14.3% and 13.3% average peak returns" | Peak run-up: 2024 **+22.7%** · 2025 **+20.9%** · 2026 **+27.2%** | **Wrong numbers.** Not on the site |
| "208 public companies · 53 upcoming decisions · 302 readouts" | none of these strings appear on the homepage or `/decisions` | Unverified from this evidence — likely a weeks-old snapshot |
| "$149/mo Quant tier" | `/pricing` shows $0 · $10/mo · $100/yr · $5; the 2,000,000-request tier is on `/developers` | Partially verifiable; the price is not on the pricing page |
| Readouts: median 3.8%, 57% within ±5%, 7.6% crash ≥30%, n=1,752 | ✅ all four on `/research` | Correct |
| SI study: FINRA point-in-time, 1,753 decisions, 3× move is a cap artefact | ✅ `/research` index says this | Correct as quoted — **but see §6** |
| Conference study 256→1,425 · CC BY 4.0 · API tiers 1k/10k/100k/2M · 80% warning · grace overage · "if it's visible on a public page, it's free in the API" | ✅ all verified on `/developers` and `/research` | Correct |

**Pattern:** the qualitative claims are right; the quantitative ones about our own studies are either from an old build or invented. A report recommending we "weaponize the archive" while misquoting the archive's headline numbers should not be forwarded to anyone outside without the table above.

**One internal contradiction worth noting:** the report asserts *"basic catalyst dates are fully priced into equities months in advance"* and two pages later cites our data showing double-digit median pre-decision run-ups. Both cannot be true; our data says the first is false.

---

# 2. THE COMPETITOR MAP IS THE WRONG MAP

Gemini's set: BioPharmCatalyst, BPIQ, BiopharmaWatch, BioRadar, CatalystAlert, FDA Tracker, "FDA Catalyst Calendar", MerlinTrader.

**What actually outranks us on Google page 1 for `pdufa calendar` (run live 2026-09-05):** FDA Tracker, RTTNews, FDA.gov, CheckRare, BPIQ, **MarketBeat**, **Assyro**, **Unusual Whales**, BiopharmaWatch — and the AI Overview cites BPIQ, Assyro, BiopharmaWatch, **TipRanks**, **Pharmacy Times**. For `pdufa dates 2026`, add **Reddit r/biotech**.

**On Bing, the two clones that copied us in the last month:** **novapharmanews** (our "19 hours ago" freshness stamp, ranked #2 directly under us) and **dansfera** (our per-drug page, our disclaimer language, plus a live price).

Gemini names none of MarketBeat, Assyro, Unusual Whales, TipRanks, Pharmacy Times, RTTNews, CheckRare, novapharmanews or dansfera. Its set is the *feature-comparison* set — sites with pricing tables to scrape. Ours is the *ranking* set — sites with authority. **The report analyses the war we've already won (feature depth) and ignores the one we're losing (authority and answer-box citation).**

---

# 3. STRATEGY BY STRATEGY

## S1 — CRL taxonomy + "recovery path" → **KEEP THE IDEA, STRIKE THE FRAMING**

The idea is sound and we are better placed than Gemini knows: we hold **458 FDA letters with full text** (309 approved / 149 unapproved), and ODIN v13 already built a CRL-class differentiation internally. Tagging letters by reason (CMC / efficacy / safety / labeling) is a real, uncopyable asset.

**But the framing breaks doctrine three times:** *"highly predictive base rates,"* *"The CRL Recovery Path,"* and the example *"similar CMC CRLs historically resubmit within 4.2 months and recover 40% of their initial post-CRL price drop within 90 days."* Those numbers are **invented** — Gemini made up 4.2 and 40% as illustration. And "recovery path" answers *"should I buy the dip?"*, which is one word from advice.

**Publishable version:** *"Of N CRLs citing manufacturing issues since 2020, N were followed by a resubmission; median time to resubmission was N months (n=N). Each letter linked."* Counts, n, links, no "recovery," no "path."

## S2 — Portfolio-aware dashboard + date-slip alerts → **KEEP, BUT IT IS BLOCKED**

Correct diagnosis of BioPharmCatalyst's weakness. **Date-slip detection already exists** — `watch_readouts.py` found 20 registry contradictions on its first sweep. Surfacing it to users is the right next step.

**Blocked by:** accounts + email/SMS require `/terms`, `/privacy`, `/refund-policy`, `/contact` — **all four still 404** (flagged in every audit since August). Nothing in S2 can ship before those exist. Gemini doesn't mention them.

## S3 — "Dilution Risk Matrix" → **REJECT AS WRITTEN**

*"mathematically demonstrate the probability of an immediate equity raise"* · *"flag the catalyst with a severe dilution warning"* · *"contextualizing why the stock might be heavily shorted into the event."*

That is a prediction, a warning label, and a trading rationale — the three things we don't publish. It would also put us in direct competition with BioRadar and FDA Tracker on *their* framing rather than ours.

**Publishable version, from data already on disk:** `conf_study/sec_shares_outstanding.json` (317 tickers) and `fmp_mcap_cache_6yr.json`. *"Shares outstanding rose 7.2% between March 2025 and April 2026."* *"Of N companies with under 12 months of runway at their PDUFA date since 2022, N filed an offering within 30 days of the decision (n=N)."* Fact, count, n. No "probability," no "risk," no "warning."

## S4 — Enterprise tier / Snowflake / "options market makers" → **DEFER**

Monetization advice, not moat advice. Doesn't move citations, impressions or rank. The T-120 series *is* valuable to exactly the buyers Gemini names — but selling it to hedge funds while publishing it CC BY 4.0 needs a licensing decision David hasn't made, and it competes for builder time with items that do move the moat. Park it.

## S5 — IRA countdown + PBM formulary mapping → **REJECT**

**IRA countdown on every small molecule is misleading.** Medicare negotiation applies only to drugs that reach the top-spend selection lists; the overwhelming majority of approvals never qualify. A countdown on every NDA implies every drug gets negotiated — false, and exactly the "false precision" the report condemns elsewhere. Also imprecise on the statute: selection eligibility begins 7 years post-approval for small molecules, negotiated prices take effect in year 9; Gemini conflates the two.

**PBM formulary mapping is data we don't hold, can't verify to primary source, changes annually, and no search query asks us for.** High maintenance, high error surface, zero citation value.

## S6 — "Anti-AI" attack marketing → **REJECT, FIRMLY**

*"Whenever a competitor's proprietary AI model predicts a 95% chance of approval … pdufa.bio should immediately publish a highly detailed public post-mortem … highlight the exact SEC filings, previous 483 inspection observations … the competitor's black-box AI model completely ignored … branding AI-probability competitors as 'speculative,' 'dangerous to retail capital,' and 'black-box.'"*

Four reasons this is wrong for us:

1. **It is itself a prediction.** A post-mortem saying "the 483 was there, they should have seen the CRL coming" claims *we* could have seen it — hindsight presented as foresight. That's the exact thing our manifesto forbids.
2. **Naming competitors and calling them "dangerous to retail capital" is a defamation surface** and turns a data source into a combatant. AI answer boxes cite neutral references; they do not cite polemics.
3. **It is a glass house.** We run ODIN v14 internally — a 51-feature approval-probability model — and choose not to publish it. A campaign built on "probability models are dangerous" is one leak away from reading as hypocrisy. Our position is *"we publish counts, not probabilities"* — a statement about what we publish, not a judgment of others.
4. **It doesn't address the actual competitive loss.** We're absent from the AI answer box because our facts are in tables, not sentences. Attacking BPIQ doesn't put a sentence on `/calendar`.

The right version of S6 already exists on the site: *"Do the studies predict outcomes? No. They measure what happened."* Say it more places. Never say it about someone else.

---

# 4. WHAT THE REPORT MISSED ENTIRELY

| Missed | Why it matters |
|---|---|
| **Speed as the moat** | The word "latency" does not appear. MIMRYLO caught 33 days early → `rusfertide pdufa date` went from nonexistent to 72 AI citations. Camizestrant, daraxonrasib, brepocitinib, zilganersen were all approved and missing until the drug-page watcher ran. Every measurable citation gain this month came from being *first and right*, not from features. |
| **The AI answer box** | Bing's answer on `pdufa dates 2026` cites five competitors and not us, directly above our #1 organic result. Google's AI Overview cites seven. The report never mentions answer boxes, grounding queries, or citation share — the metrics we actually track. |
| **Sentence supply** | AI answers quote definitional prose, honest FAQs, dated changelogs, captioned tables. We have data supremacy and sentence poverty. The report recommends more data. |
| **The datasets already on disk** | 2,714 options chains (71% event match), 45 quarters of specialist-fund 13Fs (49%), a 2017–2026 short-interest panel, six years of market cap (86%), a Form 4 index (83%). Gemini's S3 and S4 are weaker versions of what we already hold. |
| **Legal blockers** | `/terms`, `/privacy`, `/refund-policy`, `/contact` are 404. S2 and S4 cannot ship without them. |
| **Google is an authority war** | Indexed 57 of 1,412. Head-term position 68–81. The report proposes feature work; the gap is links and earned authority (the API as a link magnet, the datasets as citable objects). |

---

# 5. WHAT TO TAKE FROM IT

1. **CRL reason taxonomy** across the 458 letters — as counts with n, never as "recovery paths." This is the one new build idea worth the builder's time, and it lands on the `/crl` hub that already exists.
2. **Date-slip alerts to the front end** — once `/terms` and `/privacy` exist. Until then, the watcher output belongs on `/pdufa-date-changes` (still 404), which needs no account.
3. **Shares-outstanding delta per event** — the fact-only version of "dilution," from data we hold.
4. **The observation that the UI lags the data** — true, and the plain-language spec already addresses it. No new work implied.

---

# 6. ONE NEW AUDIT ITEM THIS SURFACED

**The short-interest study's method disclosure.** The `/research` index says *"FINRA short interest, point-in-time, matched to 1,753 FDA decisions."* The study page itself contains "FINRA" ×4 and "settlement" ×1 but **no method sentence stating which settlement dates were used.** The April red-team found BIFROST's SI features used a single April-2026 snapshot applied retroactively. Yesterday I found a full 2017–2026 FINRA panel on disk (`conf_study/si_panel_2017_2026.csv.gz`, 194 settlement dates). **Which one did the published study use?** If the panel — say so on the page, with the matching rule (nearest settlement ≤ T-14, say). If the snapshot — the "point-in-time" claim on `/research` is wrong and must be corrected, and the study recomputed from the panel. **Unverified from this evidence; for the builder's next slot.**

---

# BOTTOM LINE

Gemini correctly identifies the moat — verifiable facts, primary sources, an open API, no probabilities — and then proposes three strategies that would breach it: a dilution "probability," a countdown that implies every drug faces price negotiation, and a public campaign calling competitors dangerous. Its numbers for our own studies are stale or wrong in six of ten places, including quoting means from a page whose second sentence says means are meaningless. Its competitor list is the one on competitors' pricing pages, not the one on Google's first page.

**What it gets right, keep:** a CRL-reason taxonomy over the 458 letters we already hold, published as counts; date-slip alerts once the legal pages exist; shares-outstanding deltas as facts. **What it never mentions is what has actually moved the numbers this month:** being first to an approval, in a sentence an AI can quote. That remains the plan.

---
*Site figures verified live 2026-09-06. SERPs run live 2026-09-05. Not investment advice.*
