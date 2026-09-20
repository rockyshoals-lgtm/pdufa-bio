# Audit: the data is the most accurate it has ever been, and every date I found wrong today is one the data no longer holds
**2026-09-20, measured 20:40 UTC = 16:40 Eastern = 13:40 Pacific (Sunday).** *Per RULE 1 every time carries its zone. API `as_of` is Eastern; Vercel and GitHub are UTC; the machine is Pacific.*
**Live build `e91086372`, generated 2026-09-20T00:26:23Z. API `as_of` 2026-09-20, 456 rows.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. THE HEADLINE

Five days of work closed almost the whole 09-15 ORDER and the corpus is in better shape than at any point in this series. **Three of the four defects I found today share one shape, and it is a new one: a date that no longer exists in the dataset is still being rendered, because a renderer is reading it out of the event id.** The fourth is subtler and it matters more: one row in our flagship published statistic measures a different quantity from the other twenty-nine.

---

# 2. P0-A: ONE ROW IN THE TIMING STATISTIC IS MEASURED FROM A PRESS RELEASE

`/research/fda-decision-timing` states its own inclusion rule: *"2026 decisions where this archive holds the PDUFA goal date, **the actual FDA action date**, and a primary source we link."*

The TLX row does not meet it.

| Field | Live value |
|---|---|
| goal `date` | 2026-09-11, day precision, sourced |
| `decision_date` | 2026-09-14 |
| rendered on the study page | "goal September 11, 2026 → **September 14, 2026**, **+3 days**" |
| `decision_date_note` in the API | **null** |

**I read the source document.** Telix's ASX announcement, filed as EX-99.1 to the 6-K of 2026-09-14 (accession `0001628280-26-061892`, `pixclaraapprovalvfinal.htm`), is dated September 14 and says: *"Telix Pharmaceuticals Limited ... **today announces** that the United States Food and Drug Administration has approved its New Drug Application for Pixclara."*

**It states no FDA action date anywhere in the document.** We hold an announcement date and are publishing it in a column of action dates.

**Why this is not pedantry.** The goal date, September 11, was a **Friday**. The announcement, September 14, was a **Monday**. Agency acts late Friday, sponsor announces Monday is the single most common pattern in FDA approvals. TLX is **one of only four decisions in the "came after" bucket**. If the FDA acted on the 11th, TLX is an on-the-day decision and the published statistic is **19 early / 8 on the day / 3 late**, not 19 / 7 / 4.

**The builder already established the correct principle three days ago** and applied it in the other direction. On 09-18, MRK Lipfendra and OTSKY centanafadine were removed from this statistic because their goal dates were unsourced: the action date was wearing a goal date's field. TLX is the mirror image, one field over: the announcement date is wearing an action date's field. Same rule, same remedy.

The builder flagged the action day as open and said the margin would be corrected from the approval letter. My position is that it should not be in the statistic while it is open, because the page promises action dates and the note explaining otherwise **is not in the API and is not on the study page**.

---

# 3. P0-B: `/fda-this-month` PUBLISHES FOUR WITHDRAWN GOAL DATES, WITH EARLINESS FRAMING

| What the page says | What the API holds |
|---|---|
| "**Ahead of its September 30 goal date**, on August 5, the FDA approved Oveporexton (TAK)" | `pdufa_tak_2026-09-30` · `date: null` · precision **quarter** |
| "**Ahead of its September 30 goal date**, on August 27 ... Brepocitinib (PFE / ROIV)" | `pdufa_pfe_2026-09-30` · `date: null` · precision **quarter** |
| "**Ahead of its September 30 goal date**, on August 28 ... Rusfertide (PTGX)" | `pdufa_ptgx_2026-09-30` · `date: null` · precision **quarter** |
| "**Ahead of its November 30 goal date**, on September 9, the FDA approved HYRNUO (BAYRY)" | `pdufa_bayry_2026-11-30` · `date: null` · precision **month** |

None of those four rows holds a day-precision goal date. Three are the quarter-end placeholders withdrawn on 09-10 after Takeda and Priovant said "third quarter of calendar year 2026" in their own filings. The fourth is the November 30 that the builder withdrew on 09-14 because no Bayer filing states it.

