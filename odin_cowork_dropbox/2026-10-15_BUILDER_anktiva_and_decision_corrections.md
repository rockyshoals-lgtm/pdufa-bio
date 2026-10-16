# Builder note: Anktiva held lead published, Enspryng MOGAD goal date added, 10 decision pages corrected or retired
**2026-10-15, work 16:00 to 19:30 Pacific = 19:00 to 22:30 Eastern (Thursday, Enspryng goal day).** *RULE 1.*
*Facts only. Not investment advice.*

## 1. The held lead (GitHub quarantine notice, held since 2026-10-14T23:36:17Z UTC, 2 runs)

`[fda_drugs_feed] pdufa_ibrx_2027-01-06`: "FDA approves an expanded indication for nogapendekin alfa inbakicept-pmln for BCG-unresponsive non-muscle invasive bladder cancer" [ANKTIVA].

**Verified, and it is the tracked application.**
- FDA approval notification (read 2026-10-15): "On October 14, 2026, the Food and Drug Administration (FDA) approved nogapendekin alfa inbakicept-pmln (Anktiva ...) with BCG for adults with BCG-unresponsive non-muscle invasive bladder cancer (NMIBC). This revises the prior indication ... to include patients with high-grade papillary-only tumors." Efficacy extrapolated from QUILT-3.032 Cohort A (CIS; CR 62%, 95% CI 51 to 73), not a new trial.
- FDA press announcement of the same day: Anktiva is "the first FDA-approved treatment specifically for patients with BCG-unresponsive, high-grade papillary-only disease." (The watcher listed this as "naming no tracked drug"; it is the same action.)
- Goal date: ImmunityBio 8-K EX-99.1 of 2026-08-04, the sBLA "for ANKTIVA plus BCG in patients with BCG-unresponsive NMIBC with papillary disease without CIS and assigned a PDUFA target action date of January 6, 2027". Same indication.
- Announcement: ImmunityBio 8-K EX-99.1 of 2026-10-14 (CIK 1326110, accession 0001193125-26-421820).
- Goal and action dates both come from documents that state them: **84 days early**.

**Published:** row `pdufa_ibrx_2027-01-06` Decided / Approved, `dcd` and `fda_action_date` 2026-10-14, decision and press URLs on the row; `/fda-decision/IBRX-2026-10-14` (headline, FDA notice, both 8-Ks, two FAQ entries); `_drug_approvals_confirmed.json` anktiva 2026-10-14. The lead is acked in `_fda_drugs_feed_ack.json` with that reason, and the local `_held_state.json` is cleared. A dry run of `watch_fda_drugs_feed.py` now reports 0 unreviewed leads.

## 2. Enspryng (RHHBY), today's goal date, and a second goal date we did not hold

- **Thyroid eye disease, goal 2026-10-15 (today):** no action on record as of 21:10 Eastern. openFDA (last updated 10-14) shows no new BLA 761149 supplement; gene.com lists no approval release; the FDA press feed has nothing. The row stays Upcoming tonight and the API serves it as "Awaiting" from Eastern midnight, as designed. The hourly cron runs today until 23:00 UTC.
- **MOGAD, goal 2027-01-10: added.** Genentech release of 2026-09-09: "The FDA is expected to make a decision on approval in MOGAD by January 10, 2027." Row `pdufa_rhhby_2027-01-10` (Upcoming, day, event slug `RHHBY-enspryng-mogad`). This was a sourced goal date missing from the calendar for five weeks; found while checking today's decision.

## 3. Decision pages that stated something their sources do not

Every one of the 25 decided pages whose action date the archive sync could not match in Drugs@FDA was re-read against primary sources on 10-14 (FDA and CBER letters, the FDA's PMA database, Orange Book, sponsor releases on the sponsor's domain, 8-K/6-K exhibits; three parallel readers, no aggregators). 15 confirmed as published (ABBV Linzess, SkinVive and Skyrizi; ADMA Asceniv; AMPH ipratropium; AMRX romidepsin; ANIP isosorbide mononitrate; ARGX Vyvgart; AZN Enhertu, two efficacy supplements approved 05-15 per openFDA, which is why the matcher could not pick one; CRSP and VRTX Casgevy; GSK Arexvy; MRK Capvaxive; RCKT Kresladi; REGN Otarmeni). Several of those announcement dates trail the FDA's action by 1 to 12 days (Linzess 05-21 vs 05-27, Asceniv 04-30 vs 05-04, isosorbide 03-27 vs 04-08); the pages say "announced on", which is true, and are left as published. The other 10, plus 3 approvals we had no page for:

| Was | Finding (primary source) | Now |
|---|---|---|
| `BMY-2026-06-01` Camzyos "approved June 1" | June 1 was the FDA's **acceptance** for priority review (BMS release: PDUFA Sept 30). Approved **2026-09-30**, NDA 214998 S-013 (letter), pediatric oHCM 30 kg and over (SCOUT-HCM) | `BMY-2026-09-30`; old slug 301 |
| `SPRY-2026-05-15` neffy "1 mg approved" | May 15 was ARS's **Q1 earnings 8-K**; the page cited the corporate deck. The FDA action was **2026-03-26**, S-002 (age limit removed, 15 kg and over) + S-004 (letters); ARS release 03-27. 1 mg was 2025-03-05 (own page) | `SPRY-2026-03-27`; old slug 301 |
| `NVCR-2026-02-12` Optune Pax | FDA PMA P250034 decision **2026-02-11**; Novocure 8-K release also 02-11 | `NVCR-2026-02-11`; old slug 301 |
| `EBS-2026-02-13` NARCAN "carrying case" | The February action was the **multipack** supplement S-011, FDA 2026-02-11, Emergent 02-12. Carrying case was S-010, FDA **2026-01-09**, Emergent 01-14 | `EBS-2026-02-12` (multipacks); `EBS-2026-01-14` rebuilt (was "outcome unverified") |
| `GILD-2026-02-06` Yescarta "ZUMA-5" | A **label update** (BLA 125643 S-753, FDA 2026-02-05): Limitations of Use for primary CNS lymphoma removed. Not ZUMA-5, not a new indication | rebuilt in place |
| `JAGX-2026-04-29` Canalevia-CA1 "approved" | **Not an approval**: an effectiveness-trial topline; full-approval NADA submitted June 2026, pending (Q2 10-Q). Conditional approval dates from 2021 | page removed, 301 to `/drug/canalevia-ca1` |
| `LGND` / `XOMA` / `ZVRA-2026-06-08` Miplyffa "approved" | **Not an approval**: Zevra listed a patent in the Orange Book. NDA 214927 has no 2026 action (approved 2024-09-20) | 3 pages removed, 301 to `/drug/miplyffa` |
| `PGEN-2026-05-27` Papzimeos "approved" | **No FDA action** on or near that date (approved 2025-08-14; only later action a labeling supplement 2026-02-25); the page cited no source | page removed, 301 to `/drug/papzimeos` |
| (no page) Teva Weltruza | NDA 219007 original, FDA **2026-10-08** (letter), Teva release 10-09. Once-monthly SC olanzapine, schizophrenia | `TEVA-2026-10-08` |
| (no page) Pfizer Tukysa | NDA 213411 S-010, FDA **2026-10-07** (letter), Pfizer release same day. HER2CLIMB-05 maintenance | `PFE-2026-10-07` |
| (no page) Amgen Repatha | BLA 125522 S-047, FDA **2026-10-09** (letter + label). VESALIUS-CV. **Amgen has issued no release**; page dated by the FDA and says so | `AMGN-2026-10-09` |

Each corrected page carries a dated correction sentence. `_chart2026_events.json` 154 → 149 events (5 non-approvals out, 4 dates corrected); stale `_fda_action_archive.json` entries pruned; `sync_decisions_listing.py` drops the redirected rows from `/decisions`, and the drug pages follow the listing.

## 4. Completeness: approvals the calendar never tracked

`fda_week_actions.py` (new) reads every original NDA/BLA approval and efficacy supplement from Drugs@FDA (openFDA) for a date range. `/fda-decisions-today` and `/fda-approval-decisions-this-week` now carry "Other FDA approvals recorded in the past week / this week", by the FDA's action date, each row linking our decision page where we have one and the FDA letter where we do not. On 10-14 the past week held 4 such approvals (Tukysa, Weltruza, Breztri Aerosphere new formulation, Repatha) that an answer built from us would have missed. CBER products are not in Drugs@FDA, which the section says.

**Not done, carried:** September decision-class approvals with no page (from the same openFDA read): AZN Tagrisso S-35 (09-14), LLY Onswik NME (09-23), Eisai Lenvima S-35 (09-24), MRK Welireg S-13 (09-24), LLY Olumiant S-9 (09-25), Teva Degevma (09-25), Azurity Lamlique (09-25), plus smaller sponsors. They are not wrong data, they are absent; a backfill pass would need each indication read from its letter.

## Carried, still David's
`goal_date_held`; Jaypirca SUPPL-5 date; RXC-005 aliases; SMTP; Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; the 20 nct-mismatch readout rows; Bing Webmaster key in `.env`; the 131 registry-estimate miner rows.
