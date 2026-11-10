# Builder note: the 2026-11-09 red-team orders (Polygon to FMP, reliability, /calendar lede, items 4-11)
**2026-11-09 20:00 to 2026-11-10 ~00:30 Pacific = 23:00 Nov 9 to ~03:30 Nov 10 Eastern.** *RULE 1.*
*Facts and build mechanics only. Not investment advice.* Answers "please see updated audit from red team" (the
2026-11-09 one-document audit). David's choices (11-10): all items 1-11 in order; FMP only for now, with the
Alpaca path dormant until its secrets exist; relabel the two Novo rows "date not announced".

## 1. Polygon to FMP (order 1)
- New `price_source.py` is the one place prices come from: FMP `/stable/` primary (historical-price-eod/full,
  batch-quote-short, market-capitalization-batch), Polygon fallback only while `PRICE_POLYGON_FALLBACK` is not "0"
  **until 2026-11-17** (then delete the secret and `_polygon_daily`), Alpaca free (IEX) fallback dormant until
  `ALPACA_KEY_ID` + `ALPACA_SECRET_KEY` exist; Alpaca volume is never published (IEX is partial).
- Eleven call sites moved to it: polygon_enrich (prices / market caps / ADV), extend_runup_study, add_t120_baseline,
  build_home_board, build_readout_results (x2), sls_daily, build_sls_hub, build_sls_deepdive, build_vktx_hub,
  build_retail_pages, build_stock_runup. Every price step in the workflow now gets `FMP_API_KEY`.
- **Speed:** the forward-slate price step ran in **20 seconds locally (46/46 tickers from FMP, 48 HTTP calls)**;
  the Polygon step took 23 minutes in the last green CI run (01:18 to 01:41 UTC, Nov 6).
- **Convention kept:** split-adjusted, NOT dividend-adjusted closes. The audit suggested `adjClose`; that is FMP's
  dividend-adjusted series and would move every run-up figure on dividend payers (AZN, MRK, BMY, GILD) against
  the 1,879-event study, which was built on Polygon `adjusted=true` (splits only). FMP's `close` is the same
  convention as Polygon's. Stated on `/methodology` ("Where the stock prices come from").
- **Close-by-close diff before cutover** (`_price_cutover_diff.py` -> `_price_cutover_diff.json`): 63 tickers in
  `stock_runup_cache.json`, **17,349 common closes, 87 differ by more than 0.5%**, 0 Polygon days missing from FMP,
  2 FMP-only days, 0 tickers FMP lacked.
  - 86 are **AZN, every one dated 2025-07-29 to 2026-01-30** (largest 4.99% on 2026-01-26), none after
    AstraZeneca's ordinary shares replaced its ADRs on the NYSE on 2026-02-02. FMP's pre-listing series is not the
    traded ADR close Polygon recorded. Rule in `price_source.RECORDED_BEFORE`: before 2026-02-02 AZN closes come
    only from the recorded series; a day it lacks is dropped (the window is then skipped, never filled).
  - 1 is BAYRY 2026-08-06 (Polygon 14.32, FMP 14.24, -0.56%), an OTC ADR; left as FMP reports it.
  - `build_stock_runup` now never rewrites a cached close; a feed only adds later days.
- **Guard:** `polygon_enrich.py` writes everything that refreshed, then exits 3 naming any forward ticker that got
  no data and is not on `_price_no_feed.json` (empty today). The step is `continue-on-error` and the next step
  opens one `PRICES: no price data for X, Y` issue mentioning David; the deploy goes ahead on kept values (a frozen
  night costs ~80% of the next day's Bing AI citations, §2a). Planted test: `--plant-missing CYTK` -> exit 3,
  "::error::price feed returned nothing for 1 forward ticker(s): CYTK".
- `SLATE.as_of` was `dt.date.today()` on a UTC runner (read tomorrow after 20:00 ET); now Eastern.
- Page attributions follow the feed (SLS, VKTX, readouts, run-up by year, decision charts).
- Found on the way: `/sls` printed "SLS daily closes,  to  (Polygon..." with both dates empty (the Polygon SLS
  series had stalled); FMP fills it on the next rebuild.

## 2. Reliability as a citation metric (order 2)
- BLOCKED issues (`blocked_issue.py`) and ESCALATION issues (`quarantine_leads.py`) now open with
  **"Days since last green deploy: N (run R, finished YYYY-MM-DD HH:MM ET)"** and cc @rockyshoals-lgtm (GitHub
  emails the mention; SMTP still not set). "Still blocked" comments carry the same line.

## 3. /calendar lede (order 3)
- First sentence now: "25 FDA PDUFA goal dates are still ahead in 2026, the next on November 14, 2026, and 37 more
  are already set for 2027 and later; each links the filing it came from, and the calendar is updated daily."
  Then the existing "This page lists 110 FDA decision dates covering June 2026 to December 2026. 84 of them have
  been decided..." `tests/test_lede_matches_table.py` now recounts the ahead figure, the next date and the
  later-year figure against the grid and the 2027 month pages.

## 4. /clinical-trial-success-rates (order 4)
- Read against BIO, Informa Pharma Intelligence and QLS Advisors, "Clinical Development Success Rates 2011-2020"
  (Feb 2021; https://www.bio.org/clinical-development-success-rates-and-contributing-factors-2011-2020, PDF
  https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf). The four tiles matched
  (52.0% n=4,414; 28.9% n=4,933; 57.8% n=1,928; 90.6% n=1,453; LOA from Phase I 7.9%; oncology 5.3%; hematology
  23.9%). Wrong and fixed: the caption's sample ("9,985 transitions across 7,455 programs" is the 2006-2015
  report; this one is 12,728 across 9,704 programs, 1,779 companies); "~86-91%" and "~7.9-9.6%" blended the two
  reports; the source link was a biomedtracker.com page, now BIO's page and PDF; "readout dataset ... coming
  soon" (live since September) now links /readouts; meta description now dated 2011-2020 with exact figures.

