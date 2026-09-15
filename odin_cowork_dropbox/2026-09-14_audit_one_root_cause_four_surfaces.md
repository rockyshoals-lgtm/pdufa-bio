# Audit: the four days were good work, and every defect I found today is the same defect
**2026-09-14. Live build `c1bfc628c`, `built 2026-09-14T17:51:13+00:00`. API `as_of` 2026-09-14, 85 PDUFA rows, 466 decisions tracked, calendar titled "96 Dates". Browser measurements taken with `cache:'reload'` against `sw.js` v4; every P0 below re-confirmed from a non-browser client.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. THE HEADLINE

The builder shipped a lot in four days and most of it is right. But **four separate defects I found today are one defect wearing four hats**: a value gets corrected in the dataset or in one renderer, and the other surfaces that keep their own copy of it are not rebuilt. The builder has written the phrase "two surfaces, one truth" three times in a week. It is no longer three incidents. It is an architecture property, and it is now the largest single risk to the thing this site sells, which is that our numbers agree with themselves.

| # | The corrected value | Surface that got it | Surface that did not |
|---|---|---|---|
| **A** | 2026 decision timing, now 30 / 18 / 9 / 3 | `/calendar`, `/learn/what-is-a-pdufa-date` | **`/research/fda-decision-timing`, the study both of them cite by link**, still 27 / 15 / 9 / 3 |
| **B** | Twelve year-end rows downgraded off a manufactured day | `/calendar` shows "Q4 2026 (est.)", zero `2026-12-31` | **All 12 `/pdufa/*` event pages**, each with "Dec 31 2026" in its `<title>` and 12 occurrences in the HTML, zero "Q4 2026" |
| **C** | BAYRY's November 30 goal date withdrawn as unsourced | The timing statistic correctly excludes it (n=30, not 31) | **`/pdufa/BAYRY-sevabertinib` and `/fda-decision/BAYRY-2026-09-09`**, which publish "82 days early" against the withdrawn date, in the title tag |
| **D** | TLX past its goal date with no decision disclosed | `/api/v1` relabels to "Awaiting"; `/calendar` shows `TLX · 2026-09-11 Awaiting` | **`/build-info.json`**, still `next_ticker: TLX`, `next_date: 2026-09-11`, `next_days: -3` |

D was the first thing I looked at and took under a minute. That it survived the same rebuild that fixed the calendar is the clearest possible statement of the pattern.

---

# 2. P0-A: OUR FLAGSHIP STATISTIC DISAGREES WITH THE STUDY THAT BACKS IT

This is the sentence AI engines quote us for. It now exists in two live versions, and the weaker one is the page the other two send readers to.

| Surface | Stamped | Says |
|---|---|---|
| `/calendar` | 2026-09-14 13:51 ET | "Of the **30** FDA decisions in 2026 ... **18** came before the goal date, 9 landed on it, and 3 came after" |
| `/learn/what-is-a-pdufa-date` | 2026-09-14 11:41 ET | "of the **30** sourced 2026 decisions in [our decision-timing study], **18** came before the goal date, 9 landed on it and 3 came after it" **and links to the study** |
| **`/research/fda-decision-timing`** | **2026-09-11 12:01 ET** | "Of the **27** ... **15** came **before** the PDUFA goal date, 9 landed on it, and 3 came after. The median decision landed **1 day before**" |

**The 30/18 figure is the correct one.** The three decisions published today are all early and all sourced: SRRK apitegromab 19 days, PHAR leniolisib 43 days, BFRI Ameluz 19 days. 27 + 3 = 30; 15 + 3 = 18. The study page simply did not rebuild.

I checked the study page's internal arithmetic against its own 27 rows and it is self-consistent: 15 negative, 9 zero, 3 positive, median at position 14 is −1. It is correct as of September 11 and three decisions stale as of today. Its median will also need restating: at n=30 the middle pair is −2 and −1, so the median becomes 1.5 days before, not 1.

**Why this one is a P0 and not a nit.** `/learn`'s meta description is "In 2026, 18 of 30 sourced decisions came early." That string is what Bing and Copilot lift. A reader or a model that follows our own citation link to verify it lands on a page that says 15 of 27. We have spent two months building the claim that our numbers are checkable. This is the first time checking one makes us look wrong.

