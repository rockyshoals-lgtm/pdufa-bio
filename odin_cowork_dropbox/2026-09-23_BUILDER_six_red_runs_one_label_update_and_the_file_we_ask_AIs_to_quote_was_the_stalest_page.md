# Builder, 09-23: six red runs, one label update, and the file we ask AIs to quote was the stalest page on the site
**2026-09-23, written 18:00 Pacific = 21:00 Eastern = 2026-09-24 01:00 UTC.** *Per RULE 1 every time here carries its zone. Facts and file contents only; not investment advice.*

David asked for a currency + SEO / Bing / AI-citation audit. The first thing the audit found was that nothing had deployed since 09-21: CI had failed six consecutive scheduled runs. Section 1 is that. Sections 2–4 are what the SEO pass found and fixed; section 5 is what I found and did not change, for a ruling.

---

## 1. Why CI was red since 09-22 14:17 UTC, and what unblocked it

`mark_calendar_decided.py` exits nonzero on **"MRK 2026-09-21 goal date passed, unmarked"**. That is verify-then-publish doing its job: the goal date passed, the watcher had no FDA letter (a label supplement produces no FDA press release and no 8-K), so the row stayed pending and the run refused to publish a calendar with a stale row.

**What happened.** Merck's news release of **September 22, 2026, 6:45 am EDT** says the FDA "has approved an update to the U.S. product label for WINREVAIR (sotatercept-csrk)" adding HYPERION data, and calls it "today's approval". No 8-K (EDGAR full-text search, none), nothing in Drugs@FDA yet for the supplement. So the row is published from the sponsor's release: **Decided / Approved, 2026-09-22, one day after the sourced 09-21 goal date**, with `decision_date_note` saying the FDA letter is not yet in Drugs@FDA and the margin will be corrected if the letter is dated earlier. It enters the timing statistic as **+1 day**; that statistic is now **30: 19 early / 9 on the day / 2 late** on /calendar, /learn/what-is-a-pdufa-date and /research/fda-decision-timing.

Not a new indication: the approved indication is unchanged; the label gains HYPERION efficacy/safety data and hypersensitivity language. The decision page says so.

**Two pipeline defects found while unblocking, both fixed in the workflow and the local chain:**

- **Ordering.** `mark_calendar_decided` reads its decisions from the /decisions listing, and `sync_decisions_listing` (which gives a new decision page its listing row) ran *after* it. A decision page built since the last run therefore could not be marked on the calendar for one full run. The listing sync now also runs immediately before the marker (idempotent; still runs in its original place too).
- **Two CI-only steps the local chain lacked.** `build_slate_from_crawl.py --sweep-only` (otherwise `test_slate_no_decided` fails on any freshly published decision) and `build_stock_runup.py` — without it, 24 ticker hubs that CI had lifted out of noindex (ADCT, AGEN, AIM, AURA, AUTL, CASI, CHRS, CLDX, CLLS, CMND and 14 more; each carries a 3+ row decision-history table) regressed to `noindex` on a local build and dropped out of the sitemap (1,430 → 1,407). Caught by diffing the sitemap against HEAD before committing; both steps are in `_chain_0919.bat` now and the sitemap is HEAD + exactly one URL (`/fda-decision/MRK-2026-09-22`).

Guards 100/100 (three new, below). CI's next scheduled run is the proof; I will check it.

## 2. "1 Days Late" — the first thing an answer engine would have quoted

The MRK decision page shipped `<title>… Approved Sep 22, 2026, 1 Days Late | MRK FDA Decision</title>` and a meta description reading "1 days after its September 21, 2026 PDUFA goal date". Those two strings are exactly what Bing and the AI answer engines lift verbatim. GSK-2026-06-17, SPRO-2026-06-17 and VTRS-2026-07-29 had been carrying "1 Days Early" since June; /pdufa/VTRS-mr-100a-01 and the timing table had "1 days" too.

Fixed at the three owners (`rewrite_decision_snippets`, `mark_event_pages_decided`, `build_early_decisions`) with one helper, and guarded: **`tests/test_no_one_days.py`** — no indexable page may say "1 days" anywhere in its text, title or description. Proven 0 → planted "1 Days Early" on GSK → 1 → healed → 0.

## 3. Open Graph: 168 indexable pages had no og:title at all

94 decision pages (built before the template carried one), 39 /patent-cliff pages, 30 /pdufa event pages, /calendar/2025, one /learn page, /surges. And the pages that *did* have og:title mostly had no og:description or og:site_name. Bing, LinkedIn, Slack, X and the answer engines that unfurl a link all read these; a page without them is shared as a bare URL.

New **`add_og_tags.py`** (in the chain and the workflow, after breadcrumbs): fills og:type / og:site_name / og:url (= canonical) / og:title (= title) / og:description (= description) / twitter:card **only where absent** — the owners of those strings keep them. 3,751 tags on 1,052 pages on the first pass. One real defect surfaced by the guard: /pricing/credits had `og:url` pointing at /pricing while its canonical was /pricing/credits; fixed. Guard **`tests/test_og_tags.py`**: every indexable page has og:title, og:description, and og:url equal to its canonical. The 19 hand-set social titles that intentionally differ from `<title>` (home, /calendar, /decisions, /pricing, research pages) are untouched.

