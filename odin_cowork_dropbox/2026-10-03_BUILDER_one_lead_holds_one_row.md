# Builder, 10-03: JUVMO published, three false leads acked, and a lead now holds one row instead of the whole site
**2026-10-03, written ~12:30 Pacific = 15:30 Eastern = 19:30 UTC.** *RULE 1: every time below carries its zone. Facts and file contents only; not investment advice.*

Reply to the consolidated BUILDER ORDER of 10-03. Tier 0 and all of Tier 1 are done and guarded. From Tier 2, items 2.3, 2.5 and 2.7 are done; the rest is open (section 5). The live result is in section 6, appended after the deploy.

---

## 1. Tier 0: the queue, verified one by one

| lead | verdict | evidence read 2026-10-03 | action |
|---|---|---|---|
| ABBV tavapadon | **REAL** | openFDA (last_updated 2026-10-02): NDA 220415, ABBVIE INC, brand JUVMO, ORIG-1 AP **20260925**, review class TYPE 1, letter `220415Orig1s000ltr.pdf`. AbbVie release dated Sept. 28, 2026 (PR Newswire): "first and only selective D1/D5 receptor agonist ... for the treatment of adults with Parkinson's disease"; U.S. availability expected October 2026 | `apply_1003_juvmo.py`: row `pdufa_abbv_2026-12-31` Decided / Approved, dcd 2026-09-28 (first public day, as for Lipfendra and WINREVAIR), `fda_action_date` 2026-09-25 with the letter as source, `goal_unsourced` (AbbVie never published a goal date), so no margin. Page `/fda-decision/ABBV-2026-09-28`, whose first sentence is "JUVMO (tavapadon) was approved by the FDA on September 25, 2026 for Parkinson's disease in adults (NDA 220415)". The key-facts card shows the FDA decision date (09-25) and the announcement date (09-28) on separate lines |
| AGIO mitapivat | non-event | NDA 216196 SUPPL-7 AP 2026-09-28, class **MANUF (CMC)** | acked in `_fda_watch_ack.json` |
| RHHBY giredestrant + everolimus | false | **ANDA 220597**, NOVITIUM PHARMA, generic everolimus, ORIG-1 AP 2026-09-21 | acked in `_fda_watch_ack.json` |
| RHHBY Enspryng | false | the FDA notice is "FDA Approves First Treatment for MCT8 Deficiency": Emcitate (tiratricol), granted to Egetis, Mon 09-28 at 17:43 Eastern. The watcher matched it on the single word "thyroid" | acked in `_fda_drugs_feed_ack.json`, which did not exist until now |

Two more things this turned up:

- **The drug-page watch was holding a fourth lead that no issue named:** `/drug/tavapadon [openfda:20260925]`. It is now in `_drug_approvals_confirmed.json` (JUVMO, 2026-09-25, the letter).
- **Atebrioz re-entered the timing study on its own (2.7 confirmed).** On today's chain, `sync_fda_action_dates.py` matched NDA 221198 ORIG-1 AP 2026-09-25 for both MIRM and INCY ("re-admitted"). The FDA letter dates the approval to Friday 09-25 and Mirum's 8-K gives the goal as Saturday 09-26, so both dates are on documents and the page now states the approval came 1 day before the goal date. No code change was needed; the re-check that went in on 09-26 did it.

## 2. Why one correct refusal froze everything for six days

Three of the four leads were matcher bugs, and each has a named cause:

- **The AGIO CMC supplement passed the class filter.** The filter listed `"MANUFACTURING (CMC)"`, but openFDA spells the class `"MANUF (CMC)"`. My 09-01 stoplist never matched the string the API actually returns.
- **The everolimus generic came from the parenthetical.** The Drugs@FDA query took the generic from the row name "Giredestrant (+ everolimus)", so it searched for the combination partner. Nothing excluded ANDAs.
- **The "thyroid" match came from a parenthetical too.** The feed matcher split "(thyroid eye disease)" into single words and accepted any one of them.

The fourth lead was real. All four failed the job, and each failure opened another identical issue: 17 of them, #2 to #18.

## 3. Tier 1, item by item (every guard proved 0, then planted, then 0)

**1.3 Matcher rules** (`watch_fda_approvals.py`, `watch_sponsor_newswire.py`, which the FDA drugs feed shares, and `watch_drug_approvals.py`):

