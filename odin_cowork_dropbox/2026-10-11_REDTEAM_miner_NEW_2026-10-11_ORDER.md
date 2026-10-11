# Red team: the 10-11 miner run (daily/NEW_2026-10-11.csv), every date checked, and what the builder should publish
**2026-10-11, measured ~10:30 to 12:40 Pacific = 13:30 to 15:40 Eastern (Sunday).** *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

**Input:** `daily/NEW_2026-10-11.csv`, written 08:35 Pacific, 216 rows: 168 dated from ClinicalTrials.gov, 29 from EDGAR guidance, 19 from conference releases.
**Output:** `odin_cowork_dropbox/2026-10-11_REDTEAM_miner_NEW_2026-10-11.csv`, the same 216 rows plus `rt_*` columns: verdict, corrected precision and window, drug/trial/indication recovered from the source, presentation type and session date, the live registry status/PCD/type/update date, the verbatim timing quote, and a note. Nothing was published; this is the builder's input.

**How it was checked.** Every one of the 168 NCTs was refetched from ClinicalTrials.gov today (167 read, 1 timeout). All 29 EDGAR exhibits and all 19 releases were read in full by two parallel readers, with the timing sentence quoted verbatim. Conference first days were checked against the dates each release states. The 17 NCTs already on the site were compared with the site's own rows. No aggregator was used.

## Verdicts (216 rows)

| Verdict | Rows | Meaning for the builder |
|---|---|---|
| PUBLISH_AS_MONTH | 131 | Registry-dated readouts. Publish at **month** precision, status Estimated, source "trial-estimate (not company-confirmed)". Never as a day. |
| PUBLISH | 17 | Guidance or conference row confirmed verbatim; publish as stated (with rt_drug/rt_trial/rt_indication filled). |
| PUBLISH_FIX | 13 | Confirmed but the miner's window, trial name or type is wrong; publish the `rt_` values, not the miner's. |
| PUBLISH_CAVEAT | 3 | Confirmed, but it is an update of already-reported data or a correlative analysis; say so. |
| PUBLISH_CHECK | 1 | OCGN: filing is from March; re-check a later filing first. |
| UPDATE_DATASET | 3 | Already on the site, and the registry has since MOVED. Update the site row. |
| DUPLICATE_ON_SITE | 14 | Already on the site, registry unchanged. Do not add. |
| DUPLICATE | 7 | Same readout from a second filing. Keep the latest filing's row. |
| HOLD_WATCH | 18 | Trial completed, data lock passed, no results posted. The readout DATE is unknown. A watch item, not a calendar event. |
| HOLD_VERIFY | 2 | CNTB: a 09-30 PR may already be this readout. Verify before dating. |
| DEDUPE_TO_IMA | 1 | HMDCF row is ImageneBio's trial; publish under IMA only. |
| DROP | 5 | Already reported (QTTB x3), or not a readout at all (DFTX NDA filing; IVEVF NDA submission). |
| DROP_OR_PRECLINICAL | 1 | EDIT at AHA: non-human primate data; no patient dosed. |

## The findings that matter

1. **102 "day-precision" readouts are registry estimates.** 101 of the 102 day-dated CT.gov rows take their day from an ESTIMATED primary-completion date (one from an ACTUAL completion). A completion date is not a readout day, and the site's own rule (claim no more than the source) has forbidden this since 09-10. All 131 registry rows go out at month precision or not at all.

2. **The miner would have published a readout that happened in July.** QTTB rows 1 to 3 (SIGNAL-AA Part B, "2026-H2"): the filings say "mid-2026", and Q32 Bio reported the 36-week topline on **2026-07-13** (8-K EX-99.1, data cutoff 2026-06-30). Three rows, all DROP. The miner's `company_guidance` extractor also mapped "mid-2026" to H2, which is wrong on its face.

3. **Five "Q2 2027" rows have no Q2 in their filing.** KZIA (x2), BIOA, ANL: every filing says "second half of 2027". KRRO's Q2 is a dosing-start date; its only readout is an INTERIM read in 2027-H2. TRXB (x3) say "mid-2027", not H2.

4. **Two rows are regulatory milestones, not data.** IVEVF 2027-H1 is an NDA submission; DFTX 2027-H1 is an NDA filing.

5. **Every guidance row arrived with an empty drug, trial and indication.** Recovered from the filings for all 29; three had a wrong trial field (GPCR "SAD" is the MAD cohort; TTRX "RCT" is a design word; EYPT "AMD" is the DME program COMO/CAPRI).

6. **Conference rows: 18 of 19 confirmed, first days all correct**, with session dates and types now filled (ZLAB and NBP are posters; VIR has two orals; AMLX is a late-breaking oral). EDIT at AHA is preclinical. Three are updates of data already out (MAZE, AMLX, KYTX SPS), one is correlative only (CADL).

7. **Already-reported toplines appear inside these filings and must not be listed as upcoming:** PCVX OPUS-1 (2026-10-05), EYPT LUGANO (2026-08-17), GPCR ACCG-2671 SAD (2026-09-08), DFTX Panorama (2026-09-14), QTTB SIGNAL-AA Part B (2026-07-13).

