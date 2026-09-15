# Audit: dates, checked exhaustively. Nine of ten structural checks are clean, one row fails four ways, and nothing in the API can be sourced
**2026-09-15. Measured at 17:51 UTC = 13:51 Eastern = 10:51 Pacific.** *Per RULE 1, every date in this document is stated with its zone. The site's `as_of` is Eastern; Vercel and GitHub are UTC; the machine is Pacific.*
**Live build `a62614368`, `built 2026-09-15T04:58:31Z`. API `as_of` 2026-09-15, 456 rows.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. METHOD, BECAUSE ACCURACY IS THE ASK

Every figure below was computed against the live API in one pass rather than sampled, so the denominators are the whole corpus and not a selection. Ten structural date invariants were run over all **456** rows. Where a claim concerns what the origin serves, it was measured from more than one client and the disagreement is reported rather than resolved by preference. Where I could not verify something, it is marked unverified rather than omitted.

---

# 2. WHAT IS CLEAN, AND IT IS THE LARGER PART OF THE STORY

Nine of ten invariants return zero violations across all 456 rows.

| Check | Result |
|---|---|
| `as_of` equals today Eastern | **2026-09-15 = 2026-09-15** ✓ |
| Rows carrying a `date` at non-day precision (the 09-09 rule) | **0** |
| Rows at day precision with no `date` | **0** |
| Day-precision PDUFAs past their goal still labelled "Upcoming" | **0** |
| Rows with a `decision_date` in the future | **0** |
| `Decided` rows missing `decision_date` or `outcome` | **0** |
| Duplicate event ids | **0** |
| `Scheduled` conferences already past; `Ended` conferences still future | **0** and **0** |
| `Guided` readouts past their stated date | **0** |

**Precision census:** day 120, month 271, quarter 63, year 2. Sums to 456.
**Status census:** Estimated 266, Guided 57, Upcoming 48, Scheduled 39, Decided 36, Reported 4, Ended 2, Held 2, Awaiting 1, In progress 1. Sums to 456.

**The manufactured-day problem is genuinely dead.** The day-of-month histogram across all 120 day-precision rows is flat, and **the 15th now holds 2 rows**. In the 09-09 sweep it held 263. That is the single largest data-quality recovery in this series and it has held for six days.

The 30th holds 11 of 120, the largest bucket against an even-spread expectation of about 4. I am **not** calling that a finding. I called month-end a placeholder shape on 09-10 and was refuted by the first row I checked, and the quarter-end guard already covers the subset where rounding actually lands. Recording it as worth a periodic look, nothing more.

**One conference check I made a point of running.** `/conferences` marks IASLC WCLC "In progress" today. Its JSON-LD gives `startDate 2026-09-12`, `endDate 2026-09-15`. Today is the 15th, so "In progress" is **correct**. I checked because I twice called ERS stale by treating a multi-day congress as a one-day event, and I am not repeating it.

---

# 3. P0: ONE ROW FAILS FOUR WAYS, AND THREE OF THEM ARE DATES

`readout_cort_2026-09-15` is the only row that fails a structural check, and it fails comprehensively. Full live field dump:

```
id                readout_cort_2026-09-15     <- "readout_" prefix on a type:"PDUFA" row,
                                                 carrying the RETIRED manufactured 15th
type              PDUFA
name              Relacorilant - (GRACE resubmission)
date              2026-12-17
date_month        2026-09                     <- THREE MONTHS EARLIER THAN date
date_precision    day
days_to_decision  93                          <- agrees with date (Sep 15 + 93 = Dec 17)
status            Upcoming
therapeutic_area  Infectious                   <- for Cushing's syndrome / hypercortisolism
indication        null
url               https://clinicaltrials.gov/study/NCT06108219   <- off-site, to a trial registry
```

**Why the `date_month` error is the serious one.** `/developers` tells consumers, in our own words, *"If you sorted on `date`, sort on `date_month` first, then `date`."* A consumer following our published instruction places Corcept's relacorilant PDUFA in **September 2026**. The row itself says **December 17, 2026**. That is a three-month error in the sort key we told people to use, on a live forward PDUFA, exposed through the public API.

`days_to_decision: 93` agrees with `date`, which isolates the fault: **`date_month` is the outlier, not `date`.** December 17 is very probably the right day. The month field was left behind when the day was corrected, which is this week's recurring failure in miniature, inside a single row rather than across two pages.