- (a) an application number starting ANDA never matches;
- (b) the class filter matches by substring (LABEL, MANUF, CMC, REMS, PACKAG, BIOEQUIV), so openFDA's spelling cannot slip past it again;
- (c) a parenthetical starting with "+", "plus", "with", "and" or "in combination" is never a search or match term;
- (d) a parenthetical of two or more words matches only as the whole phrase, and a fixed list of 50 organ and tissue words is never a match term on its own.

Guard `tests/test_matcher_rules_replay.py` runs the real leads as they stood:

- AGIO SUPPL-7, ANDA 220597 and the MCT8 notice against the Enspryng row: 0 leads;
- the AbbVie headline against the pre-publication tavapadon row: 1 lead;
- the NDA 220415 ORIG-1 TYPE 1 record still counts as a decision.

Proof: 0 failures, then 6 failures against the HEAD matchers, then 0.

**1.1 Quarantine, not blockade** (`quarantine_leads.py`, plus the workflow):

- The four watchers now run in one step that cannot fail the job. Each writes its leads as JSON lines to `$WATCH_LEADS_JSONL`.
- A watcher that crashes without writing a lead is logged as a `::warning::` that says BLIND, never as a lead.
- `quarantine_leads.py collect` records the leads in `_held_state.json`, which CI now commits.
- `quarantine_leads.py apply` runs after every page is built and before the CI guards. For each held row it restores, from the last commit, three things: that row in `api/v1/dataset.mjs`, its `/pdufa/` page and its `/ticker/` hub. For a drug-page lead it restores that `/drug/` page. Everything else rebuilds and deploys.
- A held row stays exactly as it was last published. Nothing is published automatically.

Guard `tests/test_quarantine_not_blockade.py` fails in any of these cases:

- a workflow step that runs a watcher can still fail the job (`exit $rc`, or no `WATCH_LEADS_JSONL`);
- the collect or apply step is missing, or apply runs after the guards;
- the rendered `build-info.json` or `api/_build-info.json` lacks `held_since` or `held_leads`, or the two disagree;
- `restore_rows` touches a row other than the held one.

Proof, two plants:

- a held lead with `held_since` null in the rendered build-info: 0, then FAIL, then 0;
- `exit $rc` put back on the watcher step: 0, then FAIL, then 0. The first version of this guard missed this plant, because it only looked for steps reading `python watch_x.py` literally and the new step loops over the names. I fixed the guard before trusting it.

**1.2 Escalation:**

- The issue is opened **once per new lead**, not once per run.
- After the **2nd** consecutive held run, one email is sent, and the streak resets on the first clean run.
- `held_since` and `held_leads` are now in `/build-info.json`.

Guard `tests/test_escalation_replay.py` replays the 17 runs, using each issue's createdAt (UTC) and the leads it carried. Result:

- held_since 2026-09-28T17:56:34Z throughout the streak;
- exactly one email, at the second run (2026-09-28T19:21:28Z);
- 4 issues, not 17;
- a clean run resets the streak.

Proof: 0, then 2 failures (escalate after 1 run, no de-duplication), then 0.

**The email has no SMTP secret to send through.** `gh secret list` shows BING_WEBMASTER_API_KEY, FMP_API_KEY, GSC_SERVICE_ACCOUNT_JSON, POLYGON_API_KEY and VERCEL_TOKEN, and no SMTP secret. The order says "SMTP secret in Actions", but none exists, and `test_workflow_valid` rightly rejects references to secrets that do not exist. So the code sends real mail when SMTP_HOST, SMTP_USER and SMTP_PASS are set. Until then it escalates by opening an issue that @-mentions `rockyshoals-lgtm`, which GitHub emails to the owner by default. Adding the secrets and mapping them in the step is in "For David".

**1.4 `data_built_at`:**

- `build_freshness_stamp.py` writes `data_built_at` into build-info.
- `api/v1/_lib.mjs` serves `meta.data_built_at` next to `meta.as_of`, in both the normal response and the stale-cache response, read from `api/_build-info.json`.
- Every freshness stamp, home and /calendar included, gains a `data-fresh-built` slot that the existing script fills from `data_built_at`, as "data rebuilt Oct 3, 3:10 PM ET".
- The slot is empty in the static HTML, so page bytes stay constant from build to build and lastmod does not churn.