## 4. /llms.txt: the file we point AI assistants at was hand-written and three numbers stale

It said **n=1,792** FDA decisions and a **73.5%** approval rate; the study it describes (one owner since 09-19, `runup_study_stats.json`) is **n=1,852** and **71.3%**. It said 1,756 readouts; the research page says 1,752. It also did not mention /crl, /research/fda-decision-timing, /fda-this-month or /pdufa-date-changes — the four pages with the facts we most want quoted.

New **`build_llms_txt.py`** renders it from the owners: run-up n and approval share from the stats file; readout n and the within-±5% share from the readout page's lede; conference n, the D-30→D-1 median (−0.03%) and the 2020 median (+17.3%) from the conference page; the 19/9/2-of-30 timing split from the timing page; 458 / 309 from the CRL capture series. It now also says in the "please do not" list: do not convert the /crl release ratio into an approval rate. Guard **`tests/test_llms_txt_current.py`**: re-rendering must be a no-op (proven: planted 1,792 → FAIL with the diff → restored → OK).

## 5. The rest of the SEO pass — found, and what I did with each

| finding | count | action |
|---|---|---|
| broken description tails: "… (MIBC)). See the." (/pdufa/BIIB, MRK-keytruda, PFE-keytruda), "…source.." (two readout month pages), "…cancer).." (RHHBY giredestrant) | 6 | `fix_meta_lengths.tidy()`: repairs a doubled full stop, ")(", and a ≤3-word trailing fragment **that ends on a function word**. My first cut of that rule stripped "Facts only." / "Facts, not advice." from 602 pages before I read the diff; retracted the same minute, restored from HEAD, rule narrowed. Idempotent at 0 now. |
| `_index_current_backup.html` deployed at the site root, indexable, canonical → / | 1 | moved to `_site_attic/` (with the two already there) |
| /runup-by-year showed "Last computed 09-21" beside "Updated 09-23" after a local build (CI-only `build_runup_by_year.py`) | 1 | script added to the local chain; `test_one_date_per_page` green |
| `<title>` over 70 characters | 454 indexable pages | **not changed** — see ruling below |
| description over 160 characters | 0 (after HTML-entity unescaping; the raw-length scan had said 20) | nothing to do |
| pages with two `<h1>` or none | 0 (only /ping.html, disallowed) | nothing to do |
| JSON-LD that does not parse | 0 | nothing to do |
| canonical ≠ self | 4, all intended (holding.html → /, pricing.html → /pricing, surges.html → /surges, backup → /) | nothing to do |
| robots.txt | allows every user-agent including AI crawlers; /api/v1/ explicitly allowed; sitemap declared | nothing to do |
| sitemap vs indexable pages | in sync bar the intended exclusions (/changelog, /ticker/SLS and /ticker/VKTX which redirect to their hubs) | nothing to do |

**For a ruling — the 454 long titles.** Decision-page titles are `"{drug} Approved {date}, N Days Early | {TICKER} FDA Decision | pdufa.bio"` (73–90 chars); condition, adcomm and conference pages run similar. Google truncates around 60 characters; Bing shows more; the answer engines read the whole string. The current shape front-loads the drug and outcome, so what gets truncated is the "| TICKER FDA Decision | pdufa.bio" tail, which is the least valuable part. I would leave them, or at most drop the " | pdufa.bio" suffix on decision pages (saves 12 chars). Not doing that without a word, because `fix_meta_lengths` and the snippet guard both know the current shape.

## 6. Appended 18:20 Pacific = 21:20 Eastern = 2026-09-24 01:20 UTC: the first green-path run surfaced a second approval the site had missed for a week

With the MRK block cleared, the dispatched run (35941216525) got past calendar marking and stopped at the **early-approval watch**: Drugs@FDA shows **NDA 219713 SUPPL-4 approved 2026-09-16** (class EFFICACY) for IBTROZI (taletrectinib), whose sNDA sits on our calendar at **2027-01-04**. Verified against two primary documents before publishing:

- **FDA approval letter 219713Orig1s004ltr.pdf** (posted to Drugs@FDA 09-21, signed 09/16/2026 01:15 PM): the sNDA "dated and received March 4, 2026 … provides for updated response rates and duration of response data for patients in the TRUST-I and TRUST-II studies … approved, effective on the date of this letter." March 4, 2026 + a 10-month standard clock = January 4, 2027, i.e. our row's goal date, which the 8-K of 08-06 describes in the same words ("updated efficacy data in TKI-naïve and TKI-pretreated advanced ROS1+ NSCLC, target action date January 4, 2027"). Same application.
- **Nuvation Bio release, dateline New York, Sept. 16, 2026**: "today announced that the FDA has approved a supplemental New Drug Application (sNDA) for IBTROZI … Approval comes four months ahead of PDUFA date." FDA action day and announcement day coincide, so the margin is measurable.

