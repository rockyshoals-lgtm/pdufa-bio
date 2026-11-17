# Builder note: #83 unblocked -- four decisions published, and a passed goal date no longer freezes CI
**2026-11-16 ~22:00 Pacific to 2026-11-17 Eastern early morning.** *RULE 1: GitHub/UTC, page dates Eastern.*
*Facts only. Not investment advice.* Answers the 2026-11-17 URGENT order ("fix asap").

## 1. Decisions (all read from the primary document tonight)
| Row | Outcome | Source | Dates on the site |
|---|---|---|---|
| `pdufa_smmt_2026-11-14` ivonescimab | **Complete Response Letter** | Summit 8-K filed 2026-11-16, EX-99.1, release dated Nov 15, 2026: the FDA "has issued a Complete Response Letter (CRL) regarding the Biologics License Application (BLA) for ivonescimab" | `/fda-decision/SMMT-2026-11-15`; announcement day, letter date not stated: `decision_date_unsourced`, no margin, not in the census |
| `pdufa_rhhby_2026-12-18` giredestrant + everolimus (evERA) | **Approved, Wilserdly** | FDA oncology notification: "On November 16, 2026, the Food and Drug Administration approved giredestrant (Wilserdly, Genentech, Inc.) ... in combination with everolimus"; "4 weeks ahead of the FDA goal date" | `/fda-decision/RHHBY-2026-11-16`; FDA day Nov 16 vs sourced goal Dec 18: 32 days early, enters the census |
| `pdufa_cytk_2026-11-14` MYQORZO MAPLE-HCM sNDA | **Approved** (label update, indication unchanged) | Cytokinetics release Nov 16, 2026 (GlobeNewswire 04:00 ET): the FDA "has approved a supplemental New Drug Application (sNDA) updating the U.S. Prescribing Information for MYQORZO" | `/fda-decision/CYTK-2026-11-16`; FDA day not stated: unsourced, no margin |
| `pdufa_btai_2026-11-14` IGALMI at-home sNDA (TEVA) | **Approved** | Teva release Nov 16, 2026 8:00 AM (ir.tevapharm.com, read in the browser; the URL is too long for the fetcher): "today announced the U.S. Food and Drug Administration (FDA) approval of IGALMI (dexmedetomidine) sublingual film for at-home use" | `/fda-decision/TEVA-2026-11-16`; FDA day not stated: unsourced, no margin |

The lidERA row `pdufa_rhhby_2026-11-30` is a different application and stays pending (goal Nov 30).
Acked: #84/#87 (giredestrant drug-page leads: published), #85 (Genentech's Gazyva pMN release vs our SLE row), #86
(Summit 8-K: published), #88/#90 (evERA approval vs the lidERA row), #89/#91 (evERA: published).

## 2. Why CI froze, and the fix
- **`mark_calendar_awaiting.py` was in the local chain and never in the workflow.** Added to the CI step that runs
  mark_calendar_decided / period rows / withdrawn pages (the chain's position).
- **`mark_goal_date_passed.py` rendered only the hand ledger** (one entry, NRXP). It now writes an automatic block for
  every day-dated pending PDUFA row past its goal: "the FDA goal date for this application was {date}. As of {build
  date} (Eastern), pdufa.bio has found no FDA decision or sponsor announcement for this application; sources checked:
  the FDA press and drug feeds, Drugs@FDA, the sponsor's newsroom and EDGAR." The hand ledger still wins where it
  carries a sponsor quote; a block whose row is no longer pending past its goal is retired automatically.
- **Guard `tests/test_workflow_runs_chain_fixers.py`**: every script a guard's failure text tells you to run, if the
  local chain runs it, must be in the workflow. Proven 0 -> 1 -> 0: with `mark_calendar_awaiting.py` stripped from a
  copy of the workflow it fails naming that script; on the real workflow it passes (38 fixers named).
- **Replay `tests/test_past_goal_replay.py`**: a throwaway tree with a planted pending row dated yesterday runs both
  fixers; the calendar row shows Awaiting and the event page states the date passed with the sources checked and no
  pending tense. Nov 22 (CAPR, SVRA, a Sunday) and Nov 27-30 no longer need a human to keep CI green.
- **Watcher wording:** the sponsor-newswire decision pattern now also hears label-change headlines ("Prescribing
  Information ... Expanded", "label update"), which missed Cytokinetics.
- **Teva feed:** no machine-readable Teva feed exists that we can read (IR renders client-side; /rss/news-releases.xml
  is an empty shell; GlobeNewswire search is robots-disallowed). Recorded in `_sponsor_feeds.json` with feeds [];
  Teva has no pending tracked PDUFA now.
