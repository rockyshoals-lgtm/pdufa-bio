# Audit: verification of the 09-08c ORDER
**Live build `2026-09-09T03:14:29Z` commit `c78438989`. API `as_of` 2026-09-09. Every claim below fetched from the live site during this run.**
*Facts and build mechanics only. Not investment advice.*

> **Tooling note, stated because it limits this pass.** The bash sandbox lost its filesystem mount and failed twice identically; Claude in Chrome is disconnected. I verified through `web_fetch` (which surfaces meta tags) and file-level grep of the repo. **No console read this pass**: the Bing and Google numbers below are yesterday's 11:00 PT read, restated, not re-measured.

---

# 1. THE ORDER: 6 PASS, 1 PARTIAL, 2 PUSHED BACK (both correctly), 1 DEFERRED

| # | Item | Verdict | Live evidence |
|---|---|---|---|
| 1 | Approved-drug snippets | **PASS** | `/drug/camizestrant` description: *"Camizestrant: FDA approved on September 4, 2026 as Etcamah. For AstraZeneca PLC. Full catalyst history, every date sourced. Facts only."* Contains approved, the full date, and the brand. Repo count: **270 drug pages** now carry "FDA approved on" in the description. |
| 2 | `/learn` timing numbers | **PASS** | Description: *"In 2026, 20 of 32 sourced decisions came early."* Body: *"of the 32 sourced 2026 decisions ..., 20 came before the goal date, 9 landed on it and 3 came after it."* 20+9+3=32. Matches `/calendar`. |
| 3 | CDN purge + verifier | **PARTIAL, correctly blocked** | Verifier exists and ran (`RESULT: PASS`, 18 fetches). Purge is gated on a `VERCEL_TOKEN` that does not exist. **This is David's action**: create a Vercel token with cache-purge scope and add it as a repo secret. Until then the SERP freshness problem I documented yesterday stays open. |
| 4 | ERS to Ended | **PUSHED BACK, and the builder is right** | `/conferences` shows **"ERS ... Sep 5 to 9, 2026"**. It is a five-day congress, still running tonight. See my correction in section 3. |
| 5 | `/odin-track-record` | **PASS** | 308 to `/why-no-approval-probability`, which resolves 200. |
| 6 | Month sentences / captions | **PASS (sentences), PUSHED BACK (captions), accepted** | Four month headings carry a naming sentence, e.g. *"In October the FDA is due to decide on Tecentriq (RHHBY, Oct 9), Ifinatamab deruxtecan (MRK, Oct 10) ..."*. Jun to Aug have no undecided rows and correctly get none. On `<caption>`: the builder is right that a `<caption>` outside a `<table>` is invalid HTML and the grids are `<div>`. **My acceptance check was wrong, not the implementation.** The `<p class="msent">` under each heading does the extraction job. I am not asking for a table conversion on the highest-traffic page for a tag name. |
| 7 | Explainer links | **PUSHED BACK: already live** | Confirmed: `/drug/camizestrant` carries `/learn/what-is-a-pdufa-date` twice. **I owe the builder this one**: I have listed it as open in five audits. It was shipped and I kept re-listing it without re-checking. |
| 8 | `/company/{slug}` | **PASS on the redirect and the title. FAIL on the description.** See section 2. |
| 9 | UNCY case study | **DEFERRED**, accepted | Not started. It is a full content build against the 09-06f spec. |
| 10 | Brand `alternateName` | **PASS with a correction the builder volunteered** | 16/18 brand-cache entries render. The two misses are honest: `tebipenem` has an empty brand, and **`bictegravir` was seeded as "Biktarvy", which is the existing bictegravir/emtricitabine/TAF product, not the Aug 27 bictegravir + lenacapavir approval.** The builder caught its own bad seed and did not publish it. That is the right call. |

## Also shipped, from the 09-06d conference red team, and not claimed in the ack

`/conferences` now carries, in the lede, the fact-only finding I specified:

> *"The FDA does not run these meetings, and the study behind this site finds no reliable pre-conference run-up: across 1,425 presentations the median presenter moved −0.03% in the 30 trading days before the meeting and −1.59% in the 5 days after."*

