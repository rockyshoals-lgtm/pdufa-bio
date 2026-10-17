# Builder note: decided event pages say decided (title, description, no Event); brand-first decision titles; the 15:04 UTC "failure" explained and fixed
**2026-10-17, work 15:15 to 16:30 Pacific = 18:15 to 19:30 Eastern = 22:15 to 23:30 UTC (Saturday).** *RULE 1.*
*Facts only. Not investment advice.* Responds to the audit of 2026-10-17 (measured 17:45 to 18:05 Eastern).

## 0. The failed run of 15:04 UTC (11:04 Eastern), run 39043463353
**The deploy was not broken.** Live served c975628da, built 15:11:18 UTC, on every pass. The failing step was the post-deploy verifier: "/build-info.json pass2: body differs from pass 1".
- `/build-info.json` is computed per request (`api/build-info.mjs`) and carries `served_at`. Any edge cache MISS (pass 2 came from edge cle1, the others from sfo1) returns a new body.
- Three requests tonight, all MISS, differed **only** in `served_at`.
- **Fix:** `verify_live_deploy.py` compares build-info across passes with `served_at` removed. Commit, `built` and every other field must still match. Against live tonight: PASS.

**David: the same run warns `VERCEL_TOKEN does not authenticate (Error: User not found.)`.** The post-push CDN purge is therefore not running. Re-create the token at vercel.com/account/tokens and update the repo secret. The verifier still confirms live matches each deploy, but stale edge copies are no longer purged.

## 1. Decided event pages (audit 2a): the audit's 8, and more
Local sweep before the fix, over 27 indexable decided event pages:
- **10** pending-tense descriptions. The audit's 8 (IRD, RHHBY-enspryng, IBRX, INCY, MIRM, BAYRY-sevabertinib, NUVB, SRRK), plus IONS, LNTH and NUVL in a "FDA PDUFA date is Sep 22 2026 for …" form the audit's pattern did not match.
- **25** pages with an Event schema carrying `EventScheduled`.
- 1 pending title (IRD / VTRS).

**Root cause.** `mark_event_pages_decided.py` rewrote title and description only in the pass that matched a single-ticker "PDUFA date:" title. Pages retitled earlier, partner pages ("IRD / VTRS") and other description templates were never revisited, and nothing touched the Event.

**New step `fix_decided_event_meta.py`** runs right after `mark_event_pages_decided.py` (CI and chain). It reads each DECBAN's decision link and its dataset row:
- **Title:** while it still reads "PDUFA date:", or leads with a development code, or says "Approval announced" over an FDA-recorded day, it becomes "{tickers} FDA decision: {drug}, {Approved | Approval announced | Complete Response Letter} {day}".
- **Description, og: and twitter: copies:** while in the pending tense, rewritten to 120 to 155 characters:
  - "{drug} was approved by the FDA on {FDA day} … The PDUFA goal date was {goal}." when the FDA day is on record;
  - "Approval of {drug} … was announced on {day} … The FDA's action day is not yet on record." when it is not;
  - a goal date only when it is day-precision and sourced, and a CRL always as a Complete Response Letter.
- **Event schema:** every Event object removed, including the two older `/pdufa/{TICKER}` pages (ROIV, TAK).

Examples now:
- `/pdufa/IBRX-anktiva`: "Anktiva (nogapendekin alfa inbakicept) was approved by the FDA on October 14, 2026. The PDUFA goal date was January 6, 2027."
- `/pdufa/IRD-phentolamine-ophthalmic`: title "IRD / VTRS FDA decision: RYZUMVI (phentolamine), Approval announced October 16, 2026".

**The banner over-claimed too.** RYZUMVI's and Enspryng's said "the FDA decided this application on October 16 / 15", an FDA action day we do not hold. `mark_event_pages_decided.py` now writes "approval was announced on {day}; the FDA's own record of the action day is not yet posted" when the decision date is unsourced.

**Development codes and bare INNs gave way to the brand** named on each decision page:
ION373 → Zanvastro, MK-6240 → TAUKLARIFY, NVL-520 → JIDEYTRO, DTX401 → GENGLYCOS, sevabertinib → HYRNUO, apitegromab → ISEMBYLD, garetosmab → Pasatru, brepocitinib → LISRAYA, tavapadon → JUVMO. Not changed: VTRS's MR-100A-01, whose decision page itself names only the code. That is the one open case.

**Guard `test_decided_event_pages_meta.py`:**
- fails on a pending-tense title or description (any of the three carriers), on any Event in a decided page's JSON-LD, or on a banner stating an FDA day the record does not hold;
- clean: OK on 42 decided event pages;
- plants `desc`, `event` and `banner` each FAIL;
- `fix_decided_event_meta.py` is idempotent (second run: 0 pages changed).

