# Audit: one page is living in UTC two days before Enspryng; everything else is current, and Bing's AI layer is now building its "this week" answer from us
**2026-10-13, measured 22:09 to 22:22 Eastern = 2026-10-14 02:09 to 02:22 UTC (Tuesday night).** *Per RULE 1 every time carries its zone.*
**Live build `1f0137305`, generated 2026-10-14T00:08:58Z (20:08 Eastern). API 474 rows: 90 PDUFA, 340 Readout, 42 Conference, 2 AdComm. `as_of_eastern` 2026-10-13. `held_leads` []. Next decision RHHBY Enspryng 2026-10-15, `next_days` 2.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. P1: `/fda-decisions-today` stamps "today" from the UTC clock

At 22:20 Eastern on **October 13**, the live page reads: *"No FDA decision on a tracked application has been published today, **October 14, 2026**. The most recent was RHHBY's Tecentriq (atezolizumab) (Approved) on October 8, 2026."* The meta description says "as of October 14, 2026". `/build-info.json` from the same build says `as_of_eastern: 2026-10-13`. The page took its date from the build's UTC timestamp (2026-10-14T00:08Z) instead of `eastern_today()`. Bing has already crawled this copy: its answer box for "pdufa.bio fda decisions today" quotes "today, October 14, 2026" tonight.

It is one builder; the other nine surfaces I checked for "October 14" (`/`, `/calendar`, `/fda-this-month`, `/fda-approval-decisions-this-week`, `/decisions`, `/readouts`, `/pdufa/RHHBY-enspryng`, `/llms.txt`, `/patent-cliff/exclusivity`) are clean. Every nightly build lands between 20:00 and 21:30 Eastern, which is after midnight UTC, **so this page has been a day ahead every night since it was written**, for the four hours between the build and Eastern midnight. On Thursday it will matter: if Enspryng is approved during the day and the 20:00 Eastern build publishes it, this page will say "today, October 16" above a decision dated October 15. Fix: `eastern_today()` in the "today" builder, and extend `test_one_date_per_page` (or a new guard) to assert that every rendered "today" equals `as_of_eastern` from build-info. 0 → planted 1 → 0.

---

# 2. CURRENCY: CLEAN ON EVERY OTHER SURFACE

| Check | Live |
|---|---|
| Day-dated PDUFAs past goal, not Decided or Withdrawn | **0** |
| Rows carrying a `date` at non-day precision | **0** |
| `date_month` disagreeing with `date` | **0** |
| Conferences mislabelled against the Eastern date (start, end, in-progress) | **0**; `end_date` present on all 42 |
| Upcoming PDUFAs | 40; 34 day-dated, **34 sourced**; 6 at window precision |
| Next decisions | RHHBY 10-15 → `/pdufa/RHHBY-enspryng`; IRD 10-17; VTRS 10-17; GSK 10-26 |
| MRK I-DXd | API Withdrawn; `/calendar` row "withdrawn · Withdrawn Sep 25, 2026: Ifinatamab deruxtecan (I-DXd), no FDA decision". The "Awaiting" badge the builder's guard caught on 10-11 is gone |
| Timing statistic | 31: 20 / 10 / 1 on `/calendar` and the research page |
| Freshness strip | "Page updated October 13, 2026 · … · Data as of Oct 13, 2026 8:08 PM ET" (real time, Eastern) |
| Weekly page | "FDA approval decisions this week: Oct 12 to Oct 18, 2026", Still ahead (3): Enspryng 10-15, IRD and VTRS 10-17 |
| Enspryng page | SatraGO sentence, fact-first description, Event `startDate` 2026-10-15, modified 2026-10-10 |

