# Builder note: currency (Gazyva pMN), Polygon removed, measured run-up on every PDUFA row
**2026-11-13 ~19:40 to ~22:30 Pacific = 22:40 Nov 13 to ~01:30 Nov 14 Eastern.** *RULE 1.* *Facts only. Not investment advice.*
David: "do another update, ensure currency, make sure that we are using FMP for our stock prices, update our pdufa data
with the pdufa runup for all pdufas we have missed". Choices: remove Polygon now; run-up for every decided PDUFA.

## 1. Currency
- Six scheduled rebuilds green Nov 12-14 (UTC). Held leads #79, #81, #82 (ESCALATION #80).
- **Gazyva (obinutuzumab), primary membranous nephropathy: approved.** FDA notice "FDA Approves First Drug to Treat Adults
  with Primary Membranous Nephropathy", published Fri Nov 13, 2026 17:33. Row `pdufa_rhhby_2026-11-30_pmn` Decided,
  `/fda-decision/RHHBY-2026-11-13`. The notice states no action day, so `decision_date_unsourced` until Drugs@FDA posts
  the supplement; goal was guided to November 2026 only, so no margin.
- Acked: #82 (same notice vs our Gazyva SLE row, a different sBLA, goal Dec 2026); #79 (the FDA republished its April
  13, 2021 Trodelvy urothelial notice, withdrawn Nov 22, 2024, with a Nov 12, 2026 pubDate; it matched MRK's
  sacituzumab tirumotecan on "sacituzumab"). The feed watcher now also reads the linked FDA page before raising a lead
  and drops it when the page's own "On {date}" is more than 14 days old (the Trodelvy item's feed text had no date).
- **Saturday Nov 14 goals (CYTK aficamten MAPLE-HCM sNDA, SMMT ivonescimab, TEVA IGALMI at-home): no decision found as
  of 22:45 ET Friday** (no 8-K from CYTK or SMMT since Nov 4-12, no FDA notice).

## 2. FMP only
- Polygon removed: `price_source.py` has no Polygon path (FMP, plus Alpaca only if its secrets are ever added);
  `polygon_enrich.py` lost its dead Polygon client; nine scripts' key checks now read `FMP_API_KEY`;
  `add_decision_chart.py` (its own Polygon fetch) now uses price_source; every `POLYGON_API_KEY` env line is gone from
  the workflow. **David: delete the POLYGON_API_KEY repo secret.**
- Guard `tests/test_prices_fmp_only.py`: the workflow and the 171 scripts it and the chain run reference no Polygon API
  or key, yfinance, Yahoo chart endpoint, Stooq or Alpha Vantage. Research scripts outside the site pipeline (bifrost_*,
  gungnir_*, momentum scanners, odin_live_scorer) still call Polygon/yfinance and are not part of the site.
- Closes Polygon recorded before Nov 10 stay as the series of record in the caches (AZN pre-2026-02-02 rule unchanged).

## 3. Run-up for every PDUFA
- **Study coverage:** every decision in the archive (495 pages) and every Decided dataset row has a study row within 45
  days, except two: NUVL zidesamtinib (Jul 22, 2026; FMP's NUVL series ends Jul 21 after the GSK acquisition, so no
  decision-day close exists) and NVCR Optune Mya (a device PMA letter, not a PDUFA event; `extend_runup_study.py` would
  have read its "Not approvable letter" as APPROVAL and now skips it). Gazyva pMN (Nov 13) joins on the rebuild.
- **Blanks that never filled:** rows are appended the day after a decision, before post_2d/post_5d closes exist, and
  were never revisited: 13 rows lacked post_2d and 33 lacked post_5d (almost all 2026), so every post-decision figure
  excluded the newest events. New `backfill_runup_blanks.py` fills only empty cells from FMP closes with the study's
  conventions: **49 cells on 33 rows**; CORC 2025-12-30 skipped (no closes). Pre-2025 T-120 blanks (71 rows, 2020-2023)
  are left: those baselines were measured once on the recorded series.
- **The dataset's `runup_summary` was not run-up data:** 68 of 122 PDUFA rows carried one of five repeated value sets
  (e.g. {"t30": 0.38, "t7": -0.01, "t1": 0.0} on 31 rows) and 54 were null, published in /api/v1 as each event's own.
  New `sync_runup_to_dataset.py` writes measured values: **59 decided rows from their study row** (T-120, 30, 14, 7, 3
  sessions into the eve close; 1 and 5 sessions after; basis "decided") and **55 upcoming day-dated rows measured so
  far** from FMP closes (T-120, 30, 7 to the last close; basis "so far", with its date); 8 null with `runup_note`
  (NUVL, NVCR, window-only goals). Units are percent and say so.
- Study republished: 1,885 events (2020-01-08 to 2026-11-10); 2026: 189 events, T-120 median +12.17%, approval 87.8%.
- Workflow: new step after the T-120 baseline runs `backfill_runup_blanks.py && sync_runup_to_dataset.py` daily.

## Still David's
Delete the POLYGON_API_KEY secret; Google list daily; SMTP; `/surges`; outreach.