## 2. Brand-first decision titles (audit 2b)
`rewrite_decision_snippets.py`: when the row records the approved brand, the title leads with it, never a development code:
- `IRD-2026-10-16`: "Phentolamine ophthalmic solution Approval Announced …" → "RYZUMVI (phentolamine) Approval Announced Oct 16, 2026 for Presbyopia".
- `VTRS-2026-10-16`: "MR-141 Approval Announced …" → "RYZUMVI Approval Announced Oct 16, 2026 for Presbyopia". The INN is dropped to stay under 100 characters.

Both descriptions are 154 characters: "Opus Genetics announced Oct 16, 2026 that the FDA approved RYZUMVI (phentolamine 0.75%) for presbyopia, based on VEGA-2 and -3; Viatris holds U.S. rights."

`test_decision_titles_clean.py` now also fails when an approved row with a recorded brand has a decision title without it. That covers 16 rows; the planted "MR-141 …" title fails.

**Live check after deploy (bf78014, 23:00 UTC) caught one more:**
- CI's `fix_meta_lengths.py` regenerated both RYZUMVI decision descriptions to a 106-character label ("Opus Genetics (IRD) FDA decision Oct 16, 2026: Approved. RYZUMVI (phentolamine ophthalmic solution) 0.75%.").
- Cause: it keeps only descriptions it recognises as answer format, and "… announced Oct 16, 2026 that the FDA approved …" was not one of its patterns.
- Locally the step had skipped the new page, which is not in the `--no-state` lastmod file. That is the same blind spot as `test_meta_lengths` on 10-17.
- **Fix:** the pattern now recognises the form. Reproduced on CI's tree: the old code produces the label, the new code keeps the sentence.
- **Guard:** `test_decision_titles_clean.py` now also requires every row's `seo_desc` (158 characters or fewer) to be its decision page's description. 5 rows are covered, and the planted label fails.

**Also corrected in this push:** an earlier commit (8de058d) was blocked by `test_dropbox_index_complete`. It shipped `INDEX.md` listing the auditor's two 10-17 notes without the notes themselves; bf78014 adds them.

## 3. Enspryng and RYZUMVI FDA days (audit item 3): ready, nothing to swap yet
`sync_fda_action_dates.py` runs in every CI build and re-checks all three rows (`_fda_action_state.json` checked 2026-10-17: ENSPRYNG/SATRALIZUMAB, RYZUMVI/PHENTOLAMINE, result none). openFDA `last_updated` is still 2026-10-16.

When a letter posts within 10 days before the announcement date, the script:
1. writes `fda_action_date` and clears `decision_date_unsourced`;
2. then the title builder leads with "Approved {FDA day}" and the banner states the FDA day with its margin;
3. the statistic admits the row, so goal Oct 15 vs the Enspryng letter, and goal Oct 17 vs the RYZUMVI letter, enter in the same build.

## 4. Daily hubs to Bing (audit item 4)
**CI log, run 39036381484 (13:23 UTC):**
- submission order put `/fda-decisions-today` 2nd and `/fda-approval-decisions-this-week` 3rd;
- "Bing SubmitUrlBatch: HTTP 200 for 40 URL(s)";
- "IndexNow (Bing direct): HTTP 200 for 647 URL(s)".

So the two hubs are **accepted** each run, not just queued. Re-crawling and re-grounding is Bing's call, which is why Request indexing is the lever.

Both hubs already carry a `dateModified` (and `article:modified_time`) from the day's real content change (2026-10-17T01:07 Eastern). Their robots meta now adds `max-snippet:-1`.

## 5. Bepirovirsen (GSK, goal Monday 2026-10-26)
- The GSK media RSS is live and current (ESMO and ViiV items tonight).
- Ionis's IR site returns 403 to every feed URL, so Ionis is covered only through EDGAR 8-Ks.
- Watch from Friday 10-23; same runbook as Enspryng and RYZUMVI.

## Carried, still David's
- Bing Request indexing: `/fda-decisions-today`, `/fda-approval-decisions-this-week`, `/fda-decision/RHHBY-2026-10-15`, `/fda-decision/IRD-2026-10-16`.
- **VERCEL_TOKEN.**
- Restart the 9realms MCP.
- CI `SEC_USER_AGENT` empty.
- `goal_date_held`; Jaypirca SUPPL-5; RXC-005; SMTP; Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; the 20 nct-mismatch readouts; the 131 registry rows.
- VTRS's MR-100A-01 brand: its decision page names only the code. A primary source for the marketed name is needed before retitling.