**The root cause is precise and it is new.** The dates survive nowhere in the row except the **id**: `pdufa_tak_2026-09-30`, `pdufa_bayry_2026-11-30`. Under the 09-15 id policy the id is a deliberately stable primary key that keeps the date it was created with. The month page's sentence builder is reading the goal date out of the id rather than out of `date` and `date_precision`.

**That policy was the right call and I want to say so clearly, because I argued against it.** On 09-15 my item 3 asked for stale ids to be re-keyed. The builder pushed back: an id is a key a consumer may already hold, and re-keying on every FDA extension turns one event into two in their store. It shipped `date_history` instead. The builder was right. **But the decision created a hazard neither of us named: a withdrawn date now lives on in a stable field, where a renderer can pick it up by accident.** That is what happened here.

**The contrast is instructive, and the decision page is the standard.** `/fda-decision/BAYRY-2026-09-09` says, in its own words:

> "This page states no earliness figure, deliberately. We had carried a goal date of November 30, 2026 for this application and it was never sourced: no Bayer filing or release states it, and Bayer is not an SEC registrant, so there is no filing to check. The FDA's own approval letter for NDA 219972/S-001 shows the supplemental application was received on March 16, 2026, which under priority review points to September rather than November."

That is the best paragraph on the site. `/fda-this-month` is the surface it never reached. **Seventh instance of this class in three weeks.**

---

# 4. P0-C: THE COUNTDOWN IS ONE DAY STALE, ALL DAY, EVERY DAY

```
/build-info.json   next_date: "2026-09-21"   next_days: 2   built: 2026-09-20T00:26:23Z
now                2026-09-20 16:40 Eastern
correct answer     1
```

The build was generated at 00:26 UTC, which is **September 19 at 20:26 Eastern**. At that moment September 21 was indeed two days away and the value was right. It is computed once at generation and never recomputed, so from the moment the Eastern date rolls over the countdown is wrong by one, and it stays wrong for the rest of the day.

Because the build lands at roughly 20:26 Eastern, its notion of "today" is the *previous* Eastern day for essentially the entire following day. This is not an edge case; it is the normal state for about twenty hours out of twenty-four.

*A note on my own method: my first attempt to compute this returned 0 days, because I compared a date-only value against a locale-formatted string. I caught it and discarded it. The claim above rests on the plain calendar fact that today is September 20 Eastern and the date in question is September 21.*

---

# 5. A SMALLER PRECISION ITEM, IN THE MOST QUOTABLE SENTENCE ON THE PAGE

`/fda-this-month` opens, and its meta description repeats: **"3 FDA decision dates remain in September 2026."**

The three rows listed are September 21 (MRK, WINREVAIR), September 26 (INCY, zilurgisertib) and September 26 (MIRM, zilurgisertib). **INCY and MIRM are the same FDA decision** on the same application, which the page's own text confirms: *"Zilurgisertib (licensed to Mirum; MIRM holds the NDA)."*

So the true counts are **two distinct dates and two distinct FDA decisions**, carried on three rows. The FAQ further down is careful and correct ("16 tracked PDUFA **events** fall in September 2026"). The lede and the meta description are not, and the meta description is the string an answer engine lifts.

---

# 6. WHAT IS RIGHT, AND IT IS THE LARGER PART

**RARE FAYUVI, verified independently.** Ultragenyx 8-K filed 2026-09-17, accession `0001515673-26-000006`, Item 8.01. A full-text search for "FAYUVI" across EDGAR returns **exactly one document**, that filing. Approved two days ahead of a September 19 goal date that I sourced myself on 09-15 to the 8-K of 2026-04-02. Goal sourced, action sourced, margin real.

**The MRK and OTSKY removals are principled and I checked the arithmetic by hand.** Nineteen early plus seven on the day plus four late equals thirty. Sorted, the fifteenth and sixteenth margins are both minus two, so the stated median of "2 days before" is correct. The page is internally exact.

