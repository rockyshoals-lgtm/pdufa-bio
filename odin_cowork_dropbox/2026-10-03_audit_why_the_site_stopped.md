# Audit: why the site stopped updating, how to unblock it today, and what it cost in search
**2026-10-03, measured 18:11 UTC = 14:11 Eastern (Saturday).** *Per RULE 1 every time carries its zone.*
**Live build `9fa6bc890`, generated 2026-09-27T23:32:47Z. Six days old.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. WHY IT STOPPED

**Seventeen consecutive scheduled runs have failed**, #222 through #238, from 2026-09-28 17:54 UTC to 2026-10-03 15:49 UTC. The last success was #221 on 2026-09-27 at 23:30 UTC (commit `898686a`). The scheduler is firing normally. Every run fails in about 2.5 minutes against about 6 for a healthy run.

**The failing step is step 40, "Early-approval watch against FDA's own feed."** It exits 1, and every step after it is skipped: the other three watchers, the rebuild, the sitemap, the commit and the deploy. The `git` exit-code-128 annotation in the same runs is post-job cleanup, not the cause.

**This is the verify-then-publish guard doing exactly what it was built to do, and nobody answered it.** The workflow opened a blocking issue on every failed run. **There are 17 open issues, #2 to #18, every one marked unread.** No human or builder commit has landed since 2026-09-27 20:35 UTC. The escalation works; it escalates to a GitHub inbox nobody reads.

**The leads in the queue, each verified against the FDA:**

| Issue | Lead | Verdict |
|---|---|---|
| #2, #3, #5, #6 (sponsor feed, Sept 28 to 29) | ABBV tavapadon: *"U.S. FDA Approves AbbVie's JUVMO™ (tavapadon) for Parkinson's Disease"* | **Real.** Drugs@FDA **NDA 220415** ORIG-1, approved, `submission_status_date` **2026-09-25**; letter `220415Orig1s000ltr.pdf` posted Sept 29. AbbVie announced Monday Sept 28 on PR Newswire |
| #4 (FDA drugs feed, Sept 29) | RHHBY Enspryng (thyroid eye disease) ← *"FDA Approves First Treatment for MCT8 Deficiency"* | **False positive.** Different drug and disease, matched on the single token "thyroid" |
| #7 to #18 (Drugs@FDA watch, Sept 30 onward) | AGIO mitapivat, SUPPL-7 approved Sept 28 | **Non-event.** Class **MANUF (CMC)**, a manufacturing supplement, not the RISE UP sickle-cell efficacy filing due Nov 1 |
| #7 to #18 | RHHBY giredestrant + everolimus ← "everolimus" ORIG-1 approved Sept 21 | **False positive.** It is **ANDA 220597, Novitium Pharma**, a generic everolimus. Matched on the combination partner's name |

**One real approval and three false or irrelevant leads froze the entire site for six days.** And because step 40 now fails first, the sponsor-feed and FDA-feed watchers further down no longer run at all, so the queue is longer than the newest issue shows.

---

# 2. WHAT IT LEFT STALE

| Surface | Live now |
|---|---|
| `/pdufa/ABBV-tavapadon` and the API row | "**ABBV PDUFA date: Tavapadon, Dec 2026**", `Upcoming`. Approved September 25 |
| Conferences | AACR Pancreatic (ended Sept 28) and ASTRO (ended Sept 30) still "**In progress**"; EASD (from Sept 28) and WMS (from Sept 29) still "**Scheduled**" |
| Home, `/calendar` | "Updated **September 27**, 2026", which is at least honest |
| **API `meta.as_of`** | "**2026-10-03**". Computed at request time, so it reports today over six-day-old data. A consumer or monitor reading it would conclude the feed is current |

**Nothing is past its goal date undecided.** The next decision is RHHBY Tecentriq on **October 9**, six days out, so the stall has not yet cost us a scheduled decision. It will if it runs another week: Oct 9, 10, 15 and 17 are all on the board.

**JUVMO is the second of the five unbacked rows to be settled by an FDA approval rather than a ruling.** Kerendia was approved on Sept 16 against our "December 2026"; JUVMO on Sept 25 against the same. Three remain: AZN Ultomiris, NVO CagriSema, NVO Mim8.

---

# 3. UNBLOCK IT TODAY: EXACT STEPS

