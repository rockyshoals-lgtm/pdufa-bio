# Note for the pdufa builder (2026-11-18): the run-up study is now curated every rebuild

What changed (branch claude/project-thread-spc424, merged by PR; David asked for the study to be current and go live after red team):

- New `runup_study_events.py`: one owner for "what drug, what outcome, is it an FDA decision" for a study row. Reads the
  decision page (Outcome / Drug / Indication / Validation kv lines). Eligible = primary-sourced approval or CRL.
  Ineligible: "outcome unverified" pages, pages whose Outcome reads "label corrected" (their own CRL reason says it was
  not a CRL), pages listed in `runup_study_exclusions.json`, and 2025+ rows with no published page.
- New `curate_runup_study.py` (workflow step after extend_runup_study.py): relabels rows from their page, drops
  ineligible rows, one row per FDA action (same ticker + Drugs@FDA application + action date), one row per price event
  (same ticker + eve close; if the two disagree on outcome both leave). Removed rows go to `runup_study_excluded.csv`
  with the reason. Idempotent.
- New `sync_decision_runup_chip.py` (step after runup_study_stats.py, before build_decision_faq.py): writes the study's
  T-120_T-1 and post_1d onto every /fda-decision page as "120-day run-up (T-120→T-1)" and "Decision-day move". The old
  "T-120 run-up (low→high)" chip (306 of 336 matched nothing, e.g. LLY 2025-01-15 "+1.0% ($725.72→$932.06)") is
  replaced, or removed where the event is not in the study.
  -> build_decision_page.py still writes its own "120-day run-up" from a decision-day-anchored window; the sync step
     overwrites it with the study figure on the next rebuild. Suggest making build_decision_page.py read the study.
- `extend_runup_study.py`: labels new rows from the event's own page (it used the ticker's FIRST dataset row: GSK
  neladalkib Nov 17 read "tebipenem"), outcome from the page, mcap tier from FMP on the eve date, skips same-eve rows.
- `build_stock_runup.py`: the ticker-hub table is "FDA decisions in the run-up study", links rows that have a decision
  page, and says the rest are 2020-2024 research rows (SRPT showed history (1) over a table of 5).
- `tests/test_runup_study_current.py` adds checks 4 and 5 (labels, eligibility, duplicates, page chips). Plants:
  PLANT_RUNUP_STUDY=label | mislabel | chip.

Decision pages that publish something their source does not support (NOT edited by this change; for you / the date
red team). Full list with the documents read: /mnt/project-files/.task-notes/cmsg_015VmLcJ9Lr2nV4JZZZ8DzU7D9YABxUTdaqoCnU7ZQTvvA/decision_pages_source_check.md
- 35 pages marked "primary-sourced" on a keyword-matched SEC filing that announces no FDA action (runup_study_exclusions.json lists each with the finding).
- 15 pages show "✗ CRL ⚠ label corrected" in the Outcome while their CRL reason says no CRL (EQ-2025-03-27, CYTK-2025-11-07, URGN-2025-04-27, PHIO x2, JSPR x2, LSTA, ALLO, TRAW, SNSE, ESLA, ENGN, SVRA, IBRX).
- Same FDA action on two pages: ASND 2026-02-27/28, BMY 2025-04-08/11, JNJ 2025-09-19/29 (both differ from the 09-26 action date), IRON 02-13/15, VNDA 02-20/21.
- SNY-2025-12-28: CRL announced 2025-12-24.
- 74 pages whose own Validation action date differs from the page date; most are the next trading day, but AMRX-2025-01-23 (-5), AMRX-2025-09-04 (-7), JNJ-2025-03-20 (-5), NVO-2025-10-15 (-2) and MRK-2026-02-20 (+10) look wrong.
- ALVO-2025-11-02, AQST-2026-02-02, ATRA-2026-01-12, CORT-2025-12-31, FBIO-2025-10-01, RGNX-2026-02-08 say "source-verified" and "verification in progress" at once.

Open: the 2020-2024 research rows (1,334 before curation) are not source-checked and include conference readouts filed
as CRLs (MB-106, FT596, CTX110, GC012F, ADI-001, ALLO-501/715) and approvals that never happened (INO VGX-3100, CLNN
CNM-Au8). Only SRPT 2023-05-15 is excluded so far. Waiting on David whether to run the same check over them.