Presenter gating shipped too: unverified rows sit under **"Filings that mention this meeting (unreviewed)"** with the matched sentence, the source link, and *"A filing mentioning the meeting is not a confirmed presentation; these rows are not counted above."* PRECLINICAL labels are on SLS009, IBIO-610 and GLIX1. And JPM 2027 reads *"J.P. Morgan has not published 2027 dates. Third-party sites claim 11 to 14 January 2027; that is unverified and is not published here."*

That is the whole conference implementation from 09-06d, done in the fact-only form, including the parts that were easiest to fudge.

---

# 2. THE ONE REAL FAIL, AND IT IS THE ONE THAT COSTS CLICKS

**`/ticker/PFE` title is fixed. Its meta description is not.**

| Element | Live value |
|---|---|
| `<title>` | `Pfizer Inc. (PFE) FDA Catalysts: BRAFTOVI (encorafenib) in co \| pdufa.bio` |
| H1 | `Pfizer Inc. (PFE) FDA catalysts & readout calendar` |
| **`meta description`** | **`Roivant/Priovant (PFE) FDA catalysts. Next: Readout Oct 2026 for Palbociclib. 1 FDA decision on record. Source document and measured run-up on every one.`** |
| Body | `Pfizer Inc. · no upcoming catalyst on file · 10 past FDA decisions` |

The description is wrong on three counts at once: the wrong company, a "next" catalyst the page says does not exist, and 1 decision where the page lists 10. **The builder fixed the title/H1 owner (`enrich_ticker_hubs.py`) and the description owner was a different writer that did not get the majority-vote fix.** Same one-owner-per-field lesson as the CI clobber in early September, one field over.

This matters because it is the exact query in the audit: `pfizer pfe pdufa dates fda approval decisions 2026 2027`, **82 impressions at position 3.23, zero clicks**. A searcher at position 3 now sees a title that says Pfizer above a description that says Roivant. That is worse than the old state, where at least the two agreed.

**Second defect on the same page: the title is truncated mid-word.** `... BRAFTOVI (encorafenib) in co | pdufa.bio`. "in co" is a cut "in combination". That is in the emitted `<title>`, not display truncation. The generator is cutting at a character count without a word boundary.

**Acceptance:** `/ticker/PFE` description names Pfizer, states "10 FDA decisions on record", and does not claim an upcoming catalyst; title ends on a word boundary. Then check the other 33 hubs whose titles changed.

---

# 3. TWO CORRECTIONS I OWE

**ERS.** I wrote in 09-08b and 09-08c that ERS was "still `Scheduled` three days after it ended". ERS 2026 runs **September 5 to 9**. On September 8 it was in progress, which is what the page now says. I treated a five-day congress as a one-day event and called a correct state a currency defect, twice. The builder pushed back with the dates and the organiser link. Correct pushback; my error.

**The 18-page count.** I reported that 18 approved drug pages carried the generic description. **270 pages now carry an approval description**, and the builder's count of 277 is the right order of magnitude. My number came from intersecting two patterns that were each too narrow: a body string ("The FDA approved it on") that matches 244 of the pages, and a description string that matched 152. The intersection was an artifact of both, not a measurement of the defect. **The defect was roughly fifteen times larger than I reported, and I reported it as a residue of an earlier fix that had never happened.**

I also owe the builder the explainer-links item: shipped, and I carried it as open across five audits without re-checking.

---

# 4. NEW FINDING: THE SNIPPET FIX STOPPED AT APPROVALS, AND THE PENDING PAGES ARE THE HIGHER-VALUE HALF

`/drug/aficamten`, live:

- Body: *"Its PDUFA date is **Nov 14, 2026**, the FDA's goal date to complete review of the application."*
- Description: *"Aficamten: FDA catalyst dates and outcomes. For CYTOKINETICS INC. Every date and decision links its primary source. Facts only."*

**48 drug pages state an upcoming PDUFA date in the body and carry the generic description.** The guard the builder wrote covers pages whose latest decision row is an approval. Pending programs are out of its scope by construction.

This is the higher-value half of the same defect. **Ten of our nineteen Bing grounding queries are `{drug} pdufa date`.** A page whose snippet answers that query in the SERP ("Aficamten: FDA decision due November 14, 2026. For Cytokinetics.") is the single most direct thing we can do for both the click and the citation. Right now those 48 pages say nothing in the snippet that the query asks for.