Guard `tests/test_data_built_at.py` checks the rendered build-info, the API library and the rendered home and /calendar. Proved twice (stamp slot removed; `data_built_at` removed from `api/_build-info.json`): 0, then FAIL, then 0.

**1.5 Request-time statuses:**

- `liveStatus(e, today)` in `_lib.mjs` computes Conference Ended / In progress / Scheduled from `d` and `_d.end`, and PDUFA Awaiting, from the **Eastern** calendar day of the request.
- `shape()` serves it, and `?status=` filters on it.
- `days_to_decision` was also counted from the **UTC** day. It now uses the Eastern day (RULE 1): from 20:00 Eastern the UTC date is already tomorrow.

On 10-03 the served statuses are now: AACR-PANC In progress → Ended, ASTRO In progress → Ended, EASD Scheduled → Ended, WMS Scheduled → In progress. Those are exactly the four the order named.

Guard `tests/test_request_time_status.py` runs the API's own code under node for 129 Conference and PDUFA rows on four Eastern dates. Proof: 0, then 37 failures with liveStatus disconnected, then 0.

## 4. Tier 2 items done on the way

- **2.3 Brand alias in the same run.** Renaming the row to "JUVMO (tavapadon)" made `build_drug_pages.py` key the page on the brand: it **deleted the indexed `/drug/tavapadon`** and created `/drug/juvmo`, and `test_drug_pages_state_approvals` caught it.
  - Rule now: a published drug URL never moves because a brand was assigned. When the brand has no page and the generic does, the row stays on the generic page.
  - The generic page now names the brand: "JUVMO (tavapadon)" in its h1, title and description, plus a sentence saying JUVMO is the brand name.
  - The page also dates the approval by the FDA's letter date. It said "FDA approved on September 28" until I made it read the FDA action date, and it now says September 25.
- **2.5 "0 press items scanned".** The drug-page watch now prints and records in `_watch_health.json` for each pass:
  - press RSS: items, how many fall in the window, bodies read, body fetches that failed;
  - the oncology page: read or BLIND;
  - openFDA: read or BLIND.

  A zero now means "nothing new", never "could not read". I have not yet seen a CI line to say which it was on 09-27. The next run's line will show it.
- **2.7** confirmed: see section 1.

## 5. Open, in order

**Tier 2:**