8. **Extra readouts the filings guide that the miner missed** (publishable, see rt_note): GPCR aleniglipron Phase 2 data 2026-Q4 and ACCOMPLISH Phase 3 2028-H2; PCVX VAX-31 infant 2027-H1 and VAX-A1 2027-H2; OCGN OCU410ST GARDian3 2027-Q2; EYPT LUCIA 2026-Q4; HMDCF SAFFRON/SANOVO 2026-H2; TTRX HS Phase 2a 2027-Q3; LSTA MAR001 sHTG 2027-H2; DFTX DT402 ASD initial data 2026-Q4.

## P1, found on the way: the live site's registry-estimated readouts have drifted

The same CT.gov refetch was run over every Estimated/Guided readout row on the live dataset (333 NCTs read in total). **164 agree. 15 have moved, 6 are TERMINATED, 1 has results posted.** The "Readout registry watch vs ClinicalTrials.gov" CI step is advisory; `apply_readout_registry_signals.py` carries the registry's status but not its date. These rows say "Estimated {month}" for windows the registry has already replaced:

| Site row | Site says | Registry now | Type | Registry updated |
|---|---|---|---|---|
| readout_anip_2026-07-15 ANIP Yutiq | 2026-07 | 2026-03-31 | ACTUAL | 2026-10-05 |
| readout_cers_2026-07-15 CERS | 2026-07 | 2026-04-29 | ACTUAL | 2026-10-06 |
| readout_dwtx_2026-07-15 DWTX Halneuron | 2026-07 | 2026-12 | ESTIMATED | 2026-09-16 |
| readout_acrs_2026-08-15 ACRS A-101 | 2026-08 | 2026-09-21 | ACTUAL | 2026-09-29 |
| readout_clrb_2026-08-15 CLRB NOV-002 | 2026-08 | 2027-06-30 | ESTIMATED | 2026-10-01 |
| readout_grfs_2026-08-15 GRFS | 2026-08 | 2026-07-07 | ACTUAL | 2026-10-01 |
| readout_kpti_2026-08-15 KPTI selinexor | 2026-08 | 2026-05-22 | ACTUAL | 2026-09-30 |
| readout_alec_2026-09-15 ALEC AL001 | 2026-09 | 2026-05-14 | ACTUAL, **TERMINATED** | 2026-09-17 |
| readout_ardx_2026-09-15 ARDX tenapanor | 2026-09 | 2026-08-20 | ACTUAL | 2026-09-22 |
| readout_annx_2026-10-15 ANNX tanruprubart | 2026-10 | **2027-07-31** | ESTIMATED | 2026-10-06 |
| readout_eras_2026-11-15 ERAS naporafenib | 2026-11 | 2026-07-01 | ACTUAL | 2026-09-16 |
| readout_xncr_2026-12-15 XNCR | 2026-12 | 2026-07-13 | ACTUAL | 2026-09-21 |
| readout_mltx_2027-02-15 MLTX sonelokimab | 2027-02 | 2026-05-28 | ACTUAL | 2026-10-09 |
| readout_mbx_2027-05-15 MBX 2109 | 2027-05 | 2028-05 | ESTIMATED | 2026-10-07 |
| readout_goss_2027-12-15 GOSS seralutinib | 2027-12 | 2026-09-09 | ACTUAL, **TERMINATED** | 2026-10-07 |

Also TERMINATED with the site still listing an expected readout: readout_calc_2026-07-15, readout_immp_2026-10-15, readout_sngx_2026-07-15, readout_jspr_2026-08-15. Results posted: readout_huma_2027-09-15 (2026-07-29). ANNX is the one that bites first: the site says October 2026 for a readout the registry moved to July 2027 five days ago.

## ORDER for the builder

| # | Item | Acceptance |
|---|---|---|
| 1 | **Live P1.** Re-sync the 15 moved rows to the registry (month precision, `date_history` entry); mark the 6 TERMINATED rows as such and off every "expected readout" surface; HUMA to Reported or dropped. Make the registry watch write dates, not only status, and make a moved PCD a build change, not an advisory line. Guard: no Estimated readout row's `dm` differs from the live registry's PCD month by more than the day the watch last ran. | ANNX reads Jul 2027; the 6 terminated rows no longer say "expected"; guard 0 → planted 1 → 0 |
| 2 | **Ingest the red-teamed file**, using `rt_*` columns only: PUBLISH / PUBLISH_FIX / PUBLISH_CAVEAT rows; the 131 registry rows at month precision; UPDATE_DATASET for the 3; nothing from DROP, DUPLICATE, HOLD. HOLD_WATCH rows go to the watch ledger, not the calendar. | Row counts match the table above; no new day-precision readout from a PCD |
| 3 | **Fix the miner** before its next run: (a) a CT.gov PCD never yields `date_precision: day`; (b) "mid-YYYY" maps to year (or a "mid" bucket), never H2; (c) a guidance row must carry drug, trial and indication or be rejected; (d) a completed trial with a passed data lock is a watch item, not a dated row; (e) before emitting a guidance row, check EDGAR full-text for a later filing naming the same trial with "topline"/"results" (the QTTB case). | Re-run on today's input reproduces the red team's verdicts for QTTB, KZIA, BIOA, ANL, KRRO, TRXB, IVEVF-H1, DFTX |
| 4 | Publish the 10 extra readouts the filings guide (finding 8) if the dataset lacks them. | each sourced to the filing quoted in rt_note |
| 5 | Verify CNTB (HOLD_VERIFY) against the 2026-09-30 PR. | |

**Carried from earlier audits, still David's:** `goal_date_held`; Jaypirca SUPPL-5 date; RXC-005 aliases; SMTP secrets; Google Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources.