The id compounds it. `readout_cort_2026-09-15` embeds a third date, the retired 15th, in the primary key. Any consumer that parses ids, and any of our own scripts that key on them, gets a fourth answer.

**This row has now been reported in four consecutive audits** (09-09b, 09-09c, 09-10b, 09-14) as "three self-contradictions." It is four, one of them is a public sort key, and it is still live.

---

# 4. P0: ZERO OF 456 ROWS EXPOSE A SOURCE

`source_url` is present on **0 of 456 rows**. The next ten upcoming PDUFAs, in date order, every one returning `src: null`:

```
2026-09-19  RARE  UX111 (ABO-102)                        src: null
2026-09-21  MRK   WINREVAIR (sotatercept-csrk) HYPERION  src: null
2026-09-26  INCY  zilurgisertib (licensed to Mirum)      src: null
2026-09-26  MIRM  zilurgisertib                          src: null
2026-10-09  RHHBY Tecentriq adjuvant                     src: null
2026-10-10  MRK   Ifinatamab deruxtecan                  src: null
2026-10-15  RHHBY Enspryng (thyroid eye disease)         src: null
2026-10-17  IRD   Phentolamine ophthalmic 0.75%          src: null
2026-10-17  VTRS  MR-141                                 src: null
2026-10-26  GSK   Bepirovirsen (B-Well)                  src: null
```

**Three of those ten are sourced in the dataset and none of the sources reach a consumer.** MRK 2026-09-21 was sourced twice on 09-09 to Merck's 8-K of 2026-02-03 and its Q2 10-Q. MIRM 2026-09-26 was sourced on 09-10 to Mirum's 8-K. RARE 2026-09-19 I sourced this morning, below. The research is done and the API publishes none of it.

For a site whose entire proposition is *verify us against primary filings*, an API that cannot answer "says who" is the widest gap on the board. It has been carried as an open item since 09-09, six days.

---

# 5. THE FRESHNESS STAMP DISAGREES WITH ITSELF, AND WITH THE CLOCK

`/build-info.json` exists to state when we last built. Measured today from two clients.

**Non-browser client, approximately 17:44 UTC:**
```json
{"built":"2026-09-14T17:51:13+00:00","commit":"c1bfc628c","next_date":"2026-09-11","next_days":-3}
```

**Browser, 17:50 to 17:51 UTC, four consecutive probes, all identical:**
```json
{"built":"2026-09-15T04:58:31+00:00","commit":"a62614368","next_date":"2026-09-11",
 "next_days":0,"next_status":"awaiting"}

age: 2626, 2627, 2628, 2629      x-vercel-cache: HIT (4/4)
cache-control: public, max-age=300
last-modified: Tue, 15 Sep 2026 17:07:57 GMT
```

Three measured facts, stated without a mechanism attached:

1. **The body's own `built` field is 12 hours 9 minutes earlier than the resource's `last-modified` header.** The file says it was built at 04:58:31Z; HTTP says the file was modified at 17:07:57Z. The one file whose job is to state freshness disagrees with itself by half a day.
2. **It is served at `age` 2626 seconds against its own `max-age=300`**, which is 8.8 times its declared lifetime, `HIT` on every probe.
3. **Two clients six minutes apart received different bodies**, differing by a full day of build time and three commits.

I am not asserting the cause. Two candidates fit: regional edge divergence, where clients egressing from different PoPs hold different objects, or a `built` field that is not refreshed when the same content is redeployed. **They are distinguishable by one experiment**: fetch `/build-info.json` from two known-different regions within the same minute and compare `last-modified` as well as body. If `last-modified` matches and the body differs, the field is stale. If both differ, it is the edge.

This matters beyond tidiness. A crawler is a non-browser client. On today's evidence a crawler could have been told the site last built on **September 14** when it built on **September 15**, on a site that competes on being the most current in its category.

**A smaller but exact point.** `next_days: 0` alongside `next_date: "2026-09-11"`. Zero means "today"; September 11 is four days ago. The clamp is an improvement on the negative countdown and `next_status: "awaiting"` is the right addition, but the honest value for a decision with no known date is `null`, not a number that reads as today.

---

# 6. PRIMARY-SOURCE VERIFICATION OF THE NEXT DECISION, AND A TRAP IT REVEALS