**Same class, third instance:** `/conferences` carries the run-up finding in the body and a generic description (*"Every major 2026 medical conference where biotech companies present clinical data, ASCO, ESMO, ASH, AACR and more, with dates, locations"*). The quotable sentence, the one no competitor can write, is invisible to the SERP.

**The pattern is now clear enough to state as a rule:** every page that computes a fact worth searching for should put that fact in its description. We have been fixing this page-type by page-type. It should be one owner, one rule, across all templates.

---

# 5. CHANNELS: NOT RE-READ THIS PASS

Restating yesterday's 11:00 PT figures so the next read has a baseline, not as new measurements.

| | Sept 6 data |
|---|---|
| Bing | 317 clicks, 10.7K impressions, 2.97% CTR (3 mo) |
| Bing AI | 3.7K citations, 15 avg cited pages, **19 grounding queries, flat two weeks** |
| Bing answer box `pdufa dates 2026` | organic #1, **not cited**; box cites biomednexus, medswitcher, novapharmanews, assyro |
| Google | 53 clicks, 3.2K impressions, 1.7% CTR, position 19, 162 queries |
| Google Generative AI | 58 impressions, 15 pages |

**Two dated re-tests still owed, both needing Chrome:** the Sept 13 answer-box check, and grounding queries after the entity work lands.

---

# 6. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **`/ticker/PFE` description**: same majority-vote owner as the title. Then audit the other 33 changed hubs. | description names Pfizer, "10 FDA decisions on record", no phantom upcoming catalyst |
| **2** | **Title truncation on word boundary** across ticker hubs | `/ticker/PFE` title does not end mid-word; no hub title ends in a partial token |
| **3** | **Pending-drug snippets**: 48 pages with an upcoming PDUFA date get it in the description. One owner with the approval rule; extend the guard to "row has a day-precision future date ⇒ description states it". | `/drug/aficamten` description contains "November 14, 2026"; count of pending-with-date pages carrying the generic string = 0 |
| **4** | **`/conferences` description** carries the run-up finding | description contains "1,425" and "no reliable pre-conference run-up" or equivalent |
| 5 | **UNCY case study** per 09-06f, linked from `/why-no-approval-probability` | that page argues *"a drug can have two clean Phase 3 trials and still get a CRL for a manufacturing problem, a third-party facility inspection"*. **UNCY is the worked example of that exact sentence.** Acceptance list in 09-06f §5. |
| **David** | **Vercel token** with cache-purge scope, as a repo secret | verifier's purge step stops logging a skip |

Items 1 to 4 are all one class: a computed fact that exists in the body and not in the snippet. Doing them as one owner is cheaper than doing them as four.

---

# BOTTOM LINE

**Six of ten ORDER items pass live, two pushbacks are correct, and one deferral is reasonable.** Camizestrant's snippet now says it was approved on September 4 as Etcamah, `/learn` and `/calendar` finally agree on 20 of 32, the `/odin-track-record` 404 is a redirect, and every October decision now has a sentence naming the drugs. The conference work from the 09-06d red team is also live and is the honest version, including the "unreviewed filings" bucket and the refusal to guess JPM's 2027 dates.

**One item shipped half-fixed and it is the one with a number attached.** `/ticker/PFE` now has the right title over a description that still says Roivant/Priovant, promises a catalyst the page says does not exist, and undercounts the decisions by nine. That page sits at position 3.23 on 82 impressions with zero clicks, and the description is what a searcher reads.

**I owe two corrections and they are not small.** ERS is a five-day congress and I called it a stale record twice. And the generic-description defect was about 270 pages, not the 18 I reported; my count intersected two patterns that were each too narrow, then I described the result as the residue of a fix that had never happened.

**The new finding is the same defect one page-type over, on the more valuable half.** Forty-eight drug pages know their PDUFA date and do not say so in the snippet, and `{drug} pdufa date` is ten of our nineteen grounding queries. Fix that with one owner and one rule rather than another per-template pass.

---
*Verified live 2026-09-08 evening Pacific against build c78438989. Channel figures are the Sept 8 11:00 PT read, not re-measured. Bash and Chrome unavailable this pass. Not investment advice.*
