# Builder note: Enspryng TED published; /calendar rows audited against the data (11 wrong rows fixed); month sentences ordered and counted
**2026-10-16, work 00:15 to 02:30 Pacific = 03:15 to 05:30 Eastern = 07:15 to 09:30 UTC (Friday).** *RULE 1.*
*Facts only. Not investment advice.* Responds to the audit of 2026-10-16 (measured 01:53 to 02:10 Eastern).

## 0. Enspryng (satralizumab-mwge) for thyroid eye disease: published

**Source (read 07:30 UTC):** Genentech release on gene.com, dateline "South San Francisco, CA -- October 15, 2026": Genentech "announced today that the U.S. Food and Drug Administration (FDA) has approved Enspryng (satralizumab-mwge) for the treatment of adults with thyroid eye disease (TED)". SatraGO-2: proptosis response 52.9% vs 23.4% placebo, diplopia 60.7% vs 25.8% (active TED). SatraGO-1 missed its week-24 primary endpoint. Priority review, second indication after NMOSD (2020).

**No FDA action day on record.** openFDA (last_updated 2026-10-14) shows no new BLA 761149 supplement, and neither FDA feed carries a notice. The release says "announced today ... has approved", which does not state the FDA's day. So the row was published on the LNTH pattern:
- `pdufa_rhhby_2026-10-15`: Decided / Approved, `dcd` 2026-10-15, `decision_date_unsourced`, no `fda_action_date`.
- No early or late margin, and the row stays out of the timing statistic (still 32: 21 / 10 / 1).
- `sync_fda_action_dates.py` swaps in the letter date and re-admits the row when Drugs@FDA posts it.

**What was built:**
- `/fda-decision/RHHBY-2026-10-15`: title "Enspryng Approval Announced Oct 15, 2026 for Thyroid Eye Disease". The page says "pdufa.bio holds no FDA record of the action day yet", has three FAQs (led by "Was Enspryng approved for thyroid eye disease?") and a sibling link to the MOGAD row (goal Jan 10, 2027).
- `/fda-decisions-today` and the weekly page list it.

**Title fix.** `rewrite_decision_snippets.py` had silently dropped the indication from the title whenever brand, INN and indication exceeded 100 characters. It now retries with the brand alone; the INN stays in the h1. Tecentriq's title gained "for dMMR Colon Cancer" the same way.

**Did the watcher miss it? No: it was timing.**
- The 01:55 UTC run (21:55 Eastern, Oct 15) read the gene.com listing and raised nothing.
- The same parser, run at 07:25 UTC, finds the release at the top of the listing and raises a lead on `pdufa_rhhby_2026-10-15`.
- So the release reached the gene.com listing after 21:55 Eastern.
- It also raised a false lead on the MOGAD row (same brand). Both keys are acked in `_newswire_ack.json` with reasons.

The 10:00 UTC scheduled run will therefore not hold this lead: it is acked.

**David:** Bing Webmaster → URL Inspection → Request indexing for `/fda-decision/RHHBY-2026-10-15` and `/fda-decisions-today`.

## 1. /calendar: rows that contradicted the data (found by a new guard)

The calendar grids are patched in place, never regenerated, so rows outlive the facts behind them. `tests/test_calendar_rows_backed.py` (new) reads /calendar and every /calendar/2026/<month>. It fails when:
- a row that is not decided has no dataset row;
- a decided row links a page for a different drug;
- a row names a different drug than its dataset row;
- a month- or quarter-dated row is shown pending while the archive holds its approval.

Its first run found 11 wrong rows, all now fixed:

| Where | Row | Wrong | Now |
|---|---|---|---|
| /calendar June | BMY 2026-06-01 Camzyos | "pending" on the acceptance day (retired 10-15) | removed; the 09-30 row carries the approval |
| /calendar June | ZVRA, XOMA 2026-06-08 Miplyffa | "pending": a patent listing, no FDA action | removed |
| /calendar June | LGND 2026-06-08 "Approved: Miplyffa" | linked a FILSPARI page | removed |
| /calendar September | PFE/ROIV 2026-09-30 brepocitinib "Approved" | linked the **Tukysa** page (the 10-15 matcher bug, live since) | relinked to `/fda-decision/PFE-2026-08-27` (Lisraya) |
| /calendar/2026/june | ACHV 2026-06-20 | labelled "Custirsen: NSCLC" over the cytisinicline CRL | "Cytisinicline: Smoking cessation (ORCA-3)" |
| /calendar/2026/june | IONS 2026-06-30 | labelled "Donidalorsen" over the olezarsen approval | "TRYNGOLZA (olezarsen)" |
| /calendar/2026/june | ARVN 2026-06-05 "ARV-471" | page never names the code | "VEPPANU (vepdegestrant, ARV-471)" |
| /calendar December (+ /2026/december) | ABBV Dec 2026 Tavapadon | **pending**; approved as JUVMO 2026-09-25 (page 09-28) | marked Approved |
| /calendar December (+ /2026/december) | BAYRY Dec 2026 Kerendia T1D | **pending**; approved 2026-09-16 | marked Approved |
| /calendar Q4 est. | PFE Tukysa HER2CLIMB-05 | **pending**; approved 2026-10-07 | marked Approved |

**Root causes, both fixed:**
1. `mark_calendar_decided.py`'s 14-day near window accepted any same-ticker decision without a name check. A near match is now refused when the row names an INN (brepocitinib, olezarsen) that the decision does not mention and the two share no word. Code-named rows (MR-100A-01, TLX101-Px, UX111) keep matching on proximity. A dry run over all 12 calendar pages changes only the three wrong links above.
2. Month- and quarter-dated rows were never checked against decisions at all. The new `mark_calendar_period_rows.py`, in the chain and in CI after `mark_calendar_decided.py`, marks one only when:
   - a drug-name word matches;
   - an indication word matches the decision page's own "Indication" field;
   - and the decision falls in the period or up to 180 days before its end.

   This is what stops "Gazyva: Systemic Lupus Erythematosus" from taking the Gazyva nephrotic-syndrome approval.

## 2. Month sentences (audit 2a)

`inject_calendar_explainer.py`:
- names still-ahead rows in date order;
- never names a passed date as "due";
- counts month- and quarter-only rows and `/ticker/`-linked estimates (November said 10 still ahead with 12 in the grid; December 15 with 21);
- when it names fewer than are ahead, it says so.

Now:
- **October:** "In October the FDA is due to decide on MR-141 (IRD/VTRS, Oct 17), Bepirovirsen (GSK, Oct 26) and INO-3107 (INO, Oct 30)."
- **November:** "12 of them are still ahead, including Aficamten (CYTK, Nov 14), Ivonescimab plus platinum-doublet (SMMT, Nov 14), BBP-418 (BBIO, Nov 27), Giredestrant (RHHBY, Nov 30) and Povetacicept (VRTX, Nov 30)."

The audit counted 11 for November. The grid's 12th is REGN cemdisiran + pozelimab (NIMBLE, Nov 2026, month precision). June's sentence had named "Camzyos (BMY, Jun 1)" as due.

**Guard:** `test_calendar_rows_backed.py`. All five plants (orphan, wrongpage, order, wrongname, period) fail; clean passes: 156 rows across 8 calendar pages, 107 decided rows each linking a page that names the same drug.

## 3. Titles (audit 3c-4, 3b)

- `/calendar`: "FDA Calendar 2026: 106 PDUFA Dates, Updated Daily". "PDUFA" moves from first word to fourth; re-read the `pdufa calendar` position as well as `fda calendar 2026` share on the next audit.
- Weekly page: description and lede now begin "FDA approval decisions for biotech and pharma".

**Shipped:** 2bed50cdb at 07:56 UTC (03:56 Eastern). CI run 38869465648 was green. Live check at 08:02 UTC:
- `/fda-decision/RHHBY-2026-10-15` returns 200 with the TED title.
- API row: Decided / Approved / 2026-10-15.
- The today and weekly pages list it.
- build-info: `next_ticker` IRD, `held_leads` [].
- `/calendar`: no Miplyffa rows, the brepocitinib 09-30 row links PFE-2026-08-27, and the October and November sentences read as above.

## 3b. September approvals backfill (audit 2b), second push

Read every Drugs@FDA original and efficacy-supplement approval for 2026-09-01 to 09-30 (openFDA), then each FDA letter and the sponsor release. Four pages, each dated by its letter:

| Page | FDA letter | Sponsor release |
|---|---|---|
| `LLY-2026-09-23` Onswik (insulin efsitora alfa-gobe), once-weekly basal insulin, type 2 diabetes | BLA 761408, 09-23 | Lilly 09-24 (QWINT, 4 trials, >3,400 adults) |
| `MRK-2026-09-24` Welireg + Lenvima, clear cell RCC after PD-1/PD-L1 | NDA 215383 S-013 and NDA 206947 S-035, both 09-24 | Merck/Eisai 09-25 (LITESPARK-011; PFS HR 0.74; OS not significant) |
| `LLY-2026-09-25` Olumiant, severe alopecia areata age 12+ | NDA 207924 S-009, 09-25 | Lilly 09-25 (BRAVE-AA-PEDS: 42% / 27% vs 5%) |
| `TEVA-2026-09-25` Degevma (denosumab-adet), **biosimilar to and interchangeable with** Xgeva | BLA 761481 (351(k)), 09-25 | Teva 09-28 |

**Corrections to the audit's list:**
- **Onswik was already counted.** It is #41 on the FDA's Novel Drug Approvals 2026 list (46 rows, FDA content current as of 10-09), so the novel count was complete. Only the page was missing.
- **Tagrisso S-035 approves no new use.** It adds FLAURA2 final overall survival to section 14.4, and eosinophilic pneumonia to 6.2 (letter 09-14, with S-036, a myositis warning edit). AstraZeneca issued no release. No decision page: a label-data update is not an FDA decision on an application we would list.
- **Lenvima S-35 and Welireg S-13 are one approval.** It is the belzutifan + lenvatinib combination, so it gets one page.
- **Lamlique (Azurity) gets no page.** Azurity is a private sponsor with no ticker, which is the slug key. Garzulys (Emerge) and Bexlutry (Curium) are the same case.

**Two defects found on the way, both fixed:**
- **`/fda-this-month` was built before the archive learned a new page's FDA date.** The first build after every new decision page therefore failed `test_fda_days_by_action_date` (PFE yesterday, MRK today). `build_monthly_decisions.py` now runs again after `sync_archive_fda_dates.py`, in CI and in the chain.
- **The title budget cut drug names on a dangling word.** It produced "Degevma (denosumab-adet), biosimilar to and Approved". Two live titles had the same fault:
  - `BMY-2026-08-13`: "iberdomide, daratumumab, and Approved"
  - `TAK-2025-06-30`: "GAMMAGARD LIQUID ERC [Immune Globulin In Approved"

  The trimmer now drops trailing connectors, unbalanced brackets and trailing clauses. New guard `test_decision_titles_clean.py` (planted Degevma title fails).

## 3c. Order items 4 to 6
- **4, the next held lead:** nothing has been held since the 10-15 fix, so nothing to report yet. The real test of "a lead holds only its own row" is the next held lead; its note must record whether that deploy went green while the lead was held. The replay in `test_quarantine_not_blockade.py` covers the mechanism in the meantime.
- **5, Saturday 10-17, IRD/VTRS phentolamine (MR-141):** same runbook as Enspryng. Watch the gene.com-style listing for Opus Genetics and Viatris, and the FDA feeds, from Friday. On a weekend goal date the action usually lands Friday.
- **6, carried, unchanged:** `goal_date_held`; Jaypirca SUPPL-5 date; RXC-005 aliases; SMTP; Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; the 20 nct-mismatch readouts; the 131 registry rows (audit recommends watch list only); `build_sitemap.py --no-state`. New: CI `SEC_USER_AGENT` empty in the SLS step (section 4).
- **Still pending on /calendar and worth a human eye:** GILD/MRK Trodelvy (Q4 est.), whose 06-24 decision page has no "Indication" field, so the period matcher would not mark it. Also RHHBY Lunsumio + Polivy, ABBV Rinvoq vitiligo, AZN gefurulimab, NVS Pluvicto and LLY tirzepatide CV (Q4 est.); none matches a decision in the archive.

## 4. Local guards
143 pass. Three fail locally, all expected:
- `test_dropbox_index_complete`: this note, cleared on commit.
- `test_one_date_per_page`: the `--no-state` stamp; passes in CI.
- `test_sls_activity`: the local `_sls_activity.json` is five days old. CI runs `sls_daily.py` before its guards and passed at 01:53 UTC. CI's `SEC_USER_AGENT` secret is empty in that step, and EDGAR reports 0 filings since cursor 2026-09-25. **David:** check that secret.