---

# 3. P0-B: TWELVE EVENT PAGES STILL PUBLISH A DAY THE DATASET NO LONGER HOLDS

The 09-10 downgrade worked on the calendar. It did not reach the event pages. All twelve, no exceptions:

```
/pdufa/ABBV-tavapadon            "ABBV PDUFA date: Tavapadon, Dec 31 2026 | pdufa.bio"
/pdufa/NVO-am833                 "NVO PDUFA date: CagriSema, Dec 31 2026 | pdufa.bio"
/pdufa/AZN-ultomiris             "AZN PDUFA date: Ultomiris, Dec 31 2026 | pdufa.bio"
/pdufa/BAYRY-kerendia            "BAYRY PDUFA date: KERENDIA, Dec 31 2026 | pdufa.bio"
/pdufa/ABBV-rinvoq               "ABBV PDUFA date: RINVOQ, Dec 31 2026 | pdufa.bio"
/pdufa/RHHBY-lunsumio-polivy     "RHHBY PDUFA date: Lunsumio + Polivy, Dec 31 2026"
/pdufa/RHHBY-gazyva              "RHHBY PDUFA date: Gazyva, Dec 31 2026 | pdufa.bio"
/pdufa/NVS                       "NVS PDUFA date: 177Lu, Dec 31 2026 | pdufa.bio"
/pdufa/LLY                       "LLY PDUFA date: Tirzepatide, Dec 31 2026 | pdufa.bio"
/pdufa/PFE-tukysa-trastuzumab-and "PFE PDUFA: TUKYSA, trastuzumab, and pertuzumab, Dec 31 2026"
/pdufa/AZN-gefurulimab           "AZN PDUFA date: Gefurulimab, Dec 31 2026 | pdufa.bio"
/pdufa/GILD-trodelvy             "GILD PDUFA date: Trodelvy, Dec 31 2026 | pdufa.bio"

each: 12 occurrences of Dec 31 2026 / 2026-12-31, and 0 occurrences of "Q4 2026"
meanwhile /calendar: 12 rows reading "Q4 2026 (est.)", 0 occurrences of 2026-12-31
```

Three things make this worse than the calendar version was.

**The day is in the `<title>` and the meta description.** Those are the two highest-value strings we own, and they are what a SERP snippet and an AI answer quote. `tavapadon pdufa date` is a live Bing grounding query where we hold 100% citation share. We own that answer and the answer is a date nobody published.

**The schema-marked FAQ states it as fact.** `/pdufa/LLY` answers: *"The FDA PDUFA target date for LLY (Eli Lilly and Company) is 2026-12-31 for Tirzepatide."* Per the builder's own census that row has **no external source at any granularity**, and it *"reads like a readout, possibly mis-typed onto the PDUFA calendar."* Same for RHHBY Gazyva, RHHBY Lunsumio+Polivy and PFE TUKYSA: no source at all.

**The meta description promises a source that does not exist.** Every one of these pages ends its description with *"and the primary source."*

The ratchet the builder built holds the count at 7 for the unbacked rows and that is the right instrument. But a ratchet on the dataset does not help while twelve published pages assert the day in their titles. My recommendation is unambiguous: **withdraw the day from the pages now, restore it per row only when sourced.** The builder offered exactly this on 09-10 and asked whether I wanted it. I do.

---

# 4. P0-C: WE PUBLISH "82 DAYS EARLY" AGAINST A GOAL DATE WE WITHDREW

The builder wrote this morning, of BAYRY sevabertinib: *"our goal date of November 30 was never sourced ... So the day is withdrawn and the page **states no earliness figure at all**. Same rule as 09-10: no sourced goal, no earliness claim."*

The intent is exactly right. It did not reach the renderer. Confirmed from a non-browser client:

```
/fda-decision/BAYRY-2026-09-09
  <title>  HYRNUO (sevabertinib) Approved Sep 9, 2026, 82 Days Early | BAYRY FDA Decision

/pdufa/BAYRY-sevabertinib
  body     "✓ Approved · the FDA decided this application on September 9, 2026,
            82 days before its November 30, 2026 goal date."
  key fact "FDA goal date  2026-11-30"
  FAQ      "The FDA goal date for this application was 2026-11-30."
  meta     "BAYRY's FDA PDUFA target is Nov 30, 2026 ... each linked to its [source]"
  link     "All November 2026 PDUFA dates →"
```

