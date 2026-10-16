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

## 4. Local guards
143 pass. Three fail locally, all expected:
- `test_dropbox_index_complete`: this note, cleared on commit.
- `test_one_date_per_page`: the `--no-state` stamp; passes in CI.
- `test_sls_activity`: the local `_sls_activity.json` is five days old. CI runs `sls_daily.py` before its guards and passed at 01:53 UTC. CI's `SEC_USER_AGENT` secret is empty in that step, and EDGAR reports 0 filings since cursor 2026-09-25. **David:** check that secret.
