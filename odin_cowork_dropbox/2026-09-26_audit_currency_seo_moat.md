# Audit: today's decision is on the site as "under review," and the FDA's own records move our flagship statistic
**2026-09-26, measured 19:20 UTC = 15:20 Eastern = 12:20 Pacific (Saturday).** *Per RULE 1 every time carries its zone.*
**Live build `d2d69338b`, generated 2026-09-26T15:57:19Z (11:57 Eastern). API `as_of` 2026-09-26, 457 rows.**
*Facts and build mechanics only. Not investment advice.*

---

# 0. A RETRACTION FIRST: THE 67% WAS WRONG AND THE BUILDER WAS RIGHT

On 09-20 I called 309 of 458 released CRLs "the single most valuable fact on the disk" and recommended publishing it as proof that a CRL is not a rejection. The builder declined and argued it from the data. By letter year, `approval_status` splits like this:

| letter year | since approved | not approved |
|---|---|---|
| 2022 and earlier | 266 | 2 |
| 2023 | 29 | 1 |
| 2024 | 14 | 55 |
| 2025 | 0 | 59 |
| 2026 | 0 | 32 |

That is the shape of the FDA's **release policy** (archived letters published only for applications it had approved, then everything from 2024 onward), not the shape of CRL outcomes. Publishing 67% as an outcome rate would have taught answer engines a number that measures the FDA's publication choices. `/crl` now states the count, the by-year table, and says plainly that the corpus cannot answer "how often." `/llms.txt` now tells AI assistants not to convert it into a rate. That is better than what I asked for, and my lesson is the one the builder applied: **before calling a ratio a finding, look at how it is distributed over time.**

---

# 1. P0, CURRENCY: ZILURGISERTIB WAS APPROVED YESTERDAY AND THE SITE STILL SAYS "UNDER REVIEW"

**Verified in the primary source.** Business Wire release 20260925436454, Mirum Pharmaceuticals and Incyte, dated September 25, 2026: *"today announced that the U.S. Food and Drug Administration (FDA) has approved Atebrioz™ (zilurgisertib) tablets to reduce the volume of total new heterotopic ossification (HO) in adult and pediatric patients aged 12 years and older with fibrodysplasia ossificans progressiva (FOP)."* The FDA also issued a Rare Pediatric Disease Priority Review Voucher to Incyte. Goal date was **Saturday September 26**.

**What the site says at 15:20 Eastern, roughly twenty hours after the release:**

| Surface | Live |
|---|---|
| `/pdufa/MIRM-zilurgisertib` | "FDA PDUFA target **Sep 26, 2026** ... zilurgisertib is Mirum Pharmaceuticals, Inc.'s candidate **under FDA review**." Stamped **Updated September 2, 2026**. No indication on the page |
| API rows `pdufa_incy_2026-09-26`, `pdufa_mirm_2026-09-26` | `status: Upcoming`, `outcome: null` |
| `/build-info.json` | `next_ticker: INCY`, `next_date: 2026-09-26`, `next_status: upcoming` |

Today's 11:57 Eastern build ran about sixteen hours after the release and did not catch it. EDGAR full text shows **no** filing mentioning zilurgisertib since September 18, and Drugs@FDA's last update is September 24. Every source the watcher reads is silent. Only the newswire has it.

**This is the third approval this month that reached the site late for the same reason:**

| Approval | First public on | Reached the site | Lag |
|---|---|---|---|
| TLX Pixclara | Telix ASX announcement, Sep 14 | Sep 19 | 5 days |
| NUVB IBTROZI sNDA | Nuvation newswire release, Sep 16 | Sep 23 | 7 days |
| MIRM/INCY Atebrioz | Business Wire, Sep 25 | not yet | 20+ hours and counting |

