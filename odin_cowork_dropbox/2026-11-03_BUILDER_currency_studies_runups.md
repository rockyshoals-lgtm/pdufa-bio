# Builder note: currency, studies, run-up build-out
**2026-11-03, work 17:00-21:30 Pacific = 20:00-00:30 Eastern.** *RULE 1.*
*Facts only. Not investment advice.* Responds to "ensure currency again, make sure that all the studies are up to date, continue building out the runups with all the most recent pdufas". David chose: all decided PDUFAs; all studies including every /research page.

## 1. Currency
- CI: last 5 scheduled rebuilds green except one (Nov 2 21:27 UTC, transient). No decisions due Nov 1-3 on the calendar; no pending row past its goal date.
- Held lead #58 (VRTX): Vertex's Q3 8-K restates the Nov 30 povetacicept PDUFA ("approval in IgAN coming later this month"); not an approval. Acked.
- **21 announced PDUFA goal dates were on no surface of the site.** Found by an EDGAR full-text sweep of 8-K/6-K exhibits (May 1 - Nov 3) for "PDUFA" + "target action date" / "PDUFA date", diffed against the dataset. Each row quotes the sponsor's own exhibit stating a day (`apply_1103_new_pdufas.py`):

| Ticker | Goal | Application | Source |
|---|---|---|---|
| PYPD | 2026-11-28 | D-PLEX100, SSI prevention (colorectal surgery) | 6-K 2026-07-29 |
| DYN | 2027-01-21 | z-rostudirsen, DMD exon 51 | 8-K 2026-07-29 |
| INSM | 2027-01-28 | ARIKAYCE sNDA, MAC lung disease | 10-Q 2026-10-29 |
| BLTE | 2027-02-12 | tinlarebant, Stargardt type 1 | 6-K 2026-08-11 |
| PVLA | 2027-02-28 | QTORIN rapamycin, microcystic LMs | 8-K 2026-10-28 |
| BMRN | 2027-02-28 | VOXZOGO full approval, achondroplasia | 8-K 2026-11-02 |
| APMD | 2027-02-28 | AD109 (Oxnimbi), OSA | 8-K 2026-09-08 |
| NTLA | 2027-03-10 | lonvo-z, HAE | 8-K 2026-09-08 |
| BMY | 2027-03-11 | Reblozyl + JAKi, MF anemia | 8-K 2026-07-30 |
| AQST | 2027-03-16 | Anaphylm resubmission | 8-K 2026-10-15 |
| MRK | 2027-03-22 | ENFLONSIA second season | 8-K 2026-10-29 |
| ETON | 2027-03-29 | LIBERVANT ages 6-11 | 8-K 2026-10-14 |
| HRMY | 2027-04-01 | pitolisant GR | 8-K 2026-08-04 |
| JAZZ | 2027-04-16 | cannabidiol oral capsule | 8-K 2026-11-02 |
| MRK | 2027-04-22 | IDVYNSO sNDAs | 8-K 2026-10-29 |
| IMNM | 2027-04-28 | varegacestat, desmoid tumors | 8-K 2026-08-11 |
| QURE | 2027-05-01 | AMT-130, Huntington's | 8-K 2026-11-02 |
| BMY | 2027-05-13 | mezigdomide (MeziKd), RRMM | 8-K 2026-07-30 |
| ZBIO | 2027-05-27 | obexelimab, IgG4-RD | 8-K 2026-08-13 |
| BMRN | 2027-05-30 | VOXZOGO, hypochondroplasia | 8-K 2026-11-02 |
| MRK | 2027-06-15 | sac-TMT, endometrial cancer | 8-K 2026-10-29 |

  Not added, with reasons: RPRX/LGND/ZLAB restate partners' dates already on the site (neladalkib, deucrictibant, QTORIN, povetacicept); ARGX's Q3 slide lists four efgartigimod programs beside one "PDUFA date of February 18, 2027" and does not say which it belongs to; BBIO encaleret's Aug filing said May 7, its Oct 29 filing says May 8 (the row's date). Market-cap tiers from FMP at write time.
- New `ensure_calendar_month_pages.py` (workflow + chain): any month holding a dated upcoming PDUFA gets a calendar page (June 2027 created today); prev/next rechained.

## 2. Run-up study build-out
- Every decided PDUFA in the archive is in the study (1,883 rows through 2026-10-30) except NUVL's Jul 22 approval: Nuvalent's shares stop before the post-decision window (acquired by GSK), so the row cannot be computed honestly.
- **97 rows (all decisions folded in since Feb 2025, ~90 of them 2026) had no market-cap tier**, so every by-size figure silently left out nearly all of 2026. The extender read a dataset field almost no row has. `backfill_runup_mcap_tier.py` tiers each from FMP's market cap on its eve date (97/97 priced); `extend_runup_study.py` now falls back to the same, and the workflow runs the backfill after every extension (FMP_API_KEY added to that step).
- Cohort medians re-computed (`runup_study_stats.py`); by year 2026: n=187, T-120 median +12.0%, approvals 87.7%.

## 3. Studies
- **/research/pdufa-stock-run-up-by-market-cap** was a frozen September cohort ("763 decisions") with no builder. New `build_cap_study_page.py` recomputes from the run-up study every run: 837 decisions (2024-26); reaction (larger of decision-day/next-day move) Nano 10.1%, Micro 6.7%, Small 5.6%, Mid 3.8%, Large 1.5%; T-120 run-up Nano -9.0%, Micro +18.0%, Small +4.2%, Mid +12.8%, Large +6.5%. Caveat sentences are kept only while the numbers still support them.
- Timing census, cohort figures, run-up-by-year, implied-vs-actual, CRL/approval-rate pages: rebuilt by the chain from current data.
- **Not refreshable today**: /research/readout-reaction (fixed 1,752-readout Gungnir set) and /research/short-interest-fda (1,753 decisions; built on one April 2026 short-interest snapshot applied to every year, the lookahead flagged in the April red team). Both need new data, not a rebuild. /research/conference-runup rebuilds nightly; its numbers have not changed since Sept 27.
