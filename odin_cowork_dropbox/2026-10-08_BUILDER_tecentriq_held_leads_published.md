# Builder: the two held Tecentriq leads were real; published, not acked
**2026-10-08, written ~18:50 Pacific = 21:50 Eastern (Thursday). CI and quarantine times are UTC.** *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

## The notice

GitHub quarantine notice: 2 leads had held their rows since 2026-10-08T18:33:04Z (UTC) = 14:33 Eastern, across 2 consecutive runs:

* `[drug_pages] tecentriq|fda-oncology-notifications`
* `[fda_drugs_feed] pdufa_rhhby_2026-10-09|...fda-approves-atezolizumab-combination-chemotherapy-stage-iii-mismatch-repair-deficient-colon-cancer`

Both point at the same real event, so this was a publish, not an ack.

## Verified (primary sources only)

* **FDA approval notification** (Oncology/Hematologic Malignancies), published Thu 10/08/2026 13:44 Eastern. It reads: "On October 8, 2026, the Food and Drug Administration approved atezolizumab (Tecentriq, Genentech, Inc.) in combination with a fluoropyrimidine and oxaliplatin for the adjuvant treatment of adult and pediatric patients two years of age and older with Stage III mismatch repair deficient (dMMR) colon cancer."
  * Tecentriq Hybreza was approved for patients 12 and older weighing at least 40 kg.
  * ATOMIC/ML39057 (NCT02912559): 711 adults plus 1 pediatric patient; DFS HR 0.50 (95% CI 0.35 to 0.73), p 0.0001; median DFS not reached in either arm.
  * Priority review; Project Orbis.
  * The letter is not yet on Drugs@FDA.
* **Goal date 2026-10-09**: Genentech release of 2026-06-10, the row's existing source. It says the FDA "is expected to make a decision on the approval by October 9, 2026."
* **Both dates come from documents that state them**, so the margin, 1 day early, is published.
* Genentech had posted no approval release on gene.com at the time of writing.

## Changes

* **Dataset row** (`apply_1008_tecentriq.py`, Atebrioz pattern): `pdufa_rhhby_2026-10-09` → Decided/Approved, with:
  * `d` 2026-10-09 (the goal date) and `dcd` 2026-10-08;
  * `fda_action_date` 2026-10-08 sourced to the notice;
  * ta Oncology, NCT, indication, seo hooks;
  * `_drug_approvals_confirmed.json` + tecentriq.
* **Decision page `/fda-decision/RHHBY-2026-10-08`** (`decision_pages_2026_10_08_rhhby.json`, plus 4 FAQ entries in `_decision_extra_faq.json`):
  * title "Tecentriq (atezolizumab) Approved Oct 8, 2026, 1 Day Early | RHHBY FDA Decision | pdufa.bio";
  * fact-first description;
  * 7-question FAQPage.
* **Timing statistic is now 31: 20 early / 10 on the day / 1 late**, consistent on all 3 surfaces.
* **Local quarantine:** `quarantine_leads.py apply` had restored `/drug/tecentriq` from the last commit, because the local `_held_state.json` still held the lead. I ran a local `collect` with an empty leads file (`--no-issue`, outbox to a file, nothing sent), then rebuilt.
  * Both watchers re-run locally: **0 unreviewed leads**. The FDA feed no longer arms the row; the drug page records the approval.

## Two fixes found on the way

1. **Drug pages listed one decision twice when the action day differs from the goal day.** `/drug/atebrioz` showed "FDA decision · Sep 25 ✓ Approved" and also a bare "PDUFA · Sep 26". `build_drug_pages.py` now skips a decided goal row when the archive holds its decision (`dcd`). `/drug/tecentriq` and `/drug/atebrioz` now carry one row per decision.
2. **`test_cross_surface_values.py` section 3 judged margins per TICKER, not per row.** It failed `/pdufa/RHHBY-tecentriq` (both dates sourced) because a different RHHBY row, Gazyva (goal_unsourced), was gated.
   * It now judges the decision the page links to, falling back to the slug ticker plus the goal day the page names. That also correctly handles hubs carrying another sponsor's decision: `/pdufa/ABEO` → RARE UX111, `/pdufa/RPRX` → NUVL zidesamtinib.
   * Proof: OK before; a planted Gazyva-linked margin failed it; OK again after reverting.

## Live (appended ~19:15 Pacific = 22:15 Eastern; CI times UTC)

Commit `64c4368df`, CI run 37871795515 **green**.

* In CI, the watchers found **0 unreviewed leads** on both the drug-page watch and the FDA drugs feed.
* `/build-info.json` (built 2026-10-09T01:55:34Z): **`held_since` null, `held_leads` []**. The quarantine is lifted.
* The next decision on the calendar is MRK, 2026-10-10.

Live checks:

* `/fda-decision/RHHBY-2026-10-08` returns 200 with the title and description as above. It now reads "Genentech, a Roche company", with no doubled parentheses.
* `/drug/tecentriq`: one row, "FDA decision · Oct 8, 2026 ✓ Approved". `/drug/atebrioz` also has one row per decision now.
* `/pdufa/RHHBY-tecentriq` reads "decided this application on October 8, 2026, 1 day before its October 9, 2026 goal date".
* `/calendar`, `/fda-this-month`, `/fda-decisions-today` and `/decisions` each link the page.
* The API row is Decided, with its url pointing to the decision page.
