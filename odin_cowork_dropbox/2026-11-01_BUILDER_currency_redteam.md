# Builder note: Nov 1 currency + red-team pass
**2026-11-01, work afternoon/evening Pacific = evening Eastern; pushed after 01:00 UTC Nov 2.** *RULE 1.*
*Facts only. Not investment advice.* Responds to "ensure everything is up to date and current, fix any issues. red team everything."

## 0. Why the site was frozen
Every scheduled rebuild since Oct 31 failed (6 runs, BLOCKED #54): INO's Oct 30 goal date passed with no decision in the dataset, so two calendar guards blocked the commit. Nothing deployed after the Oct 31 data refresh.

## 1. Currency (decisions and dates)
| Row | Change | Source |
|---|---|---|
| INO Voceryq (INO-3107) | Approved Oct 30 (accelerated), on the goal date; /fda-decision/INO-2026-10-30 | FDA press announcement Oct 30; INOVIO release |
| AZN Ultomiris IgAN | Approved Oct 21 (BLA 761108 S-046); /fda-decision/AZN-2026-10-21 | Drugs@FDA; AZN 6-K Oct 22 |
| NVS Pluvicto mHSPC | Approved Jul 31 (S-037), was a sourceless "Q4 2026 (est.)" row; /fda-decision/NVS-2026-07-31 | FDA letter + label |
| LLY Mounjaro SURPASS-CVOT | Approved Aug 27 (S-044/S-045), was a sourceless "Q4 2026 (est.)" row; /fda-decision/LLY-2026-08-27 | FDA letter |
| AGIO mitapivat SCD | goal Nov 1 -> **Feb 1, 2027** | Agios release Oct 30 |
| EXEL zanzalintinib | goal Dec 3 -> **Mar 3, 2027** | Exelixis 8-K Oct 29 |
| RHHBY Lunsumio + Polivy (SUNMO) | new row, **Feb 9, 2027** (replaces a sourceless Q4 row) | Roche release Jun 18 |
| BBIO oral infigratinib, achondroplasia | new row, **Feb 4, 2027** (was on no surface) | BridgeBio 8-K EX-99.1 Oct 6 |
| BTAI IGALMI sNDA | sponsor -> **TEVA** (asset sale closed Oct 26); goal Nov 14 kept on BioXcel's 8-K | BioXcel 8-K Oct 30; Teva release Oct 27 |
| NVO Mim8 | sourced: review extended, no new timeline (year precision) | Novo 6-K Oct 2 |
| REGN garetosmab | goal day was never sourced ("August 2026") -> month; "12 days early" withdrawn everywhere | Regeneron release Feb 19, Q1 8-K, Q2 10-Q |
| 14 decided rows | day-precision goal sources recorded (census integrity) | sponsor 8-Ks/10-Qs |

**Timing census: 36 decisions, 22 early, 13 on the goal date, 1 late** (INO in, REGN out).

## 2. Red-team fixes
- **Calendar**: new month pages /calendar/2027/march (EXEL) and /calendar/2027/may (AXSM, BBIO encaleret); those rows were on no calendar page. Feb/Apr prev-next rechained. Removed: AGIO Nov 1, EXEL Dec 3, and the Q4 (est.) rows for Lunsumio, Trodelvy+Keytruda (approved Jun 24), Pluvicto, Tirzepatide. Dec 2026 Giredestrant row linked `href="#"`; now its event page. Month pages: the count chip and FAQ "currently tracks N" now match the row count (Feb 2027 said "1" over 3 rows) -- `retitle_calendar_months.py`.
- **Unbacked window rows** ratchet 8 -> **2** (ABBV Rinvoq vitiligo, AZN gefurulimab remain).
- **Decision h1s**: 26 pages showed the announcement day in the h1 and the FDA action day in the title (ABBV Juvmo Sep 28 vs Sep 25, MRK Winrevair, TLX Pixclara...). h1 now = action day "(announced ...)"; new nightly step `fix_decision_h1_action_date.py` (workflow + chain).
- **MNKD Furoscix ReadyFlow**: body said approved Jul 24, two days before a Jul 24 goal; FDA letter Jul 23, goal Jul 26 -> three days early, matching its title.
- **/drug junk pages**: 22 removed (conference names: european-respiratory, american-*, obesityweek, iaslc-world ...; fragments: r-chop, nct07271667, once-daily-oral ...). Connector-tail slugs (calquence-plus, keytruda-and, opdivo-in, gedatolisib-with, lifileucel-plus, bictegravir-and) merged into the drug's page with 301s. `build_drug_pages.py` JUNK_SLUG + connector strip.
- **/fda-this-month**: "in in combination", "in with BCG" fixed at source (`build_monthly_decisions.py`).
- **/surges** (Momentum Surge Radar, on pdufa.bio since Jul 25): now `noindex,follow` (drops from sitemap); "Ride the wave, exit by midday" and "ride the morning wave and exit by midday" removed as trading instructions. **David: this is a hypestock product living on pdufa.bio. Decide whether it moves to hypestock (RULE 2); I did not delete it.**
- **/screener was a July snapshot**: its table draws from an inline `const DATA=[...]` that had not changed since the first commit (2026-07-25): 395 rows, 31 "Upcoming" with past dates. No workflow step rewrote it. New `sync_screener_data.py` rebuilds DATA from the dataset each run, then `build_screener_rows.py` (which existed but was in no workflow) bakes the crawlable rows. Both added to the workflow and the chain.
- **IGALMI page follows its sponsor**: /pdufa/BTAI-igalmi -> **/pdufa/TEVA-igalmi** (301 kept); the BXCL501 2027 readout row moves to TEVA too. Without this every listing linked a /pdufa/BTAI-* page for a ticker the slate no longer carries.
- **Bare ticker event pages**: /pdufa/MRK-trodelvy, /pdufa/NVS (Pluvicto) and /pdufa/LLY (tirzepatide) still read "PDUFA date". The automatic matcher refuses them (several same-sponsor decisions, or a partner's ticker), so they are hand-linked in `_event_page_decisions.json` with sources; all three now carry the decided banner.
- **Goal moves into 2027**: `inject_goal_date_moves.py` only tagged 2026 month pages; now every year. `test_goal_date_moves_shown.py` checks the month page when /calendar's live grid has no heading for that month.
- **Duplicate HELD issues**: #55/#56/#57 were one AZN lead opened three times, because `issued_keys` is committed only on a passing run. `quarantine_leads.py raise_issue` now checks GitHub for an open issue with the same title and ack key first (same fix as the 10-15 ESCALATION duplicates).
- **Held leads #45-#57**: REAL ones published (AZN, INO); non-events acked with reasons (`apply_1101_acks.py`): #45 GSK 6-K mentions zidesamtinib, not neladalkib; #48 NVCR Q3 8-K describes Optune Gio's existing approval; #50 BioXcel asset-purchase exhibit; #51/#52 conference-name drug page.

## 3. Builder lesson (local, cost a full chain rerun)
The local chain's last step `quarantine_leads.py apply` restored INO and BTAI rows (and 9 pages) to HEAD because the local `_held_state.json` still listed the old leads. Clear it first: `quarantine_leads.py collect --leads _empty_leads.jsonl --no-issue`, then run the chain.

## 4. Not done
- `api/data.js` slate labels still contain em dashes (served as API JSON, not page copy). `api/data.js.bak_2026-08-29` is in the deploy tree.
- REGN Ordspono Feb 2027 lead not verified; not added.
- Calendar 2025 page: mark_calendar_decided reports its row markup no longer matches (316 rows, no-op). Historical page, no false claims found, but the marker is blind there.