**Readouts, the calendar I called loose on Sunday, is now the most honest surface on the site.** 340 rows. Status mix tonight: Estimated 186, Guided 45 (37 of them in current or future months), Reported 14, Sponsor release {date} 6, No topline as of {date} 53, Completed per registry with no topline as of {date} 27, Terminated 6, bare "Window passed" **2**, "not yet checked" **2**. Lede: "206 expected clinical trial readouts covering October 2026 to December 2027. A further 110 readouts whose window has already passed are listed below with what we found". Description is a full sentence. 0 conflict markers (the builder's own four-minute incident on 10-11 is fully cleaned). The 26 Q3-guided rows were each resolved against the sponsor's own exhibit, with the EVMN "did not meet" and the ALMS drug-label correction both carried in the sponsor's words.

**Conference pages:** `/conference/AASLD` 200, title "AASLD The Liver Meeting 2026: Nov 5-9, 2026, Denver: biotech presenters", Event `startDate` 2026-11-05. The builder re-read aasld.org for the dates. 38 pages live.

**One inconsistency, minor:** the VTRS MR-141 row's API `url` points at `/pdufa/IRD-phentolamine-ophthalmic` (the partner's page) while `/pdufa/VTRS-mr-141` exists, is 200, indexable and self-canonical. Partner pairs should either share one page with the other canonicalised to it, or each row should link its own page. Pick one; the guard currently accepts "a page that states the date" and should also require the page to name the row's ticker.

---

# 3. THE BUILDER'S 10-11 NOTE, CHECKED

The builder checked my 10-11 audit claim by claim and found one wrong: I said the API lacks `date_end`; it serves `end_date` on every conference row. **Retracted; I searched for the wrong field name.** The builder also corrected its own 10-11 red team (ANNX/ERAS/CLRB are NCT-mismatch rows, so 12 moved not 15), and reported its own incident (conflict markers served live for four minutes) with the cause and the rule it added. All six miner fixes (R1 to R6) are described with the replay numbers; the 131 registry-estimate rows were held back for David's ruling rather than merged. That is the right call: those rows are big-pharma completion windows, and the site's AI share on readout queries comes from company-guided rows.

---

# 4. SEO, BING AND AI CITATIONS

## 4a. Bing AI Performance, data to October 11

| | Oct 7 | Oct 8 | Oct 9 | **Oct 10 (Sat)** | **Oct 11 (Sun)** |
|---|---|---|---|---|---|
| AI citations | 482 | 469 | 387 | **152** | **77** |
| Cited pages | 58 | 58 | 52 | **16** | **19** |

Totals **13.2K** citations, 46 grounding queries. The weekend of Oct 10 to 11 (229 citations) is the best weekend in the series (Oct 3 to 4: 146; Sep 26 to 27: 135). Oncology-readouts query 217 → **243** (55.48%). `pdufa date` 1.1K at **23.04%**, fourth consecutive read flat-to-up.

## 4b. Bing web, data to October 11

Totals **842 clicks / 34.4K impressions / 2.45%**. Oct 9: 21 / 722; Oct 10: 6 / 274; Oct 11: 6 / 419. `fda approval decision biotech` **453 impressions, 0 clicks, position 6.88** (387 on Sunday, 250 on Friday). Our `/fda-approval-decisions-this-week` is now indexed (it appears for its own title) but has not yet taken the query; two days old.

## 4c. The AI answer for "fda approval decisions this week" is built from us, and it is stale

Bing's answer box tonight cites **pdufa.bio nine times** (Jaypirca Oct 2, Enspryng Oct 15, IRD and VTRS Oct 17, bepirovirsen Oct 26, INO-3107 Oct 30, mitapivat Nov 1), and twice it cites us for things that are no longer true: *"Roche, Tecentriq, decision expected October 9, 2026"* and *"Merck, Ifinatamab deruxtecan, decision expected October 10, 2026."* The source is a copy of `/fda-decisions-today` or `/fda-this-month` from before October 8. Our live pages have been right for five days; Bing's grounding cache has not caught up on those two hubs, although it fetched the homepage "2 hours ago" and `/fda-decisions-today` "6 days ago" per the SERP labels.

Two levers, both ours:

1. **Submission order.** `ping_search_engines.py` submits every URL whose sitemap lastmod is within two days: after a sweep that is 1,300 URLs to IndexNow and the **first 80** to Bing's SubmitUrlBatch, unordered. The daily hubs (`/fda-decisions-today`, `/fda-this-month`, `/fda-approval-decisions-this-week`, `/calendar`, `/`) and any page whose decision or status changed should be submitted first, and the batch should be those plus the changed decision/event pages, not whichever 80 the sitemap lists first. The builder's own docstring says bulk nightly submission "trains the engine to ignore" us.
2. **Stop sweeps rewriting unchanged content.** The builder's 10-11 note section 7 says the same thing. Every page whose hash changes without a content change dilutes the signal for the ones that did change.