**The 09-15 ORDER is substantially closed.** `source_url` went from **0 of 456** to 262 and then to 43 of 48 upcoming rows. The CORT row that I reported in four consecutive audits is re-keyed `pdufa_cort_2026-12-17` with all four faults fixed and the date sourced to Corcept's 8-K of 2026-07-29. `date_month != date[:7]` is zero across the corpus.

**The Pro link retraction deserves a line.** The builder reported a 404 that was not a 404, and found it because its own live verifier asserted "/pricing is not 200" and production answered 200. A verifier catching the person who wrote it is the system working exactly as designed.

**And the run-up study size now has one owner.** Five surfaces carried hand-typed counts from July: 1,827 / 1,786 / 1,888 / 1,754. One number, one generator, one census guard. That is the same cure the timing statistic got on 09-14, applied before I asked.

---

# 7. CHANNELS: THE RE-TEST LANDED, AND ONE NUMBER REVERSED

## 7a. Bing web search, data through September 18

| 3-month window | To Sept 13 | To Sept 18 |
|---|---|---|
| Clicks | 419 | **512** |
| Impressions | 16.1K | **20.3K** |
| CTR | 2.6% | 2.52% |

**The September 14 re-test I set on 09-14 has landed: 1.1K impressions on that Monday.** The post-outage weekdays run 1,100 / 763 / 1,100 / 753 / 569 against an August baseline of roughly 400 to 500. **The September 8 step change is now confirmed as durable across two weeks and through a three-day outage**, which is the question I could not answer for six days.

The honest caveat: within that week the trend is downward, and September 18 at 569 is the lowest post-outage weekday. I would watch the level rather than bank it.

Positions improved on the core terms: `pdufa` 6.17 → 6.09 on 1.4K impressions, `pdufa date` 5.71 → **5.48** on 499, `pdufa calendar` 43 → 67 impressions and 11 → **14** clicks.

**A measurement caveat I should have caught earlier.** Several rows in this table are byte-identical across three consecutive reads: `pfizer pfe pdufa dates fda approval decisions 2026 2027` (82 / 0 / 3.23), `pdufa date for daraonrasib in usa` (64 / 0 / 7.02), `camizestrant pdufa date` (29 / 0 / 4.62), `rusfertide pdufa date` (26 / 2 / 7.69). Those rows are frozen in Bing's sample while others move. **I have treated the PFE zero-click anomaly as a live signal in three audits and I should not have; it has not refreshed.** Only rows that changed are readable.

## 7b. AI citations, data through September 18

| | To Sept 13 | To Sept 18 |
|---|---|---|
| Total citations | 5.2K | **6.9K** |
| Average cited pages | 18 | **21** |
| Grounding queries | 22 | **25** |

September 16 set series highs on both: **418 citations and 55 average cited pages** against previous ceilings of 368 and 42.

**The share decline I raised as the most important number on 09-14 has reversed and overshot.**

| Query | Sept 7 | Sept 13 | Sept 18 |
|---|---|---|---|
| **`pdufa date`** citations | 344 | 384 | **714** |
| **`pdufa date`** share | 18.23% | 16.10% | **22.59%** |

That is the clearest content-to-channel chain we have: the `/learn` five-section restructure shipped on September 15 as the deliberate answer to that decline, and the query it targeted nearly doubled in citations while share recovered past its starting point. `pdufa dates` moved 26.42% to **35.62%**, rare-disease readouts 32.59% to **35.90%**.

Oncology readouts grew in volume and lost share: citations 77 to **114**, share 66.38% to **60.32%**. The pool grew faster than we did. `fda calendar 2026` is frozen at exactly 322 and 28.96%, identical to two decimals, so I am treating it as not refreshed rather than as flat.

**The tavapadon trade, now quantified, and it is the number David will be asked about.** On 09-14 I reported that we held **100% citation share** on `tavapadon fda approval date` for a date no sponsor had ever published. The builder removed the date from the page.

> Citations 6 → **24**. Share **100% → 20.00%**.

That is the measurable price of the accuracy standard, and it is the right trade. Being the only source of a date nobody published is worse than being a minority source of a correct one, and the alternative was teaching Copilot a fabricated December 31. But it should be recorded honestly: correcting an unsourced date cost us four fifths of an answer we owned outright.