- **2.1 Fact-first lede on every Approved page.** 1 of 126 approved decision pages leads with the fact today, and that one is JUVMO. Many of the others carry truncated indications, for example "functional constipation (FC) in patients 2 to 5 ye.", so the honest version is to do it first for the 42 rows that have an FDA record, then fix the truncation (#65) before doing the rest.
- **2.2** the running count of novel approvals.
- **2.4** MRK coverage through 8-K polling. RHHBY is already covered by the FDA drugs feed, which read 20 items from this machine today.
- **2.6** the Gazyva idiopathic nephrotic syndrome page.

**Tier 3** (3.1 and 3.2 partly, through the FDA-date changes above) **and Tier 4** are carried.

**Issues #2 to #18** are closed with one line each once the run is green (section 6).

## For David

1. **Who reads the alert:** add SMTP_HOST, SMTP_USER and SMTP_PASS (optionally SMTP_PORT and ALERT_TO) as Actions secrets and tell me. I will map them in the quarantine step and add them to `test_workflow_valid`'s known list. Until then the escalation is an @-mention issue.
2. The other items on your list are unchanged: the Google Drive exclusion, the AZN Ultomiris / NVO CagriSema / NVO Mim8 rows, and the Bing sign-in.

## Files

New:

- `apply_1003_juvmo.py`, `decision_pages_2026_10_03_abbv.json`
- `quarantine_leads.py`
- `_fda_drugs_feed_ack.json`, `_newswire_ack.json`
- `tests/test_matcher_rules_replay.py`, `tests/test_quarantine_not_blockade.py`, `tests/test_escalation_replay.py`, `tests/test_data_built_at.py`, `tests/test_request_time_status.py`
- `_verify_live_1003.py`, `_prove_1003.py`

Changed:

- the four watchers;
- `build_decision_page.py`, `build_drug_pages.py`, `build_freshness_stamp.py`, `pdufa_site_src/api/v1/_lib.mjs`;
- `.github/workflows/pdufa-rebuild.yml`, `_chain_0919.bat`;
- `_fda_watch_ack.json`, `_drug_approvals_confirmed.json`.

Local guards: **115 pass, 0 fail.**

## 6. Appended ~12:55 Pacific = 15:55 Eastern = 19:55 UTC: green, live, issues closed, and one more fix

**CI is green.** Dispatched run 37148030700 started 19:28:45 UTC and completed with `success`, the first green run since 2026-09-27. The commit was 580b20c73. The watcher lines from that run:

- `early-approval watch: 37 armed events ... 0 unreviewed approvals (5 previously reviewed)`
- `FDA drugs feed: 20 item(s) read; 0 unreviewed lead(s)`
- `sponsor-feed watch: 32 armed sponsor(s); 7 with a news feed (7 read this run)`
- `quarantine: 0 leads this run; nothing held`

**2.5 is now answered by the new line.** The run printed `drug-page watch passes: press RSS 0 item(s) ... oncology page BLIND; openFDA read -- BLIND: fda_press_rss, fda_oncology_notifications`. So "0 press items scanned" meant "could not read", not "nothing new": the drug-page watch's two fda.gov passes are blind on the runner. In the same run, the FDA drugs-feed pass read 20 items from fda.gov using a different User-Agent. My **hypothesis, not proven**, is that fda.gov refuses the anonymous UA. The drug-page watch now uses the UA that works, and the next run's line will confirm or refute it.

**Issues #2 to #18 are closed**, each with a one-line reason:

- #2, #3, #5, #6: REAL, JUVMO, published;
- #4: FALSE, MCT8 notice matched on "thyroid";
- #7 to #18: FALSE, AGIO CMC supplement and/or Novitium's generic everolimus ANDA.

**The live check found one fail, which is fixed in this commit.** `_verify_live_1003.py` on 4da0c4fa1 passed 15 of 16 items. The one fail was `/pdufa/ABBV-tavapadon`: its title read "Tavapadon, Approved September 28, 2026" (AbbVie's release day) over a banner that correctly said "the FDA decided this application on September 25, 2026 (FDA record; announced September 28, 2026)". The title also lacked the brand.

- **Fix:** `mark_event_pages_decided.py` now writes the FDA's action date into the title, sub line and key fact wherever the row has one, and adds the brand to the title and h1 in the same run. It now reads "ABBV FDA decision: JUVMO (Tavapadon), Approved September 25, 2026".
- **Guard:** `tests/test_event_page_fda_date_brand.py`. Proof on the rendered page: the pre-fix page gave 2 failures, then 0 after the fix; the old title planted back gave FAIL; restored gave 0.

Local guards now **116 pass, 0 fail**. The final live result is in the next commit's verifier run (`_verify_live_1003.py`).

## 7. Appended ~13:20 Pacific = 16:20 Eastern = 20:20 UTC: live ALL PASS, and the 2.5 hypothesis is confirmed

- **Run 37148737049** (commit ce5799c42) completed `success`, the second green run in a row.
- **`_verify_live_1003.py` passes all 16 checks** on ce5799c42:
  - build-info built today, with `data_built_at`, `held_since` null and `held_leads` [];
  - `/pdufa/ABBV-tavapadon` reads Approved, JUVMO;
  - `/fda-decision/ABBV-2026-09-28` is fact-first and cites the NDA 220415 letter;
  - the API row is Decided / Approved with `fda_action_date` 2026-09-25 and `meta.data_built_at`;
  - AACR-PANC, ASTRO and EASD are Ended and WMS is In progress;
  - `/fda-approval-letters` lists NDA 220415;
  - the home and /calendar stamps read `data_built_at`;
  - `/drug/tavapadon` is live and names JUVMO.
- **2.5 hypothesis confirmed.** With the User-Agent changed, the same run printed `drug-page watch passes: press RSS 20 item(s), 9 in the 21-day window, 9 bodies read, 0 body fetch(es) failed; oncology page read; openFDA read`. The "0 press items scanned" line was fda.gov refusing that pass's anonymous User-Agent on the runner. It was not an empty window.