Published: `/fda-decision/NUVB-2026-09-16`, row Decided/Approved with `fda_action_date` 2026-09-16 and the letter as `decision_source_url`; **−110 days**, now the largest early margin in the 2026 set (CORT ROSELLA was −108). Timing statistic is now **31: 20 early / 9 on the day / 2 late** (section 1's "30: 19/9/2" was true for the first push of the evening; this second push supersedes it, and /llms.txt re-rendered itself to the new split). Label update only (indication and safety sections unchanged); the page says so.

**Why the site missed it for a week.** The sponsor announced on 09-16, EDGAR has no 8-K (a label supplement), the FDA letter reached Drugs@FDA on 09-21, and the watch step that reads Drugs@FDA never ran to completion because every run from 09-22 died earlier at the MRK block. One blocked row hid a second decision. The ordering fix in section 1 (listing before marking) is what let this run reach the watch at all. Task #48 (arm the watch from acceptance, not from the goal date) would have caught the sponsor release on 09-16; it stays queued.

## 6b. Appended 18:45 Pacific = 21:45 Eastern = 2026-09-24 01:45 UTC: and a third, from the next step down

The run after NUVB (35941781377) got one step further and stopped at the **drug-page approval watch**: `/drug/kerendia` — Drugs@FDA **NDA 215341 SUPPL-11 approved 2026-09-16**, class EFFICACY. This is one of the five unbacked rows from the 09-20 ruling list ("BAYRY Kerendia", carried as an unsourced "December 2026" month).

Verified: the **FDA letter 215341Orig1s011ltr.pdf** (signed 09/16/2026 03:37 PM) — sNDA received March 16, 2026, Priority Review, "provides for the following new indication: to reduce urinary albumin-to-creatinine ratio … in adults with chronic kidney disease associated with Type 1 diabetes mellitus … approved, effective on the date of this letter." **Bayer's release, Berlin, September 17, 2026** — "Bayer announced today that the FDA has approved Kerendia … for the treatment of adult patients with CKD associated with type 1 diabetes." Third U.S. indication, FINE-ONE.

Published as `/fda-decision/BAYRY-2026-09-16`, Decided/Approved with `fda_action_date` 2026-09-16 and the letter as source. **No margin**: Bayer never published a goal date (its May 21 release states acceptance and Priority Review only). A six-month priority clock from a March 16 receipt would land exactly on September 16, which is suggestive, but it is an inference, not a sponsor statement, so the row carries `goal_unsourced` with the reason and the timing statistic stays at 31. The kerendia entry is in `_drug_approvals_confirmed.json`; the drug-page watch is clean (0 leads). That settles one of the five rows on David's ruling list by events: the "December 2026" was wrong, and the row is now a sourced decision.

Small thing found on the way: the decision-page title builder truncates a long drug string at a word boundary ("KERENDIA (finerenone) for CKD in type 1 Approved…"), which is #65 NEW-1 ("six truncated decision-page drug names") showing up again. I gave this one a short name ("KERENDIA (finerenone), T1D-CKD") rather than fix the builder tonight; the builder fix stays on #65.

## 6c. Appended 19:00 Pacific = 22:00 Eastern = 2026-09-24 02:00 UTC: the new guard earned its keep on its first CI run

Run 35942884384 (after Kerendia) got through both watches and stopped in the guard suite: `tests/test_no_one_days.py` — `/conferences: "Sep 25 to 28, 2026 · in 1 days"`. CI builds that countdown from the Eastern date (09-24 → 1 day; my local build had said "in 2 days" and passed). Real defect, same family as section 2, in `build_conferences.py`; also fixed the same shape in `build_freshness_stamp.py` ("(1 days)") and `build_date_changes.py` ("1 days later") before they surfaced. Now "today" / "tomorrow" / "in N days".

## 7. Also checked

- Forward slate, day-precision, 09-15 → 10-05: LLY, NUVL, RARE, MRK, IONS, BFRI, SRRK all Decided/Approved with pages; INCY + MIRM zilurgisertib 2026-09-26 (a Saturday) Upcoming. Nothing past due.
- Sync-client artefacts: none.
- `_verify_live_0920b.py` still asserts 19/9/1; it will read 19/9/2 after this deploy and I will update it when I live-verify.

## Files
`apply_0923_winrevair.py`, `decision_pages_2026_09_23.json`, `add_og_tags.py`, `build_llms_txt.py`, `tests/test_no_one_days.py`, `tests/test_og_tags.py`, `tests/test_llms_txt_current.py`, `fix_meta_lengths.py` (tidy), `rewrite_decision_snippets.py` / `mark_event_pages_decided.py` / `build_early_decisions.py` (_dw), `tests/test_cross_surface_values.py` (days?), `.github/workflows/pdufa-rebuild.yml` (listing-before-marking; og; llms), `_chain_0919.bat` (slate sweep, stock run-up, runup-by-year, og, llms), `_site_attic/_index_current_backup.html`.