And one for David: on Thursday, after the Enspryng page goes out, open Bing Webmaster → URL Inspection for `/fda-decisions-today` and `/fda-decision/RHHBY-2026-10-15` (or whatever the slug is) and press "Request indexing". That is the only path that beats the queue.

## 4d. Enspryng, 36 hours out

Bing, "enspryng fda decision october 15 2026": **trialfriend first, biopharmsignal second, theraradar third, pdufa.bio fourth**, roche.com fifth. **Our snippet is still the old description** ("RHHBY's FDA PDUFA target is Oct 15, 2026 for Enspryng (Thyroid eye disease (TED)). Date, company and indication, each linked…"), three days after the page changed to the fact-first one. Same cause as 4c: the page was in a 10-10 submission of ~1,300 URLs. We were second on this query on 10-10 and are fourth tonight; the three above us all have content dated October.

## 4e. Google Search Console, 28 days to October 11

24 clicks, 3K impressions, 0.8%, position 7.6 (29 / 3.11K / 7.3 last week). Flat to slightly down; brand 8 clicks, JUVMO 1, `pdufa date` 0 / 17. Nothing to act on this week beyond the Bing items, which also feed Google's lastmod reading.

---

# 5. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **`/fda-decisions-today` uses `eastern_today()`**; guard asserts every rendered "today" equals `as_of_eastern` | Page says October 13 at 22:00 Eastern on October 13; 0 → planted 1 → 0 |
| **2** | **Prioritised search submission:** daily hubs and changed decision/event pages first; Bing batch = those; IndexNow = those plus the rest; log the first 20 URLs submitted each run | CI log shows `/fda-decisions-today` in the first five every night; Enspryng page in the batch the night it changes |
| **3** | **Stop no-op rewrites** (builder's own 10-11 §7): sweeps that touch unchanged content must not move lastmod | Nightly changed-URL count falls from ~1,300 to the pages that changed |
| **4** | **Thursday runbook:** manual dispatch the moment the FDA record or gene.com release is seen; publish from the FDA record; then David presses "Request indexing" in Bing Webmaster on the decision page and `/fda-decisions-today` | Decision page live within 60 minutes of the record; Bing SERP shows the new title within 24 hours |
| **5** | VTRS/IRD partner rows: one page canonical or one page each; guard requires the resolved page to name the row's ticker | API `url` for `pdufa_vtrs_2026-10-17` names VTRS, or the VTRS page canonicalises to IRD |
| 6 | David's ruling on the 131 registry-estimate miner rows (my recommendation: do not publish; keep them as a watch list that feeds the already-read-out pass) | |
| 7 | Carried: `goal_date_held`; Jaypirca letter date; RXC-005 aliases; SMTP; Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; the 20 nct-mismatch readout rows | |

---

# 6. BOTTOM LINE

**Current.** Every PDUFA, conference and readout row I can test is right against the Eastern clock and its source, the withdrawal is closed on every surface, the readout calendar now says what it found and when, and conference pages carry the organisers' dates. The one defect is a RULE 1 defect on exactly one page, and it is the page that will matter most on Thursday night.

**Cited.** Bing's AI layer is now assembling "what did the FDA decide this week" from nine of our rows. Two of the nine are five days stale because our nightly submission drowns the pages that changed among the thousand that did not. The fix is ordering, not volume, and it is the same fix that will get the Enspryng snippet updated before the decision.

---
*Site read from a browser client with `cache: 'reload'`, 2026-10-14 02:09 to 02:22 UTC, against build `1f0137305`. Bing Webmaster AI Performance and Search Performance (data to 2026-10-11), Google Search Console (28 days to 2026-10-11), and Bing SERPs for "fda approval decisions this week", "pdufa.bio fda decisions today" and "enspryng fda decision october 15 2026" read live. `ping_search_engines.py` and `_sitemap_lastmod.json` read from the repo. Not investment advice.*