New queries this read: `marketbeat fda calendar` at 26.67% (we are cited on a competitor-branded query), `fda release schedule` at 26.09%, `upcoming clinical` at 6.67%.

## 7c. Google Search Console, 28 days through September 18

| | To Sept 13 | To Sept 18 |
|---|---|---|
| Clicks | 40 | **29** |
| Impressions | 2.29K | **2.53K** |
| CTR | 1.7% | **1.1%** |
| Average position | 13.4 | **11.7** |
| Queries | 103 | 109 |

**Clicks fell 27% while impressions rose and average position improved by 1.7 places.** That divergence is real and I am not going to explain it from a sliding window. Five days of slide drops five days at the front and adds five at the back, so part of the fall may be mechanical, and AI Overviews absorbing clicks is a live alternative. **The next read should use the DAYS tab for the daily series rather than the rolling total**, which is the instrument that can actually decompose it.

---

# 8. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Take TLX out of the timing statistic until the FDA action date is known**, or state on the page which rows are measured from an announcement date. Either way, expose `decision_date_note` in the API, where it currently returns null. Apply the 09-18 goal-provenance rule to the action-date field | The study page counts only rows where both dates are sourced to a document that states them; TLX carries its caveat wherever the +3 figure appears |
| **2** | **No rendered goal date may be derived from an event id.** Fix `/fda-this-month` to read `date` and `date_precision`; a row with `date: null` renders its window and never "Ahead of its <day> goal date" | Guard proved 0 → planted a day-shaped id on a quarter row → 1 → 0. TAK, PFE, PTGX and BAYRY read as windows on every surface |
| **3** | **Stop baking the countdown into the build.** Either recompute `next_days` at request time, or publish `next_date` and `next_status` only and let the client subtract | `next_days` is never stale; verified by fetching more than 24 hours after a build |
| **4** | **Count decisions, not rows, in the `/fda-this-month` lede and meta description.** Two dates and two decisions on three rows today | The lede matches the FAQ's own careful wording |
| **5** | **The five unbacked rows need your ruling and I will make my recommendation concrete: withdraw the day and the forward listing for all five** (ABBV tavapadon, AZN Ultomiris, BAYRY Kerendia, NVO CagriSema, NVO Mim8), keep the drug pages. The tavapadon share data is now the evidence for what publishing an unsourced date costs when it is wrong | Ratchet goes 9 → 4 or lower; no forward row asserts a date no filing supports |
| 6 | Carry: 22 readout leads, the 13 Estimated readouts the registry re-sync moved into the past, the therapeutic-area back-fill, the openFDA pass over the decided rows, `/calendar/2025` unmarked rows | |

---

# 9. WHERE THIS LEAVES US

**On accuracy, the direction is unambiguous.** Six days ago no row in the API could be traced to a source; today 43 of 48 upcoming PDUFAs carry one. The row I reported four times is fixed. The manufactured-day era is over and has stayed over. The next decision on the board was verified against the sponsor's own 8-K before it happened, and the approval that followed was verified again afterwards. The BAYRY decision page is the clearest statement of this site's standard that exists anywhere on it.

**The remaining defects are all the same defect and it has migrated.** It used to be a value corrected in the dataset and not in the pages. The dataset is now clean enough that the pages have nowhere to get a wrong date except the one field we deliberately froze: the id. Item 2 closes that door.

**And the channels finally answered two open questions in the same week.** The September 8 step change is durable. The `/learn` restructure did what it was built to do, on the exact query it targeted. Against that, we can now put a number on what accuracy costs when it means retracting something: four fifths of a query we owned outright. I would pay it again, and I would rather David hear it from me than from the chart.

---
*Live figures read 2026-09-20 between 20:30 and 20:55 UTC against build `e91086372`. API swept over all 456 rows. Telix announcement read in full at `0001628280-26-061892`; Ultragenyx approval confirmed at `0001515673-26-000006`. Bing and Google consoles read live; Bing data ends 2026-09-18, Google 2026-09-18. Not investment advice.*