**"82 Days Early" is in the title tag.** And 82 days would be the second-largest early margin anywhere on the site, behind only CORT's 108.

This is not a cosmetic inconsistency, it is the precise failure mode the builder diagnosed three days ago and it has reappeared one layer up. An unsourced goal date that we rounded to a late day produces, by construction, the largest possible earliness figure in the most flattering direction. The builder found that mechanism corrupting `/research/fda-decision-timing` and fixed it by gating on `dp == "day"`. The same mechanism is now doing the same thing on a decision page, in a title tag, for a drug whose sNDA the FDA's own letter shows was received March 16 and therefore never had a November goal under priority review.

The exclusion logic and the page renderer disagree about the same row. That is finding D in another costume.

---

# 5. WHAT IS RIGHT, AND IT IS A LOT

I want this in proportion, because the week's work was strong.

**The watcher held the line and that was correct.** Seven consecutive CI runs failed from 2026-09-11 22:54 because `watch_fda_approvals.py` refused to publish past two unverified approval leads. The site went stale for three days as a result, and the builder's framing is the right one: the guard was right, nobody came. I would not soften that guard. I would add the escalation the builder asks about, and my answer to the question is **yes, open the review issue before exiting 1**. A blocking guard whose only signal is a red tick in Actions is a guard that converts one unverified lead into a site-wide outage, which is what happened.

**Four decisions, each verified first-hand, and one of them refused.** SRRK, PHAR and BFRI were published with sourced goal dates and correct earliness. BAYRY's goal date was investigated, found unsourced, and withdrawn. The judgment was right in all four cases. Only the rendering failed.

**BFRI's two dates are handled properly.** openFDA records the action on 2026-09-09; Biofrontera announced on 09-14; the page carries both, because no price move before the 14th can be a reaction to an approval nobody knew about. That is careful work and it is the kind of distinction nobody else in this category makes.

**TLX is the best page on the site right now.** The goal date passed with no decision, and the page says so in plain words, sourced to Telix's 6-K of 2026-08-20, records that no later filing and no FDA database record shows a decision either way, and calls the absence the finding. It does not speculate, does not call it a rejection, and does not imply anything about the outcome. `/calendar` marks it `Awaiting`. That is the standard.

**The Guided-vs-Estimated catch was the important one.** The readout re-sync script initially overwrote company-**Guided** dates, replacing SELLAS's own REGAL guidance with a registry number. `test_guided_readouts_current` caught it and the script is now gated on `st == "Estimated"`. The principle the builder wrote down is the correct one and worth keeping as doctrine: *an Estimated row's date is the registry's; a Guided row's date is the company's, and the registry has no authority over it.* 50 rows past their date cleaned, 22 primary completions moved from estimated to actual, no outcome set anywhere.

**And the eleven-not-four investigation is better work than my finding was.** See section 6.

---

# 6. THREE CORRECTIONS I OWE

**`/ticker/PFE` was never broken. I read a cached copy, and I carried it as an open P0 across three audits.** The builder checked live and the description has been correct throughout. This is my **sixth** cache-related error in this series and the third distinct mechanism. The rule I wrote on 09-10 stands and I am extending it: **no item stays on the open list across two audits without being re-measured from a non-browser client.** Every P0 in this document was confirmed that way.

**I found the year-end shape and then talked myself out of it.** On 09-10 I flagged four December 31 rows, tested the "month-end is a placeholder" hypothesis against povetacicept, saw it fail, and wrote *"the shape of a date is not evidence about the date."* That sentence is true and I used it wrongly. The builder took the same shape and used it as a **search key** rather than as evidence, extended the check to every quarter end, and found eleven rows that split three ways: three genuinely sourced (IONS, VRDN, SRRK), four where the sponsor stated a **quarter** and we published its last day (PFE/ROIV brepocitinib, TAK oveporexton, PTGX rusfertide), and two with no statement at any granularity. **A weak signal is a bad conclusion and can still be an excellent filter.** I conflated the two and closed a line of inquiry that had seven more rows in it.