**RARE, UX111, 2026-09-19: CONFIRMED.** Ultragenyx 8-K filed 2026-04-02, Item 8.01, accession `0001193125-26-139084`:

> "The FDA set a Prescription Drug User Fee Act (PDUFA) action date of September 19, 2026."

Our date, our day precision and our status are all correct on the decision four days out. That is the right answer and it should be said plainly.

**But the same company's earlier filing is a live trap.** Ultragenyx's 8-K of **2026-02-03** says only:

> "The Company anticipates up to a six-month review period from the date of resubmission per FDA regulations, with a PDUFA date expected in the third quarter of 2026."

A harvester that took the February filing and rounded "third quarter of 2026" to its last day would have published **2026-09-30**. That is exactly the mechanism the builder found on 09-10 in the PFE, ROIV, TAK and PTGX rows. We did not fall into it here, but the conditions were present, and the general case needs a written rule rather than luck:

> **When a sponsor states the same goal date at two precisions in two filings, the most recent day-precision statement wins, and a quarter statement is never rounded to a day. A later quarter statement does not override an earlier day.**

Carried as already sourced, not re-verified today: **MRK 2026-09-21** (Merck 8-K 2026-02-03 and Q2 10-Q, sourced 09-09) and **MIRM 2026-09-26** (Mirum 8-K, sourced 09-10).

---

# 7. YESTERDAY'S FOUR P0s ARE CLOSED, AND THE BUILDER OUT-FOUND ME ON THREE

| | My count | Actual |
|---|---|---|
| P0-A, stale timing study | 1 surface | Already fixed by a later CI build (`2bd94fe79`, 23:39Z) hours after I measured the 17:51Z build. All three surfaces now 30 / 18 / 9 / 3, median 1.5 days before, the restatement I predicted |
| P0-B, pages publishing Dec 31 | **12** | **16.** Four I could not reach from the calendar: two duplicate indexable pages, a year-precision row, and a partnered event under a second ticker. Verified live today: `/pdufa/ABBV-tavapadon` now titles "Dec 2026" |
| P0-C, unsourced earliness | **1** | **5.** PFE, ROIV, PTGX and IONS carried the same figure in prose, and they are the exact four margins removed from the timing statistic on 09-10. They sat on decision pages for four days |
| P0-D, next-decision pointer | fixed | Fixed, with a qualification I accept: an Awaiting event genuinely is the next expected decision because the FDA can act any day |

**Item 5 earned itself inside one run**, which was the argument for it. It found a fifth window convention on NVCR, the calendar rendering the same four events as "Dec 2026" on one page and "Q4 2026 (est.)" on another, and the finding I would underline: **`rewrite_decision_snippets` corrected BAYRY's `<title>` while the WebPage JSON-LD in the same file kept `"82 Days Early"`.** The corrected version went to humans and the stale one to machines, and structured data is what an answer engine reads first. That is the sharpest instance of this week's pattern anyone has found.

**Item 9 was worse than the collision I reported.** The dropbox directory held 146 notes; `INDEX.md` listed 90. Fifty-six were missing, including two of the builder's own. My clobbered entry was not bad luck, it was the visible instance of months of silent loss. The index is generated from the directory now, 43 hand-written summaries preserved, 102 recovered, guarded.

---

# 8. CHANNELS, AND WHAT I WILL NOT CLAIM TODAY

**Both Bing consoles are byte-identical to yesterday's read. Data still ends September 13.** Search performance 419 clicks, 16.1K impressions, 695 keywords; AI performance 5.2K citations, 18 average cited pages, 22 grounding queries, every share unchanged to two decimals. **The Monday September 14 re-test has not landed**, and I am not re-presenting yesterday's numbers as though today's console were a new measurement. Expect it on the 16th or 17th.

**Google Search Console, 28 days ending September 13**: 40 clicks, 2.29K impressions, 1.7% CTR, average position 13.4, 103 queries. The window slid one day from yesterday's read (40 / 2.25K / 1.8% / 13.6 / 105). **One day of slide in a 28-day rolling window is not a measurement** and I am drawing nothing from it. The meaningful comparison remains yesterday's matched four-day step, 15.9 to 13.4 in average position.

**The September 8 attribution stays unbanked**, which is both the builder's caution and mine.