1. **Publish JUVMO.** Row `pdufa_abbv_2026-12-31` → Decided / Approved, `fda_action_date` **2026-09-25**, source the Drugs@FDA record and the FDA letter, announcement AbbVie's PR Newswire release of Sept 28. The goal date was never sourced, so `goal_unsourced` and **no margin**. Brand JUVMO; first selective D1/D5 receptor agonist for adults with Parkinson's disease (AbbVie's wording); availability expected October 2026. Ack the newswire key printed in issue #2.
2. **Ack in `_fda_watch_ack.json`:** AGIO mitapivat SUPPL-7, reason "CMC manufacturing supplement, not the RISE UP efficacy sNDA"; RHHBY giredestrant, reason "match is ANDA 220597, Novitium generic everolimus, the combination partner."
3. **Ack in `_fda_drugs_feed_ack.json`:** RHHBY Enspryng ↔ MCT8 deficiency notice, reason "different drug; matched on 'thyroid'."
4. **Dispatch the workflow**, then confirm the run reaches the sponsor and FDA-feed steps clean. Those have not run since September 30 and may hold more leads.
5. **Close issues #2 to #18** with the reason on each.

---

# 4. FIXES SO IT CANNOT HAPPEN AGAIN

| # | Fix | Why |
|---|---|---|
| **1** | **Quarantine, don't blockade.** A lead should freeze only the row and pages it concerns, at their current state, and let the rest of the site rebuild. The lead still opens its issue and still blocks *that row's* publication until verified | This week one real approval and three false leads froze prices, conference statuses, readouts and every other row for six days. The verify-then-publish principle survives intact; only the blast radius shrinks |
| **2** | **Escalation that reaches a person.** Seventeen unread issues prove the GitHub inbox is not a channel. After two consecutive blocked runs, send email to David (Actions can send mail through a configured SMTP secret), and put a visible "build held since {date}: {n} leads" line in `/build-info.json` | The guard has now caused two multi-day outages (Sept 11 to 14, Sept 28 to now), both because nobody saw it |
| **3** | **Tighten the matchers.** (a) Never match an **ANDA** to an armed NDA/BLA event. (b) Ignore supplement classes **MANUF/CMC and labeling-only** when the armed event is an efficacy filing. (c) For combination rows ("giredestrant + everolimus") match on the **investigational drug only**, never the partner. (d) A disease match needs the **indication phrase**, not a lone organ word like "thyroid" | Three of four leads this week fail one of these four tests. The guard's precision was 25% |
| **4** | **Honest freshness in the API.** Keep `as_of` as the request date if you like, but add `data_built_at` to `meta`, and have the freshness stamp read it | Today the API says October 3 over September 27 data. That is the stale-stamp problem we spent September fixing, reintroduced through a different field |
| **5** | **Time-derived statuses at request time.** Conference "In progress / Ended" and "Awaiting" depend only on today's date and fixed data, like `next_days`. Compute them when served | Then a held build cannot leave a finished congress saying "In progress" |

---

# 5. SEO, BING AND AI CITATIONS

*David re-authenticated Bing Webmaster mid-session. Bing data now runs through **September 30**, which covers the first three days of the stall (the first failed run was Sept 28, 17:54 UTC).*

**Bing AI citations, 3 months:**

| | to Sep 25 | to Sep 30 |
|---|---|---|
| Total citations | 8.8K | **10.1K** |
| Average cited pages | 22 | **23** |
| Grounding queries | 31 | **38** |

Daily citations: Sept 26 to 30 ran **56, 79, 553, 356, 256**. **Monday Sept 28 at 553 is the highest day in the series**, with 58 average cited pages, also a series high. Monday-to-Wednesday totals are flat week over week (1,165 against 1,176 for Sept 21 to 23).

| Query | Citations | Share, Sep 25 → Sep 30 |
|---|---|---|
| pdufa date | 863 | 22.92%, unchanged (row not refreshed) |
| fda calendar 2026 | 346 → 359 | 27.59% → 27.11% |
| upcoming clinical trial readouts rare disease ... | 234 → 258 | 47.76% → 46.99% |
| major upcoming Phase 3 oncology trial readouts ... | 147 → 191 | 58.10% → **58.77%** |
| **`09/28/2026 - approval completed`** | **60, new** | **50.00%** |

**That last row is worth reading closely.** Something, almost certainly an automated agent given the phrasing, asked about approvals completed on September 28, and **we supplied half the citations**. September 28 is the day AbbVie announced JUVMO, the one approval our frozen site did not have. The console does not show which of our pages was cited, so I cannot say what the answer contained. But the shape of the risk is plain: we are being cited for "what was approved on this date" during a week our pages could not know.

**Bing web search, 3 months:**

| | to Sep 25 | to Sep 30 |
|---|---|---|
| Clicks | 607 | **674** |
| Impressions | 24.4K | **27.4K** |
| CTR | 2.49% | 2.46% |

Daily impressions Sept 28 to 30: **827, 843, 774**, against 675, 637, 720 on the same weekdays a week earlier, **up about 20%**. Clicks 20, 20, 19 against 19, 22, 17, flat. `pdufa date` position 5.30 → **5.18** on 637 impressions; `pdufa calendar` 126 impressions, 19 clicks, position 4.04; `aasld 2026` 45 impressions at 9.13.

**So the stall has not yet shown up in Bing's numbers.** That is expected: through September 30 the frozen pages were at most three days stale, and Bing's crawl and AI index lag behind that. **The cost, if it comes, lands in the October 1 onward data, which arrives in the next two to three days.** That is the re-test to set, and it is the strongest argument for unblocking today rather than after the weekend.

**Google Search Console, 28 days to Sept 29:** 27 clicks, 3.33K impressions, 0.8% CTR, average position 7.5, 136 queries. **Flat against the Sept 25 read** (25 / 3.1K / 0.8% / 8.8). Head terms still sit on pages six and seven (`pdufa calendar` 55.4, `pdufa date` 69.7, `what is a pdufa date` 78.4). Brand queries keep growing (`pdufa.bio`, 9 clicks at position 1.1).

**The stall's cost is visible in one row:** `juvmo pdufa`, **13 impressions at position 7.0**. People searching the new brand find a page that says the drug is pending in December.

**Two more things in the Google data worth noting.** Queries such as `-site:facebook.com -site:youtube.com ... "bezuclastinib"` and a long `site:fda.gov or site:nih.gov ...` filter string are the fingerprints of **automated research agents** querying Google, and we appear for them at positions 7 to 10. AI tools are finding us through Google even where people are not.

**The answer box, live on Bing for `juvmo tavapadon fda approval`:**

> *"The FDA approved AbbVie's Juvmo (tavapadon) on **September 25** for Parkinson's disease in adults, the **43rd novel drug approval of 2026** and the first selective D1/D5 dopamine receptor partial agonist to reach the market."* (breakoutbiotechstocks.com)

**That is the third new competitor in two weeks to take a decision-day answer box with one fact-first sentence**, after trialfriend.com (Atebrioz) and simianx.ai / allsci.com (zilurgisertib). Note what this one did right: it uses the **FDA's action date** (Sept 25, matching Drugs@FDA) rather than the announcement date, and it adds a **running count** ("43rd novel drug approval of 2026") that is cheap to compute from the FDA's Novel Drug Approvals 2026 page and highly quotable. We have the same data and the better sourcing. This week we had nothing on the page at all, because the pipeline was held.

**Coverage note from the FDA feed:** the same feed listed **Gazyva (obinutuzumab) for idiopathic nephrotic syndrome, approved Sept 25**, as "naming no tracked drug." We carry a Gazyva row for lupus, not this indication. Not a miss against our calendar, but a large-cap approval we have no page for.

---

# 6. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Unblock today** per section 3: publish JUVMO, ack the three false leads, dispatch, close #2 to #18 | Next scheduled run green; build stamp today; tavapadon Decided; conferences current |
| **2** | **Quarantine instead of blockade** (section 4, item 1) | A planted false lead blocks only its own row; the rest of the site rebuilds and deploys |
| **3** | **Escalation to email** after two blocked runs, plus a held-build line in `/build-info.json` | A replay of Sept 28 sends mail the same day |
| **4** | **Matcher tightening**, four rules (section 4, item 3) | Replays of this week's three false leads produce zero leads; JUVMO still produces one |
| **5** | **`data_built_at` in API meta**; request-time conference and Awaiting statuses | The API cannot report today over old data; a held build cannot leave a finished congress "In progress" |
| 6 | **Running novel-approval count** on each NME decision page ("the Nth novel drug approval of 2026, per the FDA's list") | Count matches the FDA's Novel Drug Approvals 2026 page |
| 7 | Re-read Bing once the October 1 to 3 data lands, comparing weekday AI citations and impressions against Sept 28 to 30 | Measures what the stall actually cost |

---

# 7. BOTTOM LINE

**The site did not break. It was holding at a gate, and nobody came for six days.** One real approval (JUVMO, FDA action Sept 25) and three false or irrelevant leads (a generic everolimus, a manufacturing supplement, and a "thyroid" keyword match) stopped every rebuild since September 28. The guard opened seventeen issues saying so, and all seventeen are unread.

**The principle is right and the blast radius is wrong.** A lead should hold its own row, not the whole site. A guard that is wrong three times out of four needs tighter matching. And a guard that only escalates to an unread inbox will keep doing this.

**Meanwhile the market moved on without us.** A drug approved eight days ago still reads "December 2026" on our page while searchers type its brand name, and the answer box went to a site that published one clean, FDA-dated sentence. Section 3 gets the site current today; section 4 keeps it current.

---
*Workflow runs, job step results and issues #2 to #18 read live on GitHub in Chrome. Leads verified against openFDA Drugs@FDA (NDA 220415; ANDA 220597) and AbbVie's release of 2026-09-28. Site state computed in-page against the live API. Google Search Console and Bing Webmaster (after re-authentication) read live; Bing data ends 2026-09-30. Bing SERP for `juvmo tavapadon fda approval` read live. Not investment advice.*