## 5. CRL month pages (order 5)
- New `build_crl_months.py`: `/crl/{year}/{month}` for every month Jan 2025 through the current Eastern month (23
  pages), each stating two counts it never adds together: letters in the FDA's release dated that month, and
  CRLs among the decisions we tracked that month. Month chips on `/crl`. Guard `tests/test_crl_month_pages.py`.
- **What the pages say for October and November 2026: 0 released and 0 tracked.** openFDA's CRL release still
  holds 458 records (last updated 2026-08-26 in our snapshot; the live API answers 2026-08-13), newest letter
  2026-08-07. Every decision we tracked July to November 2026 (48) was an approval. The pages say the FDA
  publishes letters in batches, so a month with none released may still have letters not yet published.
- Note: `_crl_capture_series.json` last row is 2026-10-18; the capture step runs `|| true` and the file is not in
  the workflow's `git add` list, so the series stops growing in git. Not fixed tonight.

## 6. 2027 conference pages (order 6)
- Already in place: /conference/ASCO, /ASCO-GU and /AACR are titled "... 2027: {dates}, {city}" from
  conferences.json (re-verified on organiser sites 2026-11-08). The console data the audit read ends Nov 7.

## 7. Frozen named-drug pages (order 7)
- `build_drug_pages.py`: a drug with no pending event now opens with the decision ("The FDA approved Camizestrant on
  Sep 4, 2026. It is an AstraZeneca PLC program in ...") and its title says so ("Camizestrant FDA Approval: Approved
  Sep 4, 2026"; "Rusfertide FDA Approval: Approved Aug 28, 2026").
- **Novo rows (David's ruling):** Mim8 (denecimig) and CagriSema are "FDA goal date not announced": dataset
  `st` "Under review" with `_d.goal_date: "not announced"` and the Q3 6-K sentence; removed from the slate and the
  /calendar and December grids; both event pages carry a notice quoting the 6-K. The NVO hub had printed
  "Dec 31, 2026" for CagriSema, a day no document states; it now lists no upcoming catalyst.
  `site_windows.window_label` (the one owner of window text) returns "Not announced" for such rows,
  `event_pages.pending_rows` skips them, and new `fix_not_announced_pages.py` (after the event-page builders) clears
  the rest: meta/og/twitter descriptions, the FAQ answer, the banner, the Event JSON-LD (dropped) and the duplicate
  /pdufa/NVO-cagrisema page, where one builder had written "expected in Not announced".

## 8-11
- **8 Three-dates line:** already live via `inject_verified_against.py` on all 57 decision pages a dataset row
  points at; Enspryng reads "FDA action day October 15, 2026 (BLA 761149 S-008) · Announcement October 15, 2026
  (Genentech press release); also Roche media release, Basel, dated October 16, 2026 · Goal date October 15,
  2026"; Voceryq (INO-2026-10-30) likewise. The other 434 archive pages carry no dataset row.
- **9 Competitors:**
  - *fdatracker.com*: WordPress site, subscription products (FDA Calendar, Trial Tracker, Burn Rate, Omniview,
    Patent Tracker), membership-gated calendar; uploads dated 2013-2015 (an old domain, which is likely why it
    holds #1 for "pdufa calendar"). No per-event public pages seen on the homepage.
  - *catalystalert.io*: Next.js, "1,294 companies, 19,970 pipelines, 4,418 upcoming catalysts", every date
    labelled confirmed / estimated / AI-detected, public /fda-decision/{drug-ticker-pdufa-date} pages, /pdufa by
    month, /this-week, outcomes with stock moves, "vs" comparison pages, ML likelihood-of-approval scores and a
    "track record". Free account: next 7 days, 3 companies, an email when a watched date moves. Pro $29.99/mo.
    Its next-decisions list matches ours for Nov 14 (CYTK, SMMT, and the IGALMI at-home sNDA) and Nov 22 (SVRA,
    CAPR); it lists SNY venglustat Nov 25. What it has that we lack: date-move email alerts and an .ics feed
    (both already on our open list). What we have that it does not: the source sentence on every dated row,
    no predictions.
- **10 Year pages:** new `build_decision_subhubs.py` cuts /decisions/approvals, /decisions/crl, /decisions/2025 and
  /decisions/2026 from /decisions' own rows every run. Found broken on the way: /decisions/approvals held 82 rows
  (to July 2026) under headings "2026 · 15" and "2025 · 221" with an empty 2025 grid, and /decisions/crl held 47
  of 115 (to June 2026). Now 376 approvals and 115 CRLs; /decisions/2026 175 decisions (155 approvals, 20 CRLs),
  /decisions/2025 316 (221, 95), each linking the 2026 timing study for early/on/late margins.
- **11 Saturday 11-14:** CYTK aficamten, SMMT ivonescimab, IGALMI at-home sNDA (row ticker TEVA: BioXcel is in
  bankruptcy, BTAIQ, 8-K items 2.01/5.02/5.03 on 2026-10-30). Decision pages follow the sponsor's release as usual.

## Still David's
SMTP secrets; `/surges` RULE 2 ruling; VERCEL_TOKEN if still failing; held leads #70-#72; Alpaca keys (optional);
remove `POLYGON_API_KEY` after 2026-11-17.

## Outcome (appended 2026-11-09 ~23:05 Pacific = 2026-11-10 ~02:05 Eastern)
- Run 42761187385: **price step 13 seconds in CI** (05:17:44 to 05:17:57 UTC; Polygon took 23 minutes on Nov 6), no
  PRICES issue; the run then failed two guards (dropbox INDEX listed two uncommitted 11-09 audit notes; the new
  /decisions/{year} meta descriptions were cut mid-word). BLOCKED #73 opened with "Days since last green deploy:
  0.1 (run 42746995620, finished 2026-11-09 22:54 ET)" and cc to David: order 2 working as written.
- Run 42762573262 deployed; its post-deploy verifier failed only because it still read the old /calendar lede wording.
  `verify_live_deploy.py` now reads the forward-first lede with the same sum rule (live: 24 ahead + 84 decided + 1
  awaiting = 109).
- **Run 42764217706 green**: https://github.com/rockyshoals-lgtm/pdufa-bio/actions/runs/42764217706
- A dispatch at 05:13 UTC was refused by GitHub ("'FMP_API_KEY' is already defined"): my workflow patch had put the
  key twice in the price step. Fixed; `test_workflow_valid.py` now fails on duplicate YAML keys (PyYAML keeps the last
  one silently, so the local guard had passed).
- Live (fetched 01:50 ET): /decisions/2026 and /2025, /decisions/approvals, /decisions/crl, /crl/2026/october and
  /november, /clinical-trial-success-rates (12,728 transitions), /drug/camizestrant ("Camizestrant FDA Approval:
  Approved Sep 4, 2026"), /pdufa/NVO-am833 and NVO-mim8 ("FDA goal date: not announced", no Event schema, no
  "Dec 2026"), /methodology all 200; /sls now reads "SLS daily closes, Oct 2024 to Nov 2026".
- 15 URLs sent to Bing (bing-submit run 42765669234).
- **Held leads #70 and #71, checked against primary sources tonight, not yet published:**
  - #70 NVCR: Novocure 8-K Nov 9, 2026 (EX-99.1): FDA **Not Approvable Letter** on the Optune Mya PMA (brain
    metastases from NSCLC); "uncertainty around the degree of clinical benefit"; no safety concerns raised. A device
    PMA letter, not a CRL.
  - #71 asundexian: FDA press announcement Nov 9, 2026: **Sunharbo (asundexian) 50 mg approved**, first factor XIa
    inhibitor, with antiplatelet therapy after recent mild-to-moderate non-cardioembolic ischemic stroke or high-risk
    TIA; Bayer HealthCare; Fast Track and Priority Review. https://www.fda.gov/news-events/press-announcements/fda-approves-first-factor-xla-inhibitor-help-prevent-stroke-certain-adults-high-risk
  - /drug/asundexian (665 Bing AI citations) is held on its previous build, which says "under FDA review". Both need
    decision records next; neither row has a sponsor-stated goal day, so no early/late margin.