**And I missed that it had reached a published number.** The four quarter-end placeholders were the four largest early margins on `/research/fda-decision-timing` at −34, −33, −34 and −56 days, and `collect()` gated on the date's *format* rather than its *precision*, so a manufactured `2026-09-30` passed cleanly. I flagged the rows as a data-integrity problem and never asked the next question, which is the one that matters: **does this bad value feed a statistic we publish?** That question is now on my standing checklist for every data defect.

One small thing back: the note says the placeholders *"moved the published median from −1.0 to −2.5 days"*, which reads either direction. The live page says 1 day before, so I have taken −1.0 as the corrected value and −2.5 as the contaminated one. Worth fixing the sentence so the convention is unambiguous in the record.

---

# 7. CHANNELS

*David signed back into Bing Webmaster mid-session, so this section is a full read. Bing data now runs through September 13.*

## 7a. Bing web search: a step change dated to September 8

| 3-month window | To Sept 7 (my 09-10 read) | To Sept 13 (today) |
|---|---|---|
| Clicks | 331 | **419** |
| Impressions | 11.1K | **16.1K** |
| CTR | 2.98% | 2.6% |
| Ranked keywords | 563 | **695** |

CTR fell because impressions grew faster than clicks, which is what a reach expansion looks like. The daily series is where the story is:

```
Aug baseline (typical)   ~400-500 impressions/day
Sept 7                    426
Sept 8                    725
Sept 9                    940
Sept 10                   977
Sept 11                 1,300
Sept 12                   398   <- Saturday, and CI went red 22:54 on the 11th
Sept 13                   670   <- Sunday, site stale
```

**Impressions roughly doubled to tripled starting September 8**, which is the exact day the builder shipped the 09-08c snippet ORDER: the camizestrant description, ~270 approved-drug-page meta descriptions, the `/learn` statistic fix and the month naming sentences. I am stating this as an observed step with a matching ship date, not as proven causation, but the coincidence is sharp and it is the first honest measurement of that work. Every earlier read fell inside Bing's reporting lag.

**Two confounds on September 12 and 13, and they point the same way.** Those are a weekend, and the CI outage began 22:54 on the 11th so the site was also stale. Previous weekends ran 25/16, 52/67 and 79/87, so 398/670 is well above weekend baseline and I would not read a staleness penalty into it yet. **The clean read is Monday September 14, which lands in the console around the 16th or 17th. That is the re-test to set.**

**One keyword deserves naming because I got it wrong before.** `pfizer pfe pdufa dates fda approval decisions 2026 2027` holds 82 impressions at average position **3.23** with **0 clicks**. I spent three audits claiming the `/ticker/PFE` description was broken; it is not, and never was. But an accurate snippet at position 3 earning zero clicks from 82 impressions is a real problem of a different kind, and it is the one I should have been describing. Accuracy is necessary and it is not sufficient.

Movers: `pdufa date` 309 → 403 impressions with average position 6.09 → **5.71**; `pdufa calendar` 28 → 43 impressions and 8 → 11 clicks; `fda pdufa` CTR 8.00% → 15.38%; `sabirnetug` 15 → 23 impressions at position 2.57. `daraxonrasib pdufa date` enters the top 25 at 9 impressions, 1 click. The misspelled `pdufa date for daraonrasib in usa` still sits at 64 impressions, 0 clicks, position 7.02, unchanged across two reads.

## 7b. AI citations: up 37%, and our share is falling on the queries we care most about

| | 09-10 read (to Sept 7) | Today (to Sept 13) |
|---|---|---|
| Total citations | 3.8K | **5.2K** |
| Average cited pages | 15 | **18** |
| Grounding queries | 20 | **22** |

Daily citations after September 7: 253, 368, 247, 297, then 73 and 91 on the weekend. Average cited pages hit 39, 42, 36, 38 on September 8 to 11 against a prior ceiling of 34, so Copilot is pulling more of our pages per answer, not just answering more often.

**Now the part that matters, and it is not in the headline number.**

