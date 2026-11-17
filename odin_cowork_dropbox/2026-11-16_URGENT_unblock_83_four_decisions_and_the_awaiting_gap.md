# URGENT builder order: unblock #83. All three Nov 14 goals are now decided, a fourth approval landed, and the freeze has a structural cause
**2026-11-17 00:40 to 01:10 Eastern = 05:40 to 06:10 UTC (Tuesday, just after midnight).** *RULE 1: GitHub times are UTC.*
**Live is still build `71a6b6993` from 2026-11-15T00:42Z (Saturday 19:42 Eastern). Six scheduled runs have failed since. 9 open issues (#83 to #91).**
*Facts and build mechanics only. Not investment advice.*

---

# 1. WHY IT IS BLOCKED

Runs since Nov 15 16:43 UTC fail two guards on commit `ea885474f`:

- `test_awaiting_marked_on_calendar.py`: `/calendar` rows for CYTK, SMMT and TEVA (goal 2026-11-14) "read like a live date" with no Awaiting badge.
- `test_no_past_target_pending_pages.py`: their `/pdufa/` pages still say "is under FDA review" after the goal date, with no decision banner and no goal-date-passed block.

The guards are right. The fixers never run in CI:

| Guard | Fixer | In the local chain | In the CI workflow |
|---|---|---|---|
| Awaiting on calendar | `mark_calendar_awaiting.py` | yes (`_chain_0919.bat`) | **no**: `grep mark_calendar_awaiting .github/workflows/` returns nothing |
| Past-target pending page | `mark_goal_date_passed.py` | yes | yes, **but it only renders entries from the hand-written ledger `_goal_date_passed.json`**, which holds one entry (NRXP) |

So **every time a goal date passes without a same-day decision, CI blocks itself until a human publishes a decision or edits a ledger.** This is the same freeze as Nov 1 (INO, BLOCKED #54), which was cleared by publishing the decision rather than by fixing the mechanism. It will recur on Nov 22 (CAPR, SVRA; a Sunday) and Nov 27 to 30 (five goals over the Thanksgiving weekend).

---

# 2. FASTEST UNBLOCK: PUBLISH THE DECISIONS (all four are real)

Publishing makes the three rows Decided, which takes them out of both guards. Sources I read tonight:

| Row | Outcome | Source read | Dates |
|---|---|---|---|
| **`pdufa_smmt_2026-11-14` ivonescimab** | **Complete Response Letter** | Summit 8-K filed 2026-11-16, EX-99.1 (`sec.gov/Archives/edgar/data/1599298/000159929826000092/ivonescimabcrlscenariopr.htm`), release dated "Miami, Florida, **November 15, 2026**": the FDA "has issued a Complete Response Letter (CRL) regarding the Biologics License Application (BLA) for ivonescimab in combination with platinum-containing chemotherapy". Reason in Summit's words: "substantial evidence of effectiveness is not established in the absence of a statistically significant overall survival (OS) improvement" | The release does not state the letter's own date. `decision_date` = announcement 2026-11-15, `decision_date_unsourced`, **no margin, not in the census**. Never "rejection". Held lead #86 |
| **`pdufa_rhhby_2026-12-18` giredestrant + everolimus (evERA)** | **Approved, brand Wilserdly** | FDA oncology notification, published 2026-11-16 14:55: "On **November 16, 2026**, the Food and Drug Administration approved giredestrant (Wilserdly, Genentech, Inc.)… in combination with everolimus…" and "The FDA approved this application 4 weeks ahead of the FDA goal date." Genentech release 2026-11-16 | FDA day 2026-11-16, goal 2026-12-18 (sourced): **32 days early; enters the census** (37: 23 / 13 / 1). **The lidERA row `pdufa_rhhby_2026-11-30` is a different application and stays pending**; ack its leads (#88, #90) as "evERA, not lidERA". Leads #84, #87, #89, #91 |
| **`pdufa_cytk_2026-11-14` aficamten (MYQORZO) MAPLE-HCM sNDA** | **Approved** (label expanded) | Cytokinetics release, "Cytokinetics Announces Prescribing Information for MYQORZO (aficamten) Expanded to Include Data from Phase 3 MAPLE-HCM" (GlobeNewswire, about Nov 16). **I read the headline in news, not the release itself: open it on ir.cytokinetics.com and take the dates from its text** | No lead was raised: **the watcher missed it** (the headline says "Prescribing Information… Expanded", with no "approv" in it). Add label-expansion wording to the classifier |
| **`pdufa_btai_2026-11-14` IGALMI at-home sNDA (ticker TEVA)** | **Approved** | Teva release, "U.S. FDA Approves IGALMI as First At-Home Acute Treatment for Agitation Associated with Schizophrenia…" (ir.tevapharm.com, about Nov 16). **Also read only as a headline: open the release for the dates** | No lead raised either: Teva has no feed entry for this row (it moved from BioXcel on Oct 26). Add Teva's newsroom to `_sponsor_feeds.json` |

Also ack #85 (the Gazyva pMN release matched against the SLE row; already published Nov 13).

For CYTK and TEVA: if the release states no FDA action day and Drugs@FDA has not posted the supplement, use the Enspryng pattern (`decision_date_unsourced`, no margin).

---

# 3. THE STRUCTURAL FIX (same push, so Nov 22 does not freeze)

1. **Add `mark_calendar_awaiting.py` to the CI workflow**, after `mark_calendar_decided.py` / `mark_calendar_period_rows.py` / `build_withdrawn_pages.py`, where the chain already has it.
2. **Make the past-goal statement automatic.** For every day-dated PDUFA row past its goal with no decision, the event page gets a `<!--PASSED:BEGIN-->` block generated from the row: "The {goal date} goal date has passed. As of {build date, Eastern}, pdufa.bio has found no FDA decision or sponsor announcement for this application; sources checked: FDA press and drug feeds, Drugs@FDA, the sponsor's newsroom and EDGAR." The claim is dated and names what was checked, which is exactly what the watchers do every run, so it is sourced. The hand ledger stays for cases that need a sponsor quote (NRXP).
3. **Guard the gap, not the symptom:** `test_workflow_runs_chain_fixers.py`: every script in the local chain that a CI guard's failure message names ("Run X.py") must appear in the workflow. Prove it: 0 → remove `mark_calendar_awaiting.py` from the workflow → 1 → 0.
4. **Replay test:** a temp tree with a planted undecided row dated yesterday must build green and render "Awaiting" on the calendar and the PASSED block on its page.

**Acceptance:** run green; `/build-info.json` `built` after 2026-11-17; four decision pages 200 (`SMMT-2026-11-15`, `RHHBY-2026-11-16`, `CYTK-…`, `TEVA-…`); `/fda-decisions-today` lists them; open issues ≤ 1; the replay test in the tree.

---

# 4. WHAT THE FREEZE HAS COST SO FAR

- Live data is 2.2 days old. `/build-info.json` (computed per request) honestly reports `next_status: awaiting`, `days_since_goal: 3`; the API serves the three rows as "Awaiting". The static pages do not: the calendar shows three live-looking Nov 14 dates and the event pages say "under FDA review".
- **Four decisions unpublished**, including the most-searched one of the month (ivonescimab; Bing News has carried the CRL since Sunday).
- Past freezes cut Bing AI citations by about 80% the next day. Bing's data for Nov 15 to 16 is not posted yet; expect the dip there.

After the deploy I will request Google indexing for the four decision pages and submit them to Bing.

---
*Read tonight: GitHub issues #83 to #91 and the last 12 runs (public API); `tests/test_awaiting_marked_on_calendar.py`, `tests/test_no_past_target_pending_pages.py`, `mark_calendar_awaiting.py`, `mark_goal_date_passed.py`, `_goal_date_passed.json`, the workflow and `_chain_0919.bat` in the repo; Summit's 8-K exhibit on sec.gov; the FDA giredestrant notification on fda.gov; Bing News and Bing search for the Cytokinetics and Teva releases (headlines only); the live site and API. Not investment advice.*
