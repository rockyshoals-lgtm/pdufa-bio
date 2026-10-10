# Builder: the held remibrutinib lead was real; Rhapsido SD published, not acked
**2026-10-10, written ~09:25 Pacific = 12:25 Eastern (Saturday). Quarantine and CI times are UTC.** *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

**The lead:** GitHub quarantine notice for `[drug_pages] remibrutinib|openfda:20261006`, held since 2026-10-10T00:27:35Z across 2 consecutive runs.

## Verified, primary sources only

* **openFDA drugsfda** (the FDA's Drugs@FDA data), read live from the builder machine with `last_updated` 2026-10-09:
  * NDA218436, NOVARTIS, **SUPPL-1, AP, 20261006, class EFFICACY**.
  * The letter `218436Orig1s001ltr.pdf` is listed but returned **404** on 2026-10-10. It is listed, not yet served. `sync_fda_action_dates.py` swaps it in once posted.
* **Novartis US media release, October 7, 2026:** the FDA "approved Rhapsido(R) (remibrutinib) ... as the first treatment for adults with symptomatic dermographism (SD) inadequately controlled by H1 antihistamines."
  * RemIND SD cohort: complete response at Week 12, 29.3% vs 14.0% placebo (p=0.0229).
* **CSU approval:** ORIG-1, 2025-09-30 (Drugs@FDA).
* **Dates:** the FDA action day (Oct 6) comes from FDA data; Novartis announced on Oct 7. The page uses the FDA's day and says the announcement came a day later.
* **No goal date is held** → `goal_unsourced`, so no margin.
* **Sources not used:** the web_fetch tool's copies of openFDA and Drugs@FDA were stale (July data), and the first search results were aggregators (HCPLive, AJMC). Neither was used as a source.

## Published

* **Dataset row** (`apply_1010_rhapsido.py`): `pdufa_nvs_2026-10-06`, Decided/Approved, `fda_action_date` 2026-10-06 sourced to the Drugs@FDA overview. `_drug_approvals_confirmed.json` gains remibrutinib.
* **Decision page `/fda-decision/NVS-2026-10-06`** (`decision_pages_2026_10_10_nvs.json`, plus 3 FAQ entries):
  * Title: "Rhapsido (remibrutinib) Approved Oct 6, 2026 for Dermographism | NVS FDA Decision | pdufa.bio" (92 characters).
  * Description: fact-first.
  * FAQPage: 6 questions.
* **`/drug/remibrutinib`** now records the approval: "FDA action · Oct 6, 2026 ✓ Approved". The existing NVS readout row (Jun 2027, an unconfirmed trial estimate) is unchanged.

## Checks

* `watch_drug_approvals.py` re-run locally: **0 unreviewed leads**.
* Guards: 131 pass. Two failures, both resolved:
  * `test_sls_activity`: the collector runs in CI.
  * `test_sponsor_caveat_rendered`: my local `build_pdufa_ticker_index` ran after the caveat injector. Re-running `inject_sponsor_caveat.py` made it OK; CI's order is correct.
* Local `_held_state.json` was cleared with an empty-leads collect (`--no-issue`, outbox to a file, nothing sent), so `quarantine apply` would not restore the drug page.

## Watcher note

The drug-page watcher reported `oncology page BLIND` this run, meaning the FDA oncology notifications page was unreadable from the builder machine. The other passes read. If CI also reports it blind, that is a separate issue.