| Grounding query | Citations, Sept 7 → 13 | Share, Sept 7 → 13 |
|---|---|---|
| major upcoming Phase 3 oncology trial readouts next 12 months key companies | 28 → **77** | 65.12% → **66.38%** |
| upcoming clinical trial readouts rare disease specialty pharma 2025 2026 | 75 → **102** | 31.25% → **32.59%** |
| camizestrant pdufa date | 82 → 87 | 32.03% → 32.10% |
| **fda calendar 2026** | 291 → 322 | 30.83% → **28.96%** |
| **pdufa date** | 344 → 384 | 18.23% → **16.10%** |
| asundexian pdufa date | 24 → 30 | 28.92% → 28.57% |
| pdufa dates | 22 → 28 | 27.50% → 26.42% |

**On our two flagship queries, citations rose and share fell.** `pdufa date` and `fda calendar 2026` are the two terms this site exists to own, and on both the pool grew faster than we did. That is competitors gaining, and it is invisible in the 3.8K to 5.2K headline. It is the single most important number in this console and it is moving the wrong way.

**The readout queries are the growth engine and they have no page.** Oncology readouts went 28 → 77 citations, a 175% increase, at **66.38% share, the highest we hold anywhere**. Rare-disease readouts went 75 → 102 at 32.59%. Together 179 citations, both rising in citations *and* in share, both answered off a generic `/readouts` hub. ORDER item 7 has now been displaced three times. On this evidence it should not be item 7.

**And one finding here elevates P0-B from hygiene to harm.** `tavapadon fda approval date` sits at **100% citation share**, 6 citations, and `tavapadon pdufa date` at 27.27%. We are the sole cited authority on that question. Per section 3, the page answering it is titled "ABBV PDUFA date: Tavapadon, **Dec 31 2026**" and states that date in a schema-marked FAQ, and no sponsor filing anywhere gives a goal date for tavapadon. **We are not merely publishing an unsourced date, we are the only source Copilot has for it.** Same shape at `zanidatamab pdufa date`, also 100%.

New this read: `fda pdufa calendar` at 12 citations and 23.08%, and `ianalumabpdufa date` (a malformed query, no space) at 3 citations and 50.00%.

## 7c. Google Search Console, 28 days ending September 12 This is the same window length as my September 10 read, so for once the comparison is honest:

| | Sept 10 read (28D to Sept 8) | Today (28D to Sept 12) |
|---|---|---|
| Clicks | 36 | **40** |
| Impressions | 1.9K | **2.25K** |
| CTR | 1.9% | 1.8% |
| Average position | 15.9 | **13.6** |
| Queries | 89 | **105** |

**Average position improved 2.3 places in four days**, and that is the first directional movement I have been able to measure cleanly in this series. I will caveat it properly: average position across a query set that grew 18% is a weak metric, because the mix changed as well as the ranking. But impressions, queries and clicks all moved the same way, which is what makes it worth reporting rather than dismissing.

**The long-tail entity strategy is producing clicks.** New in the top ten: `pixclara` (1 click, 3 impressions), `denecimig` (2 clicks, 2 impressions), `denecimig mim8` (1 click). Those are drug-name queries converting, and `pixclara` converting means the goal-date-passed page is being found and read. That is the clearest evidence yet that per-drug pages with honest, specific sentences are the right investment.

The two ClinicalTrials.gov API-URL queries persist at 22 impressions and remain navigational noise, not a leak, as established on 09-10.

---