**One thing worth flagging about the tavapadon fix.** `tavapadon fda approval date` still shows **100% citation share** and the page no longer carries the date, which is the correct end state. But **fixing a page does not retract answers already grounded on it.** There will be a lag, of unknown length, during which Copilot may still serve the old December 31 date from its index while our page no longer says it. That is an argument for treating unsourced dates as urgent rather than tidy, and it is the strongest version of the point I made yesterday.

---

# 9. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Fix `readout_cort_2026-09-15`, all four faults.** `date_month` to `2026-12`; re-key the id off the retired 15th and off the `readout_` prefix on a PDUFA row; `therapeutic_area` from "Infectious" to the correct area for hypercortisolism; fill `indication`; point `url` at our own event page rather than ClinicalTrials.gov. `date` 2026-12-17 and `days_to_decision` 93 agree and should stand | The row states one date in every field; four audits of "self-contradictions" close |
| **2** | **Guard `date_month == date.slice(0,7)` whenever both are present.** Two lines, over the whole corpus, and it would have caught this row the day it appeared | Proved 0 → planted 1 → 0; runs on the API shaping code, not a sampled response |
| **3** | **Guard that the date embedded in an event id equals the row's own date**, and that a `readout_` id cannot carry `type: "PDUFA"` | Proved 0 → 1 → 0 |
| **4** | **Expose `source_url` in the API.** Zero of 456 today. Start with the three near-term rows already sourced (RARE, MRK, MIRM) so the endpoint proves the pattern, then back-fill | A consumer can answer "says who" without loading a page; `/developers` documents the field |
| **5** | **Reconcile `/build-info.json` with itself.** Make `built` equal the build that produced the served bytes, set `next_days` to `null` rather than 0 when `next_status` is "awaiting", and run the two-region experiment in section 5 to separate edge divergence from a stale field | `built` and `last-modified` agree to within one deploy; the two-client test returns one body |
| **6** | **Write the precision-provenance rule** from section 6 into the harvester and into `/methodology`: most recent day-precision statement wins, a quarter is never rounded to a day, a later quarter does not override an earlier day | Rule is in the code and stated publicly, which is itself citable content |
| 7 | **Duplicate-page ruling, my recommendation since the builder asked for one.** Kill the exact duplicates by canonicalising `ABBV-tavapadon-2` to `ABBV-tavapadon` and `NVO-cagrisema` to `NVO-am833`. **Keep** `MRK-trodelvy` and `GILD-trodelvy` as separate pages: a partnered event genuinely has two tickers and people search by ticker, which is the INCY/MIRM precedent. David rules | Two canonicals added, no pages deleted |
| 8 | Carry: the 9 unbacked pages (ratchet holding), 22 readout leads, and the therapeutic-area back-fill. **On the back-fill: 58% of forward readouts carry no area, which caps both new hubs, and the builder is right that widening the selector reintroduces the custirsen mechanism. Rank it, and do it by hand** | |

---

# 10. WHERE THIS LEAVES US

**On the thing you asked to be number one: the dataset's dates are in good shape and I can now say that with the whole corpus behind it rather than a sample.** Nine of ten structural invariants are clean across 456 rows, the manufactured-day era is over, the next decision on the site is confirmed against the sponsor's own 8-K, and a multi-day congress is labelled correctly today. That is a real position and it is defensible in public.

**Three things stop it being immaculate, and they are all narrow.** One row disagrees with itself about the month, in a field we publicly instruct people to sort on. No row in the API can be traced to a source, including the rows we have already sourced. And the file that states our freshness contradicts its own HTTP headers by twelve hours while two clients see two different versions of it.

**The pattern under all three is the same one as last week**, and it is worth naming once more because it keeps producing our only defects: a value is corrected in one place and its copies are not. `date` was fixed and `date_month` was not. The source was found and the API field was not filled. The deploy went out and the stamp did not follow. Items 2, 3 and 5 are all cheap, and each one closes a class rather than an instance.

---
*Live figures read 2026-09-15 between 17:44 and 17:52 UTC against build `a62614368`. API sweep computed over all 456 rows in a single pass. Ultragenyx quotations verified in 8-K accessions `0001193125-26-139084` (2026-04-02) and `0001193125-26-034474` (2026-02-03). Bing and Google consoles read live; Bing data ends 2026-09-13 and did not advance. Not investment advice.*