All three were first public on a sponsor newswire, before any 8-K, FDA press release or Drugs@FDA posting. The watcher's three passes (Drugs@FDA, FDA press feed, sponsor 8-K/6-K) are all downstream of that. **The watcher needs a fourth pass that reads the sponsor newswire** (Business Wire, GlobeNewswire and PR Newswire publish per-company feeds) for every armed event from acceptance onward. That is the builder's queued task #48, and this month it has cost us three decisions.

**What the search engines show for today's decision.** Bing's answer for `zilurgisertib pdufa date` says *"The FDA has set the PDUFA date for zilurgisertib to 26 September 2026"* and cites **simianx.ai** and **allsci.com**, not us. We rank organically just below it with both `/drug/zilurgisertib` and `/pdufa/MIRM-zilurgisertib`, and both snippets are stale. **Nobody in that result says "approved" yet.** The first sourced third-party page with the brand, the approval and the goal date wins that query and `atebrioz` with it. (I also ran `atebrioz` on Bing and got only Mirum's IR pages, but that result came through a session Bing then challenged with a CAPTCHA, so I am not relying on it.)

Facts for the decision page, all from the release: brand **Atebrioz**, indication FOP ages **12 and older**, 100 mg once daily, PRV to Incyte, EU MAA under review, Mirum licensed the drug from Incyte. **On the date: the release is dated September 25 and says "today"; it does not state the FDA's action day.** Under the builder's own three-gate rule no margin is published until Drugs@FDA posts the action date, which on this month's evidence takes about four days.

**A second currency gap from the same day.** Pharming's 6-K of September 25 (accession `0001828316-26-000041`) states a **new** PDUFA: *"assigned a Prescription Drug User Fee Act (PDUFA) target action date of January 30, 2027"*, Priority Review, for lower-dose Joenja in children 4 and older weighing 13 to 27 kg. **The dataset has no row for it.** Our only Pharming PDUFA row is the September 11 approval.

---

# 2. P0, ACCURACY: THE FDA'S RECORDS MOVE THE TIMING STATISTIC FROM 20/9/2 TO 20/11/1

The study page (`/research/fda-decision-timing`, modified today 11:57 Eastern) says: *"Of the 31 2026 FDA decisions ... 20 came before the PDUFA goal date, 9 landed on it, and 2 came after."* I checked the three rows whose action date rests on a press release against the FDA's own records.

| Row | What we publish | What the FDA's record says | Source |
|---|---|---|---|
| **MRK WINREVAIR** (HYPERION) | goal Sep 21 → **Sep 22, +1 day**, one of the two "late" decisions | BLA 761363 supplement 12, class Efficacy, `submission_status: AP`, **`submission_status_date: 20260921`**. Letter `761363Orig1s012,s016,s017ltr.pdf` posted Sep 22 | Drugs@FDA |
| **TLX Pixclara** | **excluded**: "the filing does not state the day the FDA acted" | NDA 218592 ORIG-1, `AP`, **`submission_status_date: 20260911`**, the goal date. Letter `218592Orig1s000ltr.pdf` posted **Sep 15** | Drugs@FDA |
| **LNTH TAUKLARIFY** | goal Aug 13 → **Aug 13, +0 days** | NDA 220496 ORIG-1, `AP`, **`submission_status_date: 20260813`** | Drugs@FDA |

**MRK is an on-the-day decision counted as late.** Merck's release went out at 6:45 a.m. Eastern on the 22nd; the FDA acted on the 21st. That is the TLX shape, announcement the morning after, and it was admitted to the statistic three days after the builder wrote the gate that should have stopped it.

**TLX is an on-the-day decision we exclude.** The exclusion was correct on September 20 and stopped being correct when the FDA posted the letter on September 15, five days *before* the exclusion was written. Nothing re-checks an excluded row when the evidence arrives. The September 11 action date also vindicates the Friday-act, Monday-announce reading from my 09-20 audit.

**LNTH is right, and I nearly filed it as wrong.** The page cites a Lantheus release dated August 14 that says "today announced" and never states August 13, and RTTNews dates the approval to August 14. I suspected the row had filled the action date from the goal date. The FDA's record confirms August 13, so **our number is right and RTTNews is wrong. The defect is our citation:** the page's "primary source" is the August 14 release **hosted on StockTitan**, which does not support the date we print, and it sends a link to a competitor. Cite the Drugs@FDA record and the FDA letter instead.

**The one remaining late decision is real.** REPL: the FDA's own notification says *"On August 6, 2026, the Food and Drug Administration granted accelerated approval to vusolimogene oderparepvec-wtpg (Tudriqev...)"*. Goal August 2, action August 6, +4. The builder's note said "no FDA document"; there is one, and it should be the row's source.

**Corrected statistic:** move MRK from late to on the day, and add TLX on the day.

```
published   n=31   20 early /  9 on the day / 2 late
corrected   n=32   20 early / 11 on the day / 1 late   (REPL only)

median check, n=32: early margins sorted
  -110 -108 -58 -43 -19 -19 -19 -12 -6 -5 -4 -4 -4 -3 -3 -2 -2 -1 -1 -1   (positions 1-20)
  then eleven zeros (21-31), then +4 (32)
  positions 16 and 17 are -2 and -2, so the median stays 2 days before
```

The headline sentence changes from **"2 came after"** to **"1 came after."** That sentence is on `/calendar`, `/learn/what-is-a-pdufa-date`, the study page and `/llms.txt`, and it is the sentence the answer engines quote.

---

# 3. THE MOAT THIS POINTS AT, AND IT IS ALREADY SITTING IN A FREE FEDERAL API

**Every date in our timing study can be the FDA's own action date, not the press-release date.** openFDA's Drugs@FDA endpoint returns `submission_status_date` and the approval-letter URL for every CDER approval, supplements included, as the three lookups above show. CBER products (gene therapies, oncolytic viruses) are not in Drugs@FDA, but the FDA publishes a dated approval notification for each, as REPL shows.

**RTTNews, the incumbent, dates at least two of these approvals to the announcement day** (TLX "Sep. 14," TAUKLARIFY "Aug. 14"). Our numbers are already more accurate than theirs on both. But **a reader cannot see why**, because our pages cite the press release. The claim we can make, and that nobody else in this category can make, is: *every action date in this study comes from the FDA's own record, linked on the page.* It is a sentence an answer engine can quote, a fact a competitor cannot copy without doing the same work, and it costs one API call per decided row.

---

# 4. STRUCTURAL CURRENCY: CLEAN

Computed in-page against the live API, all 457 rows:

| Check | Result |
|---|---|
| `as_of` equals today Eastern | 2026-09-26 ✓ |
| Rows with a `date` at non-day precision | **0** |
| `date_month` disagreeing with `date` | **0** |
| Day-precision PDUFAs past goal and not Decided | **0** |
| Decisions dated in the future | **0** |
| Guided readouts past their date | **0** |
| Scheduled conferences already past | **0** |
| Upcoming PDUFAs carrying `source_url` | **40 of 44** |

The four without a source are ABBV tavapadon, AZN Ultomiris, NVO CagriSema and NVO Mim8, the rows awaiting David's ruling. The fifth, BAYRY Kerendia, **was settled by events**: the FDA approved it on September 16, three months before the "December 2026" we were carrying. That is the clearest possible evidence for the ruling I recommended on 09-20.

**The countdown fix is verified.** `/build-info.json` now carries `served_at` and `as_of_eastern` and computes `next_days` per request: `0` for today, correct at 15:20 Eastern. Its next-decision pointer is the only wrong thing in it, and that is section 1, not the mechanism.

Today's goal date falling on a Saturday is also a pattern worth a rule. RARE's September 19 goal was a Saturday and the approval came Thursday; zilurgisertib's is a Saturday and the approval came Friday. **A weekend goal date should arm the newswire watch from the preceding Wednesday.**

---

# 5. COMPETITOR MOAT: WHERE WE LEAD, WHERE WE LOSE

**Where we lead, verified today against RTTNews's free calendar:**
- **GILD bictegravir + lenacapavir, 08/27: "pending"** a month after the approval we published on August 27.
- **ABEO, UX111, 09/19: "Pending"** directly beside a RARE row for the same event that says approved September 17. We had the identical defect and fixed it on 09-20.
- **TLX and TAUKLARIFY dated to the announcement day**, where the FDA's records say September 11 and August 13.
- Everything past a small slice sits behind a paid trial ("Get the Full Calendar, Free for 7 Days").

**Where we lose:**
- **Answer boxes on drug-name queries.** For `zilurgisertib pdufa date`, Copilot's answer cites simianx.ai and allsci.com. Neither was on our radar a week ago. We out-rank both organically and lose the box, which is the same pattern as the `what is a pdufa date` box in August.
- **A new monthly-roundup competitor with domain authority.** Haymarket's Endocrinology, Cardiology and Pulmonology Advisor sites now each publish *"FDA Drug Approval Decisions Expected in October 2026."* That is `/fda-this-month`'s exact job, on established medical-publisher domains. Their pages render client-side, so I could not read their dates; the builder should compare our October list against theirs row for row.
- **We are linking authority to a competitor.** The LNTH decision page's primary source is a StockTitan URL. A sweep for any decision page whose "primary source" is an aggregator (StockTitan, RTTNews, Seeking Alpha, Investing.com) rather than the sponsor, EDGAR or the FDA is overdue.

**The honest scorecard:** on dates we already hold, we are more accurate than the incumbent and can now prove it from federal records. On dates that changed in the last 24 hours, we are no faster than anyone, and on a decision day that is the only race that counts.

---

# 6. CHANNELS: NOT READ THIS SESSION, AND WHY

- **The Claude in Chrome extension was disconnected for the entire session** (four attempts). Bing Webmaster and Search Console are signed in only there.
- The in-app browser is **not signed in** to Bing Webmaster, and I will not sign in.
- After three live Bing searches from the in-app browser, **Bing served a CAPTCHA challenge. I did not attempt it.** The two searches that came back just before it returned degraded results (Microsoft support pages for "what is a pdufa date"), and I have discarded them.

The last console read is my 09-20 audit (data to September 18): Bing 512 clicks and 20.3K impressions on three months, AI citations 6.9K, `pdufa date` share 22.59%. **The next read should check two things specifically:** whether `pdufa date` share held after the `/learn` restructure, and whether the September 22 to 26 run of drug-specific approvals (FAYUVI, WINREVAIR, IBTROZI, Kerendia, Atebrioz) produced new grounding queries.

---

# 7. THE BUILDER'S WEEK, BRIEFLY, BECAUSE IT WAS GOOD

Six red CI runs diagnosed to a correct verify-then-publish block, with an ordering bug fixed underneath it. **NUVB's approval found at −110 days**, now the largest early margin in the set, from the FDA letter. **Kerendia settled from the FDA letter.** ACHV and UNCY moved from "late" to on the day by reading the CRL letters' own dates, which halved the late bucket before today's further halving. `og:` tags on 1,052 pages, a guard against "1 days," `/llms.txt` rendered from the stats owners instead of typed by hand (it had said n=1,792 and 73.5%), the CRL hub reconciled 458 records to 455 letters, a monthly CRL capture series, and the sync-client corruption diagnosed. And the 67% call, above.

---

# 8. FOR DAVID

1. **Exclude `Documents\Python\9realms` from Google Drive backup.** On 09-20 a sync client wrote 260 duplicate files into the build tree and **133 pages were deleted mid-build**, the timing statistic collapsing to 13 of 30 before the builder caught it. It has recurred on three days. Until it is excluded, only CI builds are trustworthy.
2. **The four unbacked rows** (ABBV tavapadon, AZN Ultomiris, NVO CagriSema, NVO Mim8). Kerendia, the fifth, was approved three months before our placeholder date. My recommendation stands: withdraw the day and the forward listing, keep the drug pages.
3. **The 454 long titles.** My view: leave them. Drug, outcome and date are front-loaded, so what Google truncates is the ticker and site name, and changing 454 titles resets snippets for a marginal gain.

---

# 9. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Publish the Atebrioz approval on both INCY and MIRM surfaces now**, sourced to Business Wire 20260925436454, with decision page, drug page, calendar, `/fda-this-month` and the next-decision pointer (which should move to RHHBY Tecentriq, October 9). No margin until Drugs@FDA posts the action date | Both rows Decided; brand, indication (FOP, 12+) and PRV on the page; `next_ticker` no longer names a decided event |
| **2** | **Add the Pharming row**: lower-dose Joenja sNDA, PDUFA 2027-01-30, Priority Review, sourced to the 6-K of 2026-09-25 | Row live with `source_url` |
| **3** | **Restate the timing statistic to 32: 20 / 11 / 1.** MRK WINREVAIR and TLX take their FDA action dates (both 2026-09-21 and 2026-09-11 respectively, from Drugs@FDA); REPL cites the FDA notification; LNTH cites NDA 220496 instead of StockTitan | All four surfaces and `/llms.txt` say "1 came after"; median stays 2 days before |
| **4** | **Backfill `fda_action_date` from Drugs@FDA for every decided CDER row**, and from the FDA approval notification for CBER rows, with the letter URL as the action-date source. Then say so on the study page | Every row in the study cites an FDA record for its action date; a guard fails any row whose action date rests only on a press release |
| **5** | **Re-check excluded rows every run.** A row excluded for `decision_date_unsourced` must be re-queried against Drugs@FDA each build and re-admitted when the record appears. TLX sat excluded for eleven days after the FDA posted its letter | Guard: no excluded row has a Drugs@FDA `submission_status_date` available |
| **6** | **Newswire pass for the watcher (task #48)**: Business Wire, GlobeNewswire and PR Newswire per-company feeds for every armed event, from acceptance onward, and from the Wednesday before any weekend goal date. Still verify-then-publish | A replay of September 14, 16 and 25 catches TLX, NUVB and Atebrioz the same day |
| **7** | **Aggregator-source sweep**: no decision page's primary source may be StockTitan, RTTNews, Seeking Alpha, Investing.com or similar | Guard over all decision pages |
| 8 | Compare our October list against Haymarket's "Expected in October 2026" roundups, row by row | Differences listed and resolved in either direction |
| 9 | Carry: AdComm historical calendar, the 13F block, exclusivity, `daily/NEW_*` into `/pdufa-date-changes` | |

---

# 10. BOTTOM LINE

**The data layer is sound and the edges are where we lose.** Every structural invariant is clean, 40 of 44 upcoming PDUFAs are sourced, and on dates we already hold we are more accurate than the incumbent. But the decision that happened yesterday is still "under review" on our site, a new PDUFA announced yesterday is not on it, and Copilot is answering today's question from two sites we had never heard of.

**And the FDA's own records improve our best statistic.** Two decisions we treated as late or unmeasurable landed on their goal dates. The truthful headline is now *"1 of 32 came after,"* and the reason we can say it with confidence is a free federal API that nobody else in this category is using to date approvals. Wire it in, cite it on every row, and the most quotable sentence we own becomes the one no competitor can check us on without doing the same work.

---
*Live figures read 2026-09-26 between 19:20 and 20:10 UTC against build `d2d69338b`. API invariants computed in-page over all 457 rows. Atebrioz verified in Business Wire 20260925436454; Pharming PDUFA in 6-K 0001828316-26-000041; action dates from openFDA Drugs@FDA (NDA 218592, NDA 220496, BLA 761363) and the FDA's Tudriqev notification of 2026-08-06. RTTNews read from its public calendar pages 7 and 8. Bing and Google consoles not read (extension disconnected). Not investment advice.*