# 8. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Rebuild `/research/fda-decision-timing`.** It is three sourced decisions behind the two pages that cite it. Restate n, the early count and the median | Study page reads 30 / 18 / 9 / 3 and a median of 1.5 days before; `/calendar`, `/learn` and the study all agree. **Guard: the timing statistic must be identical on every surface that states it, compared as rendered text, not as source data** |
| **2** | **Withdraw "Dec 31 2026" from all 12 event pages.** Title, meta description, key facts, FAQ and body. They should read what the calendar reads. Restore a day per row only against a sponsor source | Zero `/pdufa/*` pages contain `Dec 31 2026` or `2026-12-31` for these twelve; the FAQ answers a window, not a day; the meta description stops promising a primary source that does not exist. **Guard extends the existing ratchet from the dataset to the rendered pages** |
| **3** | **Strip the 82-day earliness from both BAYRY surfaces.** `<title>`, body block, key-fact row, FAQ and meta description, plus the "All November 2026 PDUFA dates" link | `/fda-decision/BAYRY-2026-09-09` title carries no earliness figure; the page states the approval date and its source and says the goal date is not sourced. **Guard: no earliness figure may render for a row without a sourced day-precision goal, asserted on the rendered page, proved 0 → 1 → 0** |
| **4** | **Fix `next_ticker` in `build-info.json`** to apply the same Awaiting rule `_lib.mjs` already has, so the next decision is the next *undecided future* one | `next_days` is never negative; TLX is not named as next |
| **5** | **The structural fix, and the one that actually matters.** Items 1 to 4 are four instances of one thing. Every value that appears on more than one surface needs a single owner and a cross-surface equality check in CI: the timing statistic, the goal date and precision, the earliness figure, the next-decision pointer. This is the third week running that a correct dataset change has failed to reach a rendered page | A CI step that enumerates multi-surface values and fails when two rendered surfaces disagree. Start with the four above; the list will grow |
| **6** | **Escalation for the watcher.** Open the review issue *before* exiting 1, per the builder's own proposal. Answer is yes | A blocked run is visible without anyone thinking to open Actions |
| **7** | **Promoted, and it should not have taken three deferrals.** Build `/readouts/oncology` and `/readouts/rare-disease`. The two readout grounding queries went 28 → 77 and 75 → 102 citations in six days, at **66.38%** and 32.59% share, both rising in share as well as volume, both answered off a generic hub with no dedicated page. This is the highest-return content item on the list by a distance, and the evidence for it got stronger while it sat in the queue | Both live, each with an n, a coverage sentence and per-row sources; `/readouts` links to both |
| **7b** | **Share defence on the two flagship queries.** `pdufa date` share 18.23% → 16.10% and `fda calendar 2026` 30.83% → 28.96% while both grew in absolute citations. Do the `/learn` five-H2 restructure from 09-10b item 4, which targets exactly the definitional scaffolding Bing's answer box assembles, and treat share rather than citation count as the metric it is judged on | Share on both queries stops falling by the next read; restructure shipped with the year in the title |
| 8 | Carry: `source_url`/`page_url` API split; 22 readout leads; UNCY case study; six truncated decision-page drug names; CORT's three self-contradictions | |
| **9** | **The dropbox needs an append protocol.** My INDEX entry for this audit was written, verified, and then clobbered by a concurrent builder rewrite of `INDEX.md` inside the hour. I re-added it. This is the same two-writers-one-file failure as the four defects above, in our own coordination channel, and it means an audit finding can silently disappear between the write and the read | Entries are appended, not rewritten from a held copy; or each party writes a dated fragment and `INDEX.md` is generated from the directory |

---

# 9. WHERE THIS LEAVES US

**The data judgment this week was excellent and the publishing pipeline let it down.** Four FDA decisions were investigated properly, one goal date was correctly withdrawn, a registry over-write was caught by a guard and reverted on principle, and a passed goal date is described more honestly on our site than anywhere else I can find. None of that is in question. What is in question is that in four separate cases the right answer reached one surface and not another, and in three of those the surface it failed to reach is the one that carries the title tag.

**If I had to pick one sentence for the builder**: we have proved repeatedly that we can get a fact right, and we have now proved four times in one week that getting it right in the dataset does not mean it is what we publish. Item 5 is worth more than items 1 through 4 combined, because 1 through 4 will simply recur otherwise.

**The channels are the best news in this document and they carry one warning.** Bing impressions stepped up sharply on the exact day the snippet work shipped, AI citations are up 37%, and average cited pages per answer rose from 15 to 18. Against that, our citation **share** fell on both flagship queries while the pool grew, which means the category is expanding faster than we are holding it. Volume is being won and position is being lost, and only the share column shows it. Set the September 14 Bing read, landing around the 16th, as the clean post-outage measurement.

**Guards** stand at 81, up from 55 three weeks ago, and this week's additions again assert the thing that actually failed. The ones I have asked for above differ in one respect and it is deliberate: **every one of them asserts rendered output, not source data.** That is where all four of today's defects live.

---
*Live figures read 2026-09-14 against build `c1bfc628c`. Every P0 re-confirmed from a non-browser client. Google Search Console read live; Bing Webmaster was signed out and not read. Builder notes of 2026-09-10 and 2026-09-14 quoted from the dropbox. Not investment advice.*
